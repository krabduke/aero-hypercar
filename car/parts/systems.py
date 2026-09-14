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
from parts import wheels, chassis, floor

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

        # the scoop: a shaped inlet facing forward, inboard of the tyre
        out[f"bduct_inlet_{tag}"] = shapes.rounded_box(
            x - r * 0.92, inb, z - r * 0.26, 90.0, BD["width"],
            BD["inlet_h"], 16.0, draft=3.0)
        # the duct carrying it back to the drum
        # the duct narrows as it goes back, because the drum needs velocity
        # at the disc, not volume in the pipe
        out[f"bduct_pipe_{tag}"] = mesh.pipe(
            [(x - r * 0.86, inb, z - r * 0.22),
             (x - r * 0.58, inb, z - r * 0.16),
             (x - r * 0.30, inb, z - r * 0.05),
             (x - r * 0.08, inb, z - r * 0.01),
             (x + r * 0.10, inb, z)],
            [BD["width"] * 0.42, BD["width"] * 0.39, BD["width"] * 0.35,
             BD["width"] * 0.31, BD["width"] * 0.28], 22, subdiv=3)
        # the drum around the disc, which is what actually directs the air
        # The drum is a scroll: air enters at one point and has to be
        # distributed round the whole disc, so it is deeper where the feed
        # comes in and it is finned inside to spread the flow. As a plain
        # annulus it directed nothing anywhere.
        w = BD["width"]
        drum = [shapes.volute(0.0, r * 0.60, r * 0.80, w * 0.16, w * 0.30,
                              seg=44, sect=14)]
        drum.append(mesh.revolve_closed(
            [(-w * 0.32, r * 0.50), (-w * 0.24, r * 0.50),
             (-w * 0.24, r * 0.88), (-w * 0.32, r * 0.88)], 40))
        for k in range(9):
            a = 2 * math.pi * k / 9
            fv, ff = mesh.box(0.0, 0.0, 0.0, w * 0.34, 4.0, r * 0.16)
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
        # the fence standing the whole assembly off the tyre
        # A fence cut to the shape of the job: it wraps the front of the
        # drum, is cut away behind the axle line where the wheel rim would
        # foul it, and rolls inboard at the trailing edge to keep the tyre
        # squirt out of the floor.
        fy = inb - sgn * BD["width"] * 0.56
        prof = shapes.panel_outline(
            [(x - r * 0.80, z - r * 0.62), (x + r * 0.44, z - r * 0.66),
             (x + r * 0.74, z - r * 0.18), (x + r * 0.60, z + r * 0.34),
             (x + r * 0.02, z + r * 0.50), (x - r * 0.66, z + r * 0.26),
             (x - r * 0.86, z - r * 0.20)], subdiv=4)
        out[f"bduct_fence_{tag}"] = shapes.shaped_panel(
            prof, fy, 8.0, rim_seg=5,
            bow=lambda fx, fz, sgn=sgn: -sgn * 26.0 * max(0.0, fx - 0.45) ** 2
                / 0.30)
        # cooling exits on the outboard face
        vanes = []
        for k in range(5):
            a = math.pi * (0.2 + 0.6 * k / 4)
            vanes.append(shapes.rounded_box(
                x + r * 0.82 * math.cos(a), inb + sgn * BD["width"] * 0.30,
                z + r * 0.82 * math.sin(a), 46.0, 6.0, 16.0, 2.5))
        out[f"bduct_vanes_{tag}"] = mesh.join(*vanes)
    return out


def _hydraulics():
    """Brake lines to every corner and the master cylinders that feed them."""
    out = {}
    lines = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        lines.append(mesh.pipe(
            [(spec.FRONT_AXLE_X + 60.0, sgn * 90.0, 300.0),
             (x * 0.55 + spec.FRONT_AXLE_X * 0.45, sgn * 170.0, 260.0),
             (x, y * 0.78, od / 2 + W["caliper_r"] * 0.8)], 8.0, 8))
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
        parts.append(([(pz + 14.0, py, -px - 22.0)
                       for (px, py, pz) in uv], uf))
        parts.append(shapes.rod_end((160.0, 0.0, 0.0), (1.0, 0.0, 0.0), 10.0))
        v, f = mesh.join(*parts)
        cyl.append(([(px + spec.FRONT_AXLE_X + 40.0, py + sgn * 86.0,
                      pz + 330.0) for (px, py, pz) in v], f))
    out["master_cylinders"] = mesh.join(*cyl)

    # The pedals go under the driver's feet, which are behind the front axle
    # line -- that is a survival-cell rule, not a styling choice. They used to
    # sit at x 495, which is 405 mm AHEAD of the front axle and 484 mm from
    # the nearest part of the driver.
    fx = spec.BODY_DETAIL["driver"]["foot_x"]
    out["pedal_box"] = mesh.join(
        shapes.rounded_box(fx + 10.0, 0.0, 250.0, 210.0, 260.0, 40.0, 10.0),
        shapes.rounded_box(fx - 10.0, -78.0, 330.0, 34.0, 60.0, 170.0, 8.0),
        shapes.rounded_box(fx - 10.0, 78.0, 330.0, 34.0, 60.0, 170.0, 8.0))
    return out


