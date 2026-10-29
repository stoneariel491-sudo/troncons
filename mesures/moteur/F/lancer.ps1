# Lance trc-codeur en priorité « sous la normale » (machine partagée), sorties redirigées,
# et note l'alimentation (Win32_Battery.BatteryStatus : 2 = sur secteur) avant et après.
# Usage : powershell -NoProfile -File mesures/moteur/F/lancer.ps1 <nom du journal> <arguments de trc-codeur…>
param([string]$Nom, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Reste)
$exe = '~\dev\cibles\troncons-F\release\trc-codeur.exe'
$dos = '~\dev\active\troncons\mesures\moteur\F\journaux'
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"debut $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim" | Out-File -Encoding utf8 "$dos\$Nom.cadre.txt"
$p = Start-Process -FilePath $exe -ArgumentList $Reste -RedirectStandardOutput "$dos\$Nom.sortie.json" -RedirectStandardError "$dos\$Nom.err.txt" -PassThru -NoNewWindow
$null = $p.Handle   # garde le descripteur : sans lui, ExitCode reste vide après la fin
$p.PriorityClass = 'BelowNormal'
$pointe = 0
while (-not $p.HasExited) { try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $pointe) { $pointe = $p.PeakWorkingSet64 } } catch {}; Start-Sleep -Milliseconds 500 }
$p.WaitForExit()
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"fin $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim code $($p.ExitCode) pointe_ensemble_de_travail_octets $pointe" | Out-File -Append -Encoding utf8 "$dos\$Nom.cadre.txt"
exit $p.ExitCode
