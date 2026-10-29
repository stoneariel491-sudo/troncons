"""Diagnostic d'un processus bloqué (lancé par le juge) : où tourne le fil donné ?

Suspend le fil quelques microsecondes, lit son pointeur d'instruction (GetThreadContext, x64),
le reprend ; n fois. Chaque adresse est rapportée au module qui la contient (EnumProcessModules).
Aucune écriture dans le processus. Commande : python -I -X utf8 echantillonner_fil.py <pid> <tid> [n]
"""
import collections
import ctypes
import ctypes.wintypes as wt
import json
import sys
import time

k32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
k32.OpenThread.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.SuspendThread.argtypes = [wt.HANDLE]
k32.ResumeThread.argtypes = [wt.HANDLE]
k32.GetThreadContext.argtypes = [wt.HANDLE, ctypes.c_void_p]
psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.DWORD]
psapi.GetModuleInformation.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD]
psapi.GetModuleBaseNameW.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_wchar_p, wt.DWORD]

pid, tid = int(sys.argv[1]), int(sys.argv[2])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
hp = k32.OpenProcess(0x0410, False, pid)
mods = (ctypes.c_void_p * 1024)()
besoin = wt.DWORD()
psapi.EnumProcessModulesEx(hp, mods, ctypes.sizeof(mods), ctypes.byref(besoin), 3)


class MODINFO(ctypes.Structure):
    _fields_ = [("base", ctypes.c_void_p), ("taille", wt.DWORD), ("entree", ctypes.c_void_p)]


modules = []
for m in mods[: besoin.value // ctypes.sizeof(ctypes.c_void_p)]:
    mi = MODINFO()
    psapi.GetModuleInformation(hp, ctypes.c_void_p(m), ctypes.byref(mi), ctypes.sizeof(mi))
    nom = ctypes.create_unicode_buffer(260)
    psapi.GetModuleBaseNameW(hp, ctypes.c_void_p(m), nom, 260)
    modules.append((mi.base or 0, mi.taille, nom.value))

# CONTEXT x64 : 1232 octets, aligné sur 16 ; ContextFlags à 0x30, Rip à 0xF8
tampon = ctypes.create_string_buffer(1232 + 16)
adr = (ctypes.addressof(tampon) + 15) & ~15
ht = k32.OpenThread(0x0002 | 0x0008 | 0x0040, False, tid)  # SUSPEND_RESUME, GET_CONTEXT, QUERY
vus = collections.Counter()
rips = collections.Counter()
for _ in range(n):
    ctypes.memset(adr, 0, 1232)
    ctypes.c_uint32.from_address(adr + 0x30).value = 0x00100001  # CONTEXT_CONTROL (AMD64)
    k32.SuspendThread(ht)
    ok = k32.GetThreadContext(ht, ctypes.c_void_p(adr))
    k32.ResumeThread(ht)
    rip = ctypes.c_uint64.from_address(adr + 0xF8).value if ok else 0
    lieu = next((f"{nm}+{rip - b:#x}" for b, t, nm in modules if b <= rip < b + t), f"{rip:#x}")
    vus[lieu.split("+")[0]] += 1
    rips[lieu] += 1
    time.sleep(0.01)
print(json.dumps({"pid": pid, "tid": tid, "echantillons": n, "modules": vus.most_common(),
                  "adresses": rips.most_common(12)}, indent=1))
