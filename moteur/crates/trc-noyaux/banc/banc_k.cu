// Banc du lot K (étapes K1 et K2) : témoins, cassures et débits des noyaux du moteur,
// sur les poids réels de gpt-oss, par un chemin indépendant des lots F et E.
//
// Pourquoi un banc en C++ (API d'exécution de CUDA) plutôt qu'en Rust : le crate
// trc-noyaux lance ses noyaux par trc-cuda (lot E) et se juge contre trc-codec (lot F),
// qui s'écrivent en même temps que lui. Ce banc inclut les mêmes sources de noyaux, mot
// pour mot (noyaux/*.cuh), et code lui-même les tronçons à partir du seul texte du § 4
// de decisions/ARCHITECTURE.md. C'est donc aussi un second codeur du format, écrit sans
// lire celui du lot F : si les deux décodent pareil, la spécification dit vrai.
//
// Modes :
//   justesse-decodeur <gguf> <couches a-b> <journal.json> [--experts n] [--casser lut|flux]
//       code chaque expert (§ 4.8, § 4.9), le décode sur la carte (decoder_echelles puis
//       decoder_codes), compare l'emplacement octet à octet à celui qu'on tire du GGUF
//       (§ 4.11, § 5.6) ; puis le chemin brut (copier_brut) sur la même partie brute.
//   debit-decodeur <gguf> <couche> <journal.json> [--experts n] [--passes p]
//       débit du décodeur par expert, en séries A B B A (A : décodage, B : copie brute
//       des mêmes octets) ; latence d'un expert seul.
//   justesse-gemv <gguf> <couche> <journal.json> [--casser]
//       exactitude au bit sur entiers, échelles E8M0 sur les 256 valeurs, écart à une
//       référence f64 sur poids réels, égalité au bit des deux noyaux.
//   debit-gemv <gguf> <couche> <journal.json> [--experts n] [--passes p]
//       débit du produit en séries A B B A (A : lot de 12 matrices, B : une matrice par
//       lancement), sur un ensemble d'emplacements bien plus grand que le cache L2.
//
// Construction : construire.bat (vcvars64, CUDA 13.1.2, -O3, sm_89, OpenMP).

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <string>
#include <vector>
#include <algorithm>
#include <chrono>
#include <ctime>
#include <omp.h>
#include <cuda_runtime.h>

#include "../noyaux/decodeur.cuh"
#include "../noyaux/gemv.cuh"

#define VERIF(x)                                                                                   \
    do {                                                                                           \
        cudaError_t e_ = (x);                                                                      \
        if (e_ != cudaSuccess) {                                                                   \
            fprintf(stderr, "CUDA : %s (%s:%d)\n", cudaGetErrorString(e_), __FILE__, __LINE__);    \
            exit(2);                                                                               \
        }                                                                                          \
    } while (0)

[[noreturn]] static void mourir(const char* m) {
    fprintf(stderr, "erreur : %s\n", m);
    exit(1);
}

static double maintenant() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static std::string horodate() {
    time_t t = time(nullptr);
    struct tm tmv;
    localtime_s(&tmv, &t);
    char b[64];
    strftime(b, sizeof b, "%Y-%m-%dT%H:%M:%S", &tmv);
    return b;
}

// ---------------------------------------------------------------------------------
// GGUF v3, lecture minimale (spécification publique), écrite pour ce banc.

struct Tenseur {
    std::string nom;
    uint32_t type = 0, nd = 0;
    uint64_t ne[4] = {1, 1, 1, 1};
    uint64_t dec = 0;  // absolu dans le fichier
};

struct Gguf {
    std::string chemin;
    std::vector<Tenseur> t;
    const Tenseur& trouver(const std::string& nom) const {
        for (auto& x : t)
            if (x.nom == nom) return x;
        fprintf(stderr, "tenseur absent : %s\n", nom.c_str());
        exit(1);
    }
};

struct Lecteur {
    const std::vector<uint8_t>& b;
    size_t p = 0;
    void verifier(size_t n) {
        if (p + n > b.size()) mourir("en-tête GGUF plus grand que le tampon de lecture");
    }
    uint32_t u32() { verifier(4); uint32_t v; memcpy(&v, &b[p], 4); p += 4; return v; }
    uint64_t u64() { verifier(8); uint64_t v; memcpy(&v, &b[p], 8); p += 8; return v; }
    std::string chaine() { uint64_t n = u64(); verifier(n); std::string s((const char*)&b[p], n); p += n; return s; }
    void sauter(uint32_t type) {
        switch (type) {
            case 0: case 1: case 7: verifier(1); p += 1; break;
            case 2: case 3: verifier(2); p += 2; break;
            case 4: case 5: case 6: verifier(4); p += 4; break;
            case 10: case 11: case 12: verifier(8); p += 8; break;
            case 8: chaine(); break;
            case 9: { uint32_t t2 = u32(); uint64_t n = u64(); for (uint64_t i = 0; i < n; ++i) sauter(t2); break; }
            default: mourir("type de métadonnée GGUF inconnu");
        }
    }
};

static std::vector<uint8_t> lire_octets(const std::string& chemin, uint64_t dec, uint64_t n) {
    FILE* f = fopen(chemin.c_str(), "rb");
    if (!f) mourir("ouverture du fichier");
    std::vector<uint8_t> v(n);
    if (_fseeki64(f, (long long)dec, SEEK_SET) != 0) mourir("positionnement");
    size_t lu = 0;
    while (lu < n) {
        size_t r = fread(v.data() + lu, 1, std::min<uint64_t>(n - lu, 64ull << 20), f);
        if (r == 0) mourir("lecture courte");
        lu += r;
    }
    fclose(f);
    return v;
}

static Gguf lire_gguf(const std::string& chemin) {
    FILE* f = fopen(chemin.c_str(), "rb");
    if (!f) mourir("ouverture du GGUF");
    std::vector<uint8_t> b(64ull << 20);
    b.resize(fread(b.data(), 1, b.size(), f));
    fclose(f);
    Lecteur r{b};
    if (r.u32() != 0x46554747u) mourir("magie GGUF");
    if (r.u32() != 3) mourir("version GGUF");
    const uint64_t nt = r.u64(), nk = r.u64();
    uint64_t alignement = 32;
    for (uint64_t i = 0; i < nk; ++i) {
        std::string cle = r.chaine();
        uint32_t type = r.u32();
        if (cle == "general.alignment" && type == 4) {
            size_t q = r.p;
            alignement = r.u32();
            r.p = q;
        }
        r.sauter(type);
    }
    Gguf g;
    g.chemin = chemin;
    for (uint64_t i = 0; i < nt; ++i) {
        Tenseur t;
        t.nom = r.chaine();
        t.nd = r.u32();
        for (uint32_t d = 0; d < t.nd; ++d) t.ne[d] = r.u64();
        t.type = r.u32();
        t.dec = r.u64();
        g.t.push_back(t);
    }
    const uint64_t debut = (r.p + alignement - 1) / alignement * alignement;
    for (auto& t : g.t) t.dec += debut;
    return g;
}

// ---------------------------------------------------------------------------------
// Une couche d'experts de gpt-oss en mémoire : gate (j = 0), up (1), down (2).

static const char* NOMS_MATRICES[3] = {"gate", "up", "down"};

struct Couche {
    int indice = 0;
    uint32_t E = 0;
    trc::DimsExpert dims{};
    std::vector<uint8_t> w[3];  // blocs MXFP4 de 17 o, ordre (expert, ligne, bloc) du GGUF
    std::vector<uint8_t> b[3];  // biais f32 [expert][ligne], octets bruts
};

static Couche lire_couche(const Gguf& g, int l, double* secondes_lecture = nullptr) {
    const double t0 = maintenant();
    Couche c;
    c.indice = l;
    for (int j = 0; j < 3; ++j) {
        char nom[96];
        snprintf(nom, sizeof nom, "blk.%d.ffn_%s_exps.weight", l, NOMS_MATRICES[j]);
        const Tenseur& tw = g.trouver(nom);
        if (tw.type != 39 || tw.nd != 3) mourir("experts : MXFP4 à trois dimensions attendu");
        const uint32_t C = (uint32_t)tw.ne[0], R = (uint32_t)tw.ne[1], E = (uint32_t)tw.ne[2];
        if (C % 32) mourir("colonnes non multiples de 32");
        if (j == 0) c.E = E;
        else if (E != c.E) mourir("nombre d'experts incohérent");
        c.dims.lignes[j] = R;
        c.dims.colonnes[j] = C;
        c.w[j] = lire_octets(g.chemin, tw.dec, (uint64_t)E * R * (C / 32) * 17);
        snprintf(nom, sizeof nom, "blk.%d.ffn_%s_exps.bias", l, NOMS_MATRICES[j]);
        const Tenseur& tb = g.trouver(nom);
        if (tb.type != 0 || tb.ne[0] != R || tb.ne[1] != E) mourir("biais : F32 [R, E] attendu");
        c.b[j] = lire_octets(g.chemin, tb.dec, (uint64_t)E * R * 4);
    }
    if (secondes_lecture) *secondes_lecture = maintenant() - t0;
    return c;
}

// ---------------------------------------------------------------------------------
// Tables rANS (§ 4.6, § 4.9.2) : fréquences sur 12 bits dont la somme vaut 4 096.
// Normalisation propre à ce banc (gloutonne sur le coût en bits) : le décodeur n'en
// dépend pas, il ne lit que la LUT ; c'est voulu, pour ne pas épouser le codeur de F.

struct Table {
    uint32_t f[256];
    uint32_t c[256];
    bool vide = true;
};

