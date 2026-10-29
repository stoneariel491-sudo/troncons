# 03 · Dérivations, structures et théorèmes (pour le mémoire)

Compagnon de `fondations/03-entropie.md`. Ici, chaque résultat est posé en entier : les
structures au bit près, les énoncés, les démonstrations, les calculs pas à pas. Les
nombres viennent des journaux de `fondations/journaux/03-entropie/` ; les figures se
régénèrent depuis `fondations/journaux/03-entropie/csv/` par
`outils/03-entropie/vers_csv.py`. Notation : $\lfloor\cdot\rfloor$ partie entière,
$H$ entropie de Shannon en bits, $\log = \log_2$.

---

## 1. Les structures, au bit près

### 1.1 Le bloc Q4_K de llama.cpp (256 poids, 144 octets, 4,5 bits par poids)

Redérivé de `ggml-common.h` (llama.cpp, MIT) et vérifié par le témoin
`temoin_champs.py` (déquantification égale à celle de `gguf`, écart nul).

```
octet   0      2      4                16                                   144
        +------+------+-----------------+------------------------------------+
        |  d   | dmin |  scales[12]     |  qs[128] : 256 codes de 4 bits     |
        | f16  | f16  | 8 × (6+6) bits  |  4 groupes de 32 octets            |
        +------+------+-----------------+------------------------------------+

scales[12] : pour les sous-blocs j = 0..3 :  échelle_j = scales[j] & 63
                                            minimum_j = scales[j+4] & 63
             pour j = 4..7 : échelle_j = (scales[j+4] & 0x0F) | ((scales[j-4] >> 6) << 4)
                             minimum_j = (scales[j+4] >> 4)   | ((scales[j]   >> 6) << 4)
qs : groupe g (0..3) = qs[32g .. 32g+31] ; poids 64g + i   = qs[32g+i] & 0x0F   (i < 32)
                                           poids 64g+32+i  = qs[32g+i] >> 4
valeur(poids k du sous-bloc j) = d · échelle_j · code_k − dmin · minimum_j
```

Bilan : 16 bits (d) + 16 (dmin) + 8 × 12 (échelles et minimums) + 256 × 4 = 1 152 bits
pour 256 poids, soit 4,5 bits par poids, dont 0,5 de métadonnées.

### 1.2 Le bloc MXFP4 (32 poids, 17 octets, 4,25 bits par poids)

Format de l'OCP (Microscaling Formats v1.0) ; disposition de `block_mxfp4` dans
`ggml-common.h`, redérivée et vérifiée par `temoin_champs.py` (journal
`temoin-champs-mxfp4.log`).

```
octet   0    1                                   17
        +----+-----------------------------------+
        | e  |  qs[16] : 32 codes E2M1 de 4 bits |
        |E8M0|                                   |
        +----+-----------------------------------+
qs[i] & 0x0F -> poids i        qs[i] >> 4 -> poids 16 + i        (i = 0..15)

code E2M1 (4 bits) :  b3   b2 b1   b0
                      signe exposant mantisse
grandeur (doublée, entière) : 0 1 2 3 4 6 8 12  pour b2b1b0 = 0..7
valeur = (−1)^b3 · grandeur · 2^(e − 128)
```

Les huit grandeurs doublées tiennent dans un seul mot de 32 bits, un demi-octet chacune :
`0xC8643210`. La déquantification d'un code $c$ est alors
$g = (\texttt{0xC8643210} \gg 4(c \,\&\, 7)) \,\&\, 15$, puis le signe du bit 3. C'est ce
que fait `valeurs4` dans `gemv.wgsl` : trois opérations entières et une conversion par
code, sans table en mémoire.

Bilan : 8 bits (e) + 32 × 4 bits = 136 bits pour 32 poids, soit 4,25 bits par poids, dont
0,25 d'échelle.

### 1.3 La tuile du codeur rANS entrelacé (format de troncons)

