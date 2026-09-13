"""Crankshaft, pistons, connecting rods.

The crank is built from real kinematics: each piston sits where its crankpin
angle and rod length put it, so the engine is modelled at a genuine instant of
its cycle rather than with all eight pistons at mid-stroke.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

C = spec.CRANK
P = spec.PISTON
R = spec.ROD
SEG = spec.RES["revolve"]
CRANK_ANGLE = 24.0      # the instant the engine is frozen at, degrees


def build():
    out = {}
    out.update(_crankshaft())
    out.update(_pistons_and_rods())
    return out


def _pin_angle(pair):
    return math.radians(spec.CRANKPIN_ANGLES[pair] + CRANK_ANGLE)


def _pin_centre(pair):
    """Crankpin centre in the y-z plane."""
    a = _pin_angle(pair)
    return (C["throw"] * math.cos(a), C["throw"] * math.sin(a))


def _piston_along(pair, bank):
    """Distance from crank centreline to the gudgeon pin, along the bore axis.

    Standard slider-crank: the pin offset is resolved into components along and
    across the bore axis, and the rod closes the triangle.
    """
    py, pz = _pin_centre(pair)
    d = common.bank_dir(bank)
    l = common.bank_lat(bank)
    along = py * d[1] + pz * d[2]
    across = py * l[1] + pz * l[2]
    return along + math.sqrt(max(R["big_end_r"] * 0.0 + spec.ROD_LENGTH ** 2
                                 - across ** 2, 1.0))


def _crankshaft():
    parts = []
    x0 = spec.BLOCK["x_front"] + 20.0
    x1 = spec.BLOCK["x_rear"] - 20.0
    n_main = C["n_mains"]

    # main journals
    for i in range(n_main):
        x = x0 + (x1 - x0) * i / (n_main - 1)
        parts.append(mesh.tube(x - 17.0, x + 17.0, 0.0, C["main_r"], SEG))

    # crankpins and webs
    for pair in range(spec.N_CYL // 2):
        py, pz = _pin_centre(pair)
        xc = spec.cylinder_x(pair)
        pv, pf = mesh.tube(xc - 21.0, xc + 21.0, 0.0, C["pin_r"], SEG)
        parts.append(([(x, y + py, z + pz) for (x, y, z) in pv], pf))
        for sgn in (-1, 1):
            wx = xc + sgn * 28.0
            a = _pin_angle(pair)
            wv, wf = mesh.tube(wx - C["web_t"] / 2, wx + C["web_t"] / 2,
                               0.0, C["web_r"], SEG)
            # counterweight: offset opposite the pin
            wv = [(x, y - math.cos(a) * C["throw"] * 0.62,
                   z - math.sin(a) * C["throw"] * 0.62) for (x, y, z) in wv]
            parts.append((wv, wf))

    # nose and flywheel flange
    parts.append(mesh.tube(x0 - C["nose_len"], x0, 0.0, C["nose_r"], SEG))
    parts.append(mesh.tube(x1, x1 + C["flange_t"], 0.0, C["flange_r"], SEG))
    return {"crankshaft": mesh.join(*parts)}


def _pistons_and_rods():
    pistons, rods = [], []
    r = spec.BORE / 2 - 0.35
    for (n, pair, bank, x, a) in spec.cylinders():
        along = _piston_along(pair, bank)

        # piston: crown, ring land grooves, skirt
        pv, pf = mesh.revolve_closed(
            [(0.0, 0.0), (0.0, r),
             (-P["crown_t"], r), (-P["crown_t"] - 2.0, r - 2.2),
             (-P["crown_t"] - 5.0, r), (-P["skirt_len"], r),
             (-P["skirt_len"], r - 7.0), (0.0 - P["crown_t"] - 1.0, r - 7.0)],
            SEG)
        pv = common.along_bank(pv, x, along, bank)
        pistons.append((pv, pf))

        # gudgeon pin
        gv, gf = mesh.tube(-13.0, 13.0, 0.0, P["pin_r"], 16)
        gv = [(z, y, px) for (px, y, z) in gv]      # axis +x -> engine +x
        gv = common.along_bank(gv, x, along - P["crown_t"] - 12.0, bank)
        pistons.append((gv, gf))

        # rod: small end at the gudgeon pin, big end on the crankpin
        py, pz = _pin_centre(pair)
        small = common.bank_point(x, along - P["crown_t"] - 12.0, 0.0, bank)
        big = (x, py, pz)
        rods.append(_rod(small, big))
    return {"pistons": mesh.join(*pistons), "conrods": mesh.join(*rods)}


def _rod(small, big):
    """I-beam rod between two eyes."""
    parts = []
    parts.append(mesh.pipe([small, big], R["beam_t"] * 0.62, 10))
    for (c, r_out, r_in, w) in ((small, R["small_end_r"], P["pin_r"] + 1.0, 15.0),
                                (big, R["big_end_r"], C["pin_r"] + 1.2, 19.0)):
        v, f = mesh.tube(-w / 2, w / 2, r_in, r_out, 24)
        v = [(px + c[0], py + c[1], pz + c[2]) for (px, py, pz) in v]
        parts.append((v, f))
    return mesh.join(*parts)
