"""Hybrid system: MGU-K on the crank nose, MGU-H on the turbo shaft,
inverter over the vee, and the battery under the engine."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
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
        fv, ff = shapes.rounded_box(Y["mguk_x"], Y["mguk_r"] + 5.0, 0.0,
                                    Y["mguk_len"] * 0.86, 11.0, 3.0, 1.2)
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
    """Inverter, battery and ECU.

    All three were plain boxes. None of them is: the inverter and the battery
    both have to reject a lot of heat and so carry fin stacks, everything has
    a connector because something plugs into it, and a cast case has radiused
    edges and draft rather than knife corners.
    """
    out = {}
    ix, iy, iz = Y["inverter_pos"]
    sx, sy, sz = Y["inverter"]
    out["inverter"] = shapes.finned_case(ix, iy, iz, sx, sy, sz,
                                         n_fins=11, fin_h=9.0, fin_t=3.4,
                                         r=7.0, axis="x")
    out["inverter_connectors"] = mesh.join(
        shapes.connector(ix - sx * 0.5 - 12.0, iy, iz + sz * 0.1, 28.0, 22.0, 16.0, 8),
        shapes.connector(ix + sx * 0.5 + 12.0, iy, iz + sz * 0.1, 28.0, 22.0, 16.0, 8))

    bx, by, bz = Y["battery_pos"]
    sx, sy, sz = Y["battery"]
    out["battery"] = shapes.finned_case(bx, by, bz, sx, sy, sz,
                                        n_fins=14, fin_h=6.0, fin_t=3.0,
                                        r=8.0, axis="x", side=-1.0)
    # the modules inside it, visible when the case is hidden
    mods = []
    for i in range(6):
        f = (i + 0.5) / 6
        mods.append(shapes.rounded_box(bx - sx / 2 + sx * f, by, bz,
                                       sx / 7.6, sy * 0.82, sz * 0.72, 4.0))
    out["battery_modules"] = mesh.join(*mods)
    out["battery_terminals"] = mesh.join(
        shapes.connector(bx - sx * 0.3, by, bz + sz * 0.5 + 7.0, 34.0, 20.0, 14.0, 2),
        shapes.connector(bx + sx * 0.3, by, bz + sz * 0.5 + 7.0, 34.0, 20.0, 14.0, 2))

    a = spec.ANCILLARY
    sx, sy, sz = a["ecu"]
    out["ecu"] = shapes.finned_case(0.0, 132.0, 176.0, sx, sy, sz,
                                    n_fins=9, fin_h=5.0, fin_t=2.6, r=5.0)
    out["ecu_connector"] = shapes.connector(-sx * 0.5 - 10.0, 132.0, 176.0,
                                            22.0, sy * 0.6, sz * 0.5, 10)
    return out
