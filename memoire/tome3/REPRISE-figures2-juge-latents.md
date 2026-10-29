# Tome III, figures, second flux : reprise du rôle « juge des chiffres du lot latents » (2026-10-27)

Rôle : juger, après corrections, le lot « espaces latents » (commit `326969f` : III-7.6, III-9.1 (d), III-9.7).
Je n'ai rien tracé. Fichiers du rôle, et eux seuls : `outils/genome/tome3/juge2-latents/` (outils et journaux),
`memoire/tome3/JUGEMENT-figures2-latents.md`, cette note. Aucune mesure, aucune carte.

## Fait
- Lu : SOCLE, inventaire (R1 à R6), REPRISE-figures, les quatre jugements du premier flux, CONVENTIONS, la note du
  lot (`REPRISE-figures2-latents.md`), `git show 326969f`, le .tex et le script du lot.
- `juge2_regen.py` : `git archive 326969f` (fins de ligne du commit : `core.autocrlf=false`, sinon tout diffère
  par les CRLF) ; script du lot relancé hors du dépôt ; **24 fichiers latents-* égaux au bit**, aucun en trop,
  aucun manquant ; les deux cassures du lot tombent (A1 : 0,0197 ; B1 : 0,0087), données intactes ; témoin du
  comparateur : 24 sur 24 tombent.
- `juge2_lecteurs.py` (GGUF, MXFP4, .sym, captures, écrits de zéro) ; `juge2_nuage_rangee.py` : 29 nombres
  neufs ou déplacés de III-9.7 égaux ; M depuis ΔW à 2e-9 des moments des ellipses commitées ; h à 361 angles
  (5e-5, six décimales) ; rose, cône, barres égaux ; rangée : 32 lignes égales à la source. **Entrées réelles :
  rapport ‖ΔW_s x‖ / ‖ΔW_f x‖ de 0,49 à 0,81 (médiane 0,61), aucune sous 0,135** ; quadratique pondéré 0,6107 =
  √(6,155 / 16,503) du spectre commité. Rangée : j = 11 (−0) ne s'éloigne pas (0,237 des deux côtés).
- `juge2_etats.py` : 35 nombres de III-7.6 égaux ; logits relus (6 132 premiers égaux, marges à 5e-10) ; bords
  refaits dans le plan et dans l'espace d'origine (égaux au juge 1 au dernier chiffre) ; ancres égales ; pureté
  aux ancres de l'ACP : 0,07 à 0,23 pour 23, 21, 13, 4, 27.
- `juge2_barrees.py` : 238 passages barrés de 188 documents ; aucun ne revient (un faux positif : le « `~~` »
  cité par le juge 1 ; « les états de petite marge » revient corrigé, pour z(1) − z(2), mesuré) ; témoin trouvé.
- Témoins de mes comparateurs (`--casser`, valeurs faussées de 1 %) : 24 / 29 et 17 / 35 nombres tombent (les
  autres sont des entiers que 1 % ne change pas à l'arrondi).

## Incidents
- **MiKTeX mis à jour 26.2 → 26.5 vers 12 h 22** (pas par moi ; `mpmcli.log`) : LaTeX 2026-06-01 et thmtools 0.76
  ne vont plus ensemble ; le préambule commun lève 6 erreurs (« Command \c@proposition already defined »,
  lignes 190 à 195). Reproduit sur neuf lignes ; amsthm seul passe. Hors lot et hors juge : à l'orchestrateur.
- **J'ai effacé `memoire/essai/pilote-tome3-latents.pdf`** (ignoré par git) : une compilation de contrôle avec
  `-halt-on-error -output-directory=<brouillon>`, arrêtée par l'erreur du préambule, efface le PDF du même nom dans
  le dossier courant (vérifié ensuite sur un faux PDF). Remplacé par le PDF français que j'ai compilé sur les
  sources du commit (sans -halt-on-error).

## Fait, suite
- `juge2_compiler.py` : pilote du lot sur les sources de `326969f`, FR et EN, deux passes chacun : 6 pages, 0 erreur
  hors du préambule (6 dedans, thmtools), 0 boîte trop pleine, 2 trop creuses (comme le lot sous 26.2), 0 renvoi
  indéfini ; pages lues (FR 100 à 800 dpi, EN 100 dpi) ; typographie anglaise juste.
- `JUGEMENT-figures2-latents.md` écrit : G1, G2, part G9 levés ; **GN1** (III-9.7 tombe : la tête parle des
  projections comme des entrées ; « autres directions où le synonyme met l'erreur » faux pour l'erreur de sortie,
  57 % du gain y est) ; **N1 à N9** ; rien corrigé dans les fichiers du lot.

## Reste
- Rien pour ce rôle. À l'orchestrateur : GN1, N1, N2 au lot latents (N2 avec le lot synonyme) ; MiKTeX 26.5 et
  thmtools (préambule commun).
