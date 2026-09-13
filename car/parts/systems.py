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
        out[f"bduct_pipe_{tag}"] = mesh.pipe(
            [(x - r * 0.86, inb, z - r * 0.22),
             (x - r * 0.30, inb, z - r * 0.05),
             (x + r * 0.10, inb, z)], BD["width"] * 0.40, 12)
        # the drum around the disc, which is what actually directs the air
        dv, df = mesh.revolve_closed(
            [(-BD["width"] * 0.30, r * 0.52), (BD["width"] * 0.30, r * 0.52),
             (BD["width"] * 0.30, r * 0.82), (-BD["width"] * 0.30, r * 0.82)],
            26)
        out[f"bduct_drum_{tag}"] = (
            [(pz + x, px + inb, py + z) for (px, py, pz) in dv], df)
        # the fence standing the whole assembly off the tyre
        out[f"bduct_fence_{tag}"] = shapes.rounded_box(
            x, inb - sgn * BD["width"] * 0.56, z - r * 0.15,
            r * 1.5, 7.0, r * 1.1, 12.0)
        # cooling exits on the outboard face
        vanes = []
        for k in range(5):
            a = math.pi * (0.2 + 0.6 * k / 4)
            vanes.append(shapes.rounded_box(
                x + r * 0.55 * math.cos(a), inb + sgn * BD["width"] * 0.30,
                z + r * 0.55 * math.sin(a), 46.0, 6.0, 16.0, 2.5))
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
        cyl.append(mesh.revolve_open(
            [(0.0, 0.0), (0.0, 26.0), (150.0, 26.0), (150.0, 0.0)],
            14, cap_start=True, cap_end=True))
        v, f = cyl[-1]
        cyl[-1] = ([(px + spec.FRONT_AXLE_X + 40.0, py + sgn * 86.0, pz + 330.0)
                    for (px, py, pz) in v], f)
    out["master_cylinders"] = mesh.join(*cyl)

    out["pedal_box"] = mesh.join(
        shapes.rounded_box(T["x_front"] - 60.0, 0.0, 250.0, 130.0, 260.0, 40.0, 10.0),
        shapes.rounded_box(T["x_front"] - 30.0, -78.0, 330.0, 34.0, 60.0, 170.0, 8.0),
        shapes.rounded_box(T["x_front"] - 30.0, 78.0, 330.0, 34.0, 60.0, 170.0, 8.0))
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
    out["harness_buckle"] = shapes.rounded_box(cx - 10.0, 0.0, 380.0,
                                               90.0, 110.0, 34.0, 8.0)

    # steering wheel: a rim, a hub, paddles and a display
    rim = []
    for sgn in (-1.0, 1.0):
        rim.append(shapes.rounded_box(T["cockpit_x0"] + 130.0, sgn * 92.0, 600.0,
                                      34.0, 90.0, 130.0, 14.0))
    rim.append(shapes.rounded_box(T["cockpit_x0"] + 130.0, 0.0, 655.0,
                                  34.0, 190.0, 40.0, 12.0))
    out["steering_wheel"] = mesh.join(*rim)
    out["wheel_display"] = shapes.rounded_box(T["cockpit_x0"] + 146.0, 0.0, 600.0,
                                              14.0, 130.0, 60.0, 5.0)
    paddles = []
    for sgn in (-1.0, 1.0):
        paddles.append(shapes.rounded_box(T["cockpit_x0"] + 108.0, sgn * 84.0,
                                          566.0, 12.0, 46.0, 84.0, 4.0))
    out["shift_paddles"] = mesh.join(*paddles)

    out["dash"] = shapes.rounded_box(T["cockpit_x0"] + 40.0, 0.0, 610.0,
                                     70.0, 300.0, 120.0, 18.0, draft=4.0)
    out["extinguisher"] = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 52.0), (240.0, 52.0), (250.0, 24.0), (250.0, 0.0)],
        16, cap_start=True, cap_end=True)
    out["extinguisher"] = ([(px + cx + 180.0, py + 150.0, pz + 260.0)
                            for (px, py, pz) in out["extinguisher"][0]],
                           out["extinguisher"][1])
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
        ring = chassis.body_section(x, inset=8.0, segments=24)
        inner = chassis.body_section(x, inset=48.0, segments=24)
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
        out[f"bulkhead_{name}"] = (verts, faces)

    panels = []
    for sgn in (-1.0, 1.0):
        panels.append(shapes.rounded_box(
            (T["cockpit_x0"] + T["cockpit_x1"]) / 2, sgn * 250.0, 420.0,
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
        socks.append(([(pz + x, sgn * (abs(y) + w * 0.5) + px * sgn, py + od / 2)
                       for (px, py, pz) in v], f))
    out["gun_sockets"] = mesh.join(*socks)

    out["starter_socket"] = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 34.0), (90.0, 30.0), (90.0, 0.0)], 12,
        cap_start=True, cap_end=True)
    xg = spec.POWERTRAIN["gearbox_x"] + spec.POWERTRAIN["gearbox_len"]
    out["starter_socket"] = ([(px + xg + 60.0, py, pz + spec.POWERTRAIN["gearbox_z"])
                              for (px, py, pz) in out["starter_socket"][0]],
                             out["starter_socket"][1])

    out["fuel_coupling"] = mesh.join(
        shapes.rounded_box(2000.0, 300.0, 500.0, 120.0, 90.0, 90.0, 22.0),
        mesh.pipe([(2000.0, 300.0, 500.0),
                   (spec.POWERTRAIN["fuel_x"], 150.0, 400.0)], 26.0, 10))

    sens = []
    for (tag, x, y, w, od) in wheels.corners():
        sgn = 1.0 if y > 0 else -1.0
        sens.append(shapes.rounded_box(x - od * 0.42, y - sgn * w * 0.1,
                                       od / 2 + od * 0.40, 44.0, 26.0, 22.0, 6.0))
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
