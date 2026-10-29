"""Ce que partagent les outils du placement disque : verrou de la carte, calme, secteur, place libre,
journal SMART / santé du NVMe (lisible sans droit d'administrateur), lectures et écritures sans tampon.

Le journal SMART : IOCTL_STORAGE_QUERY_PROPERTY (0x2D1400), StorageDeviceProtocolSpecificProperty (50),
NVMe, page de journal 02h (« SMART / Health Information », NVM Express Base Specification 2.0, § 5.16.1.3) :
octets 1-2 température composite (K), 32-47 unités lues (×512 000 octets), 48-63 unités écrites,
64-79 commandes de lecture de l'hôte, 216/220 transitions TMT1/TMT2, 224/228 secondes passées en TMT1/TMT2.
"""
import ctypes
import ctypes.wintypes as wt
import datetime as dt
import os
import pathlib
import shutil
import struct
import subprocess
import time

VERROU = pathlib.Path("~/dev/verrou-carte.txt")
MARQUE = "placement disque"
ESSAIS = pathlib.Path("~/dev/essais/troncons/placement")
RACINE = pathlib.Path(__file__).resolve().parents[3]
JOURNAUX = RACINE / "mesures/disque/placement/journaux"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.restype = ctypes.c_void_p
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.c_void_p]
k32.DeviceIoControl.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.CloseHandle.argtypes = [ctypes.c_void_p]
k32.ReadFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k32.SetFilePointerEx.argtypes = [ctypes.c_void_p, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wt.DWORD]
k32.SetEndOfFile.argtypes = [ctypes.c_void_p]
k32.SetFileInformationByHandle.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
k32.FlushFileBuffers.argtypes = [ctypes.c_void_p]

INVALIDE = 0xFFFFFFFFFFFFFFFF
GENERIC_READ, GENERIC_WRITE = 0x80000000, 0x40000000
FILE_FLAG_NO_BUFFERING, FILE_FLAG_WRITE_THROUGH, FILE_FLAG_SEQUENTIAL_SCAN = 0x20000000, 0x80000000, 0x08000000


def maintenant():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def journal(fichier, texte):
    ligne = f"[{maintenant()}] {texte}"
    print(ligne, flush=True)
    JOURNAUX.mkdir(parents=True, exist_ok=True)
    with open(JOURNAUX / fichier, "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


# ----------------------------------------------------------------------------------- SMART

def smart():
    """Le journal SMART / santé du NVMe (page 02h), lu par \\\\.\\PhysicalDrive0 ouvert sans droit d'accès."""
    h = k32.CreateFileW("\\\\.\\PhysicalDrive0", 0, 3, None, 3, 0, None)
    if h in (None, INVALIDE):
        return {"erreur": ctypes.get_last_error()}
    try:
        psd = struct.pack("<IIIIIIIIII", 3, 2, 2, 0, 40, 512, 0, 0, 0, 0)
        q = struct.pack("<II", 50, 0) + psd
        q += b"\0" * (8 + 40 + 512 - len(q))
        out = ctypes.create_string_buffer(4096)
        r = wt.DWORD()
        if not k32.DeviceIoControl(h, 0x2D1400, q, len(q), out, 4096, ctypes.byref(r), None):
            return {"erreur": ctypes.get_last_error()}
        raw = out.raw
        off, ln = struct.unpack_from("<II", raw, 8 + 16)
        d = raw[8 + off:8 + off + ln]
        u128 = lambda o: int.from_bytes(d[o:o + 16], "little")
        return {
            "t": time.time(), "temperature_c": struct.unpack_from("<H", d, 1)[0] - 273,
            "unites_lues": u128(32), "unites_ecrites": u128(48), "lectures_hote": u128(64), "ecritures_hote": u128(80),
            "tmt1_n": struct.unpack_from("<I", d, 216)[0], "tmt2_n": struct.unpack_from("<I", d, 220)[0],
            "tmt1_s": struct.unpack_from("<I", d, 224)[0], "tmt2_s": struct.unpack_from("<I", d, 228)[0],
            "capteurs_c": [x - 273 for x in struct.unpack_from("<8H", d, 200) if x],
            "pct_usure": d[5], "reserve_pct": d[3],
        }
    finally:
        k32.CloseHandle(h)


def ecart_smart(a, b):
    if "erreur" in a or "erreur" in b:
        return None
    return {"octets_lus_disque": (b["unites_lues"] - a["unites_lues"]) * 512000,
            "octets_ecrits_disque": (b["unites_ecrites"] - a["unites_ecrites"]) * 512000,
            "temp_avant": a["temperature_c"], "temp_apres": b["temperature_c"],
            "tmt_transitions": (b["tmt1_n"] - a["tmt1_n"]) + (b["tmt2_n"] - a["tmt2_n"]),
            "tmt_secondes": (b["tmt1_s"] - a["tmt1_s"]) + (b["tmt2_s"] - a["tmt2_s"])}


# ----------------------------------------------------------------------------------- machine

def ps(cmd):
    # Sortie lue en octets puis décodée sans échec : une ligne de commande d'un autre processus peut porter
    # des octets de la page de code 1252 (incident du 2026-10-26 : UnicodeDecodeError, sortie perdue).
    o = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True).stdout or b""
    try:
        t = o.decode("utf-8")
    except UnicodeDecodeError:
        t = o.decode("cp1252", errors="replace")
    return t.strip()