```
Une tuile : 32 voies (un sous-groupe) × N macro-pas (N = 256 par défaut)

         voie 0     voie 1     ...    voie 31
m = 0  [ mot 0   ][ mot 1   ]  ...  [ mot 31  ]   <- 128 octets contigus de sortie
m = 1  [ mot 32  ][ mot 33  ]  ...  [ mot 63  ]
 ...
m = N-1[ ...                                    ]

En-tête de tuile (stocké) : premier mot de 16 bits du flux partagé (4 o)
États initiaux (stockés)  : 32 × 32 bits = 128 o
Flux partagé              : mots de 16 bits, lus dans l'ordre des voies à chaque sous-pas
```

Alphabet 16 (v1 à v3) : 8 sous-pas par mot de sortie (un code de 4 bits par sous-pas).
Alphabet 256 (v4) : 4 sous-pas par mot de sortie (un octet par sous-pas).

Entrée de la table de décodage (4 096 fentes, 32 bits chacune) :

```
v1-v3 (alphabet 16) :  bits 31..17  |  16..4      |  3..0
                       biais (15)   |  f (13)     |  symbole (4)

v4 (alphabet 256)   :  bits 31..20  |  19..8      |  7..0
                       biais (12)   |  f − 1 (12) |  symbole (8)
```

avec biais = fente − cumul(symbole). Pour v4, $f \le 4096$ se range sur 12 bits sous la
forme $f-1$ ; le biais est $< f \le 4096$, donc tient aussi sur 12 bits.

### 1.4 Coût des en-têtes (calculé)

Par tuile de $N$ macro-pas : $32 \times 4 \times N$ octets de source, et $4 + 32 \times 4 =
132$ octets d'en-tête et d'états. Pour $N = 256$ : $132 / 32\,768 = 0{,}403\,\%$.

---

## 2. Le rANS : exactitude et bornes