static Table normaliser(const uint64_t* comptes) {
    Table t;
    uint64_t total = 0;
    for (int s = 0; s < 256; ++s) total += comptes[s];
    memset(t.f, 0, sizeof t.f);
    memset(t.c, 0, sizeof t.c);
    if (total == 0) return t;
    t.vide = false;
    int64_t somme = 0;
    for (int s = 0; s < 256; ++s) {
        if (comptes[s]) {
            int64_t f = llround((double)comptes[s] * trc::M / (double)total);
            t.f[s] = (uint32_t)std::max<int64_t>(1, f);
            somme += t.f[s];
        }
    }
    while (somme != (int64_t)trc::M) {
        int meilleur = -1;
        double cout_min = 1e300;
        for (int s = 0; s < 256; ++s) {
            if (!comptes[s]) continue;
            double cout;
            if (somme > (int64_t)trc::M) {
                if (t.f[s] <= 1) continue;
                cout = comptes[s] * std::log2((double)t.f[s] / (t.f[s] - 1));
            } else {
                cout = -(double)comptes[s] * std::log2((double)(t.f[s] + 1) / t.f[s]);
            }
            if (cout < cout_min) { cout_min = cout; meilleur = s; }
        }
        if (meilleur < 0) mourir("table impossible à normaliser");
        if (somme > (int64_t)trc::M) { t.f[meilleur]--; somme--; }
        else { t.f[meilleur]++; somme++; }
    }
    uint32_t c = 0;
    for (int s = 0; s < 256; ++s) { t.c[s] = c; c += t.f[s]; }
    return t;
}

// LUT de géométrie 1 (§ 4.9.2) : lut[i] = s | (f − 1) << 8 | (i − c) << 20.
static void lut_g1(const Table& t, uint32_t* lut) {
    memset(lut, 0, trc::M * 4);
    if (t.vide) return;
    for (uint32_t s = 0; s < 256; ++s)
        for (uint32_t i = t.c[s]; i < t.c[s] + t.f[s]; ++i) lut[i] = s | ((t.f[s] - 1) << 8) | ((i - t.c[s]) << 20);
}

static double bits_table(const Table& t, const uint64_t* comptes) {
    double b = 0;
    for (int s = 0; s < 256; ++s)
        if (comptes[s]) b -= comptes[s] * std::log2((double)t.f[s] / trc::M);
    return b;
}

// ---------------------------------------------------------------------------------
// Codeur rANS de géométrie 1 (§ 4.9.2), contexte connu du décodeur choisi par le mot de
// sortie. Les symboles se codent dans l'ordre exactement inverse du décodage : macro-
// pas, sous-pas et voies décroissants ; chaque voie part de L ; la pile de mots est
// renversée à la fin de la tuile.

template <class Ctx>
static std::vector<uint8_t> coder_g1(const uint8_t* src, uint32_t P, uint32_t N, const Table* tables, Ctx ctx_mot) {
    const uint32_t nmacro = P / 128, T = (nmacro + N - 1) / N;
    std::vector<uint32_t> debut(T), etats(32ull * T);
    std::vector<uint16_t> mots, pile;
    mots.reserve(P / 2);
    for (uint32_t t = 0; t < T; ++t) {
        const uint32_t m0 = t * N, m1 = std::min(m0 + N, nmacro);
        uint64_t x[32];
        for (int v = 0; v < 32; ++v) x[v] = trc::L;
        pile.clear();
        for (uint32_t m = m1; m-- > m0;) {
            for (int k = 3; k >= 0; --k) {
                for (int v = 31; v >= 0; --v) {
                    const uint32_t w = m * 32 + v;
                    const Table& tb = tables[ctx_mot(w)];
                    const uint32_t s = src[(uint64_t)w * 4 + k];
                    const uint64_t f = tb.f[s];
                    if (f == 0) mourir("symbole absent de sa table");
                    uint64_t xv = x[v];
                    if (xv >= (f << 20)) { pile.push_back((uint16_t)(xv & 0xFFFF)); xv >>= 16; }
                    x[v] = (xv / f) * trc::M + (xv % f) + tb.c[s];
                }
            }
        }
        debut[t] = (uint32_t)mots.size();
        for (int v = 0; v < 32; ++v) etats[32ull * t + v] = (uint32_t)x[v];
        mots.insert(mots.end(), pile.rbegin(), pile.rend());
    }
    const uint32_t W = (uint32_t)mots.size();
    std::vector<uint8_t> o(16 + 4ull * T + 128ull * T + 2ull * W);
    auto mettre32 = [&](size_t at, uint32_t v) { memcpy(&o[at], &v, 4); };
    mettre32(0, P);
    uint16_t n16 = (uint16_t)N;
    memcpy(&o[4], &n16, 2);
    o[6] = 1;  // géométrie 1 : octet, 4 sous-pas par mot
    o[7] = 0;
    mettre32(8, T);
    mettre32(12, W);
    memcpy(&o[16], debut.data(), 4ull * T);
    memcpy(&o[16 + 4ull * T], etats.data(), 128ull * T);
    memcpy(&o[16 + 132ull * T], mots.data(), 2ull * W);
    o.resize((o.size() + 15) / 16 * 16, 0);
    return o;
}

// ---------------------------------------------------------------------------------
// Une matrice d'un expert, tirée du GGUF : échelles, codes, médianes, δ, κ.

struct MatriceSource {
    uint32_t R, C, B, nblocs;
    std::vector<uint8_t> e, qs, med, delta, kappa, biais;
};

static MatriceSource extraire(const Couche& c, uint32_t x, int j) {
    MatriceSource m;
    m.R = c.dims.lignes[j];
    m.C = c.dims.colonnes[j];
    m.B = m.C / 32;
    m.nblocs = m.R * m.B;
    m.e.resize(m.nblocs);
    m.qs.resize(16ull * m.nblocs);
    m.med.resize(m.R);
    m.delta.resize(m.nblocs);
    m.kappa.resize(m.nblocs);
    const uint8_t* w = c.w[j].data() + (uint64_t)x * m.nblocs * 17;
    for (uint32_t beta = 0; beta < m.nblocs; ++beta) {
        m.e[beta] = w[17ull * beta];
        memcpy(&m.qs[16ull * beta], w + 17ull * beta + 1, 16);
    }
    std::vector<uint8_t> tri(m.B);
    for (uint32_t r = 0; r < m.R; ++r) {
        memcpy(tri.data(), &m.e[(uint64_t)r * m.B], m.B);
        std::sort(tri.begin(), tri.end());
        m.med[r] = tri[m.B / 2];  // § 4.10 : tri[B/2], tri croissant
        for (uint32_t b = 0; b < m.B; ++b) {
            const uint32_t beta = r * m.B + b;
            const uint32_t d = (m.e[beta] - m.med[r] + 128u) & 255u;
            m.delta[beta] = (uint8_t)d;
            m.kappa[beta] = d < 128 ? 0 : (d == 128 ? 1 : 2);
        }
    }
    m.biais.assign(c.b[j].begin() + (uint64_t)x * m.R * 4, c.b[j].begin() + (uint64_t)(x + 1) * m.R * 4);
    return m;
}

static uint32_t arrondi128(uint32_t n) { return (n + 127) / 128 * 128; }

// Tables d'une couche : par matrice, DELTA (une) et CODES_CTX (trois, par κ), communes à
// tous les experts de la couche (§ 4.6). Le bourrage éventuel (sans objet pour gpt-oss)
// compte des symboles 0 de contexte 0, comme le codeur les codera.
struct TablesCouche {
    Table t[3][4];
    uint64_t comptes[3][4][256];
};

static TablesCouche tables_couche(const Couche& c, int fils) {
    TablesCouche tc;
    memset(tc.comptes, 0, sizeof tc.comptes);
    for (int j = 0; j < 3; ++j) {
        std::vector<std::vector<uint64_t>> loc(fils, std::vector<uint64_t>(4 * 256, 0));
#pragma omp parallel for num_threads(fils) schedule(dynamic, 1)
        for (int x = 0; x < (int)c.E; ++x) {
            uint64_t* h = loc[omp_get_thread_num()].data();
            MatriceSource m = extraire(c, x, j);
            for (uint32_t beta = 0; beta < m.nblocs; ++beta) {
                h[m.delta[beta]]++;
                uint64_t* hc = h + 256 * (1 + m.kappa[beta]);
                for (int i = 0; i < 16; ++i) hc[m.qs[16ull * beta + i]]++;
            }
            h[0] += arrondi128(m.nblocs) - m.nblocs;
            h[256] += arrondi128(16 * m.nblocs) - 16 * m.nblocs;
        }
        for (int f = 0; f < fils; ++f)
            for (int i = 0; i < 4 * 256; ++i) tc.comptes[j][i / 256][i % 256] += loc[f][i];
        for (int k = 0; k < 4; ++k) tc.t[j][k] = normaliser(tc.comptes[j][k]);
    }
    return tc;
}

static std::vector<uint32_t> luts_couche(const TablesCouche& tc) {
    std::vector<uint32_t> l(3ull * 4 * trc::M);
    for (int j = 0; j < 3; ++j)
        for (int k = 0; k < 4; ++k) lut_g1(tc.t[j][k], &l[((uint64_t)j * 4 + k) * trc::M]);
    return l;
}

// ---------------------------------------------------------------------------------
// Parties de tronçon (§ 4.8).

struct FluxPartie {
    uint8_t sorte, matrice, contexte;
    std::vector<uint8_t> octets;
    uint32_t produits;
};

