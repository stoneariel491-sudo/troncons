// traceur.cpp : relève, jeton par jeton et couche par couche, les experts choisis par le routeur
// d'un modèle MoE (écrit pour gpt-oss) en faisant tourner llama.cpp b11515 tel quel.
//
// Pourquoi ce chemin plutôt que de compiler l'exemple « eval-callback » de llama.cpp :
//   - la trace vient alors du MÊME moteur, des MÊMES DLL que la base mesurée (llama.cpp b11515,
//     binaires CUDA 12.4 officiels) : les experts relevés sont ceux que la base lit vraiment ;
//   - rien n'est copié de llama.cpp : ce programme n'utilise que son interface publique
//     (include/llama.h, ggml/include/ggml*.h, licence MIT), comme une bibliothèque ;
//   - une seule unité de compilation, construite en quelques secondes avec MSVC.
//
// Le mécanisme : llama_context_params.cb_eval est le rappel que l'ordonnanceur de ggml appelle
// pour chaque nœud du graphe (ask = vrai : « voulez-vous ce tenseur ? » ; ask = faux : le tenseur
// est calculé, on peut le lire). La construction du MoE nomme ses nœuds (src/llama-graph.cpp,
// build_moe_ffn, lu dans les sources de b11515) :
//   ffn_moe_probs-<il>          F32 [n_expert, n_jetons]  scores du routeur ; pour gpt-oss (porte
//                               SOFTMAX_WEIGHT) c'est le tenseur même des logits biaisés : le
//                               rappel de nommage le renomme « probs » après « logits_biased »
//                               (premier essai : « ffn_moe_logits_biased » n'arrive jamais au rappel) ;
//   ffn_moe_argsort-<il>        I32 [n_expert, n_jetons]  experts triés par score décroissant ;
// le top-k de llama.cpp est la vue des k premières colonnes de ce tri. On lit les deux :
//   - les k premiers indices du tri = les experts que llama.cpp a choisis (la trace) ;
//   - un second chemin, indépendant : notre propre top-k sur les logits biaisés. Les deux doivent
//     donner le même ensemble (témoin interne, compté et publié) ; les poids de mélange de gpt-oss
//     sont le softmax des k logits retenus (LLAMA_EXPERT_GATING_FUNC_TYPE_SOFTMAX_WEIGHT).
//
// Deux modes, par texte :
//   lecture    : le texte entier passe en un seul lot (le modèle lit un texte réel, chaque jeton
//                voit le vrai texte qui le précède) ;
//   generation : les P premiers jetons du texte servent d'invite, puis N jetons gloutons sont
//                produits un par un (lot de 1, le régime du décodage) ; ensuite la suite
//                invite + produits est relue en un seul lot, et l'on compte, pour les jetons
//                produits, la part des choix (jeton, couche) identiques entre décodage et relecture
//                (témoin de la sensibilité numérique du routage au chemin de calcul).
//
// Sorties (préfixe P, étiquette E) :
//   P.E.lecture.trace     format de outils/chargement_localite.py (« E=… », une ligne par jeton,
//                         couches séparées par « | », experts par des espaces, ordre du score) ;
//   P.E.lecture.poids     même disposition, poids de mélange (4 décimales) ;
//   P.E.generation.trace / .poids, P.E.generation.jetons (identifiants), P.E.generation.txt ;
//   P.resume.json         comptes, témoins, temps.
//
// Usage :
//   traceur --dll-dir <dossier b11515> --modele m.gguf --prefixe P --ctx 4096 --lot 1024 --ngl 99
//           [--cpu-moe] [--moe-cache-mib M] [--threads 6] [--invite 256] [--generer 256]
//           --texte etiquette=chemin [--texte …]

#include "llama.h"
#include "ggml.h"
#include "ggml-backend.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

// Ce que le rappel accumule pendant un appel à llama_decode, couche par couche.
struct Releve {
    int n_couches = 0;
    int n_experts = 0;
    int k = 0;
    std::vector<std::vector<int32_t>> choix;      // [couche] -> k indices par jeton (tri de llama.cpp)
    std::vector<std::vector<int32_t>> choix_maison; // [couche] -> k indices par jeton (notre top-k)
    std::vector<std::vector<float>>   poids;       // [couche] -> k poids par jeton
    std::vector<char> tampon;
    long long tenseurs_lus = 0;
    long long non_contigus = 0;

    void vider() {
        for (auto & v : choix) v.clear();
        for (auto & v : choix_maison) v.clear();
        for (auto & v : poids) v.clear();
    }
};

