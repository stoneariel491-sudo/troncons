#!/usr/bin/env bash
# Lot B, 120b (frontière seulement ; seuils : 00-seuils-declares.md § 120b, déclarés avant) :
#  T2  : `troncons generer --rapide --temoin`, 32 jetons, sur le compagnon frontière du 120b (0 erreur) ;
#  P20 : le proxy sur le 20b, là où il se valide : KL(moteur exact ‖ moteur rapide) pour les compagnons
#        λ = 0 et frontière, à mettre à côté de leur KL contre la référence f64 ;
#  P120: KL(moteur exact ‖ moteur rapide frontière) sur le 120b (--flux, comme l'épreuve J1).
# Sous le verrou de la carte (séance d'évaluation, pas de vitesse), sur secteur. Une étape faite est sautée.
# Usage (racine du dépôt) : bash outils/genome/synonyme/proxy_120b.sh
set -u
ICI="$(cd "$(dirname "$0")" && pwd)"
R="$ICI/../../../mesures/genome/construction/synonyme"
T=~/dev/cibles/troncons-synonyme/release
K=~/dev/essais/troncons/genome/synonyme/kl
M=~/dev/modeles/trc
E=~/dev/essais/troncons/genome/synonyme/trc
REF=~/dev/essais/troncons/lot-R/r1/ref-openai-20b.kld
INV=~/dev/essais/troncons/modeles/donnees/invite-wiki-3000.txt
L=~/dev/verrou-carte.txt
mkdir -p "$R/proxy"
while [ -e "$L" ] && [ $(( $(date +%s) - $(stat -c %Y "$L") )) -lt 7200 ]; do echo "verrou : $(cat $L)"; sleep 60; done
echo "lot B synonyme, $(date '+%F %T'), proxy_120b.sh (évaluations), pid $$" > "$L"
trap 'grep -q "proxy_120b.sh" "$L" 2>/dev/null && rm -f "$L"' EXIT
secteur() { al=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Battery).BatteryStatus" | tr -d '\r'); [ "$al" = "2" ] || { echo "pas sur secteur ($al)"; exit 2; }; }
if [ ! -s "$R/rapide/temoin-moteur-frontiere-120b.json" ]; then
  secteur; touch "$L"
  "$T/troncons.exe" generer --modele "$E/gpt-oss-120b-frontiere.rapide.trc" --vocab "$M/gpt-oss-120b.vocab.gguf" --invite "$INV" -n 32 \
    --rapide --temoin --journal "$R/rapide/temoin-moteur-frontiere-120b.json" --sortie "$R/rapide/temoin-moteur-frontiere-120b.txt" \
    > "$R/rapide/temoin-moteur-frontiere-120b.log" 2>&1 || echo "T2 : code $?"
fi
evaluer() { # nom modele base [options]
  local nom="$1" f="$2" b="$3"; shift 3
  [ -s "$R/proxy/evaluer-$nom.json" ] && return 0
  secteur; touch "$L"
  "$T/troncons.exe" evaluer --modele "$f" --base "$b" --fenetres 10 --sortie "$K/moteur-$nom.kld" --journal "$R/proxy/evaluer-$nom.json" "$@" \
    > "$R/proxy/evaluer-$nom.log" 2>&1 || { echo "evaluer $nom : échec"; return 1; }
  sha256sum "$K/moteur-$nom.kld" > "$R/proxy/moteur-$nom.sha256"
}
juge() { # nom base test
  "$T/juge.exe" kl --base "$2" --test "$3" --json "$R/proxy/$1.json" --csv "$R/proxy/$1.csv" > /dev/null 2> "$R/proxy/$1.log"
}
evaluer exact-20b "$M/gpt-oss-20b.trc" "$REF" || exit 1
juge kl-moteur-exact-20b-contre-ref "$REF" "$K/moteur-exact-20b.kld"
juge proxy-20b-exact-contre-rapide-l0 "$K/moteur-exact-20b.kld" "$K/moteur-synonyme-l0.kld"
juge proxy-20b-exact-contre-rapide-frontiere "$K/moteur-exact-20b.kld" "$K/moteur-frontiere.kld"
juge proxy-20b-exact-contre-rapide-l1 "$K/moteur-exact-20b.kld" "$K/moteur-synonyme.kld"
evaluer exact-120b "$M/gpt-oss-120b.trc" "$REF" --flux || exit 1
evaluer rapide-frontiere-120b "$E/gpt-oss-120b-frontiere.rapide.trc" "$K/moteur-exact-120b.kld" --flux --rapide || exit 1
juge proxy-120b-exact-contre-rapide-frontiere "$K/moteur-exact-120b.kld" "$K/moteur-rapide-frontiere-120b.kld"
# témoin du proxy : le moteur exact du 120b contre lui-même doit rendre une KL nulle et 100 % de premier choix
juge proxy-120b-temoin-exact-contre-exact "$K/moteur-exact-120b.kld" "$K/moteur-exact-120b.kld"
echo "fini"
