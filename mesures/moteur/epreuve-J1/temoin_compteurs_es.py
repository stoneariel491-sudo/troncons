"""Témoin de l'instrument C8 du juge : GetProcessIoCounters compte-t-il une lecture sans tampon ?

Lit, sans tampon (FILE_FLAG_NO_BUFFERING, synchrone), des longueurs de 4 Kio à 64 Mio dans le
fichier donné, et publie l'écart de ReadTransferCount du processus pour chacune, contre la
longueur rendue par ReadFile. Commande : python -I -X utf8 temoin_compteurs_es.py <fichier> <décalage>
"""
import ctypes
import ctypes.wintypes as wt
import json
import sys

k32 = ctypes.windll.kernel32
k32.CreateFileW.restype = wt.HANDLE
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.GetCurrentProcess.restype = wt.HANDLE
k32.GetProcessIoCounters.argtypes = [wt.HANDLE, ctypes.c_void_p]
k32.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, ctypes.c_void_p]
k32.SetFilePointer.argtypes = [wt.HANDLE, ctypes.c_long, ctypes.c_void_p, wt.DWORD]


class IOC(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in ("RO", "WO", "OO", "RT", "WT", "OT")]


def lus():
    c = IOC()
    k32.GetProcessIoCounters(k32.GetCurrentProcess(), ctypes.byref(c))
    return c.RO, c.RT


h = k32.CreateFileW(sys.argv[1], 0x80000000, 1, None, 3, 0x20000000, None)  # GENERIC_READ, NO_BUFFERING
base = int(sys.argv[2]) // 4096 * 4096
tampon = k32.VirtualAlloc(None, 64 << 20, 0x3000, 0x04)
res = []
for i, lg in enumerate([4096, 1 << 20, 12 << 20, (16 << 20) - 4096, 16 << 20, (16 << 20) + 4096, 32 << 20, 64 << 20]):
    dec = base + i * (64 << 20)
    hi, lo = dec >> 32, dec & 0xFFFFFFFF
    k32.SetFilePointer(h, lo, ctypes.byref(ctypes.c_long(hi)), 0)
    n = wt.DWORD()
    o0, t0 = lus()
    ok = k32.ReadFile(h, ctypes.c_void_p(tampon), lg, ctypes.byref(n), None)
    o1, t1 = lus()
    res.append({"longueur": lg, "ok": bool(ok), "rendus": n.value, "operations": o1 - o0, "octets_comptes": t1 - t0})
# second temps : la même lecture de 12 Mio faite par un fil qui se termine, puis relue
import threading
o0, t0 = lus()


def fil():
    k32.SetFilePointer(h, base & 0xFFFFFFFF, ctypes.byref(ctypes.c_long(base >> 32)), 0)
    n = wt.DWORD()
    k32.ReadFile(h, ctypes.c_void_p(tampon), 12 << 20, ctypes.byref(n), None)


t = threading.Thread(target=fil)
t.start(); t.join()
o1, t1 = lus()
res.append({"longueur": 12 << 20, "par_un_fil_termine": True, "operations": o1 - o0, "octets_comptes": t1 - t0})
o2, t2 = lus()
res.append({"cumul_depuis_le_debut_du_processus": {"operations": o2, "octets": t2}})
print(json.dumps(res, indent=1))
