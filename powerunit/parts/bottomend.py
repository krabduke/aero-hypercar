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
    # the tail through the rear main seal, then the flywheel flange outside
    parts.append(mesh.tube(x1, spec.FLANGE_X, 0.0, C["main_r"], SEG))
    parts.append(mesh.tube(spec.FLANGE_X, spec.FLYWHEEL_X, 0.0, C["flange_r"], SEG))
    return {"crankshaft": mesh.join(*parts),
            # between the damper and the MGU-K
            "crank_trigger": _crank_trigger(spec.FRONT["trigger_x"])}


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
    # the sensor on its bracket, looking at the teeth across an air gap. The
    # bracket bolts to the MGU-K's front face, which is 5 mm behind the
    # wheel, so the sensor is slim enough to sit in that gap.
    sv, sf = mesh.revolve_closed(
        [(0.0, 0.0), (34.0, 0.0), (34.0, 3.6), (30.0, 4.4),
         (10.0, 4.4), (8.0, 5.0), (0.0, 5.0)], SM)
    parts.append(([(pz + x, py + 0.0, -px + rw + 35.0)
                   for (px, py, pz) in sv], sf))
    parts.append(shapes.rounded_box(x, 0.0, rw + 44.0, 10.0, 34.0, 22.0,
                                    4.0, seg=5))
    return mesh.join(*parts)


def _pistons_and_rods():
    """Each piston, gudgeon pin and rod is its own object. They are separate
    components on the real engine and they move relative to each other, so
    merging them into one mesh loses information."""
    bolts = []
    out = {}
    r = spec.BORE / 2 - 0.35
    for (n, pair, bank, x, a) in spec.cylinders():
        # `_piston_along` is the gudgeon pin's distance from the crank; the
        # crown is a compression height above it. It used to be taken as the
        # crown, so every piston sat 18.5 mm down its bore, the rods came out
        # 67.6 to 68.2 mm long instead of 86, and the two at bottom dead
        # centre ran 6 mm into the counterweights.
        along = _piston_along(pair, bank) + spec.compression_height()

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
        gv = common.along_bank(gv, x, along - spec.compression_height(), bank)
        out[f"gudgeon_pin_{n}"] = (gv, gf)

        # rod: small end at the gudgeon pin, big end on the crankpin
        py, pz = _pin_centre(pair)
        small = common.bank_point(x, along - spec.compression_height(), 0.0, bank)
        big = (x, py, pz)
        out[f"conrod_{n}"] = _rod(small, big)
        out[f"rod_cap_{n}"] = _rod_cap(small, big)
        bolts.extend(_rod_bolts(small, big))
        # The shells go on the crankpin, split where the rod and cap split.
        # They were built round the crank's own axis -- a pair of half-rings
        # 22.5 mm off the pin, inside the webs, carrying no rod at all.
        theta = math.atan2(small[2] - big[2], small[1] - big[1])
        for half, sgn in (("upper", 1.0), ("lower", -1.0)):
            sv, sf = shapes.bearing_shell(x, C["pin_r"], R["shell_wall"],
                                          spec.BANK_OFFSET - 2.0,
                                          arc_seg=36, sgn=sgn)
            sv = mesh.translate(mesh.rot_x(sv, theta - math.pi / 2),
                                0.0, big[1], big[2])
            out[f"rod_shell_{n}_{half}"] = (sv, sf)
    out["rod_bolts"] = mesh.join(*bolts)
    return out


def _big_end_half(small, big, rod_side):
    """One half of the big-end eye: the rod's half faces the small end, the
    cap's the other way, and they meet on the split line across the rod.

    The rod's eye and the cap were both whole rings on the same crankpin, one
    inside the other, which is why their overlap had to be declared."""
    theta = math.atan2(small[2] - big[2], small[1] - big[1])
    phase = theta - math.pi / 2 if rod_side else theta + math.pi / 2
    v, f = mesh.revolve_closed(
        [(-9.5, C["pin_r"] + R["shell_wall"]), (9.5, C["pin_r"] + R["shell_wall"]),
         (9.5, R["big_end_r"]), (-9.5, R["big_end_r"])],
        SM // 2, phase=phase, sweep=math.pi)
    return [(px + big[0], py + big[1], pz + big[2]) for (px, py, pz) in v], f


def _rod_cap(small, big):
    """The big-end cap: the half of the eye away from the rod."""
    return _big_end_half(small, big, rod_side=False)


def _rod_bolts(small, big):
    """The two bolts that hold a cap on: along the rod's axis, either side of
    the pin, from a head under the cap up across the split into the rod.

    They were vertical in the engine's frame whatever the rod was doing, so
    on a V with the rods leaning 45 degrees they stood out of the big end
    sideways and swept through the crank webs."""
    dy, dz = small[1] - big[1], small[2] - big[2]
    ln = math.hypot(dy, dz)
    d = (0.0, dy / ln, dz / ln)                  # along the rod
    l = (0.0, -d[2], d[1])                       # across it, in its plane
    # far enough out to clear the shells' locating tangs at the split
    off = R["big_end_r"] - 0.4
    out = []
    for s in (-1.0, 1.0):
        c = tuple(big[k] + l[k] * s * off for k in range(3))
        at = lambda t: tuple(c[k] + d[k] * t for k in range(3))
        out.append(mesh.pipe([at(-16.0), at(12.0)], 3.4, 10))          # shank
        out.append(mesh.pipe([at(-20.5), at(-16.0)], 5.8, 12))         # head
    return out


def _rod(small, big):
    """I-beam rod between two eyes."""
    parts = []
    parts.append(mesh.pipe([small, big], R["beam_t"] * 0.62, 10))
    v, f = mesh.tube(-7.5, 7.5, P["pin_r"] + 1.0, R["small_end_r"], SM)
    parts.append(([(px + small[0], py + small[1], pz + small[2])
                   for (px, py, pz) in v], f))
    parts.append(_big_end_half(small, big, rod_side=True))
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
    # at the front of the stack in spec.FRONT, ahead of the trigger wheel,
    # the MGU-K and the timing case. Its inertia ring is also the crank
    # pulley: the accessory belt runs in the grooves cut round it.
    x0 = spec.FRONT["damper_x0"]
    parts = []

    def lathe(profile, seg=36):
        v, f = mesh.revolve_closed(list(profile), seg)
        return ([(px, py, pz) for (px, py, pz) in v], f)

    # hub, clamped on the nose
    parts.append(lathe([(x0 + 4.0, C["nose_r"]), (x0 + 4.0, C["nose_r"] + 3.0),
                        (x0 + 40.0, C["nose_r"] + 3.0), (x0 + 40.0, C["nose_r"])],
                       28))
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
    # the crank bolt that clamps it all to the nose: a hardened washer on
    # the nose's end face and an M16 head, 24 across flats
    from parts.plumbing import _hex_prism
    parts.append(mesh.cylinder(x0 + 1.0, x0 + 4.0, C["nose_r"] + 6.0, 28))
    parts.append(_hex_prism(x0 - 9.0, x0 + 1.0, 13.9))
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
