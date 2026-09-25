"""The engine's wiring harness.

Every electrical device on the engine has a connector -- eight coils,
eight direct injectors, eight port injectors, six knock sensors, two cam
sensors -- and until now not one of them was wired to anything. This is the
loom that does it, laid out the way an engine harness is:

    ignition loom   along each cam cover's outboard shoulder, a pigtail up
                    to the connector on each coil's head
    injector loom   along each head's outboard face below the injectors, a
                    pigtail to each direct injector's connector and each
                    knock sensor's
    port injectors  pigtails from the ignition loom down to each port
                    injector's connector
    cam sensors     from the ignition loom's rear end to the cam sensors
                    behind the heads
    trunks          each bank's two looms join behind the last cylinder and
                    run down the flank to the ECU; the left bank's trunk
                    crosses under the sump

Each branch ends in a mating plug on its device's connector. Every
position comes from the part it plugs into (heads, induction, ancillaries,
hybrid), so a connector that moves takes its wire with it.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec          # noqa: E402
import mesh          # noqa: E402
import shapes        # noqa: E402
from parts import common   # noqa: E402

SM = spec.RES["small_revolve"]
H = spec.HEAD
B = spec.BLOCK

LOOM_R = 6.0         # a bank loom, in its convoluted sleeve
PIG_R = 3.2          # a pigtail to one device
TRUNK_R = 7.5        # the left bank's three looms together

IGN = (317.0, 42.0)      # ignition loom: along, lateral (bank frame)
INJ = (134.0, -96.0)     # injector loom
PFI_LOOM = (228.0, 146.0)   # port-injector loom: |y|, z, under the cover's edge


def bp(x, along, lat, bank):
    return common.bank_point(x, along, lat, bank)


def _bank_cyls(bank):
    return sorted((x, n) for (n, _p, b, x, _a) in spec.cylinders() if b == bank)


# -------------------------------------------------------------------------
# where every connector's mating plug sits

def coil_plug(x, bank):
    from parts import heads
    _x, along, lat = heads.coil_connector(x)
    return bp(x, along, lat + 15.0, bank)


def di_plug(x, bank):
    from parts import heads
    a, l = heads.DI_TIP
    s = heads.DI_CONN_S
    along = a + s * math.sin(heads.DI_TILT)
    lat = l - s * math.cos(heads.DI_TILT)
    return bp(x - 30.0, along, lat, bank)


def pfi_plugs(bank):
    """Mating plugs on the port injectors' connectors: pins face forward."""
    from parts import induction
    out = []
    for (n, _p, b, x, _a) in spec.cylinders():
        if b != bank:
            continue
        v = induction.build()[f"pfi_plug_{n}"][0]
        c = [sum(p[i] for p in v) / len(v) for i in range(3)]
        out.append((c[0] - 13.0, c[1], c[2]))
    return out


def knock_plugs(bank):
    s = -1.0 if bank == 0 else 1.0
    return [(x + 16.0, s * (B["half_width"] - 2.0 + 40.0), 12.0)
            for x in (-102.0, 0.0, 102.0)]


def cam_plugs(bank):
    """Mating plugs on the cam sensors' connectors: pins face outboard."""
    s = -1.0 if bank == 0 else 1.0
    out = []
    for j in (0, 1):
        h = spec.DECK_HEIGHT + H["height"] * 0.62
        off = H["cam_centres"] / 2 * (1 if j else -1)
        y = s * (B["bank_half_width"] + 46.0 + off * 0.3)
        z = h + abs(off) * 0.5 * (1 if j else -1)
        out.append((H["x_rear"] + 26.0, y + s * 15.0, z))
    return out


def ecu_plug():
    a = spec.ANCILLARY
    sx, sy, sz = a["ecu"]
    ex, ey, ez = -59.5 + sx / 2, 196.0, -50.0
    return (ex + sx * 0.5 + 10.0 + 11.0 + 8.0, ey, ez)


# -------------------------------------------------------------------------
# nets: what has to be wired to what. tools/route_solve finds each one a clear
# path through the engine and writes engine/harness_routes.json, which is
# what gets built; audit_intersect then checks the result like any part.
#
#   python3 engine/parts/harness.py nets.json
#   python3 ../_shared/tools/route_solve.py . nets.json engine/harness_routes.json

def _lead(p, d, k=9.0):
    """A point k mm out of a plug along its pins' direction d."""
    return [p[i] + d[i] * k for i in range(3)]


def devices(bank):
    """(name, plug, lead-out direction) for everything on a bank."""
    s = -1.0 if bank == 0 else 1.0
    tag = "lr"[bank]
    out = []
    lat = common.bank_lat(bank)
    for (x, n) in _bank_cyls(bank):
        out.append((f"coil_{n}", coil_plug(x, bank), tuple(lat)))
        out.append((f"di_{n}", di_plug(x, bank), (-1.0, 0.0, 0.0)))
    for i, p in enumerate(pfi_plugs(bank)):
        out.append((f"pfi_{tag}{i}", p, (-1.0, 0.0, 0.0)))
    for i, p in enumerate(knock_plugs(bank)):
        out.append((f"knock_{tag}{i}", p, (1.0, 0.0, 0.0)))
    for i, p in enumerate(cam_plugs(bank)):
        out.append((f"cam_{tag}{i}", p, (0.0, s, 0.0)))
    return out


