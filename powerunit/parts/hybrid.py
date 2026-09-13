"""Hybrid system: MGU-K on the crank nose, MGU-H on the turbo shaft,
inverter over the vee, and the battery under the engine."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

Y = spec.HYBRID
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_mguk())
    out.update(_mguh())
    out.update(_electronics())
    return out


def _mguk():
    """Motor-generator on the crankshaft. 200 kW both ways, so it is also the
    engine's starter and a large part of its braking recovery."""
    v, f = mesh.tube(Y["mguk_x"] - Y["mguk_len"] / 2, Y["mguk_x"] + Y["mguk_len"] / 2,
                     spec.CRANK["nose_r"] + 4.0, Y["mguk_r"], SEG)
    fins = []
    for k in range(28):
        a = 2 * math.pi * k / 28
        fv, ff = mesh.box(Y["mguk_x"], Y["mguk_r"] + 5.0, 0.0,
                          Y["mguk_len"] * 0.86, 11.0, 3.0)
        fins.append((mesh.rot_x(fv, a), ff))
    return {"mguk": mesh.join((v, f), *fins)}


def _mguh():
    """Motor-generator on the turbo shaft: harvests exhaust energy and spins
    the compressor to kill lag."""
    parts = []
    for x in spec.TURBO["x"]:
        v, f = mesh.tube(x - Y["mguh_len"] / 2, x + Y["mguh_len"] / 2,
                         spec.TURBO["shaft_r"] + 2.0, Y["mguh_r"], 30)
        v = [(px, py, pz + spec.TURBO["z"]) for (px, py, pz) in v]
        parts.append((v, f))
    return {"mguh": mesh.join(*parts)}


def _electronics():
    out = {}
    ix, iy, iz = Y["inverter_pos"]
    out["inverter"] = mesh.box(ix, iy, iz, *Y["inverter"])
    bx, by, bz = Y["battery_pos"]
    out["battery"] = mesh.box(bx, by, bz, *Y["battery"])
    a = spec.ANCILLARY
    out["ecu"] = mesh.box(0.0, 132.0, 176.0, *a["ecu"])
    return out
