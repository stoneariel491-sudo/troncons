import struct, sys
f = open(sys.argv[1], 'rb')
def r(fmt): return struct.unpack('<'+fmt, f.read(struct.calcsize('<'+fmt)))
f.read(4); ver, = r('I'); nt, nkv = r('QQ')
def ch():
    n, = r('Q'); return f.read(n).decode('utf8','replace')
tailles = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
align = 32
def val(t):
    if t == 8: return ch()
    if t == 9:
        te, n = r('IQ')
        if te == 8:
            for _ in range(n): ch()
            return None
        f.read(tailles[te]*n); return None
    return r({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])[0]
for _ in range(nkv):
    k = ch(); t, = r('I'); v = val(t)
    if k == 'general.alignment': align = v
infos = {}
for _ in range(nt):
    nom = ch(); nd, = r('I'); ne = r('Q'*nd); ty, = r('I'); off, = r('Q'); infos[nom] = (ne, ty, off)
debut = (f.tell() + align - 1)//align*align
for l in (0, 1, 5):
    for nom in ('attn_k.bias', 'attn_q.bias', 'attn_v.bias'):
        ne, ty, off = infos[f'blk.{l}.{nom}']
        f.seek(debut + off); n = ne[0]; v = struct.unpack('<%df'%n, f.read(4*n))
        print(l, nom, 'max|b| = %.3e' % max(abs(x) for x in v), 'nuls : %d/%d' % (sum(1 for x in v if x == 0), n))