def _electrical():
    """The loom, and the boxes it connects. Current has to get from the
    battery at the back to the dash at the front somehow."""
    out = {}
    runs = []
    spine = [(spec.POWERTRAIN["battery_x"], 60.0, 210.0),
             (2600.0, 90.0, 300.0), (2100.0, 96.0, 420.0),
             (T["cockpit_x0"], 70.0, 470.0), (T["x_front"] + 40.0, 40.0, 380.0)]
    runs.append(mesh.pipe(spine, 19.0, 10))
    runs.append(mesh.pipe([(p[0], -p[1], p[2]) for p in spine], 19.0, 10))
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        runs.append(mesh.pipe(
            [(x, sgn * 150.0, 330.0), (x, y * 0.8, od / 2 + 60.0)], 7.0, 6))
    out["wiring_loom"] = mesh.join(*runs)

    out["control_boxes"] = mesh.join(
        shapes.finned_case(2500.0, 150.0, 330.0, 180.0, 120.0, 80.0,
                           n_fins=7, fin_h=6.0, fin_t=3.0, r=12.0),
        shapes.finned_case(2500.0, -150.0, 330.0, 180.0, 120.0, 80.0,
                           n_fins=7, fin_h=6.0, fin_t=3.0, r=12.0))
    return out


def _cockpit():
    """A driver sits in this. Seat, belts, wheel, dash, extinguisher."""
    out = {}
    cx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2

    # six-point harness
    belts = []
    for sgn in (-1.0, 1.0):
        belts.append(shapes.rounded_box(cx - 90.0, sgn * 95.0, 560.0,
                                        300.0, 62.0, 9.0, 3.0))     # shoulder
        belts.append(shapes.rounded_box(cx + 60.0, sgn * 130.0, 330.0,
                                        62.0, 220.0, 9.0, 3.0))     # lap
    belts.append(shapes.rounded_box(cx + 20.0, 0.0, 300.0, 200.0, 60.0, 9.0, 3.0))
    out["harness"] = mesh.join(*belts)
    out["harness_buckle"] = shapes.rounded_box(cx + 22.0, 0.0, 352.0,
                                               90.0, 110.0, 34.0, 8.0)

    # The steering wheel used to be built here as well as in chassis.py: two
    # wheels 30 mm apart in the same cockpit, plus a second display and a
    # second set of shift paddles, filed under three different collections.
    # The surviving wheel is `chassis._wheel`, which carries its own display,
    # rotaries and paddles because they are all part of the wheel.

    out["dash"] = shapes.rounded_box(T["cockpit_x0"] + 30.0, 0.0, 600.0,
                                     70.0, 300.0, 120.0, 18.0, draft=4.0)
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
            faces.append((o_f + j, i_f + j, i_b + j, o_b + j))
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
        fv, ff = [], []
        for j in range(n):
            j2 = (j + 1) % n
            base = len(fv)
            fv.extend(fl[j]); fv.extend(fl[j2])
            for k in range(4):
                k2 = (k + 1) % 4
                ff.append((base + k, base + k2, base + 4 + k2, base + 4 + k))
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
    socks = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        v, f = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 44.0), (22.0, 44.0), (22.0, 0.0)], 8,
            cap_start=True, cap_end=True)
        # Recessed into the wheel cover, where a gun socket lives. It used
        # to start 2 mm proud of the tyre and stick out 22 mm further, which
        # made the pit crew's sockets the widest objects on the car and put
        # it over the legal width.
        y_out = abs(y) + w * 0.5 - 42.0
        socks.append(([(pz + x, sgn * (y_out + px), py + od / 2)
                       for (px, py, pz) in v], f))
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

    out["fuel_coupling"] = mesh.join(
        shapes.rounded_box(2000.0, 300.0, 500.0, 120.0, 90.0, 90.0, 22.0),
        mesh.pipe([(2000.0, 300.0, 500.0),
                   (spec.POWERTRAIN["fuel_x"], 150.0, 400.0)], 26.0, 10))

    sens = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        sens.append(shapes.rounded_box(x - od * 0.10, y - sgn * w * 0.46,
                                       od * 0.34, 44.0, 30.0, 22.0, 6.0))
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
