# Lance un outil Python du lot F en priorité « sous la normale » (machine partagée), sorties
# redirigées sous journaux/, alimentation (Win32_Battery.BatteryStatus : 2 = secteur) et pointe de
# l'ensemble de travail relevées. Usage :
#   powershell -NoProfile -File mesures/moteur/F/lancer_py.ps1 <nom> <script.py> <arguments…>
param([string]$Nom, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Reste)
$dos = '~\dev\active\troncons\mesures\moteur\F\journaux'
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"debut $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim" | Out-File -Encoding utf8 "$dos\$Nom.cadre.txt"
$args2 = @('-I', '-X', 'utf8', '-u') + $Reste
$p = Start-Process -FilePath 'python' -ArgumentList $args2 -RedirectStandardOutput "$dos\$Nom.sortie.txt" -RedirectStandardError "$dos\$Nom.err.txt" -PassThru -NoNewWindow
$null = $p.Handle
$p.PriorityClass = 'BelowNormal'
$pointe = 0
while (-not $p.HasExited) { try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $pointe) { $pointe = $p.PeakWorkingSet64 } } catch {}; Start-Sleep -Milliseconds 500 }
$p.WaitForExit()
$alim = (Get-CimInstance Win32_Battery).BatteryStatus
"fin $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') alimentation $alim code $($p.ExitCode) pointe_ensemble_de_travail_octets $pointe" | Out-File -Append -Encoding utf8 "$dos\$Nom.cadre.txt"
exit $p.ExitCode
