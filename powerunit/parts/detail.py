"""The hardware that makes an engine an engine rather than a shape.

Valve springs and their retainers, the timing gear train, oil and water pumps
with their pickups and housings, turbo rotating assemblies, fasteners, sensors,
heat shields and the dry-sump plumbing.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
import gaspath
from parts import common

H = spec.HEAD
V = spec.VALVE
CM = spec.CAM
T = spec.TURBO
A = spec.ANCILLARY
SM = spec.RES["small_revolve"]
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_valve_gear())
    out.update(_timing())
    out.update(_pumps())
    out.update(_turbo_internals())
    out.update(_fasteners())
    out.update(_sensors())
    out.update(_heat_shields())
    out.update(_dry_sump())
    return out


# --------------------------------------------------------------------------

def _coil_spring(r, length, turns, wire_r, segs=26, sect=10, hand=1.0):
    """A helical spring with closed and ground ends.

    The end coils of a real spring are wound at almost no pitch so the spring
    has a flat face to seat on -- wind it at constant pitch and it stands on a
    single point of wire and cocks over the first time you compress it. The
    dead coils carry an eighth of the pitch here, which is enough to keep the
    sweep from doubling back on itself.
    """
    n = int(turns * segs)
    dead = 0.9
    w = []
    for i in range(n + 1):
        tt = turns * i / n
        w.append(0.12 if (tt < dead or tt > turns - dead) else 1.0)
    tot = sum(w[1:]) or 1.0
    pts, acc = [], 0.0
    for i in range(n + 1):
        if i:
            acc += w[i]
        a = 2 * math.pi * turns * (i / n) * hand
        pts.append((length * acc / tot, r * math.cos(a), r * math.sin(a)))
    return mesh.pipe(pts, wire_r, sect, caps=True)


def _valve_gear():
    """Two springs, a retainer and a bucket tappet per valve.

    All three sit ON the valve's own axis, which in a pent-roof head is not
    the bore axis: it starts one valve radius to one side of it and leans
    further out all the way up. They used to be placed on the bore centreline
    with no lean, lying on their sides (a bucket is a cup that runs up and
    down the bore, not a roller lying across it), at heights that put the
    bucket above the camshaft that is supposed to push it.

    The stack, from the deck up, is: spring seat, spring, retainer under the
    collets at the valve tip, shim, bucket crown, lobe base circle. Each
    height below is that chain, not a guess.
    """
    from parts.heads import valve_seats
    H_SPRING, H_RETAINER, H_BUCKET = 16.0, 79.5, 82.8
    springs, retainers, buckets = [], [], []
    for seat in valve_seats():
        n, k = seat["n"], seat["k"]
        bank, tilt, xo = seat["bank"], seat["tilt"], seat["x"]

        def on_axis(v, height, flip=False):
            """Put a part built about its own +x onto this valve's axis."""
            if flip:
                v = [(-px, py, pz) for (px, py, pz) in v]
            v = [(px * math.cos(tilt) - py * math.sin(tilt),
                  px * math.sin(tilt) + py * math.cos(tilt), pz)
                 for (px, py, pz) in v]
            return common.along_bank(
                v, xo, spec.DECK_HEIGHT + height, bank,
                seat["lat"] + height * math.tan(tilt))

        # A dual spring, wound opposite hands. At 16,000 rpm a single
        # spring surges: the inner one damps it, and winding it the other
        # way means a broken coil cannot nest into the outer.
        sv, sf = mesh.join(
            _coil_spring(9.6, 60.0, 9.0, 1.75),
            _coil_spring(6.1, 58.0, 11.0, 1.25, hand=-1.0))
        springs.append((f"{n}_{k}", (on_axis(sv, H_SPRING), sf)))

        # A retainer is a cone, not a washer: it seats both springs on its
        # underside and tapers to the collet bore on top, which is what
        # locks the two together under load. The step between the two
        # seats is the only thing keeping the inner spring concentric.
        rv, rf = mesh.revolve_closed(
            [(-3.6, 3.15), (-3.6, 5.0), (-2.9, 5.0), (-2.9, 7.6),
             (-3.6, 7.6), (-3.6, 11.0), (-3.4, 12.6), (-2.2, 13.2),
             (-0.6, 13.2), (0.4, 11.8), (1.9, 9.3), (3.0, 7.0),
             (3.6, 5.4), (3.6, 3.85), (2.2, 3.5), (0.0, 3.3)], SEG)
        retainers.append((f"{n}_{k}",
                          (on_axis(rv, H_RETAINER, flip=True), rf)))

        # A bucket tappet is a closed cup running directly under the lobe:
        # a DLC crown with a chamfer round it, a skirt with an oil groove
        # so it does not pick up in the bore, and the shim that sets the
        # clearance sitting in a pocket underneath the crown.
        bv, bf = mesh.revolve_closed(
            [(-9.2, 0.0), (-9.2, 9.8), (-8.6, 10.4), (-8.6, 13.0),
             (-9.0, 13.0), (-9.0, 13.6), (-8.4, 14.0),
             (2.4, 14.0), (2.4, 13.2), (3.6, 13.2),
             (3.6, 14.0), (7.4, 14.0), (8.6, 13.6),
             (9.2, 12.6), (9.2, 11.2), (8.0, 10.9),
             (7.0, 10.4), (7.0, 0.0)], SEG)
        sh, shf = mesh.revolve_closed(
            [(-9.2, 0.0), (-9.2, 8.9), (-6.9, 8.9), (-6.9, 0.0)], SEG)
        bv, bf = mesh.join((bv, bf), (sh, shf))
        buckets.append((f"{n}_{k}", (on_axis(bv, H_BUCKET, flip=True), bf)))

    out = {}
    # one object per valve: a spring is a service item, not a texture
    for (tag, m) in springs:
        out[f"valve_spring_{tag}"] = m
    for (tag, m) in retainers:
        out[f"retainer_{tag}"] = m
    for (tag, m) in buckets:
        out[f"tappet_{tag}"] = m
    return out


