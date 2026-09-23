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
    """A gear: a bored hub with teeth round it, on the shaft at (y, z).

    Two things were wrong here. The hub was built once at the origin and
    joined to the teeth, and then built AGAIN at (y, z) -- so every cam gear
    also left a 40 mm disc sitting on the crank's centreline, four of them
    stacked at the same station, visible in any cutaway and attached to
    nothing. And the bore was 0.28r, which is 12.9 mm on a 10 mm camshaft
    nose: the gear was a ring floating round the shaft it drives.

    The hub also runs 19 mm rather than 14, all of it aft, because the gears
    are at x -262 and the camshaft noses start at -254.
    """
    parts = [mesh.tube(x - 7.0, x + 12.0, r * 0.18, r * 0.88, 26)]
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        tv, tf = shapes.rounded_box(x, r * 0.94, 0.0, 13.0, r * 0.16, 5.2, 0.7)
        parts.append((mesh.rot_x(tv, a), tf))
    v, f = mesh.join(*parts)
    return [(px, py + y, pz + z) for (px, py, pz) in v], f


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

    # ---- the coolant circuit, as a circuit ------------------------------
    #
    # This was one pipe from the block's front face up to a header tank, and
    # it met nothing at either end: 31 mm from the water pump, 52 mm from the
    # thermostat, and never within reach of the outlets. Pump, thermostat,
    # outlets and pipework were four parts of a cooling system that did not
    # cool anything, and `audit_intersect` was content because none of them
    # was in another's way.
    #
    # The loop is: pump into the block, up through the liners into the heads,
    # out of the eight outlets, forward to the thermostat on the front face,
    # and back down to the pump's eye. Everything forward of x -250 has to
    # miss the timing gears at -269..-255, and everything on the centreline
    # has to miss the crank nose.
    wp = []
    pump_out = spec.coolant_node("pump_out")
    pump_in = spec.coolant_node("pump_in")
    stat = spec.coolant_node("stat_top")
    x_fwd = spec.BLOCK["x_front"] - 18.0

    # pump discharge into the block's front face
    wp.append(mesh.pipe([pump_out, (xo - 4.0, 120.0, 20.0),
                         (spec.BLOCK["x_front"] + 8.0, 112.0, 12.0)],
                        16.0, SM, subdiv=3))
    # The two head outlet rails, gathered forward onto the thermostat. Each
    # starts at its head's outlet, behind the last cylinder, and runs the
    # length of the head's outboard side under the intake runners and over
    # the engine mounts, then turns up across the front to the thermostat.
    # They ran along y +/-126 at z 62, which on this engine is inside the
    # heads, and started at x -190, clear of the outlets they were for.
    K = spec.COOLANT
    for bank, sgn in ((0, -1.0), (1, 1.0)):
        rear = common.bank_point(spec.head_rear_x(bank) + 10.0,
                                 K["rail_along"], K["rail_lat"], bank)
        front = common.bank_point(spec.BLOCK["x_front"] + 10.0, K["rail_along"],
                                  K["rail_lat"], bank)
        # The forward run is at x_front + 6. The accessory belt's tensioner
        # occupies x -334 to -246 from y -172 to -66, and a rail forward of
        # the block face crosses it on its way in to the thermostat.
        x_rail = spec.BLOCK["x_front"] + 6.0
        path = [rear, front,
                (x_rail, front[1] * 0.92, front[2] + 30.0),
                (x_rail, sgn * 56.0, stat[2] - 6.0),
                (stat[0] + 30.0, sgn * 22.0, stat[2])]
        wp.append(mesh.pipe(mesh.smooth_path(path, 2), K["rail_r"], SM))
    # thermostat back to the pump's eye
    wp.append(mesh.pipe(
        [(stat[0] + 26.0, 26.0, stat[2] - 10.0), (x_fwd, 90.0, stat[2] - 40.0),
         (x_fwd, 170.0, 10.0), (pump_in[0] - 40.0, pump_in[1], pump_in[2]),
         pump_in], 15.0, SM, subdiv=3))
    # The header tank on the front face, above the thermostat.
    #
    # At y 130, z 150 it was a 44 mm barrel spanning y 86-174 and z 106-194,
    # and the right bank's exhaust camshaft noses forward to x -254 at
    # y 124-153, z 180-208. The tank and the camshaft were the same metal;
    # rerouting the head rails, which is what I tried first, moved a pipe
    # that was never the problem and put it through an intake valve instead.
    # The right bank's two camshafts box it in: the exhaust cam is at
    # y 124-153, z 180-208 and the intake cam at y 180-208, z 124-153, and a
    # 44 mm barrel is too fat to sit in the corner between them. At y 132,
    # z 100 on a 38 mm radius it passes under both -- 10 mm clear of the
    # intake cam -- and stays clear of the thermostat inboard of it at
    # y +/-52 and of the water pump below it, which tops out at z 30.
    tv, tf = mesh.tube(x_fwd - 32.0, x_fwd + 8.0, 0.0, 38.0, 22)
    tv = [(px, py + 132.0, pz + 100.0) for (px, py, pz) in tv]
    wp.append((tv, tf))
    wp.append(mesh.pipe([(x_fwd - 12.0, 132.0, 100.0),
                         (x_fwd - 12.0, 60.0, 118.0),
                         (stat[0] - 6.0, 18.0, stat[2] + 30.0),
                         (stat[0] - 6.0, 0.0, stat[2] + 34.0)], 8.0, SM,
                        subdiv=3))
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
            xc, -ib, T["turb_r"] * T["turb_wheel_frac"], 11, 0,
            hub=[(0.00, 0.30), (0.25, 0.42), (0.55, 0.52), (0.80, 0.56),
                 (1.00, 0.54)],
            twist=(58.0, 18.0), chord=(0.62, 0.54))

        # compressor: in along the axis at the eye, out at the tip, so the
        # inducer is steeply raked and the exducer nearly radial.
        #
        # The wheel faces the air, which means the small end faces the eye.
        # It was built from the volute plane outwards, so the hub grew from
        # 0.22 at the volute to 0.58 at the inlet: the exducer was against
        # the air intake and the inducer was against the discharge, with the
        # whole wheel back to front. Same rule as the turbine next to it --
        # the hub grows towards the exducer, and the exducer is where the
        # volute is.
        r_tip_c = T["comp_r"] * T["comp_wheel_frac"]
        xc = tx + ib * hw + ib * r_tip_c * T["wheel_depth_frac"]
        out[f"compressor_wheel_{tag}"] = _wheel(
            xc, -ib, r_tip_c, 7, 7,
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
    depth = r_tip * T["wheel_depth_frac"]
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
    """Crank and cam position sensors, knock sensors, oil and coolant pickups.

    Each is a threaded body screwed 4 mm into the crankcase wall with its
    axis through it, and its connector on the outer end. They were placed at
    y +/-122, which is 20 mm off a wall at 101.5, all pointing +y -- so the
    ones on the left grew into the engine -- with their connectors standing
    3.6 mm off their own bodies.
    """
    parts = []
    wall = spec.BLOCK["half_width"] * 0.86
    spots = [(spec.BLOCK["x_front"] + 20.0, 1.0, -40.0),
             (spec.BLOCK["x_rear"] - 40.0, -1.0, -30.0),
             (0.0, 1.0, 20.0), (-90.0, -1.0, 20.0)]
    for (x, side, z) in spots:
        v, f = mesh.cylinder(wall - 4.0, wall + 36.0, 9.0, SM)
        v = [(-ly, lx, lz) for (lx, ly, lz) in v]            # axis along +y
        if side < 0:
            v = [(-px, -py, pz) for (px, py, pz) in v]       # half turn
        parts.append(([(px + x, py, pz + z) for (px, py, pz) in v], f))
        cv, cf = shapes.rounded_box(x, side * (wall + 44.0), z, 26.0, 20.0,
                                    22.0, 4.0)
        parts.append((cv, cf))
    # and the oil temperature sensor, up through the floor of the pan's well,
    # just forward of the drain plug
    a = spec.ANCILLARY
    floor = -spec.BLOCK["skirt_depth"] - 22.0 - a["sump_depth"]
    xs = a["sump_len"] * 0.18 - 32.0
    v, f = mesh.cylinder(-4.0, 36.0, 9.0, SM)
    v = [(lz + xs, ly, -lx + floor) for (lx, ly, lz) in v]   # axis down
    parts.append((v, f))
    cv, cf = shapes.rounded_box(xs, 0.0, floor - 44.0, 26.0, 22.0, 20.0, 4.0)
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
            # Only the outer two thirds of each section: a blanket is laced
            # over the outside of a volute, and a full ring at this offset
            # would pass through the wheel the volute is wrapped round.
            #
            # Which two thirds is the whole of it. This arc used to be
            # centred on the axial direction and swept 230 degrees from
            # there, so the covered sector was the outboard FACE of the
            # volute and the two free edges ran down the inside, 0.91 of a
            # section radius in towards the wheel -- and since the spiral's
            # own radius shrinks as it goes round, each free edge cut
            # through the surface laid down by the stations before it. That
            # is the shredded-paper look: not a blanket, two free edges
            # spiralling through their own wrap.
            #
            # The sector is centred on the outward radius instead, which is
            # where a blanket goes. The free edges land on the two axial
            # faces, and the deepest either reaches is 0.34 of a section in
            # -- still clear of the passage, let alone the wheel.
            out = []
            for (p, r) in sc:
                x, y, z = p
                m = math.hypot(y, z - T["z"]) or 1.0
                uy, uz = y / m, (z - T["z"]) / m
                ring = []
                for k in range(13):
                    a = math.radians(90.0 - 110.0 + 220.0 * k / 12)
                    rr = r + off
                    ring.append((x + rr * math.cos(a),
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
        # The tie-downs, which is how a blanket is held on. They sit on the
        # crown -- straight out along the radius, on top of the wrap -- and
        # not on the diagonal between crown and face, where they used to be
        # and where nothing could have reached them.
        lace = []
        for k in range(9):
            f = (k + 0.5) / 9
            idx = min(int(f * (len(sc) - 1)), len(sc) - 2)
            (px, py, pz), r = sc[idx]
            m = math.hypot(py, pz - T["z"]) or 1.0
            uy, uz = py / m, (pz - T["z"]) / m
            lv, lf = mesh.ring_torus(0.0, 2.2, 0.9, 10, 6)
            lv = mesh.translate(lv, px,
                                py + (r + 10.0) * uy,
                                pz + (r + 10.0) * uz)
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
    """The oil circuit, as a circuit.

    Four scavenge lines out of the pan into the pump's scavenge stages, the
    stack's discharge into the tank, the tank's feed back to the pressure
    stage, and the pressure line to the cooler -- which already lands on the
    filter, and the filter on the block's gallery.

    What was here was two pipes running fore and aft under the engine,
    beginning and ending in mid-air: 66 mm from the pickup, 25 mm from the
    pump and 51 mm from the cooler. A dry sump exists to move oil round a
    loop and there was no loop anywhere in it -- five parts of one system,
    none of them touching, and every audit green, because all any of them
    asked was whether two parts were in each other's way.

    Every endpoint below comes from `spec.oil_pump_port`, `oil_pump_union`
    and `oil_tank_union` rather than from a number typed in here, so a pipe
    cannot miss a boss that has moved.
    """
    parts = []
    # The car this engine goes in closes its floor up under the pan: below
    # z -170 nothing may be wider than about 196 mm of half width, which is
    # what the dry-sump tank itself measures. Above -120 there is room out to
    # 293, which is where the oil cooler sits. So the run stays narrow while
    # it is low and only goes outboard once it has climbed -- a first pass
    # took the scavenge lines out to y 280 at z -206 and put 60 mm of
    # pipework through the hypercar's floor.
    z_low = -spec.BLOCK["skirt_depth"] - 54.0
    pan_y = -spec.ANCILLARY["sump_w"] / 2.0 - 4.0
    y_low = -150.0

    # scavenge 1 comes off the pickup itself, forward of the block where
    # there is nothing in the way but the timing gears at x -269
    p1 = spec.oil_pump_port(1)
    parts.append(mesh.pipe(
        [(spec.BLOCK["x_front"] - 16.0, -86.0, -46.0),
         (spec.BLOCK["x_front"] - 18.0, y_low, -90.0),
         (spec.BLOCK["x_front"] - 18.0, p1[1] - 20.0, p1[2] - 30.0), p1],
        9.0, SM, subdiv=3))

    # and three more out of the pan, staggered so they do not share a route:
    # aft along the flank at y 150, then up and outboard onto the ports
    for k, (sx, drop) in enumerate(((110.0, -18.0), (50.0, -30.0),
                                    (-10.0, -42.0)), start=2):
        port = spec.oil_pump_port(k)
        parts.append(mesh.pipe(
            [(sx, pan_y, z_low), (sx, y_low, z_low + drop),
             (port[0] + 40.0, y_low, z_low + drop),
             (port[0], port[1] * 0.72, port[2] - 24.0), port],
            9.0, SM, subdiv=3))

    # the stack discharges into the top of the tank. Forward of the oil
    # cooler, which fills the left flank from x -111 back and from z -118
    # up to -30.
    ret = spec.oil_pump_union("return")
    tin = spec.oil_tank_union("scavenge")
    parts.append(mesh.pipe(
        [ret, (ret[0], -240.0, -30.0), (ret[0], -196.0, -110.0),
         (tin[0] - 12.0, tin[1] + 6.0, tin[2] + 8.0), tin], 11.0, SM,
        subdiv=3))

    # the tank feeds the pressure stage from its lowest point, round the
    # front of the engine
    feed = spec.oil_tank_union("feed")
    pin = spec.oil_pump_union("feed")
    # Outboard of the left mount bracket on the way up. The bracket fills
    # x -186 to -114 from z -74 to 21 and the climb was at y -180 to -200,
    # straight through it: 295 vertices. Out at -236 it is clear of the
    # bracket and still inside the 293 mm the car allows above z -120.
    parts.append(mesh.pipe(
        [feed, (-214.0, -180.0, feed[2] + 10.0),
         (pin[0] - 8.0, -190.0, -140.0),
         (pin[0] - 8.0, -236.0, -90.0),
         (pin[0] - 8.0, -220.0, -50.0), pin], 12.0, SM, subdiv=3))

    # and the pressure stage feeds the cooler, which hands on to the filter
    # and the filter to the block's main gallery
    p0 = spec.oil_pump_port(0)
    parts.append(mesh.pipe(
        [p0, (p0[0] - 12.0, -262.0, 0.0), (-160.0, -270.0, -30.0),
         (-108.0, -255.0, -45.0)], 10.0, SM, subdiv=3))
    return {"dry_sump_lines": mesh.join(*parts)}