Paramètres : $M = 2^{12}$ (précision des probabilités), $L = 2^{16}$ (borne basse de l'état),
mots de $b = 16$ bits, état sur 32 bits. Pour un symbole $s$ : fréquence $f_s \ge 1$,
cumul $c_s = \sum_{t<s} f_t$, $\sum_s f_s = M$.

**Définition (pas de codage et de décodage).**
$$C(s, x) = \left\lfloor \frac{x}{f_s} \right\rfloor M + (x \bmod f_s) + c_s,
\qquad
D(x) = \bigl(s,\; f_s \lfloor x/M \rfloor + (x \bmod M) - c_s\bigr),$$
où, dans $D$, $s$ est l'unique symbole tel que $c_s \le x \bmod M < c_s + f_s$.

**Lemme 1 (inversion).** Pour tout $s$ et tout $x \ge 0$, $D(C(s,x)) = (s, x)$.

*Démonstration.* Posons $q = \lfloor x/f_s \rfloor$, $r = x \bmod f_s$, donc $0 \le r < f_s$ et
$x = q f_s + r$. Alors $y = C(s,x) = qM + r + c_s$ avec $0 \le r + c_s < c_s + f_s \le M$.
Donc $\lfloor y/M \rfloor = q$ et $y \bmod M = r + c_s \in [c_s, c_s + f_s)$ : la fente
désigne bien $s$. Enfin $f_s \lfloor y/M\rfloor + (y \bmod M) - c_s = f_s q + r = x$. $\square$

**Lemme 2 (intervalle et une seule lecture par pas).** Si le décodeur maintient
$x \in [L, 2^{32})$ et applique : $x \leftarrow D(x)_2$, puis, si $x < L$,
$x \leftarrow 2^{16} x + w$ avec $w$ le mot suivant du flux, alors un seul mot suffit
toujours, et l'état revient dans $[L, 2^{32})$.

*Démonstration.* Après $D$, $x' = f_s\lfloor x/M\rfloor + (x \bmod M) - c_s \ge
f_s \lfloor L/M \rfloor = 16 f_s \ge 16$. Si $x' < L$, alors $2^{16}x' + w \ge 2^{20} > L$
et $2^{16} x' + w \le 2^{16}(L - 1) + 2^{16} - 1 < 2^{32}$. Si $x' \ge L$, on a aussi
$x' < 2^{32}$ car $x' \le x$ quand $f_s \le M$ (puisque $x' = f_s\lfloor x/M\rfloor +
(x \bmod M) - c_s \le M\lfloor x/M\rfloor + (x \bmod M) = x$). $\square$

Conséquence pour la carte : la boucle n'a qu'une branche de lecture, remplacée par un
`select`.

**Lemme 2 bis (le codeur, symétrique).** Le codeur maintient $x \in [L, 2^{32})$, part de
$x = L$ et, pour coder $s$ : si $x \ge f_s 2^{20}$, il émet $x \bmod 2^{16}$ et pose
$x \leftarrow \lfloor x/2^{16} \rfloor$ ; puis $x \leftarrow C(s, x)$. Une émission suffit
toujours, et $C(s,x) \in [L, 2^{32})$.

*Démonstration.* Montrons qu'avant $C$, $x \in [16 f_s,\, 2^{20} f_s)$.
Sans émission, $x < 2^{20} f_s$ par la condition, et $x \ge L = 2^{16} = 16M \ge 16 f_s$.
Avec émission, $x \ge 2^{20} f_s$ donne $\lfloor x/2^{16}\rfloor \ge 16 f_s$, et $x < 2^{32}$
donne $\lfloor x/2^{16}\rfloor < 2^{16} \le 2^{20} f_s$. Ensuite, avec $q = \lfloor
x/f_s\rfloor \in [16,\, 2^{20} - 1]$ : $C(s,x) = qM + r + c_s \ge 16 M = L$, et
$C(s,x) \le (2^{20} - 1) M + (M - 1) = 2^{32} - 1$. $\square$

La condition d'émission $x \ge f_s 2^{20}$ avant $C$ et la condition de lecture $x' < L$
après $D$ sont les deux faces de la même transition : par le Lemme 1, l'état que lit le
décodeur juste après $D$ est l'état du codeur juste avant $C$, soit $x \in [16 f_s, 2^{20}
f_s)$ ; il est sous $L$ exactement quand le codeur avait émis.

**Lemme 3 (flux partagé entre 32 voies).** Soit, au sous-pas $k$, $b_\ell \in \{0,1\}$
l'indicateur « la voie $\ell$ renormalise ». Si le décodeur donne à la voie $\ell$ la position
$p + \sum_{j<\ell} b_j$ puis avance $p$ de $\sum_j b_j$, et si le codeur parcourt les
symboles dans l'ordre exactement inverse (macro-pas, sous-pas, voies décroissants), en
émettant avant de coder, puis renverse sa pile, alors chaque voie lit exactement le mot
que son codeur a émis.

*Démonstration.* Le codage d'une voie est une pile (dernier émis, premier lu). Les voies
étant entrelacées, la pile globale reçoit, pour le sous-pas $k$ parcouru à rebours, les
mots des voies $31, 30, \ldots, 0$ (celles qui émettent). Renversée, elle présente pour le
sous-pas $k$ dans l'ordre direct les mots des voies $0, 1, \ldots, 31$, et chaque voie qui
émettait au codage est exactement une voie qui lit au décodage (Lemme 1 appliqué voie par
voie, et Lemme 2 bis). La position de la
voie $\ell$ est donc le nombre de mots lus avant elle dans ce sous-pas, soit
$\sum_{j<\ell} b_j$. $\square$

Sur la carte, $\sum_{j<\ell} b_j = \mathrm{popcount}(\mathrm{ballot}(b) \,\&\, (2^\ell - 1))$ :
un vote et un comptage de bits (v2 à v4), au lieu d'une somme préfixe (v1).