def _timing():
    """Gear train off the crank nose driving all four camshafts. A gear train
    rather than a belt or chain: at 16,000 rpm valve timing has to be exact."""
    parts = []
    x = spec.BLOCK["x_front"] - 30.0
    # crank gear
    parts.append(_gear(x, 0.0, 0.0, 54.0, 28))
    # idlers up each side of the vee
    for bank in (0, 1):
        for k, (along, r) in enumerate(((70.0, 40.0), (140.0, 40.0))):
            p = common.bank_point(x, along, 0.0, bank)
            parts.append(_gear(x, p[1], p[2], r, 20))
        # cam gears
        for lat in (-H["cam_centres"] / 2, H["cam_centres"] / 2):
            p = common.bank_point(x, spec.DECK_HEIGHT + H["cam_height"],
                                  lat, bank)
            parts.append(_gear(x, p[1], p[2], 46.0, 24))
    # covers the gear train without swallowing the whole front of the engine
    cover = mesh.tube(x - 22.0, x - 4.0, 0.0, 152.0, 40)
    return {"timing_gears": mesh.join(*parts), "timing_cover": cover}


def _gear(x, y, z, r, teeth):
    parts = [mesh.tube(x - 7.0, x + 7.0, r * 0.28, r * 0.88, 26)]
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        tv, tf = shapes.rounded_box(x, r * 0.94, 0.0, 13.0, r * 0.16, 5.2, 0.7)
        tv = mesh.rot_x(tv, a)
        parts.append(([(px, py + y, pz + z) for (px, py, pz) in tv], tf))
    v, f = mesh.join(*parts)
    v = [(px, py + (0.0 if abs(y) < 1e-9 else 0.0), pz) for (px, py, pz) in v]
    # the hub was built about the axis; shift it to the gear centre
    hub_v, hub_f = mesh.tube(x - 7.0, x + 7.0, r * 0.28, r * 0.88, 26)
    hub_v = [(px, py + y, pz + z) for (px, py, pz) in hub_v]
    return mesh.join((hub_v, hub_f), (v, f))