# (and the harness itself: the solver loads whatever harness the last solve
# built, and must not route round its own old wires)
ENDS = ["coil_", "injector_di_", "pfi_plug_", "pfi_injector_", "knock_sensor_",
        "cam_sensor_", "ecu", "harness"]


def nets():
    out = []
    ecu = ecu_plug()
    ecu_lead = _lead(ecu, (1.0, 0.0, 0.0), 12.0)
    for bank in (0, 1):
        tag = "lr"[bank]
        dev = devices(bank)
        leads = {n: _lead(p, d) for (n, p, d) in dev}
        coils = [leads[n] for (n, _p, _d) in dev if n.startswith("coil_")]
        dis = [leads[n] for (n, _p, _d) in dev if n.startswith(("di_", "knock_"))]
        dis.sort(key=lambda p: p[0])
        pfis = sorted((leads[n] for (n, _p, _d) in dev if n.startswith("pfi_")),
                      key=lambda p: p[0])
        cams = [leads[n] for (n, _p, _d) in dev if n.startswith("cam_")]
        # three trunks along the bank, each threading its devices front to
        # back, all ending at the ECU
        # (the left bank's end at a junction behind its last cylinder, and
        # cross to the ECU as one bundle, behind the sump: nothing crosses
        # the engine anywhere else)
        end = ecu_lead if bank == 1 else JUNCTION_L
        for kind, pts in (("ign", coils + cams), ("inj", dis), ("pfi", pfis)):
            out.append({"name": f"trunk_{kind}_{tag}", "a": pts[0],
                        "via": pts[1:], "b": end, "r": trunk_r(kind), "clear": 2.5,
                        "ends": ENDS, "max_nodes": 2000000})
    out.append({"name": "trunk_cross", "a": JUNCTION_L, "via": [CROSSING],
                "b": ecu_lead, "r": TRUNK_R, "clear": 2.5, "ends": ENDS,
                "max_nodes": 400000})
    return out


def trunk_r(kind):
    """The port injectors' loom carries sixteen wires, the others more."""
    return PFI_R if kind == "pfi" else LOOM_R


PFI_R = 4.5
JUNCTION_L = [190.0, -180.0, -62.0]    # the open pocket under the left bank's rear
CROSSING = [214.0, 0.0, -150.0]        # behind the sump, ahead of the bell


def branches():
    """Each device's plug to its lead-out point: the last few millimetres,
    straight out along its pins."""
    out = []
    for bank in (0, 1):
        for (n, p, d) in devices(bank):
            out.append((n, [list(p), _lead(p, d)]))
    out.append(("ecu", [list(ecu_plug()), _lead(ecu_plug(), (1.0, 0.0, 0.0), 12.0)]))
    return out


def _closest(p, a, b):
    """The point on segment ab nearest p."""
    ab = [b[i] - a[i] for i in range(3)]
    L = sum(c * c for c in ab)
    t = 0.0 if L == 0 else max(0.0, min(1.0, sum((p[i] - a[i]) * ab[i]
                                                 for i in range(3)) / L))
    return tuple(a[i] + ab[i] * t for i in range(3))


ROUTES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "harness_routes.json")


def build():
    import json
    if not os.path.exists(ROUTES):
        return {}
    solved = json.load(open(ROUTES))
    parts = []
    lines = []
    for name, pts in solved.items():
        r = (TRUNK_R if name == "trunk_cross" else
             PFI_R if name.startswith("trunk_pfi") else
             LOOM_R if name.startswith("trunk") else PIG_R)
        parts.append(mesh.pipe([tuple(p) for p in pts], r, 12, bend=3.0 * r))
        # the centreline as built, corners rounded
        lines.append(mesh.fillet_path([tuple(p) for p in pts], [r] * len(pts),
                                      3.0 * r)[0])
    for name, pts in branches():
        # A trunk threads each lead-out point as a via, but rounds the corner
        # it turns there, so where it doubles back to reach a plug it passes
        # a few millimetres short of the point: the pigtail ended beside its
        # loom, not in it. It carries on to the trunk's actual centreline.
        lead = tuple(pts[-1])
        on = min((_closest(lead, a, b) for ln in lines
                  for a, b in zip(ln, ln[1:])), key=lambda q: math.dist(q, lead))
        path = [tuple(p) for p in pts]
        if math.dist(on, lead) > 1.0:
            path.append(on)
        parts.append(mesh.pipe(path, PIG_R, 12))
        # the mating plug on the device's connector
        parts.append(shapes.rounded_box(*pts[0], 12.0, 12.0, 12.0, 2.5))
    return {"harness": mesh.join(*parts)}


if __name__ == "__main__":
    import json
    json.dump(nets(), open(sys.argv[1], "w"), indent=1)
