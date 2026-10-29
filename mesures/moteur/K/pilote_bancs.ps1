# Pilote des bancs de débit du lot K (étapes K1 et K2), en séries A B B A de processus.
#
# Avant toute mesure : secteur (Win32_Battery.BatteryStatus = 2, relevé et journalisé), aucun
# processus llama-* sur la carte, verrou de la carte pris (~\dev\verrou-carte.txt,
# avec le lot et l'heure ; un verrou de moins de 2 h d'un autre lot fait attendre), état de la
# carte relevé avant et après chaque passe (nvidia-smi). Le verrou est retiré à la fin, même en
# cas d'erreur.
#
# K1 : A = banc_k debit-decodeur (notre décodeur, 120b, une couche, 8 experts) ;
#      B = le chemin qu'il remplace, mesuré à nouveau dans la même séance : décodeur v4 de
#          l'étude 03 (rans_v4.exe, flux-4B) puis réassemblage des flux de classe
#          (dispersion.exe, mêmes proportions que 03) ; 1/(1/v4 + 1/réassemblage) refait le 41,6.
# K2 : banc_k debit-gemv deux fois (chaque processus fait déjà A B B A en interne).
#
# Usage : powershell -ExecutionPolicy Bypass -File pilote_bancs.ps1 [-Quoi K1|K2|tout]
param([string]$Quoi = "tout", [int]$Couche = 17)

$ErrorActionPreference = "Stop"
$verrou = "~\dev\verrou-carte.txt"
$banc = "~\dev\cibles\troncons-K\banc\banc_k.exe"
$gguf = "~\dev\modeles\gguf\gpt-oss-120b-MXFP4.gguf"
$e03 = "~\dev\essais\troncons\entropie"
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$jour = Get-Date -Format "yyyyMMdd-HHmm"
$dossier = Join-Path $ici "journaux"
New-Item -ItemType Directory -Force $dossier | Out-Null
$resume = Join-Path $dossier "pilote-$jour.json"

function Etat-Carte {
    (nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw,clocks.sm,clocks.mem,temperature.gpu --format=csv,noheader) -join ""
}

function Ecrire([string]$ligne) { Add-Content -Path $resume -Value $ligne -Encoding UTF8 }

$batterie = (Get-CimInstance Win32_Battery).BatteryStatus
if ($batterie -ne 2) { throw "machine sur batterie (BatteryStatus = $batterie) : pas de mesure de débit" }
# llama-* et le traceur de gpt-oss (llama.dll dans un autre programme, rôle gpt-oss) : la carte
# n'est pas libre.
$llama = Get-Process | Where-Object { $_.ProcessName -like "llama*" -or $_.ProcessName -eq "traceur" }
if ($llama) { throw "un processus llama-* ou traceur tourne ($($llama.ProcessName -join ', ')) : mesure reportée" }

# Verrou : attendre qu'un verrou récent d'un autre lot disparaisse (au plus 60 min).
$debutAttente = Get-Date
while (Test-Path $verrou) {
    $age = (Get-Date) - (Get-Item $verrou).LastWriteTime
    if ($age.TotalHours -ge 2) { break }
    if (((Get-Date) - $debutAttente).TotalMinutes -gt 60) { throw "verrou tenu depuis plus d'une heure : $(Get-Content $verrou)" }
    Start-Sleep -Seconds 30
}
Set-Content -Path $verrou -Value "lot K (noyaux), bancs de débit K1/K2, pris le $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8

try {
    Ecrire "{"
    Ecrire "  `"pilote`": `"pilote_bancs.ps1`", `"quoi`": `"$Quoi`", `"couche`": $Couche, `"debut`": `"$(Get-Date -Format s)`","
    Ecrire "  `"alimentation_BatteryStatus`": $batterie, `"verrou`": `"pris`","
    Ecrire "  `"passes`": ["
    $premiere = $true
    function Passe([string]$nom, [string]$exe, [string[]]$argv, [string]$journal) {
        $avant = Etat-Carte
        $t0 = Get-Date
        # PowerShell 5.1 change chaque ligne de stderr d'un exécutable en erreur, fatale sous « Stop »
        # (première séance, 16 h 46 : le pilote est tombé sur la première ligne du banc) : « Continue »
        # le temps de l'appel, le code de sortie seul décide.
        $avantEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $exe @argv 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath "$journal.log" -Encoding UTF8
        $code = $LASTEXITCODE
        $ErrorActionPreference = $avantEAP
        if ($code -ne 0) { throw "$nom : code de sortie $code" }
        $duree = ((Get-Date) - $t0).TotalSeconds
        $apres = Etat-Carte
        $virgule = if ($script:premiere) { "" } else { "," }
        $script:premiere = $false
        Ecrire "    $virgule{`"passe`": `"$nom`", `"journal`": `"$(Split-Path -Leaf $journal)`", `"debut`": `"$($t0.ToString('s'))`", `"duree_s`": $([math]::Round($duree,1)), `"carte_avant`": `"$avant`", `"carte_apres`": `"$apres`", `"BatteryStatus`": $((Get-CimInstance Win32_Battery).BatteryStatus)}"
    }
    if ($Quoi -eq "K1" -or $Quoi -eq "tout") {
        # D : le même décodeur sur des DELTA codés en tuiles de 32 macro-pas (TRC_N_DELTA = 32),
        # variante déclarée le 2026-10-15 à 17 h 08 (REPRISE-K), mesurée entre B1 et B2.
        foreach ($p in @("A1", "B1", "D1", "D2", "B2", "A2")) {
            if ($p.StartsWith("A") -or $p.StartsWith("D")) {
                $j = Join-Path $dossier "k1-debit-$p-$jour.json"
                if ($p.StartsWith("D")) { $env:TRC_N_DELTA = "32" } else { Remove-Item Env:TRC_N_DELTA -ErrorAction SilentlyContinue }
                Passe "K1-$p" $banc @("debit-decodeur", $gguf, "$Couche", $j, "--experts", "4", "--passes", "5") $j
                Remove-Item Env:TRC_N_DELTA -ErrorAction SilentlyContinue
            } else {
                $j = Join-Path $dossier "k1-ref03-v4-$p-$jour.json"
                Passe "K1-$p-v4" "$e03\cuda\rans_v4.exe" @("$e03\flux-4B", "5", $j) $j
                $j = Join-Path $dossier "k1-ref03-reassemblage-$p-$jour.json"
                Passe "K1-$p-reassemblage" "$e03\cuda\dispersion.exe" @("256", "0.1287", "0.7481", "0.1232", $j) $j
            }
        }
    }
    if ($Quoi -eq "K2" -or $Quoi -eq "tout") {
        foreach ($p in @("1", "2")) {
            $j = Join-Path $dossier "k2-debit-$p-$jour.json"
            Passe "K2-$p" $banc @("debit-gemv", $gguf, "$Couche", $j, "--experts", "24", "--passes", "5") $j
        }
    }
    Ecrire "  ],"
    Ecrire "  `"fin`": `"$(Get-Date -Format s)`""
    Ecrire "}"
}
finally {
    Remove-Item -LiteralPath $verrou -ErrorAction SilentlyContinue
}