def _pumps():
    """Oil and water pumps with their pickups and housings."""
    out = {}
    parts = []
    xo = spec.BLOCK["x_front"] - 16.0
    # oil pump body, pickup and pressure line
    parts.append(mesh.pipe([(xo, -86.0, -46.0), (xo + 60.0, -96.0, -110.0),
                            (xo + 190.0, -60.0, -132.0)], 13.0, SM))
    pv, pf = shapes.rounded_box(xo + 200.0, -50.0, -140.0, 120.0, 70.0, 26.0,
                                   9.0, draft=2.0)
    parts.append((pv, pf))
    out["oil_pickup"] = mesh.join(*parts)

    wp = []
    wp.append(mesh.pipe([(xo, 86.0, -34.0), (xo - 40.0, 120.0, 30.0),
                         (xo - 30.0, 130.0, 120.0)], 17.0, SM))
    tv, tf = mesh.tube(xo - 50.0, xo - 10.0, 0.0, 44.0, 22)
    tv = [(px, py + 130.0, pz + 150.0) for (px, py, pz) in tv]
    wp.append((tv, tf))
    out["coolant_plumbing"] = mesh.join(*wp)
    return out


def _turbo_internals():
    """The two wheels on each shaft.

    The blades were flat rounded boxes, twenty-two millimetres square, stood
    up round a hub: a paddle wheel. A turbine blade and a compressor blade are
    both twisted -- the metal has to meet the gas at the angle the gas is
    arriving at, and that angle changes all the way from the hub to the tip
    because the tip is going three times as fast. The twist is the part you
    can see, and it is the part that was missing.

    The compressor also gets splitter blades: half-length blades between the
    full ones, which is how a modern wheel keeps the inducer throat open at
    the eye and still fills the exducer. Count the blades on any turbo made
    since about 1990 and they alternate.
    """
    out = {}
    for pair, tag in ((0, "1"), (2, "2")):
        _, tx, _sgn, ib = gaspath.turbo_side(pair)
        hw = T["housing_w"] * 0.6

        shaft = mesh.tube(tx - hw - 8.0, tx + hw + 8.0,
                          0.0, T["shaft_r"], 20)
        out[f"turbo_shaft_{tag}"] = (
            [(px, py, pz + T["z"]) for (px, py, pz) in shaft[0]], shaft[1])

        # turbine: inflow at the tip, out along the axis, so the hub grows
        # towards the exducer and the blades sweep back against the rotation
        xc = tx - ib * hw
        out[f"turbine_wheel_{tag}"] = _wheel(
            xc, -ib, T["turb_r"] * 0.62, 11, 0,
            hub=[(0.00, 0.30), (0.25, 0.42), (0.55, 0.52), (0.80, 0.56),
                 (1.00, 0.54)],
            twist=(58.0, 18.0), chord=(0.62, 0.54))

        # compressor: in along the axis at the eye, out at the tip, so the
        # inducer is steeply raked and the exducer nearly radial
        xc = tx + ib * hw
        out[f"compressor_wheel_{tag}"] = _wheel(
            xc, ib, T["comp_r"] * 0.66, 7, 7,
            hub=[(0.00, 0.22), (0.25, 0.30), (0.55, 0.42), (0.80, 0.52),
                 (1.00, 0.58)],
            twist=(-62.0, -8.0), chord=(0.58, 0.46))
    return out