**Lemme 4 (ce que le contrôle d'état garde, et ce qu'il ne garde pas).** Chaque voie part
de $L$ au codage ; le décodeur exact finit donc sur $L$. Le passage d'un état au suivant
ne dépend que de $(f_s, \text{biais})$ lus à la fente, et des mots du flux ; il ne dépend
pas du champ « symbole » de l'entrée de table. Une corruption confinée au champ symbole
change la sortie sans changer aucun état : le contrôle $x_{\text{fin}} = L$ ne la voit pas.

*Démonstration.* Dans $D$, la mise à jour de l'état s'écrit $x' = f\,\lfloor x/M\rfloor +
\text{biais}$ avec biais $= (x \bmod M) - c_s$, deux champs de l'entrée ; le symbole n'y
entre pas. $\square$

C'est exactement l'observation du témoin cassé de la v4 (§3.3 de `03-entropie.md`) :
sortie fausse, voies toutes sur $L$. Il faut donc, en production, une empreinte de la table
(ou de la sortie), en plus du contrôle d'état.

**Proposition 5 (débit de codage réel).** Pour une source i.i.d. de loi $p$ codée avec la
table quantifiée $q$ ($q_s = f_s/M$), la longueur moyenne par symbole tend vers
$H(p) + D(p\|q)$, plus le coût des en-têtes (§1.4) et la fin de flux (au plus 32 bits par
voie, compris dans les états stockés).

*Mesuré ici* (`rans-4B-*.json`) : $H(p) = 3{,}8652$, table 12 bits $3{,}8652$ (donc
$D(p\|q) < 10^{-4}$), réel $3{,}8774$ bits par code ; l'écart $0{,}0122 \approx 3{,}8652
\times 0{,}00403 = 0{,}0156$ moins l'arrondi des fins de tuiles. Les chiffres se tiennent.

---

## 3. L'entropie des codes quantifiés, et son estimateur

**Estimateur.** $\hat H = -\sum_s \hat p_s \log \hat p_s$ avec $\hat p_s = n_s / N$.
Biais de Miller–Madow : $\mathbb E[\hat H] = H - \frac{K-1}{2N\ln 2} + O(N^{-2})$, où
$K$ est le nombre de symboles de probabilité non nulle.

*Calcul* pour les codes Q4_K du 9B : $K = 16$, $N \approx 7{,}4 \times 10^9$ codes, biais
$\approx 15 / (2 \times 7{,}4\cdot 10^{9} \times 0{,}693) = 1{,}5 \times 10^{-9}$ bit.
Pour un champ d fp16 d'un petit tenseur ($K \approx 5\,000$ valeurs vues, $N = 40\,000$
blocs) : $\approx 0{,}09$ bit. C'est pourquoi le gain des métadonnées est dit optimiste
(§8 de `03-entropie.md`).

**Entropie idéale d'ordre 0 d'un bloc K.** Pour Q4_K, par poids :
$$\bar R_{\text{Q4\_K}} = H(\text{code}) + \frac{H(d) + H(d_{\min})}{256} + \frac{8\,(H(\text{éch}_6) + H(\text{min}_6))}{256}.$$
*Calcul* (9B) : $3{,}864 + (9{,}46 + 10{,}35)/256 + 8(4{,}89 + 5{,}19)/256 = 3{,}864 +
0{,}0774 + 0{,}315 = 4{,}256$ bits par poids, contre 4,5 stockés : taux $1{,}0573$.

Pour MXFP4, par poids :
$$\bar R_{\text{MXFP4}} = H(\text{code} \mid e) + \frac{H(e)}{32} \;\le\; H(\text{code}) + \frac{H(e)}{32}.$$

---

## 4. Le juge : bornes de débit d'un jeton

