# Lance trc-codeur (cible du lot A, codon), sorties redirigées ;
# note l'alimentation (Win32_Battery.BatteryStatus : 2 = sur secteur) avant et après, et la pointe de
# l'ensemble de travail. Reprend la forme de mesures/moteur/F/lancer.ps1 (lot F).
# Usage : powershell -NoProfile -File outils/genome/construction/codon/lancer.ps1 <nom> <arguments de trc-codeur…>
param([string]$Nom, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Reste)
$exe = '~\dev\cibles\troncons-codon\release\trc-codeur.exe'
$dos = '~\dev\active\troncons\mesures\genome\construction\codon\journaux'
New-Item -ItemType Directory -Force $dos | Out-Null
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"debut $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim" | Out-File -Encoding utf8 "$dos\$Nom.cadre.txt"
$p = Start-Process -FilePath $exe -ArgumentList $Reste -RedirectStandardOutput "$dos\$Nom.sortie.json" -RedirectStandardError "$dos\$Nom.err.txt" -PassThru -NoNewWindow
$null = $p.Handle
# Priorité normale (pas « sous la normale ») : le 2026-10-17 à 08 h 37, sous la normale, le codeur
# lisait 16 Mio toutes les 15 à 30 s, fils « prêts » mais non servis, processeur à 11 %, disque au repos,
# pendant que quatre processus Python d'une autre équipe tournaient ; [hyp.] ordonnancement des
# processus d'arrière-plan de basse priorité (mode efficacité) sur un processeur hybride.
$pointe = 0
while (-not $p.HasExited) { try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $pointe) { $pointe = $p.PeakWorkingSet64 } } catch {}; Start-Sleep -Milliseconds 500 }
$p.WaitForExit()
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"fin $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim code $($p.ExitCode) pointe_ensemble_de_travail_octets $pointe" | Out-File -Append -Encoding utf8 "$dos\$Nom.cadre.txt"
exit $p.ExitCode
