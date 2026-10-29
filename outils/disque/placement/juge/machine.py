"""La machine pour le juge du placement disque : verrou de la carte, calme, secteur, journal SMART du NVMe.

Écrit pour le juge (00-seuils-declares.md § 4), sans rien importer des outils de l'enquête.

- Verrou : ~/dev/verrou-carte.txt, une ligne « juge placement, date, script, pid ». Attendu
  tant qu'un autre le tient depuis moins de 2 h (convention de tous les flux). Le mot « ABBA » dans la ligne
  met en pause le flux des pistes (outils/pistes/spectres/commun.py).
- Calme : deux images de Win32_Process à 3 s d'écart ; un processus des autres flux qui prend plus de 5 %
  d'un cœur ou lit plus de 8 Mo pendant ces 3 s rend la machine « sous charge ».
- SMART : IOCTL_STORAGE_QUERY_PROPERTY (0x002D1400), propriété StorageDeviceProtocolSpecificProperty (50),
  NVMe (type 3), page de journal (type de donnée 2) 02h « SMART / Health Information » ; le disque physique
  s'ouvre sans droit d'accès (aucun administrateur). Champs (NVM Express Base 2.0, Figure 207) : 1-2
  température composite en kelvins ; 32-47 unités de données lues (milliers de blocs de 512 octets) ; 48-63
  unités écrites ; 216-223 transitions de gestion thermique TMT1, TMT2 ; 224-231 secondes passées en TMT1, TMT2.
"""
import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import pathlib
import struct
import subprocess
import time

VERROU = pathlib.Path("~/dev/verrou-carte.txt")
MARQUE = "juge placement"

_k = ctypes.WinDLL("kernel32", use_last_error=True)
_k.CreateFileW.restype = ctypes.c_void_p
_k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.c_void_p]
_k.DeviceIoControl.restype = wt.BOOL
_k.DeviceIoControl.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                               ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
_k.CloseHandle.argtypes = [ctypes.c_void_p]
_INVALIDE = ctypes.c_void_p(-1).value


def horodatage():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Journal:
    def __init__(self, chemin):
        self.chemin = pathlib.Path(chemin)
        self.chemin.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, texte):
        ligne = f"[{horodatage()}] {texte}"
        print(ligne, flush=True)
        with open(self.chemin, "a", encoding="utf-8") as f:
            f.write(ligne + "\n")


# ------------------------------------------------------------------------------------------- SMART

def smart():
    h = _k.CreateFileW("\\\\.\\PhysicalDrive0", 0, 0x1 | 0x2, None, 3, 0, None)
    if h in (None, _INVALIDE):
        return {"erreur": ctypes.get_last_error()}
    try:
        # STORAGE_PROPERTY_QUERY : PropertyId, QueryType, puis STORAGE_PROTOCOL_SPECIFIC_DATA (10 DWORD)
        donnees = struct.pack("<10I", 3, 2, 0x02, 0, 40, 512, 0, 0, 0, 0)
        requete = struct.pack("<II", 50, 0) + donnees + bytes(512)
        sortie = ctypes.create_string_buffer(8 + 40 + 512)
        rendu = wt.DWORD()
        if not _k.DeviceIoControl(h, 0x002D1400, requete, len(requete), sortie, len(sortie), ctypes.byref(rendu), None):
            return {"erreur": ctypes.get_last_error()}
        b = sortie.raw
        # STORAGE_PROTOCOL_DATA_DESCRIPTOR : Version, Size, puis la structure rendue ; la page suit à 8 + offset
        decalage, longueur = struct.unpack_from("<II", b, 8 + 16)
        p = b[8 + decalage: 8 + decalage + longueur]
        n128 = lambda o: int.from_bytes(p[o:o + 16], "little")
        return {"t": round(time.time(), 3), "temperature_c": struct.unpack_from("<H", p, 1)[0] - 273,
                "unites_lues": n128(32), "unites_ecrites": n128(48),
                "tmt1": struct.unpack_from("<I", p, 216)[0], "tmt2": struct.unpack_from("<I", p, 220)[0],
                "tmt1_s": struct.unpack_from("<I", p, 224)[0], "tmt2_s": struct.unpack_from("<I", p, 228)[0]}
    finally:
        _k.CloseHandle(h)


