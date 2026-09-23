"""The systems a racing car has that this one did not.

Brake duct internals, the hydraulic and electrical runs, the cockpit a driver
actually sits in, the survival cell's structure, and the hardware that gets
handled every pit stop. None of it is decoration: a brake duct with nothing
inside it is a scoop pointed at a disc, and a car with no lines on it has no
way of getting fluid or current from one end to the other.

Each part is its own object, because each is a separate thing with its own
material and its own failure mode.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import wheels, chassis, floor, detail

S = spec.SUSP
W = spec.WHEEL
T = spec.TUB
BD = spec.BRAKE_DUCT


def build():
    out = {}
    out.update(_brake_ducts())
    out.update(_hydraulics())
    out.update(_electrical())
    out.update(_cockpit())
    out.update(_survival_cell())
    out.update(_pit_hardware())
    out.update(_cooling_exits())
    return out


# --------------------------------------------------------------------------

def _brake_ducts():
    """Inlet, duct, drum and the fence that keeps it all off the tyre.

    A brake disc at 800 degrees needs about a kilogram of air a second through
    it. The duct that does that is the most aerodynamically sensitive thing on
    the corner, because it also has to keep the wheel wake off the floor.
    """
    out = {}
    for (tag, x, y, w, od) in wheels.corners():
        front = tag.startswith("f")
        r = BD["front_r"] if front else BD["rear_r"]
        sgn = 1.0 if y > 0 else -1.0
        z = od / 2
        inb = y - sgn * w * 0.30
        # The inlet has to be clear of the TYRE, not merely inboard of the
        # wheel centre. At 0.30 of the tread width from the centreline it was
        # still 60 mm inside the sidewall -- a scoop buried in rubber, taking
        # its air from inside the tyre. The feed station is the tyre's inner
        # face plus the duct's own half width and some clearance.
        feed = y - sgn * (w * 0.5 + BD["width"] * 0.55 + 10.0)

        # the scoop: a shaped inlet facing forward, inboard of the tyre
        # r * 0.04 below the axle, not 0.26. At 0.26 the mouth spanned
        # z 215-345 and the front track rod sweeps across it at z 231 on its
        # way from the steering arm to the rack -- a steering link through
        # the middle of a brake duct's inlet.
        out[f"bduct_inlet_{tag}"] = shapes.rounded_box(
            x - r * 0.92, feed, z - r * 0.04, 90.0, BD["width"],
            BD["inlet_h"], 16.0, draft=3.0)
        # the duct carrying it back to the drum
        # the duct narrows as it goes back, because the drum needs velocity
        # at the disc, not volume in the pipe
        # it also works outboard as it goes back, from the feed station to
        # the drum around the disc
        out[f"bduct_pipe_{tag}"] = mesh.pipe(
            [(x - r * 0.86, feed, z - r * 0.22),
             (x - r * 0.58, feed + (inb - feed) * 0.22, z - r * 0.16),
             (x - r * 0.30, feed + (inb - feed) * 0.58, z - r * 0.05),
             (x - r * 0.08, feed + (inb - feed) * 0.88, z - r * 0.01),
             (x + r * 0.10, inb, z)],
            [BD["width"] * 0.42, BD["width"] * 0.39, BD["width"] * 0.35,
             BD["width"] * 0.31, BD["width"] * 0.28], 22, subdiv=3)
        # the drum around the disc, which is what actually directs the air
        # The drum is a scroll: air enters at one point and has to be
        # distributed round the whole disc, so it is deeper where the feed
        # comes in and it is finned inside to spread the flow. As a plain
        # annulus it directed nothing anywhere.
        # `w` is the TYRE's width and is still needed below, so the duct's
        # own width gets its own name -- it used to shadow it, which is how
        # the fence that stands the assembly off the tyre ended up placed
        # off the duct's width instead and sat 125 mm inside the rubber.
        dw = BD["width"]
        drum = [shapes.volute(0.0, r * 0.60, r * 0.80, dw * 0.16, dw * 0.30,
                              seg=44, sect=14)]
        drum.append(mesh.revolve_closed(
            [(-dw * 0.32, r * 0.50), (-dw * 0.24, r * 0.50),
             (-dw * 0.24, r * 0.88), (-dw * 0.32, r * 0.88)], 40))
        for k in range(9):
            a = 2 * math.pi * k / 9
            fv, ff = mesh.box(0.0, 0.0, 0.0, dw * 0.34, 4.0, r * 0.16)
            drum.append(([(px, py + math.cos(a) * r * 0.70,
                           pz + math.sin(a) * r * 0.70)
                          for (px, py, pz) in fv], ff))
        dv, df = mesh.join(*drum)
        # The drum is not symmetric about its own centre -- the back plate is
        # on one face of it -- so its axis has to flip with the side, or the
        # plate ends up outboard on the left and inboard on the right. That
        # was the 2.8 mm the two drums were from being mirror images.
        out[f"bduct_drum_{tag}"] = (
            [(pz + x, sgn * px + inb, py + z) for (px, py, pz) in dv], df)
        if front:
            # a slot in the drum's lower front quarter for the steering arm,
            # which reaches forward from the upright through the drum's plane
            # to the track rod
            out[f"cut:bduct_drum_{tag}"] = shapes.rounded_box(
                x - 85.0, inb, z - 82.0, 200.0, dw * 0.9, 90.0, 12.0)
        # the fence standing the whole assembly off the tyre
        # A fence cut to the shape of the job: it wraps the front of the
        # drum, is cut away behind the axle line where the wheel rim would
        # foul it, and rolls inboard at the trailing edge to keep the tyre
        # squirt out of the floor.
        # clear of the tyre's inner face, which is what it stands the
        # assembly off
        fy = y - sgn * (w * 0.5 + 16.0)
        # Its lower edge stops above the links that cross its plane: at the
        # front the track rod reaches the steering arm through the fence's
        # lower front corner, so that corner is cut away; at the rear the
        # lower wishbone and the toe link pass under the axle, so the fence
        # stops above them.
        lo = z - r * (0.66 if front else 0.30)
        front_lo = ((x - r * 0.80, z - r * 0.28), (x - r * 0.30, lo)) \
            if front else ((x - r * 0.80, lo),)
        prof = shapes.panel_outline(
            list(front_lo) + [(x + r * 0.44, lo),
             (x + r * 0.74, z - r * 0.18), (x + r * 0.60, z + r * 0.26),
             # the top edge clears the upper wishbone, which picks up at the
             # top of the upright and used to run through this plate
             (x + r * 0.02, z + r * 0.34), (x - r * 0.66, z + r * 0.18),
             (x - r * 0.86, z - r * 0.20 if front else lo + 20.0)],
            subdiv=4)
        out[f"bduct_fence_{tag}"] = shapes.shaped_panel(
            prof, fy, 8.0, rim_seg=5,
            bow=lambda fx, fz, sgn=sgn: -sgn * 26.0 * max(0.0, fx - 0.45) ** 2
                / 0.30)
        # cooling exits on the outboard face
        #
        # Each stands on the scroll's outboard face where the scroll is. They
        # were all set at the scroll's widest section and at a radius and
        # angle measured the other way round from the scroll's own, so the
        # first one, where the scroll is still narrow, hung in the air.
        vanes = []
        for k in range(5):
            a = math.pi * (0.2 + 0.6 * k / 4)
            # the scroll's own angle for this point, and its section there
            f = ((math.pi / 2 - a) % (2 * math.pi)) / (2 * math.pi)
            R = r * (0.60 + 0.20 * f)
            rt = dw * (0.16 + 0.14 * f)
            rho = R + rt * 0.5                 # on its outer half
            face = rt * math.sqrt(0.75)        # its outboard face there
            vanes.append(shapes.rounded_box(
                x + rho * math.cos(a), inb + sgn * (face + 2.0),
                z + rho * math.sin(a), 46.0, 6.0, 16.0, 2.5))
        out[f"bduct_vanes_{tag}"] = mesh.join(*vanes)
    return out


def _ferrule(p, direction, r, length, hex_r=None):
    """The crimped end of a braided hose: a knurled collar and a hex nut.

    A hose does not merge into a caliper. It is crimped into a fitting, and
    the fitting is a hex a spanner fits and a swaged collar over the braid.
    """
    hex_r = hex_r or r * 1.30
    body, _f = mesh.revolve_closed(
        [(0.0, r * 0.72), (length * 0.30, r), (length * 0.62, r),
         (length * 0.62, r * 0.80), (length, r * 0.80)], 12)
    parts = [(shapes.orient(body, p, direction), _f)]
    hv, hf = mesh.revolve_closed(
        [(length * 0.60, 0.0), (length * 0.60, hex_r), (length * 1.34, hex_r),
         (length * 1.34, 0.0)], 6)
    parts.append((shapes.orient(hv, p, direction), hf))
    return mesh.join(*parts)


def _p_clip(p, direction, r):
    """A P-clip: the band round the hose, the tab, and the bolt through it.

    Hose that is not clipped every few hundred millimetres chafes through on
    whatever it is lying against, so every run on a real car is clipped, and
    the clips are where the run changes direction.
    """
    band, bf = mesh.ring_torus(0.0, r + 2.6, 2.4, 18, 8)
    parts = [(shapes.orient(band, p, direction), bf)]
    tv, tf = mesh.box(0.0, 0.0, r + 8.0, 5.0, 9.0, 15.0)
    parts.append((shapes.orient(tv, p, direction), tf))
    bv, blf = mesh.revolve_closed(
        [(0.0, 0.0), (0.0, 5.2), (3.4, 5.2), (3.4, 2.6), (9.0, 2.6),
         (9.0, 0.0)], 8)                       # a bolt, axis out of the tab
    bv = [(py, pz, px + r + 13.0) for (px, py, pz) in bv]
    parts.append((shapes.orient(bv, p, direction), blf))
    return mesh.join(*parts)


def _run(path, r, clips=(), per_seg=7, seg=12):
    """A fluid line: the hose itself, a fitting at each end, clips along it."""
    dense = mesh.smooth_path(path, per_seg)
    parts = [mesh.pipe(dense, r, seg)]
    d0 = tuple(dense[1][k] - dense[0][k] for k in range(3))
    d1 = tuple(dense[-1][k] - dense[-2][k] for k in range(3))
    parts.append(_ferrule(dense[0], tuple(-c for c in d0), r,
                          spec.SERVICE["line_fitting_r"] * 1.8))
    parts.append(_ferrule(dense[-1], d1, r,
                          spec.SERVICE["line_fitting_r"] * 1.8))
    for f in clips:
        i = max(1, min(len(dense) - 2, int(f * (len(dense) - 1))))
        d = tuple(dense[i + 1][k] - dense[i - 1][k] for k in range(3))
        parts.append(_p_clip(dense[i], d, r))
    return mesh.join(*parts)


# The master cylinders: their origin (the front of the body) and height.
# Each is pushed by a pedal, so they sit ahead of the driver's feet with the
# clevis 160 mm back, on the pedal.
MC_X = spec.BODY_DETAIL["driver"]["foot_x"] - 190.0
MC_Y, MC_Z = 70.0, 376.0


def _hydraulics():
    """Brake lines to every corner and the master cylinders that feed them.

    Each corner is fed twice: a hard line from the master cylinder down the
    chassis to a union on the upright's inboard side, then a short braided
    flexible hose across the suspension travel to the caliper. That split is
    not detail for its own sake -- it is why the line survives 60 mm of wheel
    travel and full lock, and a single rigid tube from pedal to caliper would
    not.
    """
    out = {}
    SV = spec.SERVICE
    r_hard = SV["line_r"] * 0.72
    lines = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        front = tag.startswith("f")
        z_cal = od / 2 + 157.0     # into the caliper's upper shoe
        y_union = y * 0.62
        z_union = od / 2 + 40.0
        # out of the master cylinder's union, over the steering rack and
        # outboard of the driver's shins
        hard = [(MC_X + 14.0, sgn * MC_Y, MC_Z + 48.0),
                (MC_X + 120.0, sgn * 120.0, 380.0)]
        if front:
            # round behind the pushrod, not across it
            hard += [(x + 180.0, sgn * 250.0, 250.0),
                     (x + 60.0, sgn * 330.0, 214.0)]
        else:
            # through the dash bulkhead's aperture, not its frame
            hard += [(spec.FRONT_AXLE_X + 110.0, sgn * 168.0, 292.0),
                     (1250.0, sgn * 170.0, 280.0),
                     (1360.0, sgn * 209.0, 250.0),
                     (1500.0, sgn * 211.0, 226.0)]
            # over the rear lower wishbone, not through it
            hard += [(2100.0, sgn * 300.0, 250.0),
                     (3050.0, sgn * 330.0, 262.0),
                     (x - 260.0, sgn * 360.0, 330.0),
                     (x - 60.0, sgn * 420.0, 352.0)]
        hard.append((x - 10.0, y_union, z_union))
        lines.append(_run(hard, r_hard,
                          clips=[0.30, 0.58, 0.84] if not front else [0.42, 0.78]))
        # the flexible loop across the travel -- slack enough to take droop
        flex = [(x - 10.0, y_union, z_union),
                (x + 26.0, y * 0.70, z_union - 26.0),
                (x + 18.0, y * 0.76, z_cal + 34.0),
                # 0.93 of the wheel's y, not 0.78: the caliper's inner face
                # is at 766 and the flexible line stopped at 648, so the
                # brakes were plumbed to within 120 mm of themselves.
                (x - 6.0, y * 0.93, z_cal)]
        lines.append(_run(flex, SV["line_r"], per_seg=8))
    out["brake_lines"] = mesh.join(*lines)

    cyl = []
    for sgn in (-1.0, 1.0):
        # body, reservoir on top, pushrod clevis out the back and the union
        # the line screws into
        v, f = mesh.revolve_closed(
            [(0.0, 0.0), (150.0, 0.0), (150.0, 20.0), (142.0, 26.0),
             (120.0, 26.0), (120.0, 30.0), (104.0, 30.0), (104.0, 26.0),
             (26.0, 26.0), (18.0, 24.0), (18.0, 14.0), (0.0, 14.0)], 30)
        parts = [(v, f)]
        rv, rf = mesh.revolve_closed(
            [(0.0, 0.0), (62.0, 0.0), (62.0, 21.0), (56.0, 24.0),
             (6.0, 24.0), (0.0, 21.0)], 24)
        parts.append(([(pz + 60.0, py, px + 30.0)
                       for (px, py, pz) in rv], rf))
        uv, uf = mesh.revolve_closed(
            [(0.0, 0.0), (26.0, 0.0), (26.0, 8.0), (20.0, 9.5),
             (14.0, 9.5), (14.0, 12.0), (0.0, 12.0)], 16)
        # on top, where the line can leave it clear of the steering rack
        parts.append(([(pz + 14.0, py, px + 22.0)
                       for (px, py, pz) in uv], uf))
        parts.append(shapes.rod_end((160.0, 0.0, 0.0), (1.0, 0.0, 0.0), 10.0))
        v, f = mesh.join(*parts)
        # Ahead of the pedals, pushed by them: the clevis at the back of
        # each is on its pedal. They were at the front axle, 250 mm behind
        # the pedals and in the driver's shins.
        cyl.append(([(px + MC_X, py + sgn * MC_Y, pz + MC_Z)
                     for (px, py, pz) in v], f))
    out["master_cylinders"] = mesh.join(*cyl)

    # The pedals go under the driver's feet, which are behind the front axle
    # line -- that is a survival-cell rule, not a styling choice. They used to
    # sit at x 495, which is 405 mm AHEAD of the front axle and 484 mm from
    # the nearest part of the driver.
    fx = spec.BODY_DETAIL["driver"]["foot_x"]
    out["pedal_box"] = mesh.join(
        shapes.rounded_box(fx + 18.0, 0.0, 250.0, 160.0, 260.0, 40.0, 10.0),
        shapes.rounded_box(fx - 10.0, -78.0, 330.0, 34.0, 60.0, 170.0, 8.0),
        shapes.rounded_box(fx - 10.0, 78.0, 330.0, 34.0, 60.0, 170.0, 8.0))
    return out


def _electrical():
    """The loom, and the boxes it connects. Current has to get from the
    battery at the back to the dash at the front somehow."""
    out = {}
    SV = spec.SERVICE
    runs = []
    # Along the cockpit floor, under the seat.
    #
    # At y 70-96 and z 420-470 it ran through the driver's hip. Out at the
    # tub's side rail it ran through the seat, the rockers and the rear
    # bulkhead instead. The one lane through a cockpit this tight is low and
    # inboard: under the seat pan, which bottoms at z 214, and inboard of it,
    # which begins at y 132.
    # It leaves the battery forward. It used to go 180 mm aft first and
    # double back, a hairpin a 32 mm bundle folded through itself on; then
    # it went 160 mm aft into the battery's own case before turning forward.
    # Under the seat it is low enough to clear the pan, which comes down to
    # z 178 at the front now the driver's hips sit there, and in the footwell
    # it passes outboard of the pedal box and under the driver's heels.
    PT = spec.POWERTRAIN
    spine = [(PT["battery_x"] - PT["battery"][0] / 2 - 4.0, 60.0,
              PT["battery_z"]),
             (1990.0, 112.0, 160.0),
             (1400.0, 140.0, 156.0),
             (T["cockpit_x0"], 100.0, 192.0),
             (900.0, 150.0, 180.0),
             (770.0, 150.0, 215.0),
             (T["x_front"] + 40.0, 60.0, 300.0)]
    # A loom is a taped bundle, so it is fattest where the most circuits are
    # still in it -- at the battery -- and thins as branches leave. Drawing it
    # at one diameter end to end says every circuit runs the whole length.
    grow = [1.00, 0.90, 0.80, 0.72, 0.62, 0.56, 0.52]
    for sy in (1.0, -1.0):
        path = [(px, sy * py, pz) for (px, py, pz) in spine]
        dense = mesh.smooth_path(path, 8)
        radii = []
        for i in range(len(dense)):
            f = i / (len(dense) - 1) * (len(grow) - 1)
            k = min(int(f), len(grow) - 2)
            radii.append(SV["loom_r"] * (grow[k] + (grow[k + 1] - grow[k]) * (f - k)))
        runs.append(mesh.pipe(dense, radii, 14))
        # tape wraps: the bundle is taped at intervals, and the tape stands
        # proud of the bundle
        for j in range(SV["loom_ties"]):
            i = int((j + 0.5) / SV["loom_ties"] * (len(dense) - 2)) + 1
            d = tuple(dense[i + 1][k] - dense[i - 1][k] for k in range(3))
            tv, tf = mesh.revolve_closed(
                [(-7.0, 0.0), (-7.0, radii[i] + 1.6), (7.0, radii[i] + 1.6),
                 (7.0, 0.0)], 14)
            runs.append((shapes.orient(tv, dense[i], d), tf))
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        # it stops inboard of the brake duct fence rather than through it
        branch = mesh.smooth_path(
            [(x - 90.0, sgn * 130.0, 340.0), (x - 20.0, sgn * 210.0, 330.0),
             (x + 30.0, y * 0.52, od / 2 + 120.0),
             (x + 10.0, y * 0.64, od / 2 + 86.0)], 7)
        runs.append(mesh.pipe(branch, 7.0, 10))
        d = tuple(branch[-1][k] - branch[-2][k] for k in range(3))
        cv, cf = shapes.connector(0.0, 0.0, 0.0, 30.0, 22.0, 16.0, pins=4)
        runs.append((shapes.orient(cv, branch[-1], d), cf))
    out["wiring_loom"] = mesh.join(*runs)

    # Outboard of the fuel cell, not inside it. At y 150 they were wholly
    # within the bladder -- the electronics were swimming in the fuel.
    # On top of the fuel cell, under the engine cover: the only place in
    # this bay that is neither bladder nor radiator. At y 150 they were in
    # the fuel; at y 288 they were in the radiator core.
    # standing on the cell's lid
    fz = (spec.POWERTRAIN["fuel_z"] + spec.POWERTRAIN["fuel"][2] / 2
          + 40.0)
    out["control_boxes"] = mesh.join(
        shapes.finned_case(2500.0, 118.0, fz, 180.0, 120.0, 80.0,
                           n_fins=7, fin_h=6.0, fin_t=3.0, r=12.0),
        shapes.finned_case(2500.0, -118.0, fz, 180.0, 120.0, 80.0,
                           n_fins=7, fin_h=6.0, fin_t=3.0, r=12.0))
    return out


def _strap(path, normals, width, thick=5.0):
    """A flat belt along `path`, lying on the surface whose outward normal
    at each point is given: `width` across, `thick` off the surface."""
    # three stations a segment, so the belt bends over the body rather than
    # cutting a straight chord through it
    dense, dn = [], []
    for i in range(len(path) - 1):
        for k in range(3):
            f = k / 3.0
            dense.append(tuple(path[i][j] + (path[i + 1][j] - path[i][j]) * f
                               for j in range(3)))
            dn.append(mesh._normalise(tuple(
                normals[i][j] + (normals[i + 1][j] - normals[i][j]) * f
                for j in range(3))))
    dense.append(path[-1])
    dn.append(normals[-1])
    path, normals = dense, dn
    n = len(path)
    verts = []
    for i in range(n):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, n - 1)]
        t = mesh._normalise(tuple(b[k] - a[k] for k in range(3)))
        nn = normals[i]
        w = mesh._normalise(mesh._cross(t, nn))
        p = path[i]
        for (sw, sn) in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
            verts.append(tuple(p[k] + sw * w[k] * width / 2
                               + sn * nn[k] * thick for k in range(3)))
    faces = []
    for i in range(n - 1):
        a, b = i * 4, (i + 1) * 4
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((a + k, a + k2, b + k2, b + k))
    faces.append((3, 2, 1, 0))
    faces.append(tuple(range((n - 1) * 4, n * 4)))
    return verts, faces


def _cockpit():
    """A driver sits in this. Seat, belts, wheel, dash, extinguisher."""
    out = {}
    cx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2

    # Six-point harness, laid on the driver. The belts were four flat boxes
    # at heights picked for a driver who sat upright further aft: the lap
    # belts ran 55 mm through his hips and the buckle 69 mm into his belly.
    # Now each belt is a strap along the surface of his torso
    # (detail.chest_point): the shoulder belts come out of the seat back
    # behind him, over the HANS collar and down his chest; the lap belts
    # come up from the sides of the bucket over his hips; the crotch strap
    # comes up between his legs; all four meet at the buckle.
    cp = detail.chest_point
    belts = []
    t_b = 0.82
    for sgn in (-1.0, 1.0):
        y = sgn * 92.0
        path = [(1925.0, y, 420.0), (1935.0, y, 510.0), (1915.0, y, 566.0),
                (1878.0, y * 1.08, 598.0), (1810.0, y * 1.20, 606.0),
                (1750.0, y * 1.32, 598.0)]
        norms = [(1.0, 0.0, 0.0), (0.84, 0.0, 0.54), (0.5, 0.0, 0.87),
                 (0.0, 0.0, 1.0), (0.0, 0.0, 1.0), (-0.3, 0.0, 0.95)]
        for (t, yy) in ((0.20, 92.0), (0.40, 76.0), (0.60, 58.0),
                        (t_b - 0.05, 34.0)):
            p_, n_ = cp(t, sgn * yy, 7.0)
            path.append(p_)
            norms.append(n_)
        belts.append(_strap(path, norms, 50.0))
        # lap belt: from the bucket's side wall, over the hip
        # it comes up outboard of the thigh and over its root
        path = [(1540.0, sgn * 184.0, 300.0), (1505.0, sgn * 160.0, 392.0)]
        norms = [(0.0, -sgn, 0.0), (0.3, 0.0, 0.95)]
        for (t, yy, lift) in ((0.95, 110.0, 12.0), (0.88, 60.0, 9.0)):
            p_, n_ = cp(t, sgn * yy, lift)
            path.append(p_)
            norms.append(n_)
        belts.append(_strap(path, norms, 50.0))
    # crotch strap: from the seat pan up between the legs
    path = [(1420.0, 0.0, 206.0), (1402.0, 0.0, 290.0)]
    norms = [(-1.0, 0.0, 0.0), (-0.8, 0.0, 0.6)]
    for t in (1.04, 0.94):
        p_, n_ = cp(t, 0.0, 7.0)
        path.append(p_)
        norms.append(n_)
    belts.append(_strap(path, norms, 44.0))
    out["harness"] = mesh.join(*belts)
    # the buckle, flat on his belly where the six belts meet
    c, n_ = cp(t_b, 0.0, 16.0)
    u = (n_[2], 0.0, -n_[0])
    bv, bf = shapes.rounded_box(0.0, 0.0, 0.0, 90.0, 110.0, 26.0, 8.0)
    out["harness_buckle"] = ([(c[0] + px * u[0] + pz * n_[0], py,
                               c[2] + px * u[2] + pz * n_[2])
                              for (px, py, pz) in bv], bf)

    # The steering wheel used to be built here as well as in chassis.py: two
    # wheels 30 mm apart in the same cockpit, plus a second display and a
    # second set of shift paddles, filed under three different collections.
    # The surviving wheel is `chassis._wheel`, which carries its own display,
    # rotaries and paddles because they are all part of the wheel.

    # Under the front of the cockpit opening, not through it. At z 540-660
    # the dash stood 42 mm proud of the body top where the opening is still
    # closing to its point, with the coaming lip running 23 mm into it; the
    # opening's rim is at z 596-624 over the dash's length, so the dash
    # tops out at 578, and the driver reads it through the opening under
    # the wheel.
    out["dash"] = shapes.rounded_box(T["cockpit_x0"] + 30.0, 0.0, 528.0,
                                     70.0, 300.0, 100.0, 18.0, draft=4.0)
    # A bottle with domed ends, a valve head, the discharge union and the
    # two straps holding it into the tub.
    ext = [mesh.revolve_closed(
        [(0.0, 0.0), (8.0, 0.0), (16.0, 30.0), (24.0, 44.0), (32.0, 52.0),
         (218.0, 52.0), (228.0, 46.0), (236.0, 32.0), (242.0, 20.0),
         (250.0, 0.0), (256.0, 0.0), (248.0, 24.0), (240.0, 40.0),
         (228.0, 50.0), (26.0, 50.0), (14.0, 40.0), (6.0, 24.0)], 34)]
    hv, hf = mesh.revolve_closed(
        [(0.0, 0.0), (46.0, 0.0), (46.0, 13.0), (40.0, 16.0),
         (30.0, 16.0), (30.0, 22.0), (16.0, 22.0), (16.0, 17.0),
         (0.0, 17.0)], 24)
    ext.append(([(px + 250.0, py, pz) for (px, py, pz) in hv], hf))
    for px in (60.0, 190.0):
        ext.append(mesh.ring_torus(px, 55.0, 4.5, 30, 8))
    v, f = mesh.join(*ext)
    out["extinguisher"] = ([(px + cx + 180.0, py + 150.0, pz + 260.0)
                            for (px, py, pz) in v], f)
    out["drink_bottle"] = shapes.rounded_box(cx + 260.0, -150.0, 280.0,
                                             150.0, 90.0, 90.0, 24.0)
    return out


def _squircle(x, hw, z0, z1, n, p=4.0):
    """A rounded-square loop in the y-z plane at x, in body_section's order:
    from +y, up over the top and round."""
    zc, hh = (z0 + z1) / 2, (z1 - z0) / 2
    e = 2.0 / p
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        out.append((x, hw * math.copysign(abs(ca) ** e, ca),
                    zc + hh * math.copysign(abs(sa) ** e, sa)))
    return out


def _survival_cell():
    """Bulkheads, side intrusion panels and the roll structure.

    The tub is a single moulding in the model, which is right, but it has
    hard points: the bulkheads the suspension and the engine bolt to.
    """
    out = {}
    for name, x in (("front", T["x_front"]), ("dash", T["cockpit_x0"]),
                    ("rear", T["cockpit_x1"]), ("engine", T["x_rear"])):
        # A bulkhead is a moulded ring frame with a rolled flange each side,
        # not a flat washer: the flange is what gives it out-of-plane
        # stiffness, and without it a 9 mm-thick ring would fold the first
        # time the suspension loaded it.
        # The frame needs real width. At inset 8 and 10 the band between the
        # outer edge and the aperture was 2 mm, so the 17 mm lightening-hole
        # eyelets centred on it stood 8 mm outside a body surface only 9 mm
        # away -- all four bulkheads were poking through the car.
        if name == "engine":
            # The engine bulkhead is the face the engine bolts to, sized to
            # the block's front rather than to the bodywork: this far back
            # the body section takes in the sidepods and the airbox, and a
            # frame drawn round it stood in both.
            ring = _squircle(x, 214.0, 64.0, 540.0, 72)
            inner = _squircle(x, 166.0, 112.0, 492.0, 72)
        else:
            ring = chassis.body_section(x, inset=8.0, segments=72)
            inner = chassis.body_section(x, inset=56.0, segments=72)
        n = len(ring)
        verts = ([(p[0] - 9.0, p[1], p[2]) for p in ring]
                 + [(p[0] + 9.0, p[1], p[2]) for p in ring]
                 + [(p[0] - 9.0, p[1], p[2]) for p in inner]
                 + [(p[0] + 9.0, p[1], p[2]) for p in inner])
        faces = []
        o_f, o_b, i_f, i_b = 0, n, 2 * n, 3 * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((o_f + j, o_f + j2, i_f + j2, i_f + j))
            faces.append((o_b + j, i_b + j, i_b + j2, o_b + j2))
            # The two RIMS, not a radial wall at every station. A wall at each
            # j is a face inside the frame and leaves the outer and inner
            # edges with one face on them: 576 of the ring's 4,992 edges.
            faces.append((o_f + j, o_b + j, o_b + j2, o_f + j2))
            faces.append((i_f + j, i_f + j2, i_b + j2, i_b + j))
        # the return flange round the inner aperture, and the lightening
        # holes between it and the outer edge
        parts = [(verts, faces)]
        for j in range(0, n, max(1, n // 14)):
            p0 = inner[j]
            p1 = ring[j]
            cx = (p0[0] + p1[0]) / 2
            cy = (p0[1] + p1[1]) / 2
            cz = (p0[2] + p1[2]) / 2
            hv, hf = mesh.revolve_closed(
                [(-11.0, 13.0), (11.0, 13.0), (11.0, 17.0), (-11.0, 17.0)], 18)
            parts.append(([(px + cx, py + cy, pz + cz)
                           for (px, py, pz) in hv], hf))
        fl = []
        for j in range(n):
            p0 = inner[j]
            d = math.hypot(p0[1], p0[2]) or 1.0
            ny, nz = p0[1] / d, p0[2] / d
            fl.append([(p0[0] - 9.0, p0[1], p0[2]),
                       (p0[0] - 24.0, p0[1] - ny * 9.0, p0[2] - nz * 9.0),
                       (p0[0] - 24.0, p0[1] - ny * 18.0, p0[2] - nz * 18.0),
                       (p0[0] - 9.0, p0[1] - ny * 14.0, p0[2] - nz * 14.0)])
        # One ring of stations swept round, not a fresh set of eight vertices
        # per segment. Built segment by segment, every edge along the sweep
        # belongs to one quad only and the flange is a sheet rather than a
        # solid -- 1,152 of its 5,280 edges, on all four bulkheads.
        fv = [p for station in fl for p in station]
        ff = []
        for j in range(n):
            b0, b1 = j * 4, ((j + 1) % n) * 4
            for k in range(4):
                k2 = (k + 1) % 4
                ff.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
        parts.append((fv, ff))
        out[f"bulkhead_{name}"] = mesh.join(*parts)

    # Set from the tub's own section at this station, so the panels are
    # inside the flank rather than 11 mm through it.
    cx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2
    hw = max(abs(p[1]) for p in chassis.body_section(cx, segments=48))
    panels = []
    for sgn in (-1.0, 1.0):
        panels.append(shapes.rounded_box(
            cx, sgn * (hw - 24.0), 420.0,
            T["cockpit_x1"] - T["cockpit_x0"], 18.0, 260.0, 20.0))
    out["side_intrusion"] = mesh.join(*panels)
    return out


def _pit_hardware():
    """What gets handled every stop: wheel guns' sockets, jack sockets, the
    starter socket, the fuel coupling, tyre-temperature sensors."""
    out = {}
    SV = spec.SERVICE
    socks = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        # Recessed into the wheel cover, where a gun socket lives. It used
        # to start 2 mm proud of the tyre and stick out 22 mm further, which
        # made the pit crew's sockets the widest objects on the car and put
        # it over the legal width.
        y_out = abs(y) + w * 0.5 - 42.0
        L = SV["gun_len"]
        R = SV["gun_bore_r"]

        def place(v):
            return [(pz + x, sgn * (y_out + px), py + od / 2)
                    for (px, py, pz) in v]

        def lathe(profile, seg=36):
            v, f = mesh.revolve_closed(list(profile), seg)
            return (place(v), f)

        parts = []
        # the bezel: a funnel in the wheel cover, rolled at the mouth so a
        # gun that arrives off-centre is pushed onto the axis rather than
        # bouncing off the rim
        parts.append(lathe([
            (L, R + 16.0), (L, R + 3.0), (L - 5.0, R - 1.0),
            (L - 14.0, R - 3.0), (4.0, R - 3.0), (0.0, R + 2.0),
            (0.0, R + 16.0)]))
        # the captive nut: the thing the gun actually turns
        parts.append(lathe([
            (2.0, 0.0), (2.0, R - 10.0), (6.0, R - 6.0), (16.0, R - 6.0),
            (20.0, R - 11.0), (20.0, 14.0), (2.0, 14.0)], 30))
        # its drive lugs -- this is the interface, and what makes the gun
        # socket a socket rather than a cup
        lr = SV["gun_lug_r"]
        br = R - lr - 4.0
        for k in range(SV["gun_lugs"]):
            a = 2.0 * math.pi * k / SV["gun_lugs"]
            lv, lf = mesh.revolve_closed(
                [(18.0, 0.0), (18.0, lr), (L - 6.0, lr),
                 (L - 3.0, lr - 2.5), (L - 3.0, 0.0)], 12)
            parts.append((place([(px, py + br * math.cos(a),
                                  pz + br * math.sin(a))
                                 for (px, py, pz) in lv]), lf))
        # the circlip that stops the nut leaving with the wheel
        cv, cf = mesh.ring_torus(L - 2.0, R - 7.0, 2.4, 30, 8)
        parts.append((place(cv), cf))
        # and the axle stub the nut screws onto, seen down the bore
        parts.append(lathe([
            (-14.0, 0.0), (-14.0, 15.0), (24.0, 15.0), (26.0, 12.0),
            (26.0, 0.0)], 20))
        socks.append(mesh.join(*parts))
    out["gun_sockets"] = mesh.join(*socks)

    # The starter socket.
    #
    # It was a 12-segment open revolve on a four-point profile -- 50 vertices,
    # the crudest object on the car -- standing in for the thing a mechanic
    # pushes a starter into. It is a bezel recessed into the crash structure,
    # a square drive down the middle of it, and the backing plate that takes
    # the torque into the gearbox casing.
    S = spec.SERVICE
    xg = spec.POWERTRAIN["gearbox_x"] + spec.POWERTRAIN["gearbox_len"]
    zg = spec.POWERTRAIN["gearbox_z"]
    sx = xg + 130.0
    parts = []

    def lathe_x(profile, cx, seg=26):
        v, f = mesh.revolve_closed(list(profile), seg)
        return ([(px + cx, py, pz + zg) for (px, py, pz) in v], f)

    # the funnel bezel, rolled over at the mouth so a socket self-centres
    parts.append(lathe_x([
        (0.0, S["starter_drive"] * 0.7), (6.0, S["starter_bezel_r"] - 4.0),
        (10.0, S["starter_bezel_r"]), (16.0, S["starter_bezel_r"] - 2.0),
        (16.0, S["starter_bezel_r"] - 8.0), (10.0, S["starter_bezel_r"] - 7.0),
        (6.0, S["starter_bezel_r"] - 11.0),
        (0.0, S["starter_drive"] * 0.7 + 4.0)], sx))
    # the square drive itself, four flats
    parts.append(lathe_x([
        (-4.0, 0.0), (-4.0, S["starter_drive"]), (54.0, S["starter_drive"]),
        (54.0, 0.0)], sx, seg=4))
    # the shaft back to the gearbox, and the backing plate
    parts.append(lathe_x([
        (54.0, 0.0), (54.0, S["starter_drive"] * 0.62),
        (128.0, S["starter_drive"] * 0.62), (128.0, 0.0)], sx - 128.0, seg=16))
    parts.append(shapes.rounded_box(sx - 122.0, 0.0, zg,
                                    12.0, 96.0, 96.0, r=8.0))
    for k in range(4):
        ang = math.pi / 2 * k + math.pi / 4
        parts.append(lathe_x([
            (0.0, 0.0), (14.0, 0.0), (14.0, 7.0), (0.0, 7.0)],
            sx - 128.0, seg=10))
        v, f = parts[-1]
        parts[-1] = ([(px, py + 36.0 * math.cos(ang), pz + 36.0 * math.sin(ang))
                      for (px, py, pz) in v], f)
    out["starter_socket"] = mesh.join(*parts)

    # above the radiator, not through its core
    out["fuel_coupling"] = mesh.join(
        shapes.rounded_box(1940.0, 296.0, 566.0, 120.0, 90.0, 90.0, 22.0),
        mesh.pipe([(1940.0, 296.0, 566.0),
                   (2140.0, 240.0, 520.0),
                   (spec.POWERTRAIN["fuel_x"], 150.0, 470.0)], 26.0, 10))

    sens = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        # An infrared tyre array is a row of lenses aimed across the tread,
        # because the temperature that matters is the difference between the
        # inner shoulder and the outer one -- one lens on a box tells you
        # nothing about how the car is using the tyre.
        # 0.55 of the tread width in, not 0.46: at 0.46 the array's outboard
        # face sat at the same station as the track rod's outer rod end.
        hx, hy, hz = x - od * 0.10, y - sgn * w * 0.55, od * 0.34
        parts = [shapes.rounded_box(hx, hy, hz, 40.0, 26.0, 20.0, 5.0)]
        for i in range(5):
            f = (i + 0.5) / 5
            lv, lf = mesh.revolve_closed(
                [(0.0, 0.0), (0.0, 6.0), (4.0, 6.0), (6.0, 4.2), (6.0, 0.0)],
                12)
            parts.append(([(pz + hx - 16.0 + 32.0 * f,
                            sgn * px + hy + sgn * 13.0, py + hz)
                           for (px, py, pz) in lv], lf))
        # the bracket that holds it off the duct, and the pigtail out of it
        parts.append(shapes.rounded_box(hx, hy - sgn * 16.0, hz + 2.0,
                                        16.0, 8.0, 26.0, 2.5))
        parts.append(shapes.rounded_box(hx, hy - sgn * 30.0, hz + 13.0,
                                        16.0, 24.0, 5.0, 2.0))
        tail = mesh.smooth_path(
            [(hx + 16.0, hy, hz - 6.0), (hx + 42.0, hy - sgn * 14.0, hz - 22.0),
             (hx + 54.0, hy - sgn * 40.0, hz - 30.0)], 6)
        parts.append(mesh.pipe(tail, 4.0, 10))
        d = tuple(tail[-1][k] - tail[-2][k] for k in range(3))
        cv, cf = shapes.connector(0.0, 0.0, 0.0, 22.0, 16.0, 12.0, pins=4)
        parts.append((shapes.orient(cv, tail[-1], d), cf))
        sens.append(mesh.join(*parts))
    out["tyre_sensors"] = mesh.join(*sens)
    return out


def _cooling_exits():
    """Louvre banks over the sidepod and engine cover exits, and the exit
    ducts behind them. Air that goes in has to come out."""
    out = {}
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        banks = []
        for (x0, x1, fz, n) in ((2700.0, 3200.0, 0.78, 8),
                                (2800.0, 3240.0, 0.52, 7)):
            for i in range(n):
                f = (i + 0.5) / n
                x = x0 + (x1 - x0) * f
                p = chassis.sidepod_point(x, sgn * 1.0, fz, 4.0)
                banks.append(shapes.rounded_box(p[0], p[1], p[2],
                                                120.0, 10.0, 26.0, 3.0))
        out[f"exit_louvres_{tag}"] = mesh.join(*banks)
    return out
