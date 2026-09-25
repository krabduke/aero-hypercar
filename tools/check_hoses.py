"""Every coolant hose clears everything it is not meant to touch.

The intersection audit has to let a hose share material with the engine --
it is pushed onto the engine's stubs, and the engine is one part here -- and
that same rule would let a hose run straight through the engine's middle
without a word. Which is what happened: the main radiator hoses ended for
months inside the cylinder banks, 300 mm from any port.

So each hose's centreline is walked here against the built car, like
tools/route_solve's checker in the sibling projects: nothing but its own
circuit (the radiators, tanks, pumps and hoses), the skins it passes through
(tub, sidepod) and, over its last 40 mm onto a stub, the engine may come
within its radius plus 1.5 mm of it.

    python3 tools/check_hoses.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _interfere  # noqa: E402

if not _interfere.in_blender():
    import subprocess
    out = subprocess.run([_interfere.blender_exe(), "-b", "--factory-startup",
                          "-P", os.path.abspath(__file__)],
                         capture_output=True, text=True).stdout
    lines = [l for l in out.splitlines()
             if l.startswith(("PASS", "FAIL", "  ", "Traceback", "Error"))]
    sys.stdout.write("".join(l + "\n" for l in lines))
    sys.exit(0 if any(l.startswith("PASS") for l in lines) else 1)

import importlib.util  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "car"))
spec_ = importlib.util.spec_from_file_location(
    "ai", os.path.join(HERE, "audit_intersect.py"))
ai = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(ai)
from parts import powertrain as pt  # noqa: E402

ONTO_STUB = 40.0
OWN = ("rad_", "lt_pump_lead_", "tub", "sidepod_")


def _trim(path, L):
    out, rem = list(path), L
    while rem > 0 and len(out) > 1:
        a, b = out[-2], out[-1]
        d = math.dist(a, b)
        if d > rem:
            f = (d - rem) / d
            out[-1] = tuple(a[k] + (b[k] - a[k]) * f for k in range(3))
            rem = 0
        else:
            out.pop()
            rem -= d
    return out


def routes():
    _built, espec = pt._load_engine()
    P, yj, _ret = pt.rad_hose_paths(espec)
    for tag, paths in P.items():
        for i, p in enumerate(paths):
            onto = tuple(p[-1]) != tuple(yj)      # ends on an engine stub
            yield f"radiator {tag}{i}", (_trim(p, ONTO_STUB) if onto else p), 18.0
    for tag, paths in pt.lt_hose_paths(espec).items():
        for i, p in enumerate(paths):
            yield f"charge cooler {tag}{i}", _trim(p, ONTO_STUB), pt.LT_HOSE_R


m = _interfere.Model(ROOT, ai.PKG)
K = 1.0 / ai.UNIT
bad = []
n_routes = 0
for name, pts, r in routes():
    n_routes += 1
    worst = {}
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / 4.0))
        for i in range(n + 1):
            p = tuple((a[k] + (b[k] - a[k]) * i / n) * K for k in range(3))
            for part in m.names:
                if part.startswith(OWN):
                    continue
                lo, hi = m.box[part]
                if not all(lo[k] - (r + 3) * K <= p[k] <= hi[k] + (r + 3) * K
                           for k in range(3)):
                    continue
                if m.inside(part, p):
                    d = -1.0
                else:
                    hit = m.tree[part].find_nearest(m.V(p))
                    if hit[0] is None or hit[3] / K > r + 1.5:
                        continue
                    if m.cut_away(part, tuple(hit[0])):
                        continue
                    d = hit[3] / K
                if part not in worst or d < worst[part][0]:
                    worst[part] = (d, tuple(round(c / K) for c in p))
    for part, (d, p) in worst.items():
        what = "through" if d < 0 else f"{d:.1f} mm from the centreline of"
        bad.append(f"  {name}: {what} {part} at {p}")
if bad:
    print(f"FAIL  {len(bad)} hoses foul something")
    for b in bad:
        print(b)
else:
    print(f"PASS  all {n_routes} coolant hoses run clear")
