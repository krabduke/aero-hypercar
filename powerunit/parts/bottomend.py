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
import shapes

SM = spec.RES["small_revolve"]
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
    out.update(_damper())
    out.update(_cap_bolts())
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
    return {"crankshaft": mesh.join(*parts),
            # between the damper and the timing case, not under the damper
            "crank_trigger": _crank_trigger(x0 - C["nose_len"] + 40.0)}


def _crank_trigger(x):
    """The toothed wheel the crank sensor reads, and the sensor reading it.

    Without this the engine cannot be started, cannot be timed and cannot be
    run: the ECU has no idea where the crank is. A 393-part model of an engine
    that had every bearing shell and no way of knowing its own crank angle was
    missing the one part that is not optional.

    It is a 60-2 wheel -- sixty tooth positions with two teeth left out, so
    the gap tells the ECU which revolution it is looking at.
    """
    parts = []
    rw = C["nose_r"] + 26.0
    parts.append(mesh.revolve_closed(
        [(x - 3.0, C["nose_r"]), (x + 3.0, C["nose_r"]),
         (x + 3.0, rw - 9.0), (x + 2.0, rw - 9.0),
         (x + 2.0, rw - 3.0), (x - 2.0, rw - 3.0),
         (x - 2.0, rw - 9.0), (x - 3.0, rw - 9.0)], SEG))
    for i in range(60):
        if i in (0, 1):                    # the missing pair: the index gap
            continue
        a = 2 * math.pi * i / 60
        tv, tf = mesh.box(0.0, 0.0, 0.0, 4.0, 3.0, 6.4)
        parts.append(([(px + x, py + math.cos(a) * (rw - 3.0)
                        - math.sin(a) * pz,
                        math.sin(a) * (rw - 3.0) + math.cos(a) * pz)
                       for (px, py, pz) in tv], tf))
    # the sensor on its bracket, looking at the teeth across an air gap
    sv, sf = mesh.revolve_closed(
        [(0.0, 0.0), (34.0, 0.0), (34.0, 7.0), (30.0, 9.5),
         (10.0, 9.5), (8.0, 13.0), (0.0, 13.0)], SM)
    parts.append(([(pz + x, py + 0.0, -px + rw + 35.0)
                   for (px, py, pz) in sv], sf))
    parts.append(shapes.rounded_box(x, 0.0, rw + 44.0, 10.0, 34.0, 22.0,
                                    4.0, seg=5))
    return mesh.join(*parts)


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
            # Rings are chamfered: a square edge would not seal and would
            # gall the bore. The oil ring is a scraper with a relieved waist.
            if tag == "oil":
                prof = [(dz - h, rr - t), (dz - h, rr - 0.3), (dz - h * 0.4, rr),
                        (dz, rr - 0.7), (dz + h * 0.4, rr),
                        (dz + h, rr - 0.3), (dz + h, rr - t)]
            else:
                prof = [(dz - h, rr - t), (dz - h, rr - 0.35),
                        (dz - h * 0.5, rr), (dz + h * 0.5, rr),
                        (dz + h, rr - 0.35), (dz + h, rr - t)]
            rv, rf = mesh.revolve_closed(prof, spec.RES["revolve"] // 2)
            out[f"ring_{tag}_{n}"] = (common.along_bank(rv, x, along, bank), rf)

        # gudgeon pin
        # A gudgeon pin is hollow, chamfered at both ends and grooved for
        # the circlips that keep it in the piston. It was a plain tube.
        pr = P["pin_r"]
        gv, gf = mesh.revolve_closed(
            [(-13.0, pr * 0.52), (-13.0, pr - 1.0), (-11.8, pr),
             (-11.0, pr), (-10.4, pr - 1.3), (-9.6, pr - 1.3),
             (-9.0, pr), (9.0, pr), (9.6, pr - 1.3), (10.4, pr - 1.3),
             (11.0, pr), (11.8, pr), (13.0, pr - 1.0), (13.0, pr * 0.52)],
            SM)
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
    v, f = mesh.tube(-9.5, 9.5, C["pin_r"] + 1.2, R["big_end_r"], SM)
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
        v, f = mesh.tube(-w / 2, w / 2, r_in, r_out, SM)
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


def _damper():
    """Harmonic damper on the crank nose.

    A flat-plane V8 has a first-order couple and a crank that rings; the
    damper is the elastomer-bonded inertia ring that stops it. The engine had
    a bare crank snout with a pulley behind the timing cover and nothing on
    the front of it at all.
    """
    C = spec.CRANK
    # ahead of the timing cover, which closes at x = -266 with its front face
    # at -284. The damper was at -300..-260 and so was buried in it; the crank
    # nose is 128 mm long now, which is what lets a damper mount in front of
    # the case the way it does on a real engine.
    x0 = -352.0
    parts = []

    def lathe(profile, seg=36):
        v, f = mesh.revolve_closed(list(profile), seg)
        return ([(px, py, pz) for (px, py, pz) in v], f)

    # hub, clamped on the nose
    parts.append(lathe([(x0 + 4.0, 0.0), (x0 + 4.0, C["nose_r"] + 3.0),
                        (x0 + 40.0, C["nose_r"] + 3.0), (x0 + 40.0, 0.0)], 28))
    # the web out to the inertia ring
    parts.append(lathe([(x0 + 10.0, C["nose_r"] + 3.0),
                        (x0 + 10.0, 74.0), (x0 + 22.0, 74.0),
                        (x0 + 22.0, C["nose_r"] + 3.0)]))
    # the elastomer band, then the inertia ring outside it
    parts.append(lathe([(x0 + 6.0, 74.0), (x0 + 6.0, 82.0),
                        (x0 + 30.0, 82.0), (x0 + 30.0, 74.0)]))
    parts.append(lathe([(x0 + 2.0, 82.0), (x0 + 2.0, 96.0),
                        (x0 + 34.0, 96.0), (x0 + 34.0, 82.0)]))
    # the belt grooves cut in its face -- this is also the crank pulley
    for k in range(5):
        gx = x0 + 8.0 + k * 5.0
        parts.append(lathe([(gx, 96.0), (gx + 2.2, 99.5),
                            (gx + 4.6, 96.0)], 36))
    # and the timing mark notch
    nv, nf = mesh.cylinder(x0 + 34.0, x0 + 38.0, 5.0, 8)
    parts.append((mesh.translate(nv, 0.0, 90.0, 0.0), nf))
    return {"crank_damper": mesh.join(*parts)}


def _cap_bolts():
    """Two studs and nuts per main cap.

    Five main caps were holding the crank down with nothing through them.
    """
    parts = []
    for i in range(spec.CRANK["n_mains"]):
        x = -204.0 + i * 102.0
        for sy in (-1.0, 1.0):
            y = sy * 38.0
            sv, sf = mesh.revolve_closed(
                [(0.0, 0.0), (78.0, 0.0), (78.0, 8.0), (0.0, 8.0)], 12)
            sv = [(py + x, pz + y, px - 82.0) for (px, py, pz) in sv]
            parts.append((sv, sf))
            nv, nf = mesh.revolve_closed(
                [(0.0, 0.0), (16.0, 0.0), (16.0, 14.0), (12.0, 15.5),
                 (4.0, 15.5), (0.0, 14.0)], 6)
            nv = [(py + x, pz + y, px - 84.0) for (px, py, pz) in nv]
            parts.append((nv, nf))
    return {"main_cap_bolts": mesh.join(*parts)}
