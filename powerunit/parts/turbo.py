"""Twin turbochargers in the vee, exhaust manifolds, wastegates, tailpipes.

Hot vee: the exhaust ports face inward into the vee and the turbos sit between
the banks. It makes the shortest possible path from port to turbine, which is
what the transient response depends on, and it keeps the outside of the engine
cold so the car's bodywork can be tight around it.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

T = spec.TURBO
E = spec.EXHAUST
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_turbos())
    out.update(_manifolds())
    out.update(_tailpipes())
    return out


def _snail(cx, cz, r, w, sgn):
    """A volute: a torus-ish housing with a tangential outlet."""
    parts = []
    prof = []
    n = 22
    for i in range(n):
        ang = 2 * math.pi * i / n
        rr = r * (0.62 + 0.30 * (i / n))          # spiral growth
        prof.append((cx + (w / 2) * math.cos(ang), rr))
    v, f = mesh.revolve_closed(
        [(cx - w / 2, r * 0.34), (cx + w / 2, r * 0.34),
         (cx + w / 2, r), (cx - w / 2, r)], 30)
    v = [(x, y * 0.0 + y, z + cz) for (x, y, z) in v]
    parts.append((v, f))
    return mesh.join(*parts)


def _turbos():
    parts = []
    for i, x in enumerate(T["x"]):
        sgn = -1 if i == 0 else 1
        # turbine housing (hot, inboard) and compressor housing (cold)
        parts.append(_housing(x - T["housing_w"] * 0.6, T["z"], T["turb_r"],
                              T["housing_w"]))
        parts.append(_housing(x + T["housing_w"] * 0.6, T["z"], T["comp_r"],
                              T["housing_w"] * 0.9))
        # centre section
        cv, cf = mesh.tube(x - T["housing_w"] * 0.6, x + T["housing_w"] * 0.6,
                           0.0, T["shaft_r"] * 2.6, 22)
        cv = [(px, py, pz + T["z"]) for (px, py, pz) in cv]
        parts.append((cv, cf))
        # wastegate
        wv, wf = mesh.cylinder(0.0, 64.0, T["wastegate_r"], 18)
        wv = [(px + x, py + T["turb_r"] * 0.8, pz + T["z"] + 30.0)
              for (px, py, pz) in wv]
        parts.append((wv, wf))
    return {"turbos": mesh.join(*parts)}


def _housing(x, z, r, w):
    v, f = mesh.revolve_closed(
        [(x - w / 2, r * 0.30), (x + w / 2, r * 0.30),
         (x + w / 2, r), (x - w / 2, r)], 30)
    return [(px, py, pz + z) for (px, py, pz) in v], f


def _manifolds():
    """One primary per cylinder, running from the inboard exhaust port up into
    the nearest turbine."""
    parts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        port = common.bank_point(x, spec.DECK_HEIGHT + 22.0,
                                 spec.HEAD["cam_centres"] * 0.30, bank)
        turb_x = T["x"][0] if x < 0 else T["x"][1]
        mid = (x * 0.6 + turb_x * 0.4, port[1] * 0.45, T["z"] - 34.0)
        end = (turb_x - T["housing_w"] * 0.6, 0.0, T["z"] - T["turb_r"] * 0.5)
        parts.append(mesh.pipe([port, mid, end], E["primary_r"],
                               spec.RES["pipe"]))
    return {"exhaust_manifolds": mesh.join(*parts)}


def _tailpipes():
    parts = []
    for i, x in enumerate(T["x"]):
        sgn = -1 if i == 0 else 1
        start = (x - T["housing_w"] * 1.1, 0.0, T["z"])
        parts.append(mesh.pipe(
            [start, (x, sgn * 46.0, T["z"] + 24.0),
             (spec.BLOCK["x_rear"] + 70.0, sgn * 52.0, T["z"] + 40.0)],
            E["collector_r"], spec.RES["pipe"]))
    return {"tailpipes": mesh.join(*parts)}
