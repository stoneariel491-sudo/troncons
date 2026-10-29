"""P2 : diagnostic du témoin T2 sur le 20b (écart de l'exclusif au LRU de V + R, avec et sans épinglage)."""
import json
import sys

sys.path.insert(0, "~/dev/active/troncons/outils/mimetisme/P2")
import cache_exclusif as ce  # noqa: E402

ce.L, ce.E = 24, 32
D = sys.argv[1]
out = {}
for nom, f in (("code.generation", "t20b.code.generation.trace"), ("wiki.generation", "w20b.wiki.generation.trace"),
               ("code.lecture", "t20b.code.lecture.trace")):
    G = ce.charger(f"{D}/{f}")
    for ep in (True, False):
        e = ce.sim(G, 154, 56, "exclusif", epingle=ep)
        u = ce.sim(G, 210, 0, "seul", epingle=ep)
        out[f"{nom}|epinglage={ep}"] = round(e["succes_vram"] + e["succes_ram"] - u["succes_vram"], 6)
print(out)
json.dump(out, open(sys.argv[2], "w"), indent=1)