static std::vector<uint8_t> assembler_partie(uint16_t couche, uint16_t expert, std::vector<FluxPartie>& flux) {
    const uint32_t n = (uint32_t)flux.size();
    size_t p = 64 + 16ull * n;
    p = (p + 15) / 16 * 16;
    std::vector<uint32_t> dec(n);
    for (uint32_t i = 0; i < n; ++i) {
        dec[i] = (uint32_t)p;
        p += flux[i].octets.size();
        p = (p + 15) / 16 * 16;
    }
    const uint32_t utiles = (uint32_t)p;
    std::vector<uint8_t> o((p + 4095) / 4096 * 4096, 0);
    const uint32_t magie = trc::MAGIE_PARTIE0;
    memcpy(&o[0], &magie, 4);
    memcpy(&o[4], &couche, 2);
    memcpy(&o[6], &expert, 2);
    o[8] = 0;  // niveau
    o[9] = 3;  // matrices
    const uint16_t nf = (uint16_t)n;
    memcpy(&o[10], &nf, 2);
    memcpy(&o[12], &utiles, 4);
    for (uint32_t i = 0; i < n; ++i) {
        uint8_t* e = &o[64 + 16ull * i];
        e[0] = flux[i].sorte;
        e[1] = flux[i].matrice;
        e[2] = flux[i].contexte;
        e[3] = 0;
        const uint32_t lon = (uint32_t)flux[i].octets.size();
        memcpy(e + 4, &dec[i], 4);
        memcpy(e + 8, &lon, 4);
        memcpy(e + 12, &flux[i].produits, 4);
        memcpy(&o[dec[i]], flux[i].octets.data(), lon);
    }
    return o;
}

struct ExpertCode {
    std::vector<uint8_t> partie;       // v1.0, niveau 0 (12 flux)
    std::vector<uint8_t> partie_brute; // fichier brut (9 flux)
    std::vector<uint8_t> attendu;      // emplacement SoA attendu (§ 5.6)
    uint64_t octets_codes_ctx = 0, octets_delta = 0;
};

static uint64_t taille_emplacement(const trc::DimsExpert& d) {
    uint64_t s = 0;
    for (int j = 0; j < 3; ++j) s += trc::disposition_matrice(d.lignes[j], d.colonnes[j]).pas;
    return s;
}

// Macro-pas par tuile des flux DELTA que code ce banc (TRC_N_DELTA ; 256 par défaut, comme le
// lot F). Le format porte N dans chaque flux (§ 4.9.1) et le décodeur le lit : changer N ne change
// pas le format, seulement la longueur de la chaîne de chaque tuile (modèle de latence,
// K-pour-le-memoire.md § 2.5 : DELTA d'un expert = 8 tuiles de 1 024 sous-pas, 152 µs).
static uint32_t N_DELTA = 256;

static ExpertCode coder_expert(const Couche& c, const TablesCouche& tc, uint32_t x) {
    ExpertCode ec;
    std::vector<FluxPartie> flux, brut;
    ec.attendu.assign(taille_emplacement(c.dims), 0);
    for (int j = 0; j < 3; ++j) {
        MatriceSource m = extraire(c, x, j);
        const trc::Disposition d = trc::disposition(c.dims, j);
        memcpy(&ec.attendu[d.base], m.qs.data(), m.qs.size());
        memcpy(&ec.attendu[d.base + d.echelles], m.e.data(), m.e.size());
        memcpy(&ec.attendu[d.base + d.biais], m.biais.data(), m.biais.size());

        flux.push_back({trc::SORTE_MEDIANES, (uint8_t)j, 0xFF, m.med, m.R});
        flux.push_back({trc::SORTE_BIAIS, (uint8_t)j, 0xFF, m.biais, 4 * m.R});
        std::vector<uint8_t> sd = m.delta;
        sd.resize(arrondi128(m.nblocs), 0);
        auto ctx_delta = [](uint32_t) { return 0u; };
        std::vector<uint8_t> fdel = coder_g1(sd.data(), (uint32_t)sd.size(), N_DELTA, &tc.t[j][0], ctx_delta);
        ec.octets_delta += fdel.size();
        flux.push_back({trc::SORTE_DELTA, (uint8_t)j, 0, std::move(fdel), (uint32_t)sd.size()});
        std::vector<uint8_t> sc = m.qs;
        sc.resize(arrondi128(16 * m.nblocs), 0);
        const uint8_t* kap = m.kappa.data();
        const uint32_t nb = m.nblocs;
        auto ctx_codes = [kap, nb](uint32_t w) { return (w >> 2) < nb ? (uint32_t)kap[w >> 2] : 0u; };
        std::vector<uint8_t> fcod = coder_g1(sc.data(), (uint32_t)sc.size(), 256, &tc.t[j][1], ctx_codes);
        ec.octets_codes_ctx += fcod.size();
        flux.push_back({trc::SORTE_CODES_CTX, (uint8_t)j, 0xFF, std::move(fcod), (uint32_t)sc.size()});

        brut.push_back({trc::SORTE_ECHELLES_BRUTES, (uint8_t)j, 0xFF, m.e, m.nblocs});
        brut.push_back({trc::SORTE_CODES_BRUTS, (uint8_t)j, 0xFF, m.qs, 16 * m.nblocs});
        brut.push_back({trc::SORTE_BIAIS, (uint8_t)j, 0xFF, m.biais, 4 * m.R});
    }
    ec.partie = assembler_partie((uint16_t)c.indice, (uint16_t)x, flux);
    ec.partie_brute = assembler_partie((uint16_t)c.indice, (uint16_t)x, brut);
    return ec;
}

// ---------------------------------------------------------------------------------
// Lancements (les mêmes géométries que l'enveloppe Rust, abi::grilles_decodeur).

static uint32_t FILS_ECH = 128;  // essai : fils par bloc de decoder_echelles (TRC_FILS_ECH)
static uint32_t tuiles_attendues(uint32_t octets, uint32_t N = 256) { return (arrondi128(octets) / 128 + N - 1) / N; }

static dim3 grille_echelles(const trc::DimsExpert& d) {
    uint32_t t = 0;
    for (int j = 0; j < 3; ++j) t = std::max(t, tuiles_attendues(d.lignes[j] * (d.colonnes[j] / 32), N_DELTA));
    return dim3((t + FILS_ECH / 32 - 1) / (FILS_ECH / 32), 3);
}
static dim3 grille_codes(const trc::DimsExpert& d) {
    uint32_t t = 0;
    for (int j = 0; j < 3; ++j) t = std::max(t, tuiles_attendues(16 * d.lignes[j] * (d.colonnes[j] / 32)));
    return dim3((t + 7) / 8, 3);
}
static dim3 grille_brut(const trc::DimsExpert& d) {
    uint32_t n = 0;
    for (int j = 0; j < 3; ++j) n = std::max(n, d.lignes[j] * (d.colonnes[j] / 32));
    return dim3(std::min<uint32_t>((n + 255) / 256, 96), 3);
}

static void lancer_decodage(const uint8_t* partie, uint8_t* empl, const uint32_t* luts, const trc::DimsExpert& d,
                            uint32_t* ctl, cudaStream_t s) {
    decoder_echelles<<<grille_echelles(d), FILS_ECH, 0, s>>>(partie, empl, luts, d, ctl);
    decoder_codes<<<grille_codes(d), 256, 0, s>>>(partie, empl, luts, d, ctl);
}

// Lot de n experts (decoder_echelles_lot puis decoder_codes_lot, grilles (X, 3, n)).
static void lancer_lot(const trc::DescDecodage* descs, uint32_t n, const trc::DimsExpert& d, cudaStream_t s) {
    dim3 g1 = grille_echelles(d), g2 = grille_codes(d);
    g1.z = n;
    g2.z = n;
    decoder_echelles_lot<<<g1, FILS_ECH, 0, s>>>(descs, d);
    decoder_codes_lot<<<g2, 256, 0, s>>>(descs, d);
}

static void lancer_brut(const uint8_t* partie, uint8_t* empl, const trc::DimsExpert& d, uint32_t* ctl, cudaStream_t s) {
    copier_brut<<<grille_brut(d), 256, 0, s>>>(partie, empl, d, ctl);
}

// ---------------------------------------------------------------------------------
// Petits utilitaires.

struct Alea {
    uint64_t s;
    explicit Alea(uint64_t g) : s(g) {}
    uint64_t suivant() {
        uint64_t z = (s += 0x9E3779B97F4A7C15ull);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
        return z ^ (z >> 31);
    }
    double uniforme() { return (suivant() >> 11) * (1.0 / 9007199254740992.0); }
    double normale() {
        double u = std::max(uniforme(), 1e-300), v = uniforme();
        return std::sqrt(-2.0 * std::log(u)) * std::cos(6.283185307179586 * v);
    }
};

