# creer-disque-modeles.ps1 -- cree le disque D: "Modeles", non chiffre, pour les poids des modeles.
#
# Windows PowerShell 5.1, ASCII pur. A lancer par Stone, dans un PowerShell OUVERT EN ADMINISTRATEUR :
#
#   powershell -ExecutionPolicy Bypass -File creer-disque-modeles.ps1            (montre seulement)
#   powershell -ExecutionPolicy Bypass -File creer-disque-modeles.ps1 -Appliquer (fait)
#
# Ce qu'il fait, dans l'ordre :
#   1. verifie les droits d'administrateur, que la lettre D: est libre et que C: peut ceder la taille demandee ;
#   2. reduit C: de -TailleGo (200 par defaut) ;
#   3. cree une partition sur l'espace libere, lettre D:, formatee en NTFS, nommee "Modeles" ;
#   4. relit l'etat BitLocker de C: et de D:. C: doit rester chiffre. Si D: est chiffre, le script le dit
#      et ne fait rien d'autre : la decision revient a Stone.
# Pourquoi : les poids des modeles sont des fichiers publics ; sur C:, BitLocker les dechiffre par le
# processeur a chaque lecture et refuse BypassIO (troncons, fondations/01-machine.md, section 2).
# Avant de lancer : la cle de recuperation BitLocker de C: est sauvegardee (fait le 2026-10-15).

param(
    [switch]$Appliquer,
    [int]$TailleGo = 200
)

$ErrorActionPreference = 'Stop'

function Dire([string]$m) { Write-Host $m }

# 1. Les verifications
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Dire "Il faut lancer ce PowerShell en administrateur (clic droit, Executer en tant qu'administrateur)."; exit 1 }
if (Get-Volume -DriveLetter D -ErrorAction SilentlyContinue) { Dire "La lettre D: est deja prise. Rien n'est fait."; exit 1 }

$partC = Get-Partition -DriveLetter C
$bornes = Get-PartitionSupportedSize -DriveLetter C
$octets = [int64]$TailleGo * 1GB
$nouvelle = $partC.Size - $octets
$marge = 20GB
Dire ("C: fait {0:N1} Go ; Windows permet de le reduire jusqu'a {1:N1} Go." -f ($partC.Size / 1GB), ($bornes.SizeMin / 1GB))
Dire ("Demande : reduire C: de {0} Go, il ferait alors {1:N1} Go." -f $TailleGo, ($nouvelle / 1GB))
if ($nouvelle -lt ($bornes.SizeMin + $marge)) {
    Dire ("Trop grand : il faut garder au moins 20 Go au-dessus du minimum. Maximum possible ici : {0} Go. Relance avec -TailleGo plus petit." -f [math]::Floor(($partC.Size - $bornes.SizeMin - $marge) / 1GB))
    exit 1
}
$libre = (Get-Volume -DriveLetter C).SizeRemaining
Dire ("Libre sur C: aujourd'hui : {0:N1} Go ; apres : environ {1:N1} Go (avant le deplacement des modeles)." -f ($libre / 1GB), (($libre - $octets) / 1GB))

if (-not $Appliquer) {
    Dire ""
    Dire "Rien n'a ete modifie. Pour le faire : relance avec -Appliquer."
    exit 0
}

# 2. Reduire C:
Dire "Reduction de C: en cours (quelques minutes)..."
Resize-Partition -DriveLetter C -Size $nouvelle

# 3. Creer D:
Dire "Creation de D: ..."
$p = New-Partition -DiskNumber $partC.DiskNumber -UseMaximumSize -DriveLetter D
Format-Volume -Partition $p -FileSystem NTFS -NewFileSystemLabel 'Modeles' -Confirm:$false | Out-Null
$v = Get-Volume -DriveLetter D
Dire ("D: cree : {0:N1} Go, {1}, nom {2}." -f ($v.Size / 1GB), $v.FileSystem, $v.FileSystemLabel)

# 4. Relire BitLocker
foreach ($l in 'C:', 'D:') {
    $b = Get-BitLockerVolume -MountPoint $l
    Dire ("{0} protection BitLocker : {1} (chiffre a {2} %)" -f $l, $b.ProtectionStatus, $b.EncryptionPercentage)
}
$d = Get-BitLockerVolume -MountPoint 'D:'
if ($d.VolumeStatus -ne 'FullyDecrypted') {
    Dire "ATTENTION : D: est chiffre ou en cours de chiffrement. Ne rien copier dessus ; le dire avant d'aller plus loin."
    exit 2
}
Dire "Fini : C: reste chiffre, D: ne l'est pas."
exit 0
