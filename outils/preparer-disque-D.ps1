# preparer-disque-D.ps1 -- prepare le disque D: "Modeles" (non chiffre) en une seule fois, avec deux redemarrages.
#
# Windows PowerShell 5.1, ASCII pur. Lance par le raccourci du Bureau, qui demande les droits d'administrateur.
#
# Etape 1 (le clic de Stone) :
#   - verifie : administrateur, secteur, lettre D: libre, aucun agent en cours (troncons.exe, llama-*, cargo) ;
#   - demande de taper OUI ;
#   - coupe le fichier d'echange de C: (il bloque la reduction : fondations, journal 259 du 2026-10-15) ;
#   - inscrit une tache planifiee qui lancera l'etape 2 a la prochaine ouverture de session ;
#   - redemarre apres confirmation.
# Etape 2 (automatique, apres le redemarrage) :
#   - reduit C: (200 Go si possible, sinon le maximum s'il depasse 150 Go) et cree D: "Modeles" en NTFS ;
#   - verifie que C: reste chiffre et que D: ne l'est pas ;
#   - REMET le fichier d'echange automatique dans tous les cas (bloc finally), retire la tache ;
#   - ecrit le compte rendu sur le Bureau et redemarre apres confirmation.
# Journal : Bureau\disque-D-journal.txt

param(
    [int]$Etape = 1,
    [int]$TailleGo = 200,
    [int]$MinimumGo = 150
)

$ErrorActionPreference = 'Stop'
$bureau = [Environment]::GetFolderPath('Desktop')
$journal = Join-Path $bureau 'disque-D-journal.txt'
$tache = 'troncons-disque-D-etape2'
$ici = $PSCommandPath

function Dire([string]$m) {
    $ligne = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $m
    Write-Host $m
    Add-Content -Path $journal -Value $ligne -Encoding ASCII
}

function Attendre-Touche([string]$m) {
    Write-Host ''
    Write-Host $m
    [void](Read-Host 'Appuie sur Entree')
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Il faut les droits d'administrateur : lance le raccourci du Bureau et accepte la demande de Windows."
    Attendre-Touche 'Rien n a ete modifie.'
    exit 1
}

if ($Etape -eq 1) {
    Dire '=== Etape 1 : preparation ==='
    $bat = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
    if ($bat -and $bat.BatteryStatus -ne 2) { Dire 'Le portable n est pas sur secteur : branche-le, puis relance.'; Attendre-Touche 'Rien n a ete modifie.'; exit 1 }
    if (Get-Volume -DriveLetter D -ErrorAction SilentlyContinue) { Dire 'La lettre D: est deja prise : rien n est fait.'; Attendre-Touche 'Rien n a ete modifie.'; exit 1 }
    $agents = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(troncons|llama-|cargo|rustc|banc-chemin|trc-codeur)' }
    if ($agents) {
        Dire ('Des programmes des agents tournent encore : ' + (($agents | Select-Object -ExpandProperty ProcessName -Unique) -join ', ') + '. Attends la pause, puis relance.')
        Attendre-Touche 'Rien n a ete modifie.'
        exit 1
    }
    $partC = Get-Partition -DriveLetter C
    Dire ('C: fait {0:N1} Go, {1:N1} Go libres.' -f ($partC.Size / 1GB), ((Get-Volume -DriveLetter C).SizeRemaining / 1GB))
    Write-Host ''
    Write-Host 'Ce qui va se passer :'
    Write-Host '  1. le fichier d echange de C: est coupe, puis le PC redemarre ;'
    Write-Host '  2. apres le redemarrage, ouvre ta session : la suite se lance seule ;'
    Write-Host ('     elle reduit C: de {0} Go et cree D: "Modeles", non chiffre ;' -f $TailleGo)
    Write-Host '  3. le fichier d echange est remis, puis un dernier redemarrage.'
    Write-Host 'Avant de continuer : ta cle de recuperation BitLocker doit etre sauvegardee.'
    $r = Read-Host 'Tape OUI pour continuer'
    if ($r -ne 'OUI') { Dire 'Annule par Stone : rien n a ete modifie.'; exit 0 }

    $cs = Get-CimInstance Win32_ComputerSystem
    Set-CimInstance -InputObject $cs -Property @{ AutomaticManagedPagefile = $false }
    Get-CimInstance Win32_PageFileSetting -ErrorAction SilentlyContinue | Remove-CimInstance
    Dire 'Fichier d echange de C: coupe (il disparaitra au redemarrage).'

    $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}" -Etape 2 -TailleGo {1} -MinimumGo {2}' -f $ici, $TailleGo, $MinimumGo)
    $dec = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $pri = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $tache -Action $act -Trigger $dec -Principal $pri -Force | Out-Null
    Dire 'Etape 2 inscrite : elle se lancera a la prochaine ouverture de session.'

    Attendre-Touche 'Le PC va redemarrer. Enregistre ce qui est ouvert.'
    Restart-Computer -Force
    exit 0
}

