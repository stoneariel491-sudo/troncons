"""Diagnostic d'un fil bloqué : adresses de retour de troncons.exe trouvées sur sa pile, nommées.

Lit le pointeur de pile (CONTEXT.Rsp, x64) du fil suspendu, puis 256 Kio de pile
(ReadProcessMemory) ; chaque mot de 64 bits qui tombe dans le module visé est nommé par dbghelp
(SymFromAddr, PDB de la construction). Lecture seule. Heuristique : un mot de la pile qui pointe dans
le code n'est pas toujours une adresse de retour vivante ; l'ordre (du sommet vers le fond) aide.
Commande : python -I -X utf8 pile_fil.py <pid> <tid> <module.exe> <dossier du pdb>
"""
import ctypes
import ctypes.wintypes as wt
import json
import sys

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
dbg = ctypes.windll.dbghelp
for f, r in ((k32.OpenThread, wt.HANDLE), (k32.OpenProcess, wt.HANDLE)):
    f.restype = r
k32.SuspendThread.argtypes = k32.ResumeThread.argtypes = [wt.HANDLE]
k32.GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.DWORD]
psapi.GetModuleInformation.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD]
psapi.GetModuleBaseNameW.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_wchar_p, wt.DWORD]
dbg.SymInitializeW.argtypes = [wt.HANDLE, ctypes.c_wchar_p, wt.BOOL]
dbg.SymFromAddrW.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64), ctypes.c_void_p]

pid, tid, cible, pdb = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3].lower(), sys.argv[4]
hp = k32.OpenProcess(0x0410, False, pid)


class MODINFO(ctypes.Structure):
    _fields_ = [("base", ctypes.c_void_p), ("taille", wt.DWORD), ("entree", ctypes.c_void_p)]


mods = (ctypes.c_void_p * 1024)()
besoin = wt.DWORD()
psapi.EnumProcessModulesEx(hp, mods, ctypes.sizeof(mods), ctypes.byref(besoin), 3)
modules = []
for m in mods[: besoin.value // 8]:
    mi = MODINFO()
    psapi.GetModuleInformation(hp, ctypes.c_void_p(m), ctypes.byref(mi), ctypes.sizeof(mi))
    nom = ctypes.create_unicode_buffer(260)
    psapi.GetModuleBaseNameW(hp, ctypes.c_void_p(m), nom, 260)
    modules.append((mi.base or 0, mi.taille, nom.value.lower()))

tampon = ctypes.create_string_buffer(1232 + 16)
adr = (ctypes.addressof(tampon) + 15) & ~15
ctypes.c_uint32.from_address(adr + 0x30).value = 0x00100001
ht = k32.OpenThread(0x0002 | 0x0008 | 0x0040, False, tid)
k32.SuspendThread(ht)
k32.GetThreadContext(ht, ctypes.c_void_p(adr))
rsp = ctypes.c_uint64.from_address(adr + 0x98).value
pile = ctypes.create_string_buffer(256 << 10)
lu = ctypes.c_size_t()
k32.ReadProcessMemory(hp, ctypes.c_void_p(rsp), pile, len(pile), ctypes.byref(lu))
k32.ResumeThread(ht)

dbg.SymSetOptions(0x00000002 | 0x00000010)  # UNDNAME | DEFERRED_LOADS
dbg.SymInitializeW(hp, pdb, False)
dbg.SymLoadModuleExW.argtypes = [wt.HANDLE, wt.HANDLE, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint64, wt.DWORD, ctypes.c_void_p, wt.DWORD]
dbg.SymLoadModuleExW.restype = ctypes.c_uint64
for b, t, nm in modules:
    if nm == cible:
        base_cible = dbg.SymLoadModuleExW(hp, None, pdb + "\\" + nm, None, b, t, None, 0)


class SYM(ctypes.Structure):
    _fields_ = [("SizeOfStruct", wt.ULONG), ("TypeIndex", wt.ULONG), ("Reserved", ctypes.c_uint64 * 2),
                ("Index", wt.ULONG), ("Size", wt.ULONG), ("ModBase", ctypes.c_uint64), ("Flags", wt.ULONG),
                ("Value", ctypes.c_uint64), ("Address", ctypes.c_uint64), ("Register", wt.ULONG),
                ("Scope", wt.ULONG), ("Tag", wt.ULONG), ("NameLen", wt.ULONG), ("MaxNameLen", wt.ULONG),
                ("Name", ctypes.c_wchar * 1024)]


trouves = []
mots = (ctypes.c_uint64 * (lu.value // 8)).from_buffer(pile)
for i, w in enumerate(mots):
    for b, t, nm in modules:
        if b <= w < b + t and nm == cible:
            s = SYM()
            s.SizeOfStruct = 88
            s.MaxNameLen = 1024
            dep = ctypes.c_uint64()
            ok = dbg.SymFromAddrW(hp, w, ctypes.byref(dep), ctypes.byref(s))
            trouves.append({"profondeur_octets": 8 * i, "adresse": f"{nm}+{w - b:#x}",
                            "fonction": s.Name if ok else None})
print(json.dumps({"module_charge": base_cible, "pid": pid, "tid": tid, "rsp": f"{rsp:#x}", "octets_de_pile": lu.value,
                  "retours": trouves[:40]}, ensure_ascii=False, indent=1))