// vrai si le nom est exactement « préfixe » suivi d'un numéro de couche (les vues dérivées, par
// exemple « ffn_moe_probs-0 (reshaped) », sont écartées : premier essai, elles passaient)
bool commence_par(const char * s, const char * p) {
    const size_t n = std::strlen(p);
    if (std::strncmp(s, p, n) != 0 || s[n] == 0) return false;
    for (const char * q = s + n; *q; ++q)
        if (*q < '0' || *q > '9') return false;
    return true;
}

const char * ARGSORT = "ffn_moe_argsort-";
const char * LOGITS  = "ffn_moe_probs-";

bool rappel(ggml_tensor * t, bool ask, void * ud) {
    auto * r = static_cast<Releve *>(ud);
    const bool est_tri = commence_par(t->name, ARGSORT);
    const bool est_logits = commence_par(t->name, LOGITS);
    if (ask) {
        return est_tri || est_logits;
    }
    if (!est_tri && !est_logits) {
        return true;
    }
    const int il = std::atoi(std::strrchr(t->name, '-') + 1);
    if (il < 0 || il >= r->n_couches) {
        std::fprintf(stderr, "couche hors bornes : %s\n", t->name);
        return false;
    }
    if (!ggml_is_contiguous(t)) {
        r->non_contigus++;
        return false;  // on ne lit pas un tenseur dont on ne connaît pas la disposition
    }
    const size_t n = ggml_nbytes(t);
    r->tampon.resize(n);
    ggml_backend_tensor_get(t, r->tampon.data(), 0, n);
    r->tenseurs_lus++;
    const int64_t ne0 = t->ne[0];
    const int64_t nj = t->ne[1];
    if (ne0 != r->n_experts) {
        std::fprintf(stderr, "%s : ne0 = %lld, attendu %d experts\n", t->name, (long long) ne0, r->n_experts);
        return false;
    }
    if (est_tri) {
        if (t->type != GGML_TYPE_I32) return false;
        const int32_t * d = reinterpret_cast<const int32_t *>(r->tampon.data());
        for (int64_t j = 0; j < nj; ++j)
            for (int i = 0; i < r->k; ++i) r->choix[il].push_back(d[j * ne0 + i]);
    } else {
        if (t->type != GGML_TYPE_F32) return false;
        const float * d = reinterpret_cast<const float *>(r->tampon.data());
        std::vector<int32_t> idx(ne0);
        for (int64_t j = 0; j < nj; ++j) {
            const float * l = d + j * ne0;
            for (int64_t e = 0; e < ne0; ++e) idx[e] = (int32_t) e;
            // top-k par score décroissant ; à égalité, l'indice le plus petit (choix déclaré)
            std::partial_sort(idx.begin(), idx.begin() + r->k, idx.end(), [&](int32_t a, int32_t b) {
                return l[a] > l[b] || (l[a] == l[b] && a < b);
            });
            float m = l[idx[0]];
            double s = 0.0;
            for (int i = 0; i < r->k; ++i) s += std::exp((double) l[idx[i]] - m);
            for (int i = 0; i < r->k; ++i) {
                r->choix_maison[il].push_back(idx[i]);
                r->poids[il].push_back((float) (std::exp((double) l[idx[i]] - m) / s));
            }
        }
    }
    return true;
}

