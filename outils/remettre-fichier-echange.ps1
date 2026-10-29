# remettre-fichier-echange.ps1 -- remet le fichier d'echange gere par Windows, puis propose le redemarrage.
# A lancer par Stone, en administrateur (raccourci du Bureau). Ne touche a rien d'autre.
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "Il faut accepter la demande d'administrateur de Windows."; Read-Host 'Entree'; exit 1 }
$cs = Get-CimInstance Win32_ComputerSystem
Set-CimInstance -InputObject $cs -Property @{ AutomaticManagedPagefile = $true }
Write-Host ("Fichier d'echange gere par Windows : " + (Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile)
Write-Host "Il sera actif apres le redemarrage."
$r = Read-Host 'Taper OUI pour redemarrer maintenant'
if ($r -eq 'OUI') { Restart-Computer -Force }
