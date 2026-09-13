"""Cylinder heads, camshafts, valves, cam covers, injectors and coils."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common

H = spec.HEAD
V = spec.VALVE
CM = spec.CAM
SEG = spec.RES["revolve"]
SM = spec.RES["small_revolve"]


def build():
    out = {}
    out.update(_heads())
    out.update(_valves())
    out.update(_cams())
    out.update(_covers())
    out.update(_ignition())
    return out


def _heads():
    out = {}
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        v, f = shapes.rounded_box(
            0.0, 8.0, spec.DECK_HEIGHT + H["height"] / 2,
            H["x_rear"] - H["x_front"], H["half_width"] * 2, H["height"],
            r=11.0, seg=5, draft=1.2)
        v = [(x, y * ca - z * sa, y * sa + z * ca) for (x, y, z) in v]
        # the box was built about the world origin; rotate then it already sits
        # on the bank axis because its centre was placed along +z
        out[f"head_{'lr'[bank]}"] = (v, f)
    return out


def valve_seats():
    """(cylinder, index, is_intake, station, lateral, tilt) for every valve.

    One definition, used by the valves themselves, by the springs, retainers
    and buckets in detail.py, and by the cam lobes that open them -- so they
    cannot drift apart.
    """
    inc = math.radians(V["included_angle"] / 2)
    out = []
    for (n, pair, bank, x, a) in spec.cylinders():
        for k, (is_in, sgn_x, sgn_y) in enumerate((
                (True,  -1, -1), (True,  -1, 1),
                (False,  1, -1), (False,  1, 1))):
            hr = V["intake_head_r"] if is_in else V["exhaust_head_r"]
            out.append({
                "n": n, "k": k, "bank": bank, "is_in": is_in, "hr": hr,
                "x": x + sgn_y * hr * 0.95,
                "lat": 0.0,
                "tilt": inc * (1 if is_in else -1),
            })
    return out


def _valve_profile(hr):
    """A poppet valve section: seat face, margin, tulip underhead, stem, tip.

    The old profile was a cone on a stick. A real valve has a 45 degree seat
    face that matches the cut in the head, a flat margin outboard of it so the
    edge is not a knife, a tulip blending the underhead into the stem, and a
    keeper groove at the tip for the collets.
    """
    sa = math.tan(math.radians(V["seat_angle"]))
    m = V["margin"]
    tip = -V["length"]
    kg = V["keeper_groove"]
    st = V["stem_r"]
    return [
        (0.0, 0.0),
        (0.0, hr),                                  # head face, flat
        (-m, hr),                                   # margin
        (-m - hr * 0.30 * sa, hr * 0.70),           # 45 degree seat face
        (-m - hr * 0.52, hr * V["tulip"]),          # tulip
        (-m - hr * 0.92, st * 1.5),
        (-m - hr * 1.25, st),                       # stem
        (tip + 9.0, st),
        (tip + 7.0, st - kg),                       # keeper groove
        (tip + 4.5, st - kg),
        (tip + 2.5, st),
        (tip, st),
        (tip, 0.0),
    ]


def _valves():
    """Four valves per cylinder in a narrow pent-roof, each its own object.

    A joined `valves` mesh cannot be inspected, cannot be animated and cannot
    be counted. There are thirty-two of them and they are all different.
    """
    out = {}
    for s in valve_seats():
        vv, vf = mesh.revolve_open(_valve_profile(s["hr"]), SM,
                                   cap_start=True, cap_end=True)
        t = s["tilt"]
        vv = [(px * math.cos(t) - py * math.sin(t),
               px * math.sin(t) + py * math.cos(t), pz) for (px, py, pz) in vv]
        vv = common.along_bank(vv, s["x"], spec.DECK_HEIGHT - 1.0,
                               s["bank"], s["lat"])
        kind = "in" if s["is_in"] else "ex"
        tag = f"{s['n']}_{s['k'] % 2 + 1}"
        out[f"valve_{kind}_{tag}"] = (vv, vf)

        # the pair of collets that grip the keeper groove and hold the
        # retainer down. They are what actually keeps the valve in the engine.
        cv, cf = mesh.revolve_closed(
            [(-4.2, V["stem_r"] - V["keeper_groove"] * 0.8),
             (4.2, V["stem_r"] - V["keeper_groove"] * 0.8),
             (4.2, V["stem_r"] + 2.6), (-4.2, V["stem_r"] + 2.6)],
            12, sweep=math.pi * 0.86)
        t = s["tilt"]
        cv = [(px - V["length"] + 6.0, py, pz) for (px, py, pz) in cv]
        cv = [(px * math.cos(t) - py * math.sin(t),
               px * math.sin(t) + py * math.cos(t), pz) for (px, py, pz) in cv]
        cv = common.along_bank(cv, s["x"], spec.DECK_HEIGHT - 1.0,
                               s["bank"], s["lat"])
        out[f"collets_{kind}_{tag}"] = (cv, cf)
    return out


def lobe_profile(duration_crank, lift, segments=72):
    """Radius against cam angle for a flat-follower lobe.

    r(theta) = base + lift(theta), with the lift a raised cosine over the
    duration and a quiet ramp either side to take up clearance without
    hammering the bucket. Duration is quoted in crank degrees and the cam
    turns at half crank speed, so the lobe occupies half of it.
    """
    base = CM["base_r"]
    half = duration_crank / 2.0 / 2.0          # cam degrees either side of nose
    ramp = CM["ramp"]
    pts = []
    for i in range(segments):
        a = 360.0 * i / segments
        d = ((a + 180.0) % 360.0) - 180.0      # -180..180, nose at 0
        t = abs(d) / half
        if t >= 1.0:
            r = base
        elif t > 1.0 - ramp:
            # the ramp: a small linear lift-off before the flank proper
            f = (1.0 - t) / ramp
            r = base + lift * 0.04 * f
        else:
            u = t / (1.0 - ramp)
            r = base + lift * 0.04 + (lift * 0.96) * 0.5 * (1 + math.cos(math.pi * u))
        pts.append((math.radians(a), r))
    return pts


def _cam_lobe(x, lat, bank, phase_deg, duration, lift, width):
    """One lobe: a swept profile, phased to when its valve should open."""
    prof = lobe_profile(duration, lift)
    ph = math.radians(phase_deg)
    rings = []
    for dx in (-width / 2, width / 2):
        ring = []
        for (a, r) in prof:
            ring.append((dx, r * math.cos(a + ph), r * math.sin(a + ph)))
        rings.append(ring)
    n = len(prof)
    verts = rings[0] + rings[1]
    faces = []
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, i2, n + i2, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    verts = common.along_bank(verts, x, spec.DECK_HEIGHT + H["cam_height"],
                              bank, lat)
    return verts, faces


def _cams():
    """Four camshafts -- one intake and one exhaust per bank -- each a shaft
    with journals, and a phased lobe for every valve it opens."""
    out = {}
    for bank in (0, 1):
        for side, kind in ((-1, "in"), (1, "ex")):
            lat = side * H["cam_centres"] / 2
            tag = f"{'lr'[bank]}_{kind}"
            cv, cf = mesh.tube(H["x_front"], H["x_rear"], 0.0,
                               CM["journal_r"] * 0.72, SM)
            cv = [(z, y, px) for (px, y, z) in cv]
            cv = common.along_bank(cv, 0.0, spec.DECK_HEIGHT + H["cam_height"],
                                   bank, lat)
            out[f"camshaft_{tag}"] = (cv, cf)

            journals = []
            for (n, pair, b2, x, a) in spec.cylinders():
                if b2 != bank:
                    continue
                jv, jf = mesh.tube(x - CM["lobe_w"] * 2.4, x - CM["lobe_w"] * 1.7,
                                   0.0, CM["journal_r"], SM)
                jv = [(z, y, px) for (px, y, z) in jv]
                journals.append(common.along_bank(
                    jv, 0.0, spec.DECK_HEIGHT + H["cam_height"], bank, lat))
                journals[-1] = (journals[-1], jf)
            out[f"cam_journals_{tag}"] = mesh.join(*journals)

            is_in = kind == "in"
            dur = CM["duration_in"] if is_in else CM["duration_ex"]
            # phase each lobe to its own cylinder's firing position
            for (n, pair, b2, x, a) in spec.cylinders():
                if b2 != bank:
                    continue
                idx = spec.FIRING_ORDER.index(n)
                fire = idx * (720.0 / spec.N_CYL)
                centre = (fire - CM["lobe_centre_ex"] if not is_in
                          else fire + CM["lobe_centre_in"])
                for j, dx in enumerate((-CM["lobe_w"] * 1.2,
                                        CM["lobe_w"] * 1.2)):
                    out[f"camlobe_{tag}_{n}_{j + 1}"] = _cam_lobe(
                        x + dx, lat, bank, centre / 2.0, dur,
                        CM["lobe_lift"], CM["lobe_w"])
    return out


def _covers():
    """Cam covers, oil filler and the bolt flange that holds them down.

    A cam cover is not a lid. It is a casting: crowned so it clears the valve
    gear, ribbed so it does not drum at 16,000 rpm, drafted down the sides,
    and bolted round its perimeter. It was a rectangular box.
    """
    out = {}
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        z = spec.DECK_HEIGHT + H["height"] + 12.0
        rot = lambda vs: [(x, y * ca - zz * sa, y * sa + zz * ca)
                          for (x, y, zz) in vs]

        v, f = shapes.ribbed_cover(
            H["x_front"] + 7.0, H["x_rear"] - 7.0,
            H["half_width"] * 0.92, z, 34.0, n_ribs=9, rib_h=5.0, rib_w=8.0)
        v = [(x, y + 8.0, zz) for (x, y, zz) in v]
        out[f"camcover_{'lr'[bank]}"] = (rot(v), f)

        bolts = []
        n = 11
        for i in range(n):
            fx = (i + 0.5) / n
            x = H["x_front"] + (H["x_rear"] - H["x_front"]) * fx
            for sgn in (-1.0, 1.0):
                bv, bf = shapes.bolt_boss(0, 0, 0, 7.0, 9.0)
                bv = [(pz + x, py + 8.0 + sgn * H["half_width"] * 0.88,
                       px + z - 4.0) for (px, py, pz) in bv]
                bolts.append((bv, bf))
        out[f"camcover_bolts_{'lr'[bank]}"] = (rot(mesh.join(*bolts)[0]),
                                               mesh.join(*bolts)[1])

        fv, ff = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 21.0), (9.0, 23.0), (17.0, 20.0), (17.0, 0.0)],
            16, cap_start=True, cap_end=True)
        fv = [(pz + H["x_front"] + 46.0, py + 8.0, px + z + 26.0)
              for (px, py, pz) in fv]
        out[f"oil_filler_{'lr'[bank]}"] = (rot(fv), ff)
    return out


def _ignition():
    """One direct injector and one coil-on-plug per cylinder, each its own
    object -- they are serviced individually, so they are modelled that way.

    The injector is a stepped body with a nozzle tip; the coil is a body, a
    boot down to the plug and the plug itself, because the plug is the part
    that actually wears out.
    """
    out = {}
    for (n, pair, bank, x, a) in spec.cylinders():
        iv, if_ = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 3.0), (6.0, 4.2), (14.0, 4.2),
             (18.0, 7.0), (48.0, 7.0), (52.0, 9.5), (62.0, 9.5), (62.0, 0.0)],
            14, cap_start=True, cap_end=True)
        iv = [(z, y, px) for (px, y, z) in iv]
        out[f"injector_{n}"] = (common.along_bank(
            iv, x, spec.DECK_HEIGHT + 6.0, bank, spec.BORE * 0.40), if_)

        cv, cf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 5.5), (10.0, 6.5), (26.0, 7.5),
             (30.0, 11.0), (74.0, 11.0), (74.0, 0.0)],
            14, cap_start=True, cap_end=True)
        cv = [(z, y, px) for (px, y, z) in cv]
        out[f"coil_{n}"] = (common.along_bank(
            cv, x, spec.DECK_HEIGHT + 10.0, bank, 0.0), cf)

        pv, pf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 2.4), (5.0, 3.1), (9.0, 7.8), (16.0, 7.8),
             (18.0, 6.2), (26.0, 6.2), (26.0, 0.0)],
            10, cap_start=True, cap_end=True)
        pv = [(z, y, px) for (px, y, z) in pv]
        out[f"sparkplug_{n}"] = (common.along_bank(
            pv, x, spec.DECK_HEIGHT - 14.0, bank, 0.0), pf)
    return out
