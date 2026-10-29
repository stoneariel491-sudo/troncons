# Attend que la carte soit libre (aucun llama-*, aucun traceur, aucun verrou), puis lance le pilote
# des bancs de débit du lot K (pilote_bancs.ps1, qui revérifie tout et prend le verrou).
# Sondage toutes les 20 s ; une ligne par changement d'état ; abandon après $HeuresMax heures.
#
# Usage : powershell -ExecutionPolicy Bypass -File attendre_et_mesurer.ps1 [-Quoi tout] [-HeuresMax 6]
param([string]$Quoi = "tout", [double]$HeuresMax = 6, [double]$MinutesCalme = 5)
# Calme exigé : la carte doit être libre $MinutesCalme minutes de suite. Raison (séance de 17 h 01) :
# une série d'un autre rôle relance llama-completion passe après passe sans verrou ; le pilote avait
# saisi le trou entre deux passes, et une passe de l'autre a démarré 4 s après notre verrou.

$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$verrou = "~\dev\verrou-carte.txt"
$debut = Get-Date
$etat = ""
$libreDepuis = $null
while ($true) {
    $occ = @(Get-Process | Where-Object { $_.ProcessName -like "llama*" -or $_.ProcessName -eq "traceur" })
    $v = Test-Path $verrou
    $nouveau = "occupants=" + (($occ | ForEach-Object { $_.ProcessName }) -join ",") + " verrou=$v"
    if ($nouveau -ne $etat) { Write-Output "$(Get-Date -Format s) $nouveau"; $etat = $nouveau }
    if ($occ.Count -eq 0 -and -not $v) {
        if (-not $libreDepuis) { $libreDepuis = Get-Date }
        if (((Get-Date) - $libreDepuis).TotalMinutes -ge $MinutesCalme) { break }
    } else { $libreDepuis = $null }
    if (((Get-Date) - $debut).TotalHours -gt $HeuresMax) { Write-Output "$(Get-Date -Format s) abandon : carte jamais libre"; exit 3 }
    Start-Sleep -Seconds 20
}
Write-Output "$(Get-Date -Format s) carte libre : pilote $Quoi"
& powershell -ExecutionPolicy Bypass -File (Join-Path $ici "pilote_bancs.ps1") -Quoi $Quoi
Write-Output "$(Get-Date -Format s) pilote fini, code $LASTEXITCODE"