def alimentation():
    return ps("(Get-CimInstance Win32_Battery).BatteryStatus")


def place_libre():
    return shutil.disk_usage("C:\\").free


def autres_lourds(exclure=()):
    """Processus des autres flux qui travaillent : python, trc-*, troncons, cargo, rustc, juge,
    genome-capture, llama-* (hors serveurs http, blender-mcp, ce processus et ses enfants), qui ont pris
    plus de 5 % d'un cœur ou lu plus de 8 Mo en 3 s."""
    moi = [os.getpid(), *exclure]
    filtre = " -and ".join(f"$_.ProcessId -ne {p} -and $_.ParentProcessId -ne {p}" for p in moi)
    s = ps(
        "$f = { Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(genome-capture|juge|trc-.*|troncons|cargo|rustc|python|llama.*)[.]exe$' "
        f"-and {filtre} -and $_.CommandLine -notmatch 'http[.]server|blender-mcp' }} }}; "
        "$a = @{}; & $f | ForEach-Object { $a[$_.ProcessId] = $_ }; Start-Sleep -Seconds 3; "
        "& $f | ForEach-Object { $o = $a[$_.ProcessId]; if ($o) { "
        "$cpu = (($_.KernelModeTime + $_.UserModeTime) - ($o.KernelModeTime + $o.UserModeTime)) / 3e7; "
        "$lu = ($_.ReadTransferCount - $o.ReadTransferCount) / 1e6; "
        "if ($cpu -gt 0.05 -or $lu -gt 8) { $c = ($_.CommandLine -replace '[ ]+', ' '); "
        "'{0}:{1}:cpu {2:N2} coeur:lu {3:N0} Mo:{4}' -f $_.Name, $_.ProcessId, $cpu, $lu, $c.Substring(0, [Math]::Min(100, $c.Length)) } } }")
    return [x for x in s.splitlines() if x.strip()]


# ----------------------------------------------------------------------------------- verrou

def verrou_prendre(seance, script, nom_journal):
    """Attend le verrou de la carte s'il est tenu depuis moins de 2 h par un autre, puis le prend."""
    n = 0
    while VERROU.exists() and MARQUE not in VERROU.read_text(encoding="utf-8", errors="replace") \
            and time.time() - VERROU.stat().st_mtime < 2 * 3600:
        if n % 10 == 0:
            journal(nom_journal, f"verrou tenu : {VERROU.read_text(encoding='utf-8', errors='replace').strip()!r} ; attente")
        n += 1
        time.sleep(60)
    VERROU.write_text(f"{MARQUE}, {maintenant()}, séance de vitesse ABBA {seance}, {script}, pid {os.getpid()}\n", encoding="utf-8")
    journal(nom_journal, f"verrou pris : {VERROU.read_text(encoding='utf-8').strip()}")


def verrou_rafraichir():
    try:
        if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
            os.utime(VERROU)
            return True
    except OSError:
        pass
    return False


def verrou_rendre(nom_journal):
    if VERROU.exists() and MARQUE in VERROU.read_text(encoding="utf-8", errors="replace"):
        VERROU.unlink()
        journal(nom_journal, "verrou rendu")


def attendre_calme(nom_journal, exclure=(), vides_requis=2):
    vides, n = 0, 0
    while vides < vides_requis:
        au = autres_lourds(exclure)
        vides = 0 if au else vides + 1
        if au and n % 5 == 0:
            journal(nom_journal, f"attente du calme : {au}")
        n += 1
        if vides < vides_requis:
            verrou_rafraichir()
            time.sleep(60)
    journal(nom_journal, f"calme : relevé vide {vides_requis} fois de suite à une minute d'écart")


# ----------------------------------------------------------------------------------- E/S

class Tampon:
    """Mémoire alignée sur la page (VirtualAlloc), exigée par FILE_FLAG_NO_BUFFERING."""

    def __init__(self, n):
        self.n = n
        self.p = k32.VirtualAlloc(None, n, 0x3000, 0x04)
        if not self.p:
            raise MemoryError(n)

    def octets(self, k):
        return ctypes.string_at(self.p, k)

    def liberer(self):
        if self.p:
            k32.VirtualFree(self.p, 0, 0x8000)
            self.p = None


def ouvrir_lecture(chemin, sans_tampon=True):
    h = k32.CreateFileW(str(chemin), GENERIC_READ, 1, None, 3, FILE_FLAG_NO_BUFFERING if sans_tampon else 0, None)
    if h in (None, INVALIDE):
        raise OSError(ctypes.get_last_error(), f"ouverture de {chemin}")
    return h


def lire_a(h, tampon, decalage, longueur):
    """ReadFile synchrone à `decalage` (le pointeur de fichier de la poignée ; une poignée par fil)."""
    nouv = ctypes.c_longlong()
    if not k32.SetFilePointerEx(h, decalage, ctypes.byref(nouv), 0):
        raise OSError(ctypes.get_last_error(), "SetFilePointerEx")
    lus = wt.DWORD()
    if not k32.ReadFile(h, tampon.p, longueur, ctypes.byref(lus), None):
        raise OSError(ctypes.get_last_error(), f"ReadFile à {decalage}")
    return lus.value


def fermer(h):
    k32.CloseHandle(h)