def ecart_smart(a, b):
    if "erreur" in a or "erreur" in b:
        return None
    return {"octets_lus_disque": (b["unites_lues"] - a["unites_lues"]) * 512000,
            "octets_ecrits_disque": (b["unites_ecrites"] - a["unites_ecrites"]) * 512000,
            "temperature": [a["temperature_c"], b["temperature_c"]],
            "tmt": (b["tmt1"] - a["tmt1"]) + (b["tmt2"] - a["tmt2"])}


# ------------------------------------------------------------------------------------------- machine

def powershell(cmd, delai=120):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                          capture_output=True, text=True, timeout=delai).stdout.strip()


def secteur():
    """Vrai si Win32_Battery BatteryStatus vaut 2 (sur secteur)."""
    return powershell("(Get-CimInstance Win32_Battery).BatteryStatus") == "2"


def charge_autres(miens=()):
    """Les processus des autres flux qui travaillent (plus de 5 % d'un cœur ou 8 Mo lus en 3 s)."""
    exclus = {os.getpid(), *miens}
    liste = ",".join(str(p) for p in exclus)
    cmd = (
        f"$x = @({liste}); "
        "$m = '^(python|pythonw|trc-.*|troncons|cargo|rustc|juge|genome-capture|llama.*)[.]exe$'; "
        "$f = { Get-CimInstance Win32_Process | Where-Object { $_.Name -match $m -and ($x -notcontains $_.ProcessId) "
        "-and ($x -notcontains $_.ParentProcessId) -and ($_.CommandLine -notmatch 'blender-mcp|http[.]server') } }; "
        "$a = @{}; foreach ($p in (& $f)) { $a[$p.ProcessId] = $p }; Start-Sleep -Seconds 3; "
        "foreach ($p in (& $f)) { $o = $a[$p.ProcessId]; if ($o) { "
        "$c = (($p.KernelModeTime + $p.UserModeTime) - ($o.KernelModeTime + $o.UserModeTime)) / 3e7; "
        "$l = ($p.ReadTransferCount - $o.ReadTransferCount) / 1e6; "
        "if ($c -gt 0.05 -or $l -gt 8) { $t = ($p.CommandLine -replace '\\s+', ' '); "
        "'{0} {1} : {2:N2} coeur, {3:N0} Mo lus : {4}' -f $p.Name, $p.ProcessId, $c, $l, $t.Substring(0, [Math]::Min(90, $t.Length)) } } }"
    )
    return [x for x in powershell(cmd).splitlines() if x.strip()]


# ------------------------------------------------------------------------------------------- verrou

def verrou_libre_pour_moi():
    if not VERROU.exists():
        return True
    try:
        texte = VERROU.read_text(encoding="utf-8", errors="replace")
        age = time.time() - VERROU.stat().st_mtime
    except OSError:
        return True
    return MARQUE in texte or age > 2 * 3600


def verrou_prendre(script, journal):
    n = 0
    while not verrou_libre_pour_moi():
        if n % 10 == 0:
            journal(f"verrou tenu par un autre : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; j'attends")
        n += 1
        time.sleep(60)
    VERROU.write_text(f"{MARQUE}, {horodatage()}, {script} (séance ABBA de l'étage disque), pid {os.getpid()}\n", encoding="utf-8")
    journal(f"verrou pris : {VERROU.read_text(encoding='utf-8').strip()}")


def verrou_rafraichir():
    try:
        if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
            os.utime(VERROU)
    except OSError:
        pass


def verrou_rendre(journal):
    try:
        if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
            VERROU.unlink()
            journal("verrou rendu")
    except OSError as e:
        journal(f"verrou : {e}")


def attendre_calme(journal, miens=(), vides=2, limite_s=None):
    """Attend deux relevés vides à une minute d'écart. Rend False si `limite_s` passe avant."""
    t0, k, n = time.time(), 0, 0
    while k < vides:
        a = charge_autres(miens)
        k = 0 if a else k + 1
        if a and n % 5 == 0:
            journal(f"pas calme : {a}")
        n += 1
        if k < vides:
            if limite_s and time.time() - t0 > limite_s:
                return False
            verrou_rafraichir()
            time.sleep(60)
    journal(f"calme : {vides} relevés vides à une minute d'écart")
    return True