# Etape 2
Dire '=== Etape 2 : creation de D: ==='
Start-Sleep -Seconds 20
$ok = $false
try {
    $partC = Get-Partition -DriveLetter C
    $bornes = Get-PartitionSupportedSize -DriveLetter C
    $marge = 20GB
    $maxGo = [math]::Floor(($partC.Size - $bornes.SizeMin - $marge) / 1GB)
    Dire ('C: peut ceder au plus {0} Go (marge de 20 Go gardee).' -f $maxGo)
    $go = [math]::Min($TailleGo, $maxGo)
    if ($go -lt $MinimumGo) {
        Dire ('Trop peu de place liberable ({0} Go < {1} Go) : un autre fichier bloque encore. Rien n est reduit.' -f $go, $MinimumGo)
        $ev = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 259 } -MaxEvents 1 -ErrorAction SilentlyContinue
        if ($ev) { Dire ('Fichier qui bloque, selon Windows : ' + (($ev.Message -split "`n") | Where-Object { $_ -match 'non d.pla' } | Select-Object -First 1)) }
    } else {
        Dire ("Reduction de C: de $go Go (quelques minutes)...")
        Resize-Partition -DriveLetter C -Size ($partC.Size - [int64]$go * 1GB)
        $p = New-Partition -DiskNumber $partC.DiskNumber -UseMaximumSize -DriveLetter D
        Format-Volume -Partition $p -FileSystem NTFS -NewFileSystemLabel 'Modeles' -Confirm:$false | Out-Null
        $v = Get-Volume -DriveLetter D
        Dire ('D: cree : {0:N1} Go, {1}, nom {2}.' -f ($v.Size / 1GB), $v.FileSystem, $v.FileSystemLabel)
        foreach ($l in 'C:', 'D:') {
            $b = Get-BitLockerVolume -MountPoint $l
            Dire ('{0} BitLocker : {1}, chiffre a {2} %.' -f $l, $b.VolumeStatus, $b.EncryptionPercentage)
        }
        if ((Get-BitLockerVolume -MountPoint 'D:').VolumeStatus -ne 'FullyDecrypted') { Dire 'ATTENTION : D: est chiffre. Ne rien copier dessus avant d en parler.' } else { $ok = $true }
    }
} catch {
    Dire ('ERREUR : ' + $_.Exception.Message)
} finally {
    $cs = Get-CimInstance Win32_ComputerSystem
    Set-CimInstance -InputObject $cs -Property @{ AutomaticManagedPagefile = $true }
    Dire 'Fichier d echange automatique REMIS (actif apres le redemarrage).'
    Unregister-ScheduledTask -TaskName $tache -Confirm:$false -ErrorAction SilentlyContinue
    Dire 'Tache de l etape 2 retiree.'
}
if ($ok) { Dire 'Fini : C: reste chiffre, D: Modeles est pret et non chiffre.' } else { Dire 'Termine avec un probleme : voir les lignes ci-dessus. Rien n est perdu.' }
Attendre-Touche 'Un dernier redemarrage remet le fichier d echange.'
Restart-Computer -Force
