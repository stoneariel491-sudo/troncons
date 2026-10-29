"""Identité du NVMe (lecture seule, sans administrateur) : NVMe Identify Controller (CNS 1) par
IOCTL_STORAGE_QUERY_PROPERTY, propriété StorageAdapterProtocolSpecificProperty (49), type NVMe (3),
donnée Identify (1). Champs (NVM Express Base 2.0, Figure 275) : modèle 24-63, micrologiciel 64-71,
MDTS octet 77, HMPRE 272-275 et HMMIN 276-279 (tampon mémoire de l'hôte préféré et minimal, en unités de
4 Kio ; non nuls : le contrôleur demande un tampon dans la RAM de l'hôte, signe d'un disque sans DRAM).

  python -I -X utf8 outils/disque/placement/juge/identifier.py
"""
import ctypes
import ctypes.wintypes as wt
import json
import struct

k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateFileW.restype = ctypes.c_void_p
k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.c_void_p]
k.DeviceIoControl.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                              ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
k.CloseHandle.argtypes = [ctypes.c_void_p]

h = k.CreateFileW(r"\\.\PhysicalDrive0", 0, 3, None, 3, 0, None)
d = struct.pack("<10I", 3, 1, 1, 0, 40, 4096, 0, 0, 0, 0)
q = struct.pack("<II", 49, 0) + d + bytes(4096)
o = ctypes.create_string_buffer(8 + 40 + 4096)
r = wt.DWORD()
ok = k.DeviceIoControl(h, 0x2D1400, q, len(q), o, len(o), ctypes.byref(r), None)
err = ctypes.get_last_error()
k.CloseHandle(h)
if not ok:
    print(json.dumps({"erreur": err}))
else:
    b = o.raw
    off, ln = struct.unpack_from("<II", b, 8 + 16)
    p = b[8 + off:8 + off + ln]
    print(json.dumps({"modele": p[24:64].decode(errors="replace").strip(), "micrologiciel": p[64:72].decode(errors="replace").strip(),
                      "mdts_puissance_de_2_pages": p[77], "hmpre_4kio": struct.unpack_from("<I", p, 272)[0],
                      "hmmin_4kio": struct.unpack_from("<I", p, 276)[0],
                      "hmpre_mio": struct.unpack_from("<I", p, 272)[0] * 4 / 1024}, ensure_ascii=False))
