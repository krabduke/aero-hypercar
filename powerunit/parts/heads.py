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
    out.update(_gaskets())
    return out


def _gaskets():
    """Multi-layer head gaskets, between each bank deck and its head.

    The head was bolted straight onto the block deck with nothing in the
    joint. An MLS gasket is mostly bore rings -- the folded steel beads that
    actually do the sealing -- carried on a thin frame, so that is what it is
    here rather than a plain shim.
    """
    out = {}
    t = 1.6
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        dx = spec.cylinder_x(0, bank) - spec.cylinder_x(0)
        parts = []
        # the fire ring round each bore, folded proud of the sheet
        for i in range(spec.N_CYL // 2):
            cx = spec.cylinder_x(i) + dx
            r0 = spec.BORE / 2
            v, f = mesh.revolve_closed(
                [(0.0, r0), (t, r0), (t, r0 + 5.0), (t * 1.9, r0 + 6.5),
                 (0.0, r0 + 6.5), (0.0, r0 + 5.0)], 44)
            v = [(py + cx, pz, px + spec.DECK_HEIGHT) for (px, py, pz) in v]
            parts.append((v, f))
            # coolant and oil transfer holes either side of each bore
            for sy in (-1.0, 1.0):
                hv, hf = mesh.revolve_closed(
                    [(0.0, 5.0), (t, 5.0), (t, 8.5), (0.0, 8.5)], 12)
                hv = [(py + cx, pz + sy * (r0 + 20.0), px + spec.DECK_HEIGHT)
                      for (px, py, pz) in hv]
                parts.append((hv, hf))
        # the sheet the rings are carried on, as a perimeter rail
        hw = H["half_width"] - 4.0
        x0 = spec.cylinder_x(0) + dx - spec.BORE / 2 - 26.0
        x1 = spec.cylinder_x(3) + dx + spec.BORE / 2 + 26.0
        for sy in (-1.0, 1.0):
            rv, rf = shapes.rounded_box(
                (x0 + x1) / 2, sy * (hw - 7.0), spec.DECK_HEIGHT + t / 2,
                x1 - x0, 14.0, t, r=0.6, seg=3)
            parts.append((rv, rf))
        for ex in (x0 + 7.0, x1 - 7.0):
            rv, rf = shapes.rounded_box(
                ex, 0.0, spec.DECK_HEIGHT + t / 2,
                14.0, 2 * hw, t, r=0.6, seg=3)
            parts.append((rv, rf))
        v, f = mesh.join(*parts)
        d, lat = common.bank_dir(bank), common.bank_lat(bank)
        v = [(x, y * lat[1] + z * d[1], y * lat[2] + z * d[2])
             for (x, y, z) in v]
        out[f"head_gasket_{'lr'[bank]}"] = (v, f)
    return out


def _head_features(bank):
    """What is actually cut into and cast onto a cylinder head.

    The head was a 120-vertex rounded box. It is the most complex casting on
    the engine: a pent-roof chamber over every bore, a valve seat around every
    valve, a plug well down the middle of each chamber, port bosses out both
    faces, cam tunnel bosses along the top and a bolt boss at every stud.
    """
    parts = []
    V_ = spec.VALVE
    for (n, pair, b2, x, a) in spec.cylinders():
        if b2 != bank:
            continue
        # plug well
        wv, wf = mesh.revolve_ring(
            [(0.0, 9.0), (0.0, 15.0), (30.0, 15.0), (30.0, 9.0)], SM)
        parts.append((common.along_bank(wv, x, spec.DECK_HEIGHT + 10.0, bank), wf))

        # port bosses, one each side, around the valve pairs
        for is_in, lat_sgn in ((True, -1.0), (False, 1.0)):
            hr = V_["intake_head_r"] if is_in else V_["exhaust_head_r"]
            pv, pf = mesh.revolve_ring(
                [(0.0, hr * 1.10), (0.0, hr * 1.45), (16.0, hr * 1.40),
                 (16.0, hr * 1.05)], SM)
            d = common.bank_dir(bank)
            lat = common.bank_lat(bank)
            # from the declared ports, so the boss is round the hole
            import gaspath
            _p = (gaspath.intake_port(bank, 0.0) if is_in
                  else gaspath.exhaust_port(bank, 0.0))
            off = lat_sgn * (50.0 if is_in else 58.0)
            base = spec.DECK_HEIGHT + spec.HEAD["height"] * (
                0.40 if is_in else 0.38)
            parts.append(([(px + x,
                            py * lat[1] + (pz + base) * d[1] + off * lat[1],
                            py * lat[2] + (pz + base) * d[2] + off * lat[2])
                           for (px, py, pz) in pv], pf))

        # cam tunnel bosses
        for side in (-1, 1):
            tv, tf = mesh.revolve_closed(
                [(-11.0, 0.0), (-11.0, 21.0), (11.0, 21.0), (11.0, 0.0)], SM)
            tv = [(z, y, px) for (px, y, z) in tv]
            parts.append((common.along_bank(
                tv, x - spec.CAM["lobe_w"] * 2.05,
                spec.DECK_HEIGHT + H["cam_height"], bank,
                side * H["cam_centres"] / 2), tf))
    return mesh.join(*parts)


def _heads():
    out = {}
    for bank in (0, 1):
        a = spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        # each head bolts to its own bank, and the banks are staggered along
        # the crank -- so the castings are too
        v, f = shapes.rounded_box(
            spec.cylinder_x(0, bank) - spec.cylinder_x(0), 8.0,
            spec.DECK_HEIGHT + H["height"] / 2,
            H["x_rear"] - H["x_front"], H["half_width"] * 2, H["height"],
            r=11.0, seg=5, draft=1.2)
        # Onto the bank frame, the same one _head_features and every other
        # per-bank part uses. This was a raw rotation by bank_angle_rad, which
        # for bank 0 put the casting at y +57..+186 while its own features sat
        # at y -174..-59 -- the opposite bank. Each head was therefore half on
        # one side of the engine and half on the other, and the two of them
        # shared 68 per cent of one head's volume.
        d, lat = common.bank_dir(bank), common.bank_lat(bank)
        v = [(x, y * lat[1] + z * d[1], y * lat[2] + z * d[2])
             for (x, y, z) in v]
        out[f"head_{'lr'[bank]}"] = mesh.join((v, f), _head_features(bank))
        out[f"cut:head_{'lr'[bank]}"] = mesh.join(*[
            _chamber(x, bank) for (n, pair, b2, x, a) in spec.cylinders()
            if b2 == bank])
    return out


def _chamber(x, bank, segments=48):
    """The combustion chamber over one bore, as a cutter: the bore's circle,
    capped by a pent roof -- two planes leaning at half the valves' included
    angle, meeting on a ridge along the crank direction -- and running 1 mm
    below the deck so the cut is clean."""
    r = spec.BORE / 2
    ridge = H["chamber_ridge"]
    slope = math.tan(math.radians(spec.VALVE["included_angle"] / 2))
    ring_lo, ring_hi = [], []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        lat, ax = r * math.cos(a), r * math.sin(a)
        ring_lo.append((-1.0, lat, ax))
        ring_hi.append((ridge - abs(lat) * slope, lat, ax))
    n = segments
    verts = ring_lo + ring_hi + [(-1.0, 0.0, 0.0), (ridge, 0.0, 0.0)]
    c_lo, c_hi = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((n + i, n + j, j, i))
        faces.append((c_lo, i, j))
        faces.append((c_hi, n + j, n + i))
    # local: px along the bore, py across it, pz along the crank
    return common.along_bank([(px, py, pz) for (px, py, pz) in verts],
                             x, spec.DECK_HEIGHT, bank), faces


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
                "x": x + sgn_y * hr * 1.02,
                # Across the bore: intakes one side of the bore axis,
                # exhausts the other. `sgn_x` was computed here and then
                # thrown away in favour of a hard 0.0, which stacked all four
                # valves of every cylinder on the bore centreline -- so the
                # two intakes were the same valve twice, the two exhausts
                # likewise, and the four tappets sat inside one another.
                # 1.04 so the intake pair clears the exhaust pair: at 0.95
                # the two circles were 0.6 mm inside one another
                "lat": sgn_x * hr * 1.04,
                # Splayed OUTWARD: a pent-roof valve leans further from the
                # bore axis as it rises, which is what opens the chamber up
                # and lets the ports run straight. The sign here was opposite
                # to the sign of `lat`, so every valve crossed the bore axis
                # on the way up and its tip came out over the other bank's
                # cam.
                "tilt": sgn_x * inc,
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
    out = [
        (0.0, 0.0),
        (0.0, hr * 0.88),
        (-0.35, hr * 0.97),                         # dished face, radiused
        (-0.9, hr),                                 # head face
        (-m, hr),                                   # margin
        (-m - hr * 0.30 * sa, hr * 0.70),           # 45 degree seat face
        (-m - hr * 0.33 * sa, hr * 0.63),           # back-cut below the seat
    ]
    # the tulip: a real underhead is a curve from the seat into the stem, not
    # a chamfer. Twelve points along a blend makes it one.
    x0, r0 = out[-1]
    x1, r1 = -m - hr * 1.30, st
    for i in range(1, 13):
        t = i / 13.0
        e = t * t * (3 - 2 * t)                     # smoothstep
        out.append((x0 + (x1 - x0) * t,
                    r0 + (r1 - r0) * e))
    out += [
        (x1, st),                                   # stem
        (tip + 11.0, st),
        (tip + 9.6, st - kg * 0.35),
        (tip + 8.6, st - kg),                       # keeper groove, radiused
        (tip + 5.6, st - kg),
        (tip + 4.6, st - kg * 0.35),
        (tip + 3.2, st),
        (tip + 0.8, st),
        (tip, st - 0.7),                            # chamfered tip
        (tip, 0.0),
    ]
    # `along_bank` sends +x outward, away from the crank. The profile above is
    # drawn from the combustion face at 0 to the stem tip at -length, so as
    # written every valve in the engine pointed DOWN the bore: an 86 mm stem
    # through the deck, through the block and into the crankshaft, with its
    # collets 47 mm from the crank centreline and its retainer and spring
    # left 160 mm away at the top of the head where they belong. Mirroring
    # it puts the face on the chamber and the tip under the tappet.
    # The list is reversed as well as negated so the winding is unchanged.
    return [(-px, r) for (px, r) in reversed(out)]


def _valves():
    """Four valves per cylinder in a narrow pent-roof, each its own object.

    A joined `valves` mesh cannot be inspected, cannot be animated and cannot
    be counted. There are thirty-two of them and they are all different.
    """
    out = {}
    for s in valve_seats():
        vv, vf = mesh.revolve_open(_valve_profile(s["hr"]), SEG,
                                   cap_start=True, cap_end=True)
        t = s["tilt"]
        vv = [(px * math.cos(t) - py * math.sin(t),
               px * math.sin(t) + py * math.cos(t), pz) for (px, py, pz) in vv]
        vv = common.along_bank(vv, s["x"], spec.DECK_HEIGHT + V["face_along"],
                               s["bank"], s["lat"] + V["face_along"] * math.tan(t))
        kind = "in" if s["is_in"] else "ex"
        tag = f"{s['n']}_{s['k'] % 2 + 1}"
        out[f"valve_{kind}_{tag}"] = (vv, vf)

        # the pair of collets that grip the keeper groove and hold the
        # retainer down. They are what actually keeps the valve in the engine.
        # A collet is a tapered wedge: the outside matches the retainer's
        # cone, the inside has the bead that sits in the valve's groove.
        gr = V["stem_r"] - V["keeper_groove"] * 0.8
        cv, cf = mesh.revolve_closed(
            [(-4.6, gr), (-4.6, V["stem_r"] + 3.4), (-1.4, V["stem_r"] + 2.6),
             (1.8, V["stem_r"] + 1.4), (4.6, V["stem_r"] + 0.6), (4.6, gr),
             (1.4, gr), (0.0, V["stem_r"] - 0.2), (-1.4, gr)],
            SEG // 2, sweep=math.pi * 0.86)
        t = s["tilt"]
        cv = [(-px + V["length"] - 6.0, py, pz) for (px, py, pz) in cv]
        cv = [(px * math.cos(t) - py * math.sin(t),
               px * math.sin(t) + py * math.cos(t), pz) for (px, py, pz) in cv]
        cv = common.along_bank(cv, s["x"], spec.DECK_HEIGHT + V["face_along"],
                               s["bank"], s["lat"] + V["face_along"] * math.tan(t))
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
    """One lobe: a swept profile, phased to when its valve should open.

    A lobe has width, and both faces are chamfered -- a sharp edge on a cam
    would scuff the bucket the first time it ran. Two rings made a prism with
    knife edges; five make the part.
    """
    prof = lobe_profile(duration, lift, segments=110)
    ph = math.radians(phase_deg)
    ch = width * 0.13
    rings = []
    for (dx, shrink) in ((-width / 2, ch), (-width / 2 + ch, 0.0),
                         (width / 2 - ch, 0.0), (width / 2, ch)):
        ring = []
        for (a, r) in prof:
            rr = max(r - shrink, 1.0)
            ring.append((dx, rr * math.cos(a + ph), rr * math.sin(a + ph)))
        rings.append(ring)
    n = len(prof)
    verts = [v for r in rings for v in r]
    faces = []
    for k in range(len(rings) - 1):
        a, b = k * n, (k + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((a + i, a + i2, b + i2, b + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (len(rings) - 1) * n
    faces.append(tuple(range(base, base + n)))
    # The lobe is lathed about its own +x, which is its WIDTH. `along_bank`
    # reads the axial run out of z, exactly as the shaft and the journals
    # already do -- without the swap every lobe on the engine was turned
    # ninety degrees, lying across the cam with its profile in the plan view
    # and its 11 mm width pointing down the bore at the bucket.
    verts = [(z, y, px) for (px, y, z) in verts]
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
            # A camshaft is stepped: a drive nose at the front, a thrust
            # flange, the running diameter, and a tapered tail. It was a tube.
            jr = CM["journal_r"]
            xf, xr = H["x_front"], H["x_rear"]
            # Counter-clockwise in (x, r), the same winding `mesh.tube` uses,
            # so the normals face out: along the axis first, up at the tail,
            # then back along the outside through every step and undercut.
            cv, cf = mesh.revolve_closed(
                [(xf - 26.0, 0.0), (xr, 0.0),
                 (xr, jr * 0.46), (xr - 3.0, jr * 0.58),
                 (xr - 9.0, jr * 0.62),           # tapered tail
                 (xr - 15.0, jr * 0.74), (xr - 17.0, jr * 0.74),
                 (xr - 19.0, jr * 0.70),          # rear journal shoulder
                 (xf + 10.0, jr * 0.70),          # running diameter
                 (xf + 8.0, jr * 0.74),
                 (xf + 4.0, jr * 0.74),
                 (xf + 3.0, jr * 0.96),
                 (xf - 1.0, jr * 0.96),           # thrust flange
                 (xf - 2.0, jr * 0.74),
                 (xf - 5.0, jr * 0.74),
                 (xf - 6.0, jr * 0.56),
                 (xf - 13.0, jr * 0.56),          # drive nose
                 (xf - 14.0, jr * 0.50),
                 (xf - 22.0, jr * 0.50),
                 (xf - 23.0, jr * 0.34),
                 (xf - 25.0, jr * 0.34),
                 (xf - 26.0, jr * 0.26)], SM)
            # the lathe runs along its own +x; along_bank reads the axial run
            # out of z, so swap before placing it on the bank
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
        # Negated. `rot` below turns (y, z) by +a, and a point on the deck
        # axis then lands at y = -z*sin(a) -- which for bank 0, whose angle
        # is negative, is +y. Bank 0 is the LEFT bank: `common.bank_dir(0)`
        # is (0, -0.707, +0.707) and every other part in this module sits on
        # -y. So every cam cover, every one of its bolts and both oil fillers
        # were built over the other bank's camshafts. Nothing caught it,
        # because a cover was still covering *a* head and the clearance
        # checks that pair `plenum_l` with `camcover_l` were comparing
        # opposite sides of the engine and passing on the 400 mm between them.
        a = -spec.bank_angle_rad(bank)
        ca, sa = math.cos(a), math.sin(a)
        z = spec.DECK_HEIGHT + H["height"] + 1.0
        rot = lambda vs: [(x, y * ca - zz * sa, y * sa + zz * ca)
                          for (x, y, zz) in vs]

        v, f = shapes.ribbed_cover(
            H["x_front"] + 7.0, H["x_rear"] - 7.0,
            H["half_width"] * 0.86, z, 34.0, n_ribs=9, rib_h=5.0, rib_w=8.0)
        # centred on the head, not 8 mm outboard of it: offset, the cover's
        # outer corner stood 3 mm proud of the casting it bolts to
        v = [(x, y + 2.0, zz) for (x, y, zz) in v]
        out[f"camcover_{'lr'[bank]}"] = (rot(v), f)
        # It is a casting, 4 mm thick and open underneath. It was solid, and
        # a third of it hung below its own flange inside the head, so the
        # camshafts, their lobes and their caps were all inside a block of
        # aluminium.
        cv, cf = shapes.cover_cavity(
            H["x_front"] + 7.0, H["x_rear"] - 7.0,
            H["half_width"] * 0.86, z, 34.0, 4.0)
        # and nothing of it below the flange, end walls included
        x0c, x1c = H["x_front"] + 7.0, H["x_rear"] - 7.0
        below = mesh.box((x0c + x1c) / 2, 0.0, z - 40.0, x1c - x0c + 6.0,
                         H["half_width"] * 2.2, 80.0)
        cv, cf = mesh.join((cv, cf), below)
        cv = [(x, y + 2.0, zz) for (x, y, zz) in cv]
        out[f"cut:camcover_{'lr'[bank]}"] = (rot(cv), cf)

        # A cam cover's bolts go round the injector bosses, not through
        # them. At eleven evenly spaced stations two of them landed within
        # 10 mm of a cylinder centre, and a port injector is 9 mm across the
        # body on a 7 mm boss -- so cylinders 4 and 8 had their injectors
        # inside a cover bolt.
        bores = [cx for (_n, _p, b, cx, _a) in spec.cylinders() if b == bank]
        bolts = []
        n = 11
        for i in range(n):
            fx = (i + 0.5) / n
            x = H["x_front"] + (H["x_rear"] - H["x_front"]) * fx
            if min(abs(x - cx) for cx in bores) < 18.0:
                continue
            for sgn in (-1.0, 1.0):
                bv, bf = shapes.bolt_boss(0, 0, 0, 7.0, 9.0)
                # on the cover's own centre line, +2 like the cover: the
                # cover was moved in from +8 and its bolts were not, so one
                # row stood 6 mm off its edge and the other 6 mm inside it
                bv = [(pz + x, py + 2.0 + sgn * H["half_width"] * 0.88,
                       px + z - 4.0) for (px, py, pz) in bv]
                bolts.append((bv, bf))
        out[f"camcover_bolts_{'lr'[bank]}"] = (rot(mesh.join(*bolts)[0]),
                                               mesh.join(*bolts)[1])

        fv, ff = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 21.0), (9.0, 23.0), (17.0, 20.0), (17.0, 0.0)],
            SM, cap_start=True, cap_end=True)
        fv = [(pz + H["x_front"] + 46.0, py + 8.0, px + z + 26.0)
              for (px, py, pz) in fv]
        out[f"oil_filler_{'lr'[bank]}"] = (rot(fv), ff)
    return out


def _ignition():
    """One direct injector and one coil-on-plug per cylinder, each its own
    object -- they are serviced individually, so they are modelled that way.

    `injector_di_*`, not `injector_*`. This engine has two injection systems:
    these, screwed into the chamber at 350 bar, and the port injectors
    induction.py stands in the runners at 6 bar. Both were called `injector_n`
    and assembly put two objects of the same name in the scene -- one of them
    renamed out from under every audit that looked for it, and the high
    pressure feeds in plumbing.py aiming at whichever rail happened to survive
    the merge. Naming the system is what makes the two fuel circuits separable.

    The injector is a stepped body with a nozzle tip; the coil is a body, a
    boot down to the plug and the plug itself, because the plug is the part
    that actually wears out.
    """
    out = {}
    for (n, pair, bank, x, a) in spec.cylinders():
        iv, if_ = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 3.0), (6.0, 4.2), (14.0, 4.2),
             (18.0, 7.0), (48.0, 7.0), (52.0, 9.5), (62.0, 9.5), (62.0, 0.0)],
            SM, cap_start=True, cap_end=True)
        iv = [(z, y, px) for (px, y, z) in iv]
        out[f"injector_di_{n}"] = (common.along_bank(
            iv, x, spec.DECK_HEIGHT + 20.0, bank, -40.0), if_)

        cv, cf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 5.5), (10.0, 6.5), (26.0, 7.5),
             (30.0, 11.0), (74.0, 11.0), (74.0, 0.0)],
            SM, cap_start=True, cap_end=True)
        # A coil-on-plug stands UP the bore, in the well between the two
        # camshafts, with its boot on the plug. The `(z, y, px)` swap the
        # camshaft needs sends the axis along the crank instead, which laid
        # all eight coils on their sides across the engine and buried them
        # in the block.
        out[f"coil_{n}"] = (common.along_bank(
            cv, x, spec.DECK_HEIGHT + 64.0, bank, 0.0), cf)

        # 14 mm across the flats, which is what fits between four valves
        pv, pf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 2.4), (5.0, 3.1), (9.0, 6.4), (16.0, 6.4),
             (18.0, 5.2), (26.0, 5.2), (26.0, 0.0)],
            SM, cap_start=True, cap_end=True)
        # and the plug screws in on the same axis, tip in the chamber
        out[f"sparkplug_{n}"] = (common.along_bank(
            pv, x, spec.DECK_HEIGHT + 34.0, bank, 0.0), pf)
    return out