std::string lire_fichier(const std::string & chemin) {
    std::ifstream f(chemin, std::ios::binary);
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

std::string meta(const llama_model * m, const char * cle) {
    char tampon[256] = {0};
    if (llama_model_meta_val_str(m, cle, tampon, sizeof(tampon)) < 0) return "";
    return tampon;
}

double maintenant() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

// Une passe de relevé (lot unique ou jeton par jeton) : renvoie, pour chaque jeton relevé,
// les k experts de chaque couche, dans l'ordre des jetons.
struct Trace {
    std::vector<std::vector<int32_t>> choix;  // [jeton] -> n_couches * k
    std::vector<std::vector<float>> poids;
};

// Déplace ce que le rappel a relevé dans la trace ; vérifie que chaque couche a le même nombre
// de jetons et compte les désaccords entre le tri de llama.cpp et notre top-k.
bool recolter(Releve & r, Trace & tr, long long & desaccords, long long & comparaisons, long long & ordre_diff) {
    const size_t nj = r.choix[0].size() / r.k;
    for (int il = 0; il < r.n_couches; ++il) {
        if (r.choix[il].size() != nj * r.k || r.choix_maison[il].size() != nj * r.k) {
            std::fprintf(stderr, "couche %d : %zu choix, %zu choix maison, attendu %zu\n", il,
                         r.choix[il].size() / r.k, r.choix_maison[il].size() / r.k, nj);
            return false;
        }
    }
    for (size_t j = 0; j < nj; ++j) {
        std::vector<int32_t> ligne;
        std::vector<float> lp;
        for (int il = 0; il < r.n_couches; ++il) {
            const int32_t * a = &r.choix[il][j * r.k];
            const int32_t * b = &r.choix_maison[il][j * r.k];
            std::vector<int32_t> sa(a, a + r.k), sb(b, b + r.k);
            bool meme_ordre = std::equal(sa.begin(), sa.end(), sb.begin());
            std::sort(sa.begin(), sa.end());
            std::sort(sb.begin(), sb.end());
            comparaisons++;
            if (sa != sb) desaccords++;
            else if (!meme_ordre) ordre_diff++;
            // poids alignés sur l'ordre de llama.cpp (on cherche chaque expert dans notre top-k)
            for (int i = 0; i < r.k; ++i) {
                ligne.push_back(a[i]);
                float w = NAN;
                for (int q = 0; q < r.k; ++q)
                    if (b[q] == a[i]) w = r.poids[il][j * r.k + q];
                lp.push_back(w);
            }
        }
        tr.choix.push_back(std::move(ligne));
        tr.poids.push_back(std::move(lp));
    }
    r.vider();
    return true;
}

void ecrire_trace(const std::string & chemin, const Trace & tr, size_t debut, int n_couches, int k, int E,
                  const std::string & entete) {
    FILE * f = std::fopen(chemin.c_str(), "wb");
    std::fprintf(f, "# %s\nE=%d\n", entete.c_str(), E);
    for (size_t j = debut; j < tr.choix.size(); ++j) {
        for (int il = 0; il < n_couches; ++il) {
            if (il) std::fputs(" |", f);
            for (int i = 0; i < k; ++i) std::fprintf(f, "%s%d", (il == 0 && i == 0) ? "" : " ", tr.choix[j][il * k + i]);
        }
        std::fputc('\n', f);
    }
    std::fclose(f);
}

void ecrire_poids(const std::string & chemin, const Trace & tr, size_t debut, int n_couches, int k) {
    FILE * f = std::fopen(chemin.c_str(), "wb");
    for (size_t j = debut; j < tr.poids.size(); ++j) {
        for (int il = 0; il < n_couches; ++il) {
            if (il) std::fputs(" |", f);
            for (int i = 0; i < k; ++i) std::fprintf(f, "%s%.4f", (il == 0 && i == 0) ? "" : " ", tr.poids[j][il * k + i]);
        }
        std::fputc('\n', f);
    }
    std::fclose(f);
}

void journal_muet(ggml_log_level niveau, const char * texte, void *) {
    // on garde les avertissements, les erreurs et le bilan du cache d'experts
    if (niveau >= GGML_LOG_LEVEL_WARN || std::strstr(texte, "moe_cache") || std::strstr(texte, "MoE cache") || std::strstr(texte, "slots (") || std::strstr(texte, "offload")) std::fputs(texte, stderr);
}

// Passe une suite de jetons par lots de « lot » jetons, positions à partir de « pos0 », en
// demandant la sortie de TOUS les jetons. Raison (mesurée au premier essai) : llama.cpp ne garde
// à la dernière couche que les jetons dont on demande la sortie (élagage avant le FFN de la
// dernière couche) ; avec la sortie du seul dernier jeton, la couche 23 de gpt-oss-20b ne
// relevait qu'un jeton sur 383. Les lots bornent le tampon des logits (lot × 201 088 × 4 octets).
bool passer(llama_context * c, const llama_token * t, int n, int pos0, int lot) {
    llama_batch b = llama_batch_init(lot, 0, 1);
    for (int d = 0; d < n; d += lot) {
        const int m = std::min(lot, n - d);
        b.n_tokens = m;
        for (int i = 0; i < m; ++i) {
            b.token[i] = t[d + i];
            b.pos[i] = pos0 + d + i;
            b.n_seq_id[i] = 1;
            b.seq_id[i][0] = 0;
            b.logits[i] = 1;
        }
        if (llama_decode(c, b) != 0) {
            llama_batch_free(b);
            return false;
        }
    }
    llama_batch_free(b);
    return true;
}

}  // namespace