def _wheel(xc, dirn, r_tip, n_full, n_split, hub, twist, chord):
    """A bladed wheel: hub of revolution, blades lofted from hub to tip.

    `hub` is [(axial fraction, radius as a fraction of the tip)], `twist` the
    blade angle at the hub and at the tip in degrees, and `chord` the blade
    length at each as a fraction of the wheel's axial depth. A splitter blade
    starts half way down and is half as long.
    """
    depth = r_tip * 0.96
    prof = [(xc + dirn * f * depth, rr * r_tip) for (f, rr) in hub]
    hv, hf = mesh.revolve_open(
        [(prof[0][0], 0.001)] + prof + [(prof[-1][0], 0.001)],
        SM, cap_start=True, cap_end=True)
    parts = [([(px, py, pz + T["z"]) for (px, py, pz) in hv], hf)]

    n_span, n_chord = 7, 9
    for k in range(n_full + n_split):
        split = k >= n_full
        idx = (k - n_full) if split else k
        a0 = 2 * math.pi * idx / max(n_full, 1)
        if split:
            a0 += math.pi / max(n_full, 1)
        rings = []
        for i in range(n_span):
            fs = i / (n_span - 1)
            r = r_tip * (0.34 + 0.66 * fs)
            start = (0.50 if split else 0.0) * depth
            c = (chord[0] + (chord[1] - chord[0]) * fs) * depth
            if split:
                c *= 0.5
            ang = math.radians(twist[0] + (twist[1] - twist[0]) * fs)
            t = r_tip * 0.05 * (1.0 - 0.45 * fs)
            rings.append(_blade_ring(xc, dirn, start, c, ang, t, r, a0,
                                     n_chord))
        parts.append(_loft_blade(rings))
    return mesh.join(*parts)


def _blade_ring(xc, dirn, start, chord, ang, t, r, a0, n_chord):
    """One closed aerofoil section, wrapped onto the wheel at radius r.

    Built flat in (along the chord, across it), pitched by the local twist,
    then bent round the hub -- so a section at the tip subtends less angle
    than the same chord at the hub, which is what makes a blade look twisted
    rather than sheared.
    """
    upper, lower = [], []
    for j in range(n_chord):
        u = j / (n_chord - 1)
        cam = 0.16 * math.sin(math.pi * u)
        half = t * math.sin(math.pi * min(max(u, 0.03), 0.97)) / chord
        upper.append((u, cam + half))
        lower.append((u, cam - half))
    loop = upper + list(reversed(lower))
    ring = []
    for (u, v) in loop:
        du = (u - 0.5) * chord
        dv = v * chord
        ax = du * math.cos(ang) - dv * math.sin(ang)
        tg = du * math.sin(ang) + dv * math.cos(ang)
        a = a0 + tg / max(r, 1e-3)
        ring.append((xc + dirn * (start + chord * 0.5 + ax),
                     r * math.cos(a), T["z"] + r * math.sin(a)))
    return ring


