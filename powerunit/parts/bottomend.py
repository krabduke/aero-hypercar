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
    """Each piston, gudgeon pin and rod is its own object. They are separate
    components on the real engine and they move relative to each other, so
    merging them into one mesh loses information."""
    out = {}
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
        out[f"piston_{n}"] = (pv, pf)

        # Ring pack: top compression, second compression, oil control. Three
        # separate parts with three different jobs and three different
        # sections -- the oil ring is a scraper and is nothing like the other
        # two -- so three objects, not one called "rings".
        for tag, dz, rr, t, h in (("top", -2.2, r - 0.4, 2.6, 1.1),
                                  ("second", -5.4, r - 0.5, 2.9, 1.2),
                                  ("oil", -9.0, r - 0.6, 3.6, 1.5)):
            rv, rf = mesh.tube(dz - h, dz + h, rr - t, rr, 28)
            out[f"ring_{tag}_{n}"] = (common.along_bank(rv, x, along, bank), rf)

        # gudgeon pin
        gv, gf = mesh.tube(-13.0, 13.0, 0.0, P["pin_r"], 16)
        gv = [(z, y, px) for (px, y, z) in gv]      # axis +x -> engine +x
        gv = common.along_bank(gv, x, along - P["crown_t"] - 12.0, bank)
        out[f"gudgeon_pin_{n}"] = (gv, gf)

        # rod: small end at the gudgeon pin, big end on the crankpin
        py, pz = _pin_centre(pair)
        small = common.bank_point(x, along - P["crown_t"] - 12.0, 0.0, bank)
        big = (x, py, pz)
        out[f"conrod_{n}"] = _rod(small, big)
        out[f"rod_cap_{n}"] = _rod_cap(big)
    return out


def _rod_cap(big):
    """Big-end cap and its two bolts."""
    parts = []
    v, f = mesh.tube(-9.5, 9.5, C["pin_r"] + 1.2, R["big_end_r"], 24)
    parts.append(([(px + big[0], py + big[1], pz + big[2]) for (px, py, pz) in v], f))
    for sgn in (-1, 1):
        bv, bf = mesh.cylinder(0.0, 34.0, 4.2, 10)
        bv = [(pz + big[0], py + big[1] + sgn * (R["big_end_r"] - 5.0),
               px + big[2] - 17.0) for (px, py, pz) in bv]
        parts.append((bv, bf))
    return mesh.join(*parts)


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


def pin_centre(pair, theta_deg):
    """Crankpin centre in the y-z plane at a given crank angle."""
    a = math.radians(spec.CRANKPIN_ANGLES[pair] + theta_deg)
    return (C["throw"] * math.cos(a), C["throw"] * math.sin(a))


def piston_along(pair, bank, theta_deg):
    """Gudgeon pin distance from the crank centreline, along the bore axis."""
    py, pz = pin_centre(pair, theta_deg)
    d, l = common.bank_dir(bank), common.bank_lat(bank)
    along = py * d[1] + pz * d[2]
    across = py * l[1] + pz * l[2]
    return along + math.sqrt(max(spec.ROD_LENGTH ** 2 - across ** 2, 1.0))


def rod_tilt(pair, bank, theta_deg):
    """Rod angle from the bore axis, radians. asin(across / L)."""
    py, pz = pin_centre(pair, theta_deg)
    l = common.bank_lat(bank)
    across = py * l[1] + pz * l[2]
    return math.asin(max(-1.0, min(1.0, across / spec.ROD_LENGTH)))


def kinematics():
    """Everything the viewer needs to turn a crank angle into part positions.

    The slider-crank is solved in the viewer rather than baked, so the engine
    can be run at any angle. These are the same functions the geometry was
    built from, so the model at the build angle and the model the viewer
    draws at that angle are the same model.
    """
    out = {"build_angle": CRANK_ANGLE, "throw": C["throw"],
           "rod": spec.ROD_LENGTH, "pins": spec.CRANKPIN_ANGLES,
           "firing_order": spec.FIRING_ORDER, "cylinders": []}
    for (n, pair, bank, x, ang) in spec.cylinders():
        d = common.bank_dir(bank)
        out["cylinders"].append({
            "n": n, "pair": pair, "bank": bank, "x": x,
            "dir": [d[1], d[2]],
            "along0": piston_along(pair, bank, CRANK_ANGLE),
            "tilt0": rod_tilt(pair, bank, CRANK_ANGLE),
        })
    return out


def pivots():
    """Moving parts and what they move about.

    Pistons and their rings and pins slide along the bore, so their pivot is
    the gudgeon pin. Rods swing about that same pin, so they share it. The
    crankshaft turns about its own centreline.
    """
    out = {}
    out["crankshaft"] = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1.0, "crank", "")
    for (n, pair, bank, x, ang) in spec.cylinders():
        along = piston_along(pair, bank, CRANK_ANGLE)
        d = common.bank_dir(bank)
        pin = (x, d[1] * along, d[2] * along)
        for stem, role in (("piston", "slider"), ("rings", "slider"),
                           ("gudgeon_pin", "slider"), ("conrod", "rod"),
                           ("rod_cap", "rod")):
            out[f"{stem}_{n}"] = (pin, (1.0, 0.0, 0.0), 1.0, role, n)
    return out