int main(int argc, char ** argv) {
    std::string dll_dir, modele, prefixe;
    std::vector<std::pair<std::string, std::string>> textes;
    int ctx = 4096, ngl = 99, threads = 6, invite = 256, generer = 0, lot = 1024, cache_mio = 0;
    bool cpu_moe = false, bavard = false, op_offload = true;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto suivant = [&]() { return std::string(argv[++i]); };
        if (a == "--dll-dir") dll_dir = suivant();
        else if (a == "--modele") modele = suivant();
        else if (a == "--prefixe") prefixe = suivant();
        else if (a == "--ctx") ctx = std::atoi(argv[++i]);
        else if (a == "--ngl") ngl = std::atoi(argv[++i]);
        else if (a == "--threads") threads = std::atoi(argv[++i]);
        else if (a == "--invite") invite = std::atoi(argv[++i]);
        else if (a == "--generer") generer = std::atoi(argv[++i]);
        else if (a == "--lot") lot = std::atoi(argv[++i]);
        else if (a == "--moe-cache-mib") cache_mio = std::atoi(argv[++i]);
        else if (a == "--cpu-moe") cpu_moe = true;
        else if (a == "--sans-op-offload") op_offload = false;
        else if (a == "--bavard") bavard = true;
        else if (a == "--texte") {
            std::string v = suivant();
            const size_t p = v.find('=');
            textes.emplace_back(v.substr(0, p), v.substr(p + 1));
        } else {
            std::fprintf(stderr, "argument inconnu : %s\n", a.c_str());
            return 2;
        }
    }
    if (modele.empty() || prefixe.empty() || textes.empty()) {
        std::fprintf(stderr, "usage : voir l'en-tête de traceur.cpp\n");
        return 2;
    }
    if (!bavard) llama_log_set(journal_muet, nullptr);
    if (!dll_dir.empty()) ggml_backend_load_all_from_path(dll_dir.c_str());
    else ggml_backend_load_all();
    llama_backend_init();

    const double t_debut = maintenant();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = ngl;
    // --cpu-moe : tous les tenseurs d'experts dans un tampon de l'hôte (même règle que l'option
    // du même nom de llama.cpp : motif sur les noms « *_exps ») ; projetés par mmap.
    llama_model_tensor_buft_override surcharges[2] = {{nullptr, nullptr}, {nullptr, nullptr}};
    if (cpu_moe) {
        ggml_backend_dev_t cpu = ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_CPU);
        surcharges[0].pattern = "\\.ffn_(up|down|gate|gate_up)_(ch|)exps";
        surcharges[0].buft = ggml_backend_dev_buffer_type(cpu);
        mp.tensor_buft_overrides = surcharges;
    }
    llama_model * m = llama_model_load_from_file(modele.c_str(), mp);
    if (!m) {
        std::fprintf(stderr, "chargement impossible : %s\n", modele.c_str());
        return 1;
    }
    const double t_charge = maintenant();
    const std::string arch = meta(m, "general.architecture");
    Releve r;
    r.n_couches = llama_model_n_layer(m);
    r.n_experts = std::atoi(meta(m, (arch + ".expert_count").c_str()).c_str());
    r.k = std::atoi(meta(m, (arch + ".expert_used_count").c_str()).c_str());
    r.choix.resize(r.n_couches);
    r.choix_maison.resize(r.n_couches);
    r.poids.resize(r.n_couches);
    std::fprintf(stderr, "architecture %s : %d couches, %d experts, k = %d\n", arch.c_str(), r.n_couches, r.n_experts, r.k);
    if (r.n_experts <= 0 || r.k <= 0) return 1;

    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = ctx;
    cp.n_batch = lot;
    cp.n_ubatch = lot;
    cp.n_threads = threads;
    cp.n_threads_batch = threads;
    cp.cb_eval = rappel;
    cp.cb_eval_user_data = &r;
    cp.no_perf = false;
    // cache d'experts de llama.cpp en VRAM (même option que --moe-cache-mib) : la trace vient alors
    // du même calcul que la base qui l'utilise, et llama.cpp publie son propre taux de succès
    cp.moe_cache_size = (size_t) cache_mio * 1024 * 1024;
    // --sans-op-offload : les grands lots calculent les experts de l'hôte sur le processeur au lieu
    // de les copier vers la carte couche par couche (sur 120b, la copie lit 61 Go par lot par fautes
    // de page à ~170 Mo/s, mesuré : plus de six minutes par lot de 1 024 jetons)
    cp.op_offload = op_offload;
    llama_context * c = llama_init_from_model(m, cp);
    if (!c) {
        std::fprintf(stderr, "contexte impossible\n");
        return 1;
    }
    const llama_vocab * voc = llama_model_get_vocab(m);
    const int n_vocab = llama_vocab_n_tokens(voc);

    std::ostringstream js;
    js << "{\n \"modele\": \"" << modele << "\",\n \"architecture\": \"" << arch << "\",\n \"couches\": " << r.n_couches
       << ",\n \"experts\": " << r.n_experts << ",\n \"k\": " << r.k << ",\n \"ngl\": " << ngl
       << ",\n \"cpu_moe\": " << (cpu_moe ? "true" : "false") << ",\n \"moe_cache_mib\": " << cache_mio
       << ",\n \"ctx\": " << ctx << ",\n \"lot\": " << lot << ",\n \"op_offload\": " << (op_offload ? "true" : "false")
       << ",\n \"chargement_s\": " << (t_charge - t_debut) << ",\n \"textes\": [";

    bool premier = true;
    for (auto & [etiquette, chemin] : textes) {
        const std::string texte = lire_fichier(chemin);
        std::vector<llama_token> jetons(texte.size() + 16);
        int n = llama_tokenize(voc, texte.c_str(), (int32_t) texte.size(), jetons.data(), (int32_t) jetons.size(), true, false);
        if (n < 0) return 1;
        jetons.resize(n);
        if ((int) jetons.size() > ctx) jetons.resize(ctx);
        std::fprintf(stderr, "[%s] %zu jetons\n", etiquette.c_str(), jetons.size());

        long long des = 0, cmp = 0, ord = 0;
        // ---- lecture : tout le texte en un lot ----
        llama_memory_clear(llama_get_memory(c), true);
        Trace lecture;
        double t0 = maintenant();
        if (!passer(c, jetons.data(), (int) jetons.size(), 0, lot)) {
            std::fprintf(stderr, "échec du décodage (lecture %s)\n", etiquette.c_str());
            return 1;
        }
        double t_lecture = maintenant() - t0;
        if (!recolter(r, lecture, des, cmp, ord)) return 1;
        if (lecture.choix.size() != jetons.size()) {
            std::fprintf(stderr, "lecture %s : %zu jetons relevés pour %zu\n", etiquette.c_str(), lecture.choix.size(), jetons.size());
            return 1;
        }
        const std::string entete = "traceur gpt-oss, " + etiquette + ", " + modele;
        ecrire_trace(prefixe + "." + etiquette + ".lecture.trace", lecture, 0, r.n_couches, r.k, r.n_experts, entete + ", lecture");
        ecrire_poids(prefixe + "." + etiquette + ".lecture.poids", lecture, 0, r.n_couches, r.k);
        std::fprintf(stderr, "[%s] lecture : %.1f s (%.1f jetons/s), désaccords tri/top-k %lld sur %lld, ordre différent %lld\n",
                     etiquette.c_str(), t_lecture, jetons.size() / t_lecture, des, cmp, ord);

        js << (premier ? "" : ",") << "\n  {\"etiquette\": \"" << etiquette << "\", \"chemin\": \"" << chemin
           << "\", \"jetons\": " << jetons.size() << ", \"lecture_s\": " << t_lecture
           << ", \"lecture_desaccords\": " << des << ", \"lecture_comparaisons\": " << cmp << ", \"lecture_ordre_different\": " << ord;
        premier = false;

        // ---- génération : invite puis N jetons gloutons, un par un ----
        if (generer > 0) {
            long long gdes = 0, gcmp = 0, gord = 0;
            const int P = std::min<int>(invite, (int) jetons.size());
            std::vector<llama_token> suite(jetons.begin(), jetons.begin() + P);
            llama_memory_clear(llama_get_memory(c), true);
            Trace gen;
            t0 = maintenant();
            if (!passer(c, suite.data(), P, 0, lot)) return 1;
            if (!recolter(r, gen, gdes, gcmp, gord)) return 1;
            const double t_invite = maintenant() - t0;
            t0 = maintenant();
            for (int g = 0; g < generer; ++g) {
                const float * lg = llama_get_logits_ith(c, -1);
                llama_token best = 0;
                for (int v = 1; v < n_vocab; ++v)
                    if (lg[v] > lg[best]) best = v;
                suite.push_back(best);
                if ((int) suite.size() >= ctx) break;
                if (!passer(c, &suite.back(), 1, (int) suite.size() - 1, lot)) return 1;
                if (!recolter(r, gen, gdes, gcmp, gord)) return 1;
            }
            const double t_gen = maintenant() - t0;
            // gen.choix : P jetons d'invite (passés en un lot) + chaque jeton produit, passé seul dans
            // le modèle juste après avoir été choisi. La trace de génération garde les lignes P … fin :
            // le routage de chaque jeton produit quand il entre dans le modèle.
            const size_t n_produits = suite.size() - P;
            if (gen.choix.size() != suite.size()) {
                std::fprintf(stderr, "génération %s : %zu lignes pour %zu jetons\n", etiquette.c_str(), gen.choix.size(), suite.size());
                return 1;
            }
            ecrire_trace(prefixe + "." + etiquette + ".generation.trace", gen, P, r.n_couches, r.k, r.n_experts, entete + ", generation");
            ecrire_poids(prefixe + "." + etiquette + ".generation.poids", gen, P, r.n_couches, r.k);
            {
                FILE * f = std::fopen((prefixe + "." + etiquette + ".generation.jetons").c_str(), "wb");
                for (size_t j = 0; j < suite.size(); ++j) std::fprintf(f, "%d%c", suite[j], j + 1 == (size_t) P ? '\n' : ' ');
                std::fclose(f);
                std::string txt;
                char piece[512];
                for (size_t j = P; j < suite.size(); ++j) {
                    int q = llama_token_to_piece(voc, suite[j], piece, sizeof(piece), 0, true);
                    if (q > 0) txt.append(piece, q);
                }
                f = std::fopen((prefixe + "." + etiquette + ".generation.txt").c_str(), "wb");
                std::fwrite(txt.data(), 1, txt.size(), f);
                std::fclose(f);
            }
            // relecture de invite + produits en un lot : même routage pour les jetons produits ?
            std::vector<llama_token> relu(suite.begin(), suite.end());
            llama_memory_clear(llama_get_memory(c), true);
            Trace rel;
            long long rdes = 0, rcmp = 0, rord = 0;
            if (!passer(c, relu.data(), (int) relu.size(), 0, lot)) return 1;
            if (!recolter(r, rel, rdes, rcmp, rord)) return 1;
            long long memes = 0, total = 0, jetons_identiques = 0;
            for (size_t j = P; j < relu.size() && j < gen.choix.size(); ++j) {
                bool tout = true;
                for (int il = 0; il < r.n_couches; ++il) {
                    std::vector<int32_t> a(gen.choix[j].begin() + il * r.k, gen.choix[j].begin() + (il + 1) * r.k);
                    std::vector<int32_t> b(rel.choix[j].begin() + il * r.k, rel.choix[j].begin() + (il + 1) * r.k);
                    std::sort(a.begin(), a.end());
                    std::sort(b.begin(), b.end());
                    total++;
                    if (a == b) memes++;
                    else tout = false;
                }
                if (tout) jetons_identiques++;
            }
            std::fprintf(stderr, "[%s] génération : %zu jetons en %.1f s (%.2f jetons/s), invite %.1f s ; relecture : %lld/%lld choix (jeton, couche) identiques, %lld jetons entièrement identiques\n",
                         etiquette.c_str(), n_produits, t_gen, n_produits / t_gen, t_invite, memes, total, jetons_identiques);
            js << ", \"invite\": " << P << ", \"produits\": " << n_produits << ", \"generation_s\": " << t_gen
               << ", \"invite_s\": " << t_invite << ", \"generation_desaccords\": " << gdes << ", \"generation_comparaisons\": " << gcmp
               << ", \"relecture_choix_identiques\": " << memes << ", \"relecture_choix_total\": " << total
               << ", \"relecture_jetons_identiques\": " << jetons_identiques << ", \"relecture_jetons_total\": " << (relu.size() - P);
        }
        js << "}";
    }
    js << "\n ],\n \"tenseurs_lus\": " << r.tenseurs_lus << ",\n \"non_contigus\": " << r.non_contigus
       << ",\n \"duree_totale_s\": " << (maintenant() - t_debut) << "\n}\n";
    FILE * f = std::fopen((prefixe + ".resume.json").c_str(), "wb");
    const std::string s = js.str();
    std::fwrite(s.data(), 1, s.size(), f);
    std::fclose(f);
    llama_free(c);
    llama_model_free(m);
    return 0;
}