def _loft_blade(rings):
    """Close a stack of aerofoil sections into a blade, tip included."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for s in range(n):
            s2 = (s + 1) % n
            faces.append((a + s, a + s2, b + s2, b + s))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (len(rings) - 1) * n
    faces.append(tuple(range(base, base + n)))
    return verts, faces


def _fasteners():
    """Head studs, cam cover bolts and sump bolts."""
    parts = []
    for bank in (0, 1):
        for (n, pair, b2, x, a) in spec.cylinders():
            if b2 != bank:
                continue
            for sgn in (-1, 1):
                sv, sf = mesh.cylinder(0.0, 132.0, 5.0, SM)
                sv = [(pz, py, px) for (px, py, pz) in sv]
                sv = common.along_bank(sv, x, spec.DECK_HEIGHT - 10.0, bank,
                                       sgn * (spec.BORE / 2 + 13.0))
                parts.append((sv, sf))
    sump = []
    a = spec.ANCILLARY
    z = -spec.BLOCK["skirt_depth"] - 22.0
    for k in range(18):
        f = k / 17
        x = -a["sump_len"] / 2 + a["sump_len"] * f
        for sgn in (-1, 1):
            bv, bf = mesh.cylinder(0.0, 14.0, 4.4, SM)
            bv = [(pz + x, py + sgn * a["sump_w"] / 2, px + z - 14.0)
                  for (px, py, pz) in bv]
            sump.append((bv, bf))
    return {"head_studs": mesh.join(*parts), "sump_bolts": mesh.join(*sump)}


def _sensors():
    """Crank and cam position sensors, knock sensors, oil and coolant pickups."""
    parts = []
    spots = [(spec.BLOCK["x_front"] + 20.0, 122.0, -40.0),
             (spec.BLOCK["x_rear"] - 40.0, -122.0, -30.0),
             (0.0, 122.0, 20.0), (-90.0, -122.0, 20.0),
             (120.0, 0.0, -spec.BLOCK["skirt_depth"] - 30.0)]
    for (x, y, z) in spots:
        v, f = mesh.cylinder(0.0, 46.0, 9.0, SM)
        v = [(pz + x, px + y, py + z) for (px, py, pz) in v]
        parts.append((v, f))
        cv, cf = shapes.rounded_box(x, y * 1.12, z + 26.0, 26.0, 22.0, 20.0, 4.0)
        parts.append((cv, cf))
    return {"sensors": mesh.join(*parts)}


def _sheet(rows, t):
    """Give a grid of stations thickness in z and close it into a solid."""
    nr, nc = len(rows), len(rows[0])
    lo = [(x, y, z - t/2) for r in rows for (x, y, z) in r]
    hi = [(x, y, z + t/2) for r in rows for (x, y, z) in r]
    verts = lo + hi
    o = len(lo)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i*nc + j
            faces.append((k, k+nc, k+nc+1, k+1))
            faces.append((o+k, o+k+1, o+k+nc+1, o+k+nc))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i*nc + j
            faces.append((k, k+nc, o+k+nc, o+k) if j == 0
                         else (k+nc, k, o+k, o+k+nc))
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i*nc + j
            faces.append((k+1, k, o+k, o+k+1) if i == 0
                         else (k, k+1, o+k+1, o+k))
    return verts, faces


def _heat_shields():
    """Blankets over the turbine housings and their collectors.

    These were two pressed sheets stretched the length of the vee at a fixed
    height, from the days when the exhaust was a pair of logs at that height.
    The exhaust is not there any more: the primaries climb to z = 351 and the
    collectors sit at 381, so the sheets were threading between them rather
    than covering anything, and from above they read as two smooth logs lying
    across the middle of the engine.

    What a turbocharged engine actually carries is a blanket: a quilted wrap
    laced over the turbine volute and the collector feeding it, which is the
    hottest metal on the car and the part nearest the bodywork. It is tied on
    rather than bolted, so it follows the shape underneath with a lace line
    down the seam.
    """
    parts = []
    for pair in (0, 2):
        _, tx, _sgn, ib = gaspath.turbo_side(pair)
        sc = gaspath.turbine_scroll(pair)
        # a shell standing off the volute, open where the inlet flange and
        # the outlet snout come through
        def scroll_rings(off):
            # only the outer two thirds of each section: a blanket is laced
            # over the outside of a volute, and a full ring at this offset
            # would pass through the wheel the volute is wrapped round
            out = []
            for (p, r) in sc:
                x, y, z = p
                m = math.hypot(y, z - T["z"]) or 1.0
                uy, uz = y / m, (z - T["z"]) / m
                ring = []
                for k in range(13):
                    a = math.radians(-115.0 + 230.0 * k / 12)
                    rr = r + off
                    ring.append((x + rr * math.cos(a) * 1.35,
                                 y + rr * math.sin(a) * uy,
                                 z + rr * math.sin(a) * uz))
                out.append(ring)
            return out
        # a 4 mm wrap, not a solid: what is under a blanket is under it, not
        # inside it, and the audit is right to say so
        parts.append(_shell_rings(scroll_rings(9.0), scroll_rings(5.0),
                                  closed=False))

        # and the same over the collector that feeds it
        cp = gaspath.collector_path(pair)
        parts.append(_shell_rings(_sleeve(cp, gaspath.COLLECTOR_RADII, 9.0),
                                  _sleeve(cp, gaspath.COLLECTOR_RADII, 5.0)))
        # the lace line down the seam, which is how a blanket is held on
        lace = []
        for k in range(9):
            f = (k + 0.5) / 9
            idx = min(int(f * (len(sc) - 1)), len(sc) - 2)
            (px, py, pz), r = sc[idx]
            m = math.hypot(py, pz - T["z"]) or 1.0
            lv, lf = mesh.ring_torus(0.0, 1.9, 0.9, 10, 6)
            lv = mesh.translate(lv, px + (r + 6.0) * 1.35 * 0.72,
                                py + (r + 6.0) * 0.5 * (py / m),
                                pz + (r + 6.0) * 0.5 * ((pz - T["z"]) / m))
            lace.append((lv, lf))
        parts.append(mesh.join(*lace))
    return {"heat_shields": mesh.join(*parts)}


def _shell_rings(outer, inner, closed=True):
    """Close two stacks of rings into a thin shell, rimmed all the way round.

    `closed` says whether each ring is a loop (a sleeve) or an arc (a wrap
    with two free edges that need rims of their own).
    """
    n = len(outer[0])
    m = len(outer)
    verts = [v for r in outer for v in r] + [v for r in inner for v in r]
    off = m * n
    faces = []
    span = n if closed else n - 1
    for i in range(m - 1):
        a, b = i * n, (i + 1) * n
        for s in range(span):
            s2 = (s + 1) % n
            faces.append((a + s, a + s2, b + s2, b + s))
            faces.append((off + a + s, off + b + s,
                          off + b + s2, off + a + s2))
    last = (m - 1) * n
    for s in range(span):
        s2 = (s + 1) % n
        faces.append((s, off + s, off + s2, s2))
        faces.append((last + s, last + s2, off + last + s2, off + last + s))
    if not closed:
        for i in range(m - 1):
            a, b = i * n, (i + 1) * n
            faces.append((a, b, off + b, off + a))
            faces.append((a + n - 1, off + a + n - 1,
                          off + b + n - 1, b + n - 1))
    return verts, faces


def _sleeve(path, radii, off):
    """Rings of a given standoff around a path, framed against world up."""
    rings = []
    for i, p in enumerate(path):
        if i == 0:
            t = [path[1][k] - p[k] for k in range(3)]
        elif i == len(path) - 1:
            t = [p[k] - path[-2][k] for k in range(3)]
        else:
            t = [path[i + 1][k] - path[i - 1][k] for k in range(3)]
        t = mesh._normalise(t)
        up = (0.0, 1.0, 0.0) if abs(t[1]) < 0.9 else (0.0, 0.0, 1.0)
        n1 = mesh._normalise(mesh._cross(t, up))
        n2 = mesh._cross(t, n1)
        r = radii[min(i, len(radii) - 1)] + off
        ring = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            ca, sa = math.cos(a), math.sin(a)
            ring.append(tuple(p[j] + n1[j] * r * ca + n2[j] * r * sa
                              for j in range(3)))
        rings.append(ring)
    return rings


def _dry_sump():
    """Scavenge and pressure lines running to the tank."""
    parts = []
    z = -spec.BLOCK["skirt_depth"] - 40.0
    for i, sgn in enumerate((-1.0, 1.0)):
        parts.append(mesh.pipe(
            [(spec.BLOCK["x_rear"] - 40.0, sgn * 110.0, z),
             (60.0, sgn * 150.0, z - 16.0),
             (spec.BLOCK["x_front"] + 10.0, sgn * 120.0, -10.0)],
            11.0, SM))
    return {"dry_sump_lines": mesh.join(*parts)}