static double mediane(std::vector<double> v) {
    std::sort(v.begin(), v.end());
    const size_t n = v.size();
    return n % 2 ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

static std::string liste(const std::vector<double>& v, const char* fmt = "%.6e") {
    std::string s = "[";
    char b[64];
    for (size_t i = 0; i < v.size(); ++i) {
        snprintf(b, sizeof b, fmt, v[i]);
        s += (i ? ", " : "");
        s += b;
    }
    return s + "]";
}

static void entete_journal(FILE* j, const char* mode, int argc, char** argv) {
    cudaDeviceProp p;
    VERIF(cudaGetDeviceProperties(&p, 0));
    size_t libre, total;
    VERIF(cudaMemGetInfo(&libre, &total));
    fprintf(j, "{\n  \"outil\": \"banc_k\", \"mode\": \"%s\", \"date\": \"%s\",\n  \"commande\": \"", mode, horodate().c_str());
    for (int i = 0; i < argc; ++i) {
        for (const char* c = argv[i]; *c; ++c) {
            if (*c == '\\' || *c == '"') fputc('\\', j);
            fputc(*c, j);
        }
        if (i + 1 < argc) fputc(' ', j);
    }
    fprintf(j, "\",\n  \"carte\": \"%s\", \"sm\": \"%d.%d\", \"multiprocesseurs\": %d, \"vram_libre_mio\": %.0f,\n",
            p.name, p.major, p.minor, p.multiProcessorCount, libre / 1048576.0);
    fprintf(j, "  \"n_delta\": %u, \"fils_echelles\": %u,\n", N_DELTA, FILS_ECH);
}

static const char* option(int argc, char** argv, const char* nom, const char* defaut) {
    for (int i = 1; i + 1 < argc; ++i)
        if (!strcmp(argv[i], nom)) return argv[i + 1];
    return defaut;
}
static bool drapeau(int argc, char** argv, const char* nom) {
    for (int i = 1; i < argc; ++i)
        if (!strcmp(argv[i], nom)) return true;
    return false;
}

// Octets différents entre deux emplacements, par matrice et par région.
struct Ecarts {
    uint64_t codes = 0, echelles = 0, biais = 0, autres = 0;
    uint64_t total() const { return codes + echelles + biais + autres; }
};

static Ecarts comparer(const std::vector<uint8_t>& a, const uint8_t* b, const trc::DimsExpert& d) {
    Ecarts e;
    if (memcmp(a.data(), b, a.size()) == 0) return e;
    for (int j = 0; j < 3; ++j) {
        const trc::Disposition p = trc::disposition(d, j);
        const uint64_t nb = (uint64_t)d.lignes[j] * (d.colonnes[j] / 32);
        for (uint64_t i = 0; i < p.pas; ++i) {
            if (a[p.base + i] == b[p.base + i]) continue;
            if (i < 16 * nb) e.codes++;
            else if (i >= p.echelles && i < p.echelles + nb) e.echelles++;
            else if (i >= p.biais && i < p.biais + 4ull * d.lignes[j]) e.biais++;
            else e.autres++;
        }
    }
    return e;
}

// ---------------------------------------------------------------------------------
// Mode justesse-decodeur (témoin de K1).

static int justesse_decodeur(int argc, char** argv) {
    if (argc < 5) mourir("justesse-decodeur <gguf> <couches a-b> <journal.json> [--experts n] [--casser lut|flux]");
    const std::string chemin = argv[2];
    int c0 = 0, c1 = 0;
    if (sscanf(argv[3], "%d-%d", &c0, &c1) != 2) { c0 = c1 = atoi(argv[3]); }
    FILE* jo = fopen(argv[4], "w");
    if (!jo) mourir("journal");
    const int n_exp_max = atoi(option(argc, argv, "--experts", "100000"));
    const std::string casser = option(argc, argv, "--casser", "");
    const int fils = atoi(option(argc, argv, "--fils", "4"));
    entete_journal(jo, "justesse-decodeur", argc, argv);
    fprintf(jo, "  \"casser\": \"%s\", \"fils\": %d,\n  \"couches\": [\n", casser.c_str(), fils);

    Gguf g = lire_gguf(chemin);
    const int LOT = 4;  // experts sur la carte à la fois
    uint64_t tot_experts = 0, tot_faux = 0, tot_faux_brut = 0, tot_hors_l = 0, tot_format = 0, tot_pointeur = 0;
    uint64_t tot_octets_partie = 0, tot_poids = 0, tot_octets_origine = 0;
    uint64_t tot_tuiles = 0;
    const double t_debut = maintenant();
    for (int l = c0; l <= c1; ++l) {
        double t_lec = 0;
        Couche c = lire_couche(g, l, &t_lec);
        const double t1 = maintenant();
        TablesCouche tc = tables_couche(c, fils);
        const double t_tables = maintenant() - t1;
        std::vector<uint32_t> luts = luts_couche(tc);
        const uint64_t te = taille_emplacement(c.dims);
        const uint32_t E = std::min<uint32_t>(c.E, (uint32_t)n_exp_max);

        uint32_t *d_luts, *d_ctl;
        uint8_t *d_part, *d_empl;
        size_t cap_partie = 0;
        VERIF(cudaMalloc(&d_luts, luts.size() * 4));
        VERIF(cudaMemcpy(d_luts, luts.data(), luts.size() * 4, cudaMemcpyHostToDevice));
        if (casser == "lut") {
            // Une fente de la LUT de CODES_CTX, contexte κ = 1 (le plus fréquent), matrice 0.
            uint32_t v = luts[1ull * trc::M + 7] ^ 1u;
            VERIF(cudaMemcpy(d_luts + 1ull * trc::M + 7, &v, 4, cudaMemcpyHostToDevice));
        }
        VERIF(cudaMalloc(&d_empl, LOT * te));
        VERIF(cudaMalloc(&d_ctl, LOT * 4 * 4));
        d_part = nullptr;

        uint64_t faux = 0, faux_brut = 0, hors_l = 0, format = 0, pointeur = 0, octets_partie = 0, octets_delta = 0,
                 octets_codes = 0;
        Ecarts ecarts_couche;
        double t_codage = 0, t_carte = 0;
        std::vector<uint8_t> retour(LOT * te);
        for (uint32_t x0 = 0; x0 < E; x0 += 16) {
            const uint32_t nx = std::min<uint32_t>(16, E - x0);
            std::vector<ExpertCode> ec(nx);
            const double ta = maintenant();
#pragma omp parallel for num_threads(fils) schedule(dynamic, 1)
            for (int i = 0; i < (int)nx; ++i) ec[i] = coder_expert(c, tc, x0 + i);
            t_codage += maintenant() - ta;
            const double tb = maintenant();
            for (uint32_t i = 0; i < nx; ++i) {
                cap_partie = std::max({cap_partie, ec[i].partie.size(), ec[i].partie_brute.size()});
                octets_partie += ec[i].partie.size();
                octets_delta += ec[i].octets_delta;
                octets_codes += ec[i].octets_codes_ctx;
            }
            static size_t cap_alloue = 0;
            if (cap_partie > cap_alloue || !d_part) {
                if (d_part) VERIF(cudaFree(d_part));
                VERIF(cudaMalloc(&d_part, LOT * cap_partie));
                cap_alloue = cap_partie;
            }
            for (uint32_t i0 = 0; i0 < nx; i0 += LOT) {
                const uint32_t n = std::min<uint32_t>(LOT, nx - i0);
                // Chemin codé.
                for (int brut = 0; brut < 2; ++brut) {
                    VERIF(cudaMemset(d_empl, 0, LOT * te));
                    VERIF(cudaMemset(d_ctl, 0, LOT * 16));
                    for (uint32_t i = 0; i < n; ++i) {
                        std::vector<uint8_t> p = brut ? ec[i0 + i].partie_brute : ec[i0 + i].partie;
                        if (!brut && casser == "flux" && i == 0) {
                            // Un bit retourné au milieu des mots de CODES_CTX de la matrice 1.
                            const uint8_t* e = &p[64 + 16 * 7];
                            uint32_t dec, lon;
                            memcpy(&dec, e + 4, 4);
                            memcpy(&lon, e + 8, 4);
                            p[dec + lon / 2] ^= 0x10;
                        }
                        VERIF(cudaMemcpy(d_part + i * cap_partie, p.data(), p.size(), cudaMemcpyHostToDevice));
                        if (brut) lancer_brut(d_part + i * cap_partie, d_empl + i * te, c.dims, d_ctl + 4 * i, 0);
                        else lancer_decodage(d_part + i * cap_partie, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i, 0);
                    }
                    VERIF(cudaGetLastError());
                    VERIF(cudaDeviceSynchronize());
                    VERIF(cudaMemcpy(retour.data(), d_empl, n * te, cudaMemcpyDeviceToHost));
                    uint32_t ctl[LOT * 4];
                    VERIF(cudaMemcpy(ctl, d_ctl, sizeof ctl, cudaMemcpyDeviceToHost));
                    for (uint32_t i = 0; i < n; ++i) {
                        Ecarts e = comparer(ec[i0 + i].attendu, retour.data() + i * te, c.dims);
                        if (brut) {
                            faux_brut += e.total() ? 1 : 0;
                            format += ctl[4 * i + 1];
                        } else {
                            faux += e.total() ? 1 : 0;
                            ecarts_couche.codes += e.codes;
                            ecarts_couche.echelles += e.echelles;
                            ecarts_couche.biais += e.biais;
                            ecarts_couche.autres += e.autres;
                            hors_l += ctl[4 * i + 0];
                            format += ctl[4 * i + 1];
                            pointeur += ctl[4 * i + 2];
                        }
                    }
                }
            }
            t_carte += maintenant() - tb;
        }
        VERIF(cudaFree(d_luts));
        VERIF(cudaFree(d_empl));
        VERIF(cudaFree(d_ctl));
        if (d_part) VERIF(cudaFree(d_part));
        d_part = nullptr;

        uint64_t poids = 0, origine = 0;
        for (int j = 0; j < 3; ++j) {
            const uint64_t nb = (uint64_t)c.dims.lignes[j] * (c.dims.colonnes[j] / 32);
            poids += nb * 32 * E;
            origine += (nb * 17 + 4ull * c.dims.lignes[j]) * E;
        }
        // Bits par poids de l'entropie des tables (sans en-têtes) : témoin de cohérence avec F1.
        double bits_tab = 0;
        for (int j = 0; j < 3; ++j)
            for (int k = 0; k < 4; ++k) bits_tab += bits_table(tc.t[j][k], tc.comptes[j][k]);
        const uint64_t poids_couche = poids / E * c.E;

        tot_experts += E;
        tot_faux += faux;
        tot_faux_brut += faux_brut;
        tot_hors_l += hors_l;
        tot_format += format;
        tot_pointeur += pointeur;
        tot_octets_partie += octets_partie;
        tot_poids += poids;
        tot_octets_origine += origine;
        for (int j = 0; j < 3; ++j) {
            const uint32_t nb = c.dims.lignes[j] * (c.dims.colonnes[j] / 32);
            tot_tuiles += (uint64_t)E * (tuiles_attendues(nb) + tuiles_attendues(16 * nb));
        }
        fprintf(jo,
                "    {\"couche\": %d, \"experts\": %u, \"experts_faux\": %llu, \"experts_faux_brut\": %llu, "
                "\"octets_faux\": {\"codes\": %llu, \"echelles\": %llu, \"biais\": %llu, \"autres\": %llu}, "
                "\"voies_hors_L\": %llu, \"erreurs_format\": %llu, \"pointeurs_faux\": %llu, "
                "\"octets_parties\": %llu, \"octets_delta\": %llu, \"octets_codes_ctx\": %llu, \"octets_origine\": %llu, "
                "\"taux_origine_sur_partie\": %.6f, \"bits_par_poids_entropie_tables\": %.6f, "
                "\"s_lecture\": %.2f, \"s_tables\": %.2f, \"s_codage\": %.2f, \"s_carte\": %.2f}%s\n",
                l, E, (unsigned long long)faux, (unsigned long long)faux_brut,
                (unsigned long long)ecarts_couche.codes, (unsigned long long)ecarts_couche.echelles,
                (unsigned long long)ecarts_couche.biais, (unsigned long long)ecarts_couche.autres,
                (unsigned long long)hors_l, (unsigned long long)format, (unsigned long long)pointeur,
                (unsigned long long)octets_partie, (unsigned long long)octets_delta, (unsigned long long)octets_codes,
                (unsigned long long)origine, (double)origine / octets_partie, bits_tab / poids_couche, t_lec,
                t_tables, t_codage, t_carte, l < c1 ? "," : "");
        fflush(jo);
        fprintf(stderr, "couche %d : %u experts, faux %llu (brut %llu), hors L %llu, format %llu, taux %.4f, %.0f s\n", l,
                E, (unsigned long long)faux, (unsigned long long)faux_brut, (unsigned long long)hors_l,
                (unsigned long long)format, (double)origine / octets_partie, maintenant() - t1 + t_lec);
    }
    fprintf(jo,
            "  ],\n  \"total\": {\"experts\": %llu, \"experts_faux\": %llu, \"experts_faux_brut\": %llu, "
            "\"voies_hors_L\": %llu, \"erreurs_format\": %llu, \"pointeurs_faux\": %llu, \"tuiles\": %llu, "
            "\"octets_parties\": %llu, \"octets_origine\": %llu, \"taux_origine_sur_partie\": %.6f, "
            "\"poids\": %llu, \"secondes\": %.1f}\n}\n",
            (unsigned long long)tot_experts, (unsigned long long)tot_faux, (unsigned long long)tot_faux_brut,
            (unsigned long long)tot_hors_l, (unsigned long long)tot_format, (unsigned long long)tot_pointeur,
            (unsigned long long)tot_tuiles, (unsigned long long)tot_octets_partie,
            (unsigned long long)tot_octets_origine, (double)tot_octets_origine / tot_octets_partie,
            (unsigned long long)tot_poids, maintenant() - t_debut);
    fclose(jo);
    fprintf(stderr, "total : %llu experts, %llu faux (brut %llu), hors L %llu, format %llu\n",
            (unsigned long long)tot_experts, (unsigned long long)tot_faux, (unsigned long long)tot_faux_brut,
            (unsigned long long)tot_hors_l, (unsigned long long)tot_format);
    return 0;
}

// ---------------------------------------------------------------------------------
// Mode debit-decodeur (seuil de K1).
//
// A : décodage de n experts, l'un après l'autre sur un seul flux CUDA (deux lancements
//     par expert), comme le moteur décode ses défauts ;
// B : copie brute des mêmes octets (copier_brut, chemin du fichier brut), même
//     emplacement, même ordre ;
// C : les n experts en un lot (decoder_echelles_lot puis decoder_codes_lot), variante
//     ajoutée le 2026-10-15 vers 15 h 30, seuil déclaré avant sa première mesure (REPRISE-K).
// Séries A B C C B A, `passes` fois ; chaque série dure ≈ 0,25 s. Le bruit de référence est
// l'écart de A à lui-même. Les experts tournent sur n emplacements distincts (n · 25 Mo
// ≫ 32 Mo de cache L2) pour qu'aucune série ne vive dans le cache.

static int debit_decodeur(int argc, char** argv) {
    if (argc < 5) mourir("debit-decodeur <gguf> <couche> <journal.json> [--experts n] [--passes p]");
    const std::string chemin = argv[2];
    const int l = atoi(argv[3]);
    FILE* jo = fopen(argv[4], "w");
    if (!jo) mourir("journal");
    const uint32_t n = (uint32_t)atoi(option(argc, argv, "--experts", "8"));
    const int passes = atoi(option(argc, argv, "--passes", "5"));
    const int fils = atoi(option(argc, argv, "--fils", "4"));
    entete_journal(jo, "debit-decodeur", argc, argv);
    Gguf g = lire_gguf(chemin);
    Couche c = lire_couche(g, l);
    TablesCouche tc = tables_couche(c, fils);
    std::vector<uint32_t> luts = luts_couche(tc);
    std::vector<ExpertCode> ec(n);
#pragma omp parallel for num_threads(fils) schedule(dynamic, 1)
    for (int i = 0; i < (int)n; ++i) ec[i] = coder_expert(c, tc, (uint32_t)i);
    size_t cap = 0;
    uint64_t octets_parties = 0;
    for (auto& e : ec) {
        cap = std::max({cap, e.partie.size(), e.partie_brute.size()});
        octets_parties += e.partie.size();
    }
    const uint64_t te = taille_emplacement(c.dims);
    uint32_t *d_luts, *d_ctl;
    uint8_t *d_part, *d_brut, *d_empl;
    VERIF(cudaMalloc(&d_luts, luts.size() * 4));
    VERIF(cudaMalloc(&d_part, n * cap));
    VERIF(cudaMalloc(&d_brut, n * cap));
    VERIF(cudaMalloc(&d_empl, n * te));
    VERIF(cudaMalloc(&d_ctl, 16 * n));
    VERIF(cudaMemcpy(d_luts, luts.data(), luts.size() * 4, cudaMemcpyHostToDevice));
    for (uint32_t i = 0; i < n; ++i) {
        VERIF(cudaMemcpy(d_part + i * cap, ec[i].partie.data(), ec[i].partie.size(), cudaMemcpyHostToDevice));
        VERIF(cudaMemcpy(d_brut + i * cap, ec[i].partie_brute.data(), ec[i].partie_brute.size(), cudaMemcpyHostToDevice));
    }
    std::vector<uint8_t> retour(te);
    auto verifier = [&](bool brut) -> uint64_t {
        VERIF(cudaMemset(d_empl, 0, n * te));
        VERIF(cudaMemset(d_ctl, 0, 16 * n));
        for (uint32_t i = 0; i < n; ++i) {
            if (brut) lancer_brut(d_brut + i * cap, d_empl + i * te, c.dims, d_ctl + 4 * i, 0);
            else lancer_decodage(d_part + i * cap, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i, 0);
        }
        VERIF(cudaDeviceSynchronize());
        uint64_t faux = 0;
        std::vector<uint32_t> ctl(4 * n);
        VERIF(cudaMemcpy(ctl.data(), d_ctl, 16 * n, cudaMemcpyDeviceToHost));
        for (uint32_t i = 0; i < n; ++i) {
            VERIF(cudaMemcpy(retour.data(), d_empl + i * te, te, cudaMemcpyDeviceToHost));
            faux += (comparer(ec[i].attendu, retour.data(), c.dims).total() || ctl[4 * i] || ctl[4 * i + 1]) ? 1 : 0;
        }
        return faux;
    };
    const uint64_t faux_avant = verifier(false), faux_brut_avant = verifier(true);

    // Descripteurs du lot C, et son témoin : mêmes octets que A.
    std::vector<trc::DescDecodage> descs(n);
    for (uint32_t i = 0; i < n; ++i)
        descs[i] = {(uint64_t)(d_part + i * cap), (uint64_t)(d_empl + i * te), (uint64_t)d_luts, (uint64_t)(d_ctl + 4 * i)};
    trc::DescDecodage* d_descs;
    VERIF(cudaMalloc(&d_descs, n * sizeof(trc::DescDecodage)));
    VERIF(cudaMemcpy(d_descs, descs.data(), n * sizeof(trc::DescDecodage), cudaMemcpyHostToDevice));
    auto verifier_lot = [&]() -> uint64_t {
        VERIF(cudaMemset(d_empl, 0, n * te));
        VERIF(cudaMemset(d_ctl, 0, 16 * n));
        lancer_lot(d_descs, n, c.dims, 0);
        VERIF(cudaDeviceSynchronize());
        uint64_t faux = 0;
        std::vector<uint32_t> ctl(4 * n);
        VERIF(cudaMemcpy(ctl.data(), d_ctl, 16 * n, cudaMemcpyDeviceToHost));
        for (uint32_t i = 0; i < n; ++i) {
            VERIF(cudaMemcpy(retour.data(), d_empl + i * te, te, cudaMemcpyDeviceToHost));
            faux += (comparer(ec[i].attendu, retour.data(), c.dims).total() || ctl[4 * i] || ctl[4 * i + 1]) ? 1 : 0;
        }
        return faux;
    };
    const uint64_t faux_lot_avant = verifier_lot();

    cudaEvent_t e0, e1;
    VERIF(cudaEventCreate(&e0));
    VERIF(cudaEventCreate(&e1));
    auto serie = [&](int quoi, int reps) -> double {
        VERIF(cudaEventRecord(e0));
        for (int r = 0; r < reps; ++r)
            for (uint32_t i = 0; i < n; ++i) {
                if (quoi == 0) lancer_decodage(d_part + i * cap, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i, 0);
                else if (quoi == 1) lancer_brut(d_brut + i * cap, d_empl + i * te, c.dims, d_ctl + 4 * i, 0);
                else if (i == 0) lancer_lot(d_descs, n, c.dims, 0);
            }
        VERIF(cudaEventRecord(e1));
        VERIF(cudaEventSynchronize(e1));
        float ms;
        VERIF(cudaEventElapsedTime(&ms, e0, e1));
        return ms / 1e3 / (reps * (double)n);  // secondes par expert
    };
    int reps[3];
    for (int q = 0; q < 3; ++q) {
        serie(q, 2);
        const double t = serie(q, 3);
        reps[q] = std::max(3, std::min(5000, (int)(0.25 / (t * n)) + 1));
    }
    std::vector<double> temps[3];
    const int ordre[6] = {0, 1, 2, 2, 1, 0};
    for (int p = 0; p < passes; ++p)
        for (int q : ordre) temps[q].push_back(serie(q, reps[q]));
    VERIF(cudaGetLastError());

    // Latence d'un expert seul (flux vide avant et après) : ce que paie un défaut isolé.
    std::vector<double> latence;
    for (int r = 0; r < 40; ++r) {
        const uint32_t i = r % n;
        VERIF(cudaDeviceSynchronize());
        VERIF(cudaEventRecord(e0));
        lancer_decodage(d_part + i * cap, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i, 0);
        VERIF(cudaEventRecord(e1));
        VERIF(cudaEventSynchronize(e1));
        float ms;
        VERIF(cudaEventElapsedTime(&ms, e0, e1));
        latence.push_back(ms * 1e-3);
    }
    const uint64_t faux_apres = verifier(false);
    const uint64_t faux_lot_apres = verifier_lot();
    VERIF(cudaFree(d_descs));

    // Décomposition du temps d'un expert : un événement avant et après chaque noyau, sur le
    // même flux, 8 experts à la suite, 20 fois. Temps des noyaux (decoder_echelles,
    // decoder_codes) et trous entre deux noyaux (le temps où la carte attend l'hôte).
    std::vector<double> t_ech, t_cod, t_trou;
    {
        std::vector<cudaEvent_t> ev(3 * n + 1);
        for (auto& e : ev) VERIF(cudaEventCreate(&e));
        for (int r = 0; r < 20; ++r) {
            VERIF(cudaDeviceSynchronize());
            for (uint32_t i = 0; i < n; ++i) {
                VERIF(cudaEventRecord(ev[3 * i]));
                decoder_echelles<<<grille_echelles(c.dims), FILS_ECH>>>(d_part + i * cap, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i);
                VERIF(cudaEventRecord(ev[3 * i + 1]));
                decoder_codes<<<grille_codes(c.dims), 256>>>(d_part + i * cap, d_empl + i * te, d_luts, c.dims, d_ctl + 4 * i);
                VERIF(cudaEventRecord(ev[3 * i + 2]));
            }
            VERIF(cudaEventRecord(ev[3 * n]));
            VERIF(cudaEventSynchronize(ev[3 * n]));
            for (uint32_t i = 0; i < n; ++i) {
                float a, b, g;
                VERIF(cudaEventElapsedTime(&a, ev[3 * i], ev[3 * i + 1]));
                VERIF(cudaEventElapsedTime(&b, ev[3 * i + 1], ev[3 * i + 2]));
                t_ech.push_back(a * 1e-3);
                t_cod.push_back(b * 1e-3);
                if (i + 1 < n) {
                    VERIF(cudaEventElapsedTime(&g, ev[3 * i + 2], ev[3 * i + 3]));
                    t_trou.push_back(g * 1e-3);
                }
            }
        }
        for (auto& e : ev) VERIF(cudaEventDestroy(e));
    }

    uint64_t octets_codes = 0, octets_sortie = 0;
    for (int j = 0; j < 3; ++j) {
        const uint64_t nb = (uint64_t)c.dims.lignes[j] * (c.dims.colonnes[j] / 32);
        octets_codes += 16 * nb;
        octets_sortie += 17 * nb + 4ull * c.dims.lignes[j];
    }
    const double tA = mediane(temps[0]), tB = mediane(temps[1]), tC = mediane(temps[2]);
    const double pireC = *std::max_element(temps[2].begin(), temps[2].end());
    auto disp = [](const std::vector<double>& v) {
        return (*std::max_element(v.begin(), v.end()) - *std::min_element(v.begin(), v.end())) /
               *std::min_element(v.begin(), v.end());
    };
    const double seuil = 0.8 * 41.6;
    fprintf(jo,
            "  \"couche\": %d, \"experts\": %u, \"passes\": %d, \"ordre\": \"A B C C B A\",\n"
            "  \"A\": \"decodage (decoder_echelles + decoder_codes), un expert apres l'autre\",\n"
            "  \"B\": \"copie brute des memes octets (copier_brut)\",\n"
            "  \"octets_codes_par_expert\": %llu, \"octets_sortie_par_expert\": %llu, \"octets_partie_moyens\": %.0f,\n"
            "  \"lancements_par_serie\": [%d, %d],\n"
            "  \"temps_s_par_expert\": {\"A\": %s, \"B\": %s},\n"
            "  \"mediane_s_par_expert\": {\"A\": %.6e, \"B\": %.6e},\n"
            "  \"dispersion\": {\"A\": %.4f, \"B\": %.4f},\n"
            "  \"go_s_codes\": {\"A\": %.2f, \"B\": %.2f, \"A_pire\": %.2f},\n"
            "  \"go_s_sortie\": {\"A\": %.2f, \"B\": %.2f},\n"
            "  \"go_s_entree_partie\": {\"A\": %.2f},\n"
            "  \"latence_expert_seul_s\": {\"mediane\": %.6e, \"min\": %.6e, \"max\": %.6e},\n"
            "  \"decomposition_s_medianes\": {\"decoder_echelles\": %.6e, \"decoder_codes\": %.6e, \"trou_entre_experts\": %.6e},\n"
            "  \"C\": \"les n experts en un lot (decoder_echelles_lot + decoder_codes_lot)\",\n"
            "  \"temps_s_par_expert_C\": %s, \"mediane_s_par_expert_C\": %.6e, \"dispersion_C\": %.4f,\n"
            "  \"go_s_codes_C\": {\"mediane\": %.2f, \"pire\": %.2f}, \"seuil_tient_C\": %s,\n"
            "  \"temoins_C\": {\"experts_faux_avant\": %llu, \"experts_faux_apres\": %llu},\n"
            "  \"seuil_go_s_codes\": %.2f, \"seuil_source\": \"0,8 x 41,6 Go/s (ARCHITECTURE.md 6.5, K1)\",\n"
            "  \"seuil_tient\": %s,\n"
            "  \"temoins\": {\"experts_faux_avant\": %llu, \"experts_faux_brut_avant\": %llu, \"experts_faux_apres\": %llu}\n}\n",
            l, n, passes, (unsigned long long)octets_codes, (unsigned long long)octets_sortie,
            (double)octets_parties / n, reps[0] * (int)n * 2, reps[1] * (int)n, liste(temps[0]).c_str(),
            liste(temps[1]).c_str(), tA, tB, disp(temps[0]), disp(temps[1]), octets_codes / tA / 1e9,
            octets_codes / tB / 1e9, octets_codes / *std::max_element(temps[0].begin(), temps[0].end()) / 1e9,
            octets_sortie / tA / 1e9, octets_sortie / tB / 1e9, (double)octets_parties / n / tA / 1e9,
            mediane(latence), *std::min_element(latence.begin(), latence.end()),
            *std::max_element(latence.begin(), latence.end()), mediane(t_ech), mediane(t_cod),
            t_trou.empty() ? 0.0 : mediane(t_trou), liste(temps[2]).c_str(), tC, disp(temps[2]), octets_codes / tC / 1e9,
            octets_codes / pireC / 1e9, (octets_codes / pireC / 1e9 >= seuil) ? "true" : "false",
            (unsigned long long)faux_lot_avant, (unsigned long long)faux_lot_apres, seuil,
            (octets_codes / *std::max_element(temps[0].begin(), temps[0].end()) / 1e9 >= seuil) ? "true" : "false",
            (unsigned long long)faux_avant, (unsigned long long)faux_brut_avant, (unsigned long long)faux_apres);
    fclose(jo);
    fprintf(stderr, "C (lot de %u) : %.1f Go/s de codes (médiane), pire %.1f ; faux %llu/%llu\n", n, octets_codes / tC / 1e9,
            octets_codes / pireC / 1e9, (unsigned long long)faux_lot_avant, (unsigned long long)faux_lot_apres);
    fprintf(stderr, "A (décodage) : %.1f Go/s de codes (médiane), %.3f ms par expert ; B (brut) : %.1f Go/s ; latence %.3f ms ; échelles %.1f us, codes %.1f us, trou %.1f us ; faux %llu/%llu/%llu\n",
            octets_codes / tA / 1e9, tA * 1e3, octets_codes / tB / 1e9, mediane(latence) * 1e3, mediane(t_ech) * 1e6,
            mediane(t_cod) * 1e6, t_trou.empty() ? 0.0 : mediane(t_trou) * 1e6,
            (unsigned long long)faux_avant, (unsigned long long)faux_brut_avant, (unsigned long long)faux_apres);
    return 0;
}

// ---------------------------------------------------------------------------------
// GEMV : emplacements construits directement depuis la source (sans codage), et
// référence sur le processeur.

static double valeur_poids(uint8_t code, uint8_t e) {  // k[code] · 2^(e − 128), exact en double
    static const double k[8] = {0, 1, 2, 3, 4, 6, 8, 12};
    const double v = std::ldexp(k[code & 7], (int)e - 128);
    return (code & 8) ? -v : v;
}

// y64 = W x + b en double, depuis un emplacement (disposition SoA) d'une matrice.
static void gemv_ref(const uint8_t* mat, uint32_t R, uint32_t C, const float* x, double* y) {
    const trc::Disposition d = trc::disposition_matrice(R, C);
    const uint32_t B = C / 32;
    for (uint32_t r = 0; r < R; ++r) {
        double s = 0;
        for (uint32_t b = 0; b < B; ++b) {
            const uint64_t beta = (uint64_t)r * B + b;
            const uint8_t e = mat[d.echelles + beta];
            const uint8_t* q = mat + 16 * beta;
            for (int i = 0; i < 16; ++i) {
                s += valeur_poids(q[i] & 15, e) * x[32 * b + i];
                s += valeur_poids(q[i] >> 4, e) * x[32 * b + 16 + i];
            }
        }
        float bf;
        memcpy(&bf, mat + d.biais + 4ull * r, 4);
        y[r] = s + bf;
    }
}

struct MatriceHote {
    uint32_t R, C;
    std::vector<uint8_t> octets;  // pas de la matrice (codes, échelles, biais)
    std::vector<float> x;
};

static int justesse_gemv(int argc, char** argv) {
    if (argc < 5) mourir("justesse-gemv <gguf> <couche> <journal.json> [--casser]");
    FILE* jo = fopen(argv[4], "w");
    if (!jo) mourir("journal");
    const bool casser = drapeau(argc, argv, "--casser");
    const double decalage = casser ? 1.01 : 1.0;  // cassure : référence décalée de 1 %
    entete_journal(jo, "justesse-gemv", argc, argv);
    fprintf(jo, "  \"casser\": %s, \"seuil_ecart_relatif\": 1e-5,\n", casser ? "true" : "false");
    Alea a(20261015);

    auto lancer_une = [&](const MatriceHote& m, std::vector<float>& y_seul, std::vector<float>& y_lot) {
        uint8_t* d_m;
        float *d_x, *d_y, *d_y2;
        trc::DescGemv* d_desc;
        VERIF(cudaMalloc(&d_m, m.octets.size()));
        VERIF(cudaMalloc(&d_x, 4ull * m.C));
        VERIF(cudaMalloc(&d_y, 4ull * m.R));
        VERIF(cudaMalloc(&d_y2, 4ull * m.R));
        VERIF(cudaMalloc(&d_desc, sizeof(trc::DescGemv)));
        VERIF(cudaMemcpy(d_m, m.octets.data(), m.octets.size(), cudaMemcpyHostToDevice));
        VERIF(cudaMemcpy(d_x, m.x.data(), 4ull * m.C, cudaMemcpyHostToDevice));
        VERIF(cudaMemset(d_y, 0xFF, 4ull * m.R));
        VERIF(cudaMemset(d_y2, 0xFF, 4ull * m.R));
        trc::DescGemv dsc{(uint64_t)d_m, (uint64_t)d_x, (uint64_t)d_y2, m.R, m.C};
        VERIF(cudaMemcpy(d_desc, &dsc, sizeof dsc, cudaMemcpyHostToDevice));
        gemv_mxfp4<<<(m.R + 31) / 32, 256>>>(d_m, d_x, d_y, m.R, m.C);
        gemv_mxfp4_lot<<<dim3((m.R + 31) / 32, 1), 256>>>(d_desc);
        VERIF(cudaGetLastError());
        VERIF(cudaDeviceSynchronize());
        y_seul.resize(m.R);
        y_lot.resize(m.R);
        VERIF(cudaMemcpy(y_seul.data(), d_y, 4ull * m.R, cudaMemcpyDeviceToHost));
        VERIF(cudaMemcpy(y_lot.data(), d_y2, 4ull * m.R, cudaMemcpyDeviceToHost));
        cudaFree(d_m); cudaFree(d_x); cudaFree(d_y); cudaFree(d_y2); cudaFree(d_desc);
    };

    // (1) Exactitude au bit sur entiers : e ∈ [126, 130], x ∈ {−2..2}, biais entiers.
    // Chaque terme est un multiple de 1/4 d'au plus 12 · 4 · 2 = 96 ; une somme de 4 096
    // termes reste sous 2^19 : tout tient dans les 24 bits de la mantisse, dans
    // n'importe quel ordre. La référence (double, exacte ici) doit donc être égalée au bit.
    fprintf(jo, "  \"entiers\": [\n");
    const uint32_t formes[5][2] = {{2880, 2880}, {37, 96}, {5, 32}, {100, 4096}, {33, 2880}};
    uint64_t faux_entiers_total = 0;
    for (int f = 0; f < 5; ++f) {
        MatriceHote m;
        m.R = formes[f][0];
        m.C = formes[f][1];
        const trc::Disposition d = trc::disposition_matrice(m.R, m.C);
        m.octets.assign(d.pas, 0);
        const uint64_t nb = (uint64_t)m.R * (m.C / 32);
        for (uint64_t i = 0; i < 16 * nb; ++i) m.octets[i] = (uint8_t)a.suivant();
        for (uint64_t i = 0; i < nb; ++i) m.octets[d.echelles + i] = (uint8_t)(126 + a.suivant() % 5);
        for (uint32_t r = 0; r < m.R; ++r) {
            const float bf = (float)((int)(a.suivant() % 101) - 50);
            memcpy(&m.octets[d.biais + 4ull * r], &bf, 4);
        }
        m.x.resize(m.C);
        for (auto& v : m.x) v = (float)((int)(a.suivant() % 5) - 2);
        std::vector<double> y64(m.R);
        gemv_ref(m.octets.data(), m.R, m.C, m.x.data(), y64.data());
        std::vector<float> ys, yl;
        lancer_une(m, ys, yl);
        uint64_t faux = 0, faux_lot = 0;
        for (uint32_t r = 0; r < m.R; ++r) {
            const float ref = (float)(y64[r] * decalage);
            faux += memcmp(&ys[r], &ref, 4) != 0;
            faux_lot += memcmp(&yl[r], &ref, 4) != 0;
        }
        faux_entiers_total += faux + faux_lot;
        fprintf(jo, "    {\"lignes\": %u, \"colonnes\": %u, \"lignes_fausses\": %llu, \"lignes_fausses_lot\": %llu}%s\n", m.R,
                m.C, (unsigned long long)faux, (unsigned long long)faux_lot, f < 4 ? "," : "");
    }
    fprintf(jo, "  ],\n");

    // (2) Les 256 échelles E8M0 : ligne r d'un bloc, code 1 (k = 1) au poids 0, x = e_0 :
    // y[r] = 2^(r − 128) exactement, sous-normaux (r = 0, 1) compris.
    uint64_t faux_e8m0 = 0;
    {
        MatriceHote m;
        m.R = 256;
        m.C = 32;
        const trc::Disposition d = trc::disposition_matrice(m.R, m.C);
        m.octets.assign(d.pas, 0);
        for (uint32_t r = 0; r < 256; ++r) {
            m.octets[16ull * r] = 0x01;
            m.octets[d.echelles + r] = (uint8_t)r;
        }
        m.x.assign(32, 0.0f);
        m.x[0] = 1.0f;
        std::vector<float> ys, yl;
        lancer_une(m, ys, yl);
        for (uint32_t r = 0; r < 256; ++r) {
            const float ref = (float)(std::ldexp(1.0, (int)r - 128) * decalage);
            faux_e8m0 += (memcmp(&ys[r], &ref, 4) != 0) + (memcmp(&yl[r], &ref, 4) != 0);
        }
    }
    fprintf(jo, "  \"e8m0_256_valeurs_fausses\": %llu,\n", (unsigned long long)faux_e8m0);

    // (3) Poids réels (8 experts × 3 matrices de la couche), x ~ N(0, 1) en f32,
    // écart relatif max |y − y64| / max |y64| contre la référence en double ; égalité au
    // bit entre gemv_mxfp4 et gemv_mxfp4_lot.
    Gguf g = lire_gguf(argv[2]);
    Couche c = lire_couche(g, atoi(argv[3]));
    double pire = 0;
    uint64_t lot_different = 0;
    fprintf(jo, "  \"reels\": [\n");
    const uint32_t nexp = std::min<uint32_t>(8, c.E);
    for (uint32_t x = 0; x < nexp; ++x) {
        for (int j = 0; j < 3; ++j) {
            MatriceSource s = extraire(c, x, j);
            MatriceHote m;
            m.R = s.R;
            m.C = s.C;
            const trc::Disposition d = trc::disposition_matrice(m.R, m.C);
            m.octets.assign(d.pas, 0);
            memcpy(&m.octets[0], s.qs.data(), s.qs.size());
            memcpy(&m.octets[d.echelles], s.e.data(), s.e.size());
            memcpy(&m.octets[d.biais], s.biais.data(), s.biais.size());
            m.x.resize(m.C);
            for (auto& v : m.x) v = (float)a.normale();
            std::vector<double> y64(m.R);
            gemv_ref(m.octets.data(), m.R, m.C, m.x.data(), y64.data());
            std::vector<float> ys, yl;
            lancer_une(m, ys, yl);
            double emax = 0, ymax = 0;
            for (uint32_t r = 0; r < m.R; ++r) {
                emax = std::max(emax, std::fabs((double)ys[r] - y64[r] * decalage));
                ymax = std::max(ymax, std::fabs(y64[r] * decalage));
            }
            lot_different += memcmp(ys.data(), yl.data(), 4ull * m.R) != 0;
            const double rel = emax / ymax;
            pire = std::max(pire, rel);
            fprintf(jo, "    {\"expert\": %u, \"matrice\": %d, \"ecart_relatif\": %.3e, \"max_y\": %.4e}%s\n", x, j, rel,
                    ymax, (x + 1 == nexp && j == 2) ? "" : ",");
        }
    }
    const bool tient = faux_entiers_total == 0 && faux_e8m0 == 0 && pire <= 1e-5 && lot_different == 0;
    fprintf(jo,
            "  ],\n  \"pire_ecart_relatif\": %.3e, \"lot_different_du_seul\": %llu, \"lignes_entieres_fausses\": %llu,\n"
            "  \"temoin_tient\": %s\n}\n",
            pire, (unsigned long long)lot_different, (unsigned long long)faux_entiers_total, tient ? "true" : "false");
    fclose(jo);
    fprintf(stderr, "gemv : entiers faux %llu, e8m0 faux %llu, pire écart %.3e, lot ≠ seul %llu -> %s\n",
            (unsigned long long)faux_entiers_total, (unsigned long long)faux_e8m0, pire,
            (unsigned long long)lot_different, tient ? "tient" : "tombe");
    return 0;
}

// ---------------------------------------------------------------------------------
// Mode debit-gemv (seuil de K2).
//
// n emplacements réels (couche donnée, experts 0 .. n − 1) en VRAM ; groupes de 4
// experts = 12 matrices (ce que demande une couche du modèle). A : un lancement
// gemv_mxfp4_lot par groupe ; B : un lancement gemv_mxfp4 par matrice. Les groupes
// tournent, si bien que chaque lancement lit des poids absents du cache L2.
// Débit en Go/s de MXFP4 équivalents (poids × 17 / 32), l'unité du 209,4 de l'étude 03.

static int debit_gemv(int argc, char** argv) {
    if (argc < 5) mourir("debit-gemv <gguf> <couche> <journal.json> [--experts n] [--passes p]");
    FILE* jo = fopen(argv[4], "w");
    if (!jo) mourir("journal");
    uint32_t n = (uint32_t)atoi(option(argc, argv, "--experts", "24"));
    n = n / 4 * 4;
    const int passes = atoi(option(argc, argv, "--passes", "5"));
    entete_journal(jo, "debit-gemv", argc, argv);
    Gguf g = lire_gguf(argv[2]);
    Couche c = lire_couche(g, atoi(argv[3]));
    if (n > c.E) n = c.E / 4 * 4;
    const uint64_t te = taille_emplacement(c.dims);
    uint8_t* d_empl;
    float *d_x, *d_y;
    trc::DescGemv* d_desc;
    VERIF(cudaMalloc(&d_empl, n * te));
    uint32_t cmax = 0, rmax = 0;
    for (int j = 0; j < 3; ++j) { cmax = std::max(cmax, c.dims.colonnes[j]); rmax = std::max(rmax, c.dims.lignes[j]); }
    VERIF(cudaMalloc(&d_x, 4ull * cmax * 3 * n));
    VERIF(cudaMalloc(&d_y, 4ull * rmax * 3 * n));
    Alea a(7);
    std::vector<float> xs(3ull * n * cmax);
    for (auto& v : xs) v = (float)a.normale();
    VERIF(cudaMemcpy(d_x, xs.data(), xs.size() * 4, cudaMemcpyHostToDevice));
    std::vector<trc::DescGemv> descs;
    double poids_par_groupe = 0;
    for (uint32_t x = 0; x < n; ++x) {
        std::vector<uint8_t> h(te, 0);
        for (int j = 0; j < 3; ++j) {
            MatriceSource s = extraire(c, x, j);
            const trc::Disposition d = trc::disposition(c.dims, j);
            memcpy(&h[d.base], s.qs.data(), s.qs.size());
            memcpy(&h[d.base + d.echelles], s.e.data(), s.e.size());
            memcpy(&h[d.base + d.biais], s.biais.data(), s.biais.size());
            descs.push_back({(uint64_t)(d_empl + x * te + d.base), (uint64_t)(d_x + (3ull * x + j) * cmax),
                             (uint64_t)(d_y + (3ull * x + j) * rmax), s.R, s.C});
            if (x < 4) poids_par_groupe += (double)s.R * s.C;
        }
        VERIF(cudaMemcpy(d_empl + x * te, h.data(), te, cudaMemcpyHostToDevice));
    }
    VERIF(cudaMalloc(&d_desc, descs.size() * sizeof(trc::DescGemv)));
    VERIF(cudaMemcpy(d_desc, descs.data(), descs.size() * sizeof(trc::DescGemv), cudaMemcpyHostToDevice));
    const uint32_t groupes = n / 4;
    cudaEvent_t e0, e1;
    VERIF(cudaEventCreate(&e0));
    VERIF(cudaEventCreate(&e1));
    auto serie = [&](int quoi, int reps) -> double {
        VERIF(cudaEventRecord(e0));
        for (int r = 0; r < reps; ++r)
            for (uint32_t gi = 0; gi < groupes; ++gi) {
                if (quoi == 0) {
                    gemv_mxfp4_lot<<<dim3((rmax + 31) / 32, 12), 256>>>(d_desc + 12 * gi);
                } else {
                    for (int k = 0; k < 12; ++k) {
                        const trc::DescGemv& dd = descs[12 * gi + k];
                        gemv_mxfp4<<<(dd.lignes + 31) / 32, 256>>>((const uint8_t*)dd.matrice, (const float*)dd.x,
                                                                    (float*)dd.y, dd.lignes, dd.colonnes);
                    }
                }
            }
        VERIF(cudaEventRecord(e1));
        VERIF(cudaEventSynchronize(e1));
        float ms;
        VERIF(cudaEventElapsedTime(&ms, e0, e1));
        return ms / 1e3 / (reps * (double)groupes);  // secondes par groupe de 12 matrices
    };
    int reps[2];
    for (int q = 0; q < 2; ++q) {
        serie(q, 2);
        const double t = serie(q, 3);
        reps[q] = std::max(3, std::min(20000, (int)(0.25 / (t * groupes)) + 1));
    }
    std::vector<double> temps[2];
    const int ordre[4] = {0, 1, 1, 0};
    for (int p = 0; p < passes; ++p)
        for (int q : ordre) temps[q].push_back(serie(q, reps[q]));
    VERIF(cudaGetLastError());
    // Latence d'un lot seul (une couche : 12 matrices), flux vide avant et après.
    std::vector<double> latence;
    for (int r = 0; r < 40; ++r) {
        VERIF(cudaDeviceSynchronize());
        VERIF(cudaEventRecord(e0));
        gemv_mxfp4_lot<<<dim3((rmax + 31) / 32, 12), 256>>>(d_desc + 12 * (r % groupes));
        VERIF(cudaEventRecord(e1));
        VERIF(cudaEventSynchronize(e1));
        float ms;
        VERIF(cudaEventElapsedTime(&ms, e0, e1));
        latence.push_back(ms * 1e-3);
    }
    const double octets_equiv = poids_par_groupe * 17.0 / 32.0;
    double octets_lus = 0;  // codes + échelles + biais + x, par groupe
    for (int k = 0; k < 12; ++k) {
        const trc::DescGemv& dd = descs[k];
        octets_lus += (double)dd.lignes * dd.colonnes * 17 / 32 + 4.0 * dd.lignes + 4.0 * dd.colonnes;
    }
    const double tA = mediane(temps[0]), tB = mediane(temps[1]);
    const double pireA = *std::max_element(temps[0].begin(), temps[0].end());
    auto disp = [](const std::vector<double>& v) {
        return (*std::max_element(v.begin(), v.end()) - *std::min_element(v.begin(), v.end())) /
               *std::min_element(v.begin(), v.end());
    };
    const double seuil = 0.8 * 209.4;
    fprintf(jo,
            "  \"couche\": %s, \"experts\": %u, \"groupes\": %u, \"passes\": %d, \"ordre\": \"A B B A\",\n"
            "  \"A\": \"gemv_mxfp4_lot, 12 matrices par lancement\", \"B\": \"gemv_mxfp4, une matrice par lancement\",\n"
            "  \"octets_vram_occupes\": %llu, \"octets_equiv_par_groupe\": %.0f, \"octets_lus_par_groupe\": %.0f,\n"
            "  \"temps_s_par_groupe\": {\"A\": %s, \"B\": %s},\n"
            "  \"mediane_s_par_groupe\": {\"A\": %.6e, \"B\": %.6e},\n"
            "  \"dispersion\": {\"A\": %.4f, \"B\": %.4f},\n"
            "  \"go_s_equiv\": {\"A\": %.2f, \"B\": %.2f, \"A_pire\": %.2f},\n"
            "  \"go_s_lus\": {\"A\": %.2f, \"B\": %.2f},\n"
            "  \"latence_lot_seul_s\": {\"mediane\": %.6e, \"min\": %.6e, \"max\": %.6e},\n"
            "  \"seuil_go_s_equiv\": %.2f, \"seuil_source\": \"0,8 x 209,4 Go/s (ARCHITECTURE.md 6.5, K2)\",\n"
            "  \"seuil_tient\": %s\n}\n",
            argv[3], n, groupes, passes, (unsigned long long)(n * te), octets_equiv, octets_lus, liste(temps[0]).c_str(),
            liste(temps[1]).c_str(), tA, tB, disp(temps[0]), disp(temps[1]), octets_equiv / tA / 1e9,
            octets_equiv / tB / 1e9, octets_equiv / pireA / 1e9, octets_lus / tA / 1e9, octets_lus / tB / 1e9,
            mediane(latence), *std::min_element(latence.begin(), latence.end()),
            *std::max_element(latence.begin(), latence.end()), seuil,
            octets_equiv / pireA / 1e9 >= seuil ? "true" : "false");
    fclose(jo);
    fprintf(stderr, "gemv : A (lot) %.1f Go/s équiv., B (seul) %.1f ; latence d'une couche %.1f us\n",
            octets_equiv / tA / 1e9, octets_equiv / tB / 1e9, mediane(latence) * 1e6);
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage : banc_k justesse-decodeur | debit-decodeur | justesse-gemv | debit-gemv ...\n");
        return 1;
    }
    const std::string mode = argv[1];
    if (const char* f = getenv("TRC_FILS_ECH")) FILS_ECH = (uint32_t)atoi(f);
    if (const char* f = getenv("TRC_N_DELTA")) N_DELTA = (uint32_t)atoi(f);
    if (mode == "justesse-decodeur") return justesse_decodeur(argc, argv);
    if (mode == "debit-decodeur") return debit_decodeur(argc, argv);
    if (mode == "justesse-gemv") return justesse_gemv(argc, argv);
    if (mode == "debit-gemv") return debit_gemv(argc, argv);
    mourir("mode inconnu");
}