On note $B$ les octets de poids qu'un jeton doit lire (non compressés), $r$ le taux de
compression sans perte, $D$, $P$ les débits effectifs du disque et de la PCIe, $\Delta$ le
débit de sortie du décodeur sur la carte, $G$ le débit auquel le produit matrice-vecteur
consomme des poids décodés.

**Proposition 6 (temps d'un jeton, chaîne recouverte).** Si les étages sont recouverts
(le tronçon $i+1$ se lit pendant que le tronçon $i$ se décode et se calcule), et si le
décodeur et le produit partagent la carte, alors
$$T(r) = \max\!\left( \frac{B}{rD},\; \frac{B}{rP},\; B\left(\frac{1}{\Delta} + \frac{1}{G}\right) \right),
\qquad T(1) = \max\!\left(\frac{B}{D}, \frac{B}{P}, \frac{B}{G}\right).$$

*Démonstration.* Chaque étage traite tout le volume du jeton ; un pipeline recouvert est
borné par son étage le plus lent. Le disque et la PCIe voient $B/r$ octets. La carte
exécute en série le décodage ($B/\Delta$) et le produit ($B/G$). $\square$

**Corollaire 7 (quand la compression gagne).** Le gain $T(1)/T(r)$ vaut exactement $r$
tant que $rD \le \left(1/\Delta + 1/G\right)^{-1}$ (et $D \le P$). Au-delà, il plafonne à
$D\,(1/\Delta + 1/G)$.

*Calcul* avec les chiffres mesurés sur la machine, sur secteur : $D = 2{,}8$ Go/s
(étude 01), $P = 4$ à $12{,}2$ Go/s, $\Delta = 70$ Go/s de codes produits (décodeur v4,
Vulkan, `rans-4B-B*-secteur.json`) et $G = 209$ Go/s de poids MXFP4 consommés (produit
brut, `gemv-gptoss20b-secteur.json`) : $(1/70 + 1/209)^{-1} = 52{,}4$ Go/s
$\gg rD = 1{,}09 \times 2{,}8 = 3{,}05$ Go/s. Le gain vaut donc exactement $r$ : chaque
pour cent de compression devient un pour cent de jetons par seconde, et la carte reste
occupée à $3{,}05 / 52{,}4 \approx 6\,\%$ par le décodage et le produit réunis. Sur
batterie ($\Delta = 26{,}8$, $G = 66{,}4$) : $(1/26{,}8 + 1/66{,}4)^{-1} = 19{,}1$ Go/s,
toujours six fois $rD$.

**Proposition 8 (régime résident : fondre ne paie pas sur une carte de ce rapport).**
Quand les poids résident en VRAM (débit $V$), un produit fondu doit, par octet de poids,
lire $1/r$ octet de flux et exécuter $a_{\text{dec}} + a_{\text{mv}}$ opérations, contre
$1$ octet et $a_{\text{mv}}$ opérations pour le chemin brut. Avec $A$ le débit
arithmétique de la carte :
$$\frac{T_{\text{fondu}}}{T_{\text{brut}}} = \frac{\max\!\left(\frac{1}{rV},\, \frac{a_{\text{dec}} + a_{\text{mv}}}{A}\right)}{\max\!\left(\frac{1}{V},\, \frac{a_{\text{mv}}}{A}\right)}.$$
Le fondu gagne seulement si $(a_{\text{dec}} + a_{\text{mv}})/A < 1/V$, c'est-à-dire si la
carte a au moins $a_{\text{dec}} + a_{\text{mv}}$ opérations disponibles par octet de VRAM.

*Calcul* : un pas rANS v4 coûte environ 25 opérations entières et produit un octet (deux
poids) ; $a_{\text{dec}} \approx 25$ par octet. La RTX 4060 Laptop offre $A/V \approx
(24 \times 128 \times 2{,}0\text{–}2{,}5\,\text{GHz}) / 251\,\text{Go/s} \approx 24$ à $31$
opérations par octet (ordre de grandeur). Le décodage seul consomme donc déjà presque tout
le budget, avant la moindre multiplication : le fondu est limité par le calcul, à un débit
proche de celui du décodeur seul, quand le brut l'est par la mémoire. La mesure de
`banc_gemv` (§4.5 de `03-entropie.md`) tranche le rapport réel.

---

## 5. Distorsion-débit : ce que coûte un débit fixe

**Théorème 9 (Gish et Pierce, 1968 ; haut débit).** Une quantification uniforme de pas
$\Delta$ suivie d'un codage entropique idéal atteint, quand $\Delta \to 0$,
$$D = \frac{\Delta^2}{12}, \qquad R = H(Q) = h(X) - \log \Delta + o(1),$$
donc $R_{\text{ECSQ}}(D) = h(X) - \tfrac12 \log(12 D)$.

**Borne inférieure de Shannon.** Pour l'erreur quadratique, $R(D) \ge h(X) - \tfrac12
\log(2\pi e D)$.

**Corollaire 10 (écart de l'ECSQ).** $R_{\text{ECSQ}}(D) - R_{\text{SLB}}(D) =
\tfrac12 \log \frac{2\pi e}{12} = \tfrac12 \log \frac{\pi e}{6}$.
*Calcul* : $\pi e / 6 = 8{,}5397 / 6 = 1{,}4233$ ; $\log_2 1{,}4233 = 0{,}5092$ ;
la moitié : $0{,}2546$ bit, soit $10 \log_{10}(1{,}4233) = 1{,}53$ dB.

**Théorème 11 (Panter et Dite, 1951 ; débit fixe, haut débit).** La meilleure
quantification scalaire à $2^R$ niveaux atteint
$D \approx \frac{1}{12}\left(\int p^{1/3}\right)^3 2^{-2R}$.

*Calcul pour une gaussienne* $\mathcal N(0, \sigma^2)$ :
$\int p^{1/3} = (2\pi\sigma^2)^{-1/6} \int e^{-x^2/(6\sigma^2)}dx = (2\pi\sigma^2)^{-1/6}
\sqrt{6\pi}\,\sigma$, d'où $\left(\int p^{1/3}\right)^3 = (2\pi)^{-1/2}\sigma^{-1}
(6\pi)^{3/2}\sigma^3 = 6\sqrt{3}\,\pi\,\sigma^2$, et $D_{\text{PD}} = \frac{\sqrt3\,\pi}{2}
\sigma^2 2^{-2R}$. Comparée à $D(R) = \sigma^2 2^{-2R}$ (gaussienne, borne exacte), la
perte en débit vaut $\tfrac12 \log \frac{\sqrt3\pi}{2} = \tfrac12 \log 2{,}7207 = 0{,}722$
bit. L'ECSQ sur la même gaussienne perd $0{,}2546$ bit (Corollaire 10, car la borne de
Shannon est atteinte par la gaussienne). **Différence : $0{,}722 - 0{,}255 = 0{,}467$ bit
par poids**, ce que gagne en théorie un codage entropique sur un débit fixe optimal, à
haut débit.

*Mesuré ici* (`rd-proxy-4B.json`) : à erreur égale à un Q4_K réécrit, l'ECSQ demande
0,41 à 0,46 bit de moins, en accord avec 0,467 malgré le régime à 4 bits, qui n'est pas
asymptotique, et des sources non gaussiennes (kurtosis 3,8 à 6,6).

---

## 6. Calculs des chiffres clés (pas à pas)

1. **Octets par jeton, 9B Q4_K_M** : somme des octets de tous les tenseurs, sauf
   `token_embd` (non lié à la tête) : 5,10 Go (journal `entropie-9B.json`).
2. **Poids Q4_K par seconde au disque** : 2,8 Go/s ÷ 144 octets × 256 poids = 4,98 × 10⁹
   poids/s ; demi-octets à produire : 4,98 × 10⁹ / 2 = 2,49 Go/s.
3. **Marge du décodeur** : 65 Go/s ÷ 2,49 Go/s = 26.
4. **Jetons par seconde en flux complet, 9B** : 2,8 / 5,10 = 0,549 ; avec $r = 1{,}042$ :
   0,572 ; avec $r = 1{,}053$ : 0,578.
5. **Régime résident** : 251 Go/s ÷ 144 × 256 = 446 × 10⁹ poids Q4_K/s ; décodeur
   v4 : 130 × 10⁹ codes/s ; rapport 3,4.
6. **Métadonnées Q4_K** : stockées 0,5 bit/poids ; idéal 0,392 ; gain 0,108 bit/poids,
   contre 4 − 3,865 = 0,135 pour les codes.
7. **MXFP4, échelles** : 8 bits par bloc de 32 = 0,25 bit/poids stocké. Sur les 72
   tenseurs de gpt-oss-20b (`mxfp4-contexte-gptoss20b.json`) : $H(e) = 1{,}554$ bit à
   l'ordre 0, soit 0,049 bit/poids ; $H(e \mid \text{médiane}) + H(\text{médiane})/90 =
   1{,}011 + 0{,}015 = 1{,}026$ bit, soit 0,032 bit/poids. Gain : 0,218 bit/poids, plus que
   celui des codes eux-mêmes (4 − 3,862 = 0,138). Réel (`taux-mxfp4-gptoss20b.json`) :
   0,037 bit/poids pour les échelles, 3,866 pour les codes, total 3,903, taux
   $4{,}25 / 3{,}903 = 1{,}0888$.
8. **Effet sur le cache d'experts de gpt-oss-120b** (calculé, hypothèses de l'étude 06,
   routage uniforme) : une mémoire qui garde 26 % des experts en clair en garde
   $26\,\% \times r$ codés, soit 28,3 % avec $r = 1{,}0887$ (mesuré sur les 108 tenseurs
   d'experts de gpt-oss-120b, `taux-mxfp4-gptoss120b.json`). Octets disque par jeton :
   $(1 - h) \times 1{,}91 / r$, de $0{,}740 \times 1{,}91 = 1{,}413$ Go à
   $0{,}717 \times 1{,}91 / 1{,}0887 = 1{,}258$ Go, soit 11,0 % de moins, donc +12,4 % de
   jetons par seconde là où le disque borne. Le taux agit deux fois : sur les octets lus et
   sur la place du cache.
   Avec les trois classes d'échelle ($r = 1{,}1026$, `taux-mxfp4-classes-gptoss120b.json`) :
   $h = 26\,\% \times 1{,}1026 = 28{,}7\,\%$, octets disque
   $0{,}713 \times 1{,}91 / 1{,}1026 = 1{,}236$ Go, soit 12,6 % de moins et +14,4 % de jetons
   par seconde.

---

## 7. Ce qui pourrait être faux dans ces dérivations

- La Proposition 6 suppose un recouvrement parfait des étages ; en pratique, le premier
  tronçon d'un jeton et la synchronisation entre couches ajoutent un temps mort que
  l'étude 04 mesure.
- La Proposition 8 compte des « opérations » comme si toutes coûtaient un cycle de voie ;
  les multiplications entières 32 bits, les échanges de sous-groupe et les lectures en
  mémoire partagée n'ont pas le même débit sur Ada. Seule la mesure `banc_gemv` tranche.
- Le Théorème 11 et le Corollaire 10 sont asymptotiques (haut débit) ; à 4 bits par poids
  ils ne sont qu'indicatifs, et la mesure du §5 de `03-entropie.md` les remplace.
- Les lemmes du §2 valent pour les paramètres fixés ici ($M = 2^{12}$, $L = 2^{16}$, mots
  de 16 bits) ; ils se généralisent dès que $L$ est un multiple de $M$ et que
  $L \cdot 2^{b} \le 2^{32}$, mais ce n'est démontré ici que pour ce choix.
