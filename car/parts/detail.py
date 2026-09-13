"""Body detail: cooling exits, wing pylons, suspension fairings, the crash
structures, and the driver.

These are the parts that separate a shape from a car. Each one is placed on
the actual body surface via `chassis.surface_point` / `chassis.sidepod_point`
rather than at a guessed offset, so nothing floats above the skin or sinks
into it when the section changes along the car.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import chassis, common, wheels

BD = spec.BODY_DETAIL
FW = spec.FRONT_WING
S = spec.SUSP
W = spec.WHEEL
F = spec.FLOOR


def build():
    out = {}
    out.update(_gills())
    out.update(_nose())
    out.update(_crash_structures())
    out.update(_airbox())
    out.update(_driver())
    out.update(_service())
    return out


# --------------------------------------------------------------------------

def _gills():
    """Louvre banks venting the radiators and the engine bay.

    Air that goes into a sidepod has to come out somewhere; on a real car that
    exit is a bank of louvres, and it is one of the most recognisable pieces
    of surface detail there is.
    """
    parts = []
    for (x0, x1, ang, n, length, h) in BD["gills"]:
        for mirror in (1.0, -1.0):
            a = ang if mirror > 0 else 180.0 - ang
            for k in range(n):
                f = k / max(n - 1, 1)
                x = x0 + (x1 - x0) * f
                px, py, pz = chassis.surface_point(x, a, -4.0)
                v, fc = shapes.rounded_box(0.0, 0.0, 0.0, length, 10.0, h)
                # cant each blade so it stands off the skin at its trailing edge
                t = math.radians(22.0)
                ct, st = math.cos(t), math.sin(t)
                rot = [(vx * ct - vz * st, vy, vx * st + vz * ct)
                       for (vx, vy, vz) in v]
                parts.append(([(px + vx, py + vy, pz + vz)
                               for (vx, vy, vz) in rot], fc))

    pod = []
    for (x0, x1, f_z, n, length, h) in BD["sidepod_gills"]:
        for sgn in (-1.0, 1.0):
            for k in range(n):
                f = k / max(n - 1, 1)
                x = x0 + (x1 - x0) * f
                px, py, pz = chassis.sidepod_point(x, sgn * 1.0, f_z, -6.0)
                v, fc = shapes.rounded_box(0.0, 0.0, 0.0, length, 12.0, h)
                t = math.radians(20.0)
                ct, st = math.cos(t), math.sin(t)
                rot = [(vx * ct - vz * st, vy, vx * st + vz * ct)
                       for (vx, vy, vz) in v]
                pod.append(([(px + vx, py + vy, pz + vz)
                             for (vx, vy, vz) in rot], fc))
    return {"gills": mesh.join(*parts),
            "sidepod_gills": mesh.join(*pod)}


def _nose():
    """The pylons that carry the front wing, and the cape under the nose.

    A front wing bolted to nothing is the giveaway that a model was never
    thought through. These two pylons are what hold it, and the cape is the
    sculpted underside that turns the flow outboard around the front tyre.
    """
    out = {}
    px_x = BD["nose_pylon_x"]
    pylons = []
    for sgn in (-1.0, 1.0):
        y = sgn * BD["nose_pylon_y"]
        top = chassis.surface_point(px_x + 190.0, -90.0)
        pylons.append(mesh.pipe(
            [(FW["x"] + 140.0, y, FW["z"] + 30.0),
             (px_x + 120.0, y, (FW["z"] + top[2]) / 2),
             (px_x + 190.0, y * 0.7, top[2] + 20.0)],
            BD["nose_pylon_t"], 10))
    out["nose_pylons"] = mesh.join(*pylons)

    capes = []
    for sgn in (-1.0, 1.0):
        rows = []
        for f in (0.0, 0.4, 0.75, 1.0):
            x = BD["cape_x0"] + (BD["cape_x1"] - BD["cape_x0"]) * f
            under = chassis.surface_point(x, -90.0)
            row = []
            for g in (0.0, 0.45, 1.0):
                y = sgn * BD["cape_y"] * g * (0.5 + 0.5 * f)
                row.append((x, y, under[2] + 8.0 - 34.0 * g * (0.4 + 0.6 * f)))
            rows.append(row)
        capes.append(_grid_skin(rows, 9.0))
    out["nose_cape"] = mesh.join(*capes)
    return out


def _grid_skin(rows, t):
    """Give a grid of stations thickness in z and close it into a solid."""
    nr, nc = len(rows), len(rows[0])
    lo = [(x, y, z - t / 2) for row in rows for (x, y, z) in row]
    hi = [(x, y, z + t / 2) for row in rows for (x, y, z) in row]
    verts = lo + hi
    off = len(lo)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i * nc + j
            faces.append((k, k + nc, k + nc + 1, k + 1))
            faces.append((off + k, off + k + 1, off + k + nc + 1,
                          off + k + nc))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i * nc + j
            faces.append((k, k + nc, off + k + nc, off + k) if j == 0
                         else (k + nc, k, off + k, off + k + nc))
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i * nc + j
            faces.append((k + 1, k, off + k, off + k + 1) if i == 0
                         else (k, k + 1, off + k + 1, off + k))
    return verts, faces


def faired_leg(p0, p1, sect, chord):
    """Sweep an aerofoil section along a suspension leg, chord streamwise.

    Every suspension member on a modern car is a wing section: a round tube at
    300 km/h is pure drag and produces nothing. suspension.py builds its arms
    with this rather than with pipes.
    """
    verts = []
    for p in (p0, p1):
        for (u, v) in sect:
            verts.append((p[0] + (u - 0.35) * chord, p[1], p[2] + v * chord))
    n = len(sect)
    faces = []
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, i2, n + i2, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    return verts, faces


def _crash_structures():
    """Side impact tubes and the rear crash box behind the gearbox."""
    out = {}
    sides = []
    for sgn in (-1.0, 1.0):
        for zz in (250.0, 420.0):
            # inside the sidepod flank, allowing for the tube's own radius
            a = chassis.sidepod_point(1740.0, sgn * 1.0, 0.0,
                                      -BD["crash_r"])
            b = chassis.sidepod_point(1980.0, sgn * 0.94, 0.0,
                                      -BD["crash_r"])
            sides.append(mesh.pipe(
                [(a[0], a[1] * 0.55, zz), (b[0], b[1], zz)],
                BD["crash_r"], 12))
    out["side_impact"] = mesh.join(*sides)

    x = spec.POWERTRAIN["gearbox_x"] + spec.POWERTRAIN["gearbox_len"]
    z = spec.POWERTRAIN["gearbox_z"]
    # tapered to stay inside the engine cover, which narrows faster than it
    out["crash_structure"] = mesh.revolve_open(
        [(x, 118.0), (x + 200.0, 92.0), (x + 340.0, 58.0)],
        18, cap_start=True, cap_end=True)
    out["crash_structure"] = (
        [(px, py, pz + z) for (px, py, pz) in out["crash_structure"][0]],
        out["crash_structure"][1])
    return out


def _airbox():
    """Roll-hoop air intake feeding the engine, and its plenum duct."""
    out = {}
    x = BD["airbox_x"]
    w, h = BD["airbox_w"], BD["airbox_h"]
    L = BD["airbox_len"]
    top = chassis.surface_point(x, 90.0)
    # The scoop stands proud at the roll hoop and is swallowed by the engine
    # cover within its own length -- it is an intake, not a second fuselage.
    rows = []
    for (dx, sw, sh, dz) in ((-40.0, w, h, 24.0),
                             (L * 0.22, w * 0.90, h * 0.82, 8.0),
                             (L * 0.62, w * 0.62, h * 0.46, -40.0),
                             (L, w * 0.34, h * 0.20, -96.0)):
        ring = []
        for i in range(16):
            a = 2 * math.pi * i / 16
            p = 2.0 / 2.8
            ca, sa = math.cos(a), math.sin(a)
            ring.append((x + dx,
                         sw * math.copysign(abs(ca) ** p, ca),
                         top[2] - 20.0 + dz
                         + sh * math.copysign(abs(sa) ** p, sa)))
        rows.append(ring)
    out["airbox"] = common.loft(rows)
    return out


def _driver():
    """A driver in the seat. Everything above the coaming is what sets the
    scale of a single-seater; without it the cockpit reads as a slot."""
    out = {}
    D = BD["driver"]
    parts = []
    # helmet
    hv, hf = mesh.revolve_closed(
        [(-D["helmet_r"] * 0.86, 0.0), (-D["helmet_r"] * 0.80, D["helmet_r"] * 0.62),
         (-D["helmet_r"] * 0.30, D["helmet_r"] * 0.96),
         (D["helmet_r"] * 0.30, D["helmet_r"] * 0.96),
         (D["helmet_r"] * 0.74, D["helmet_r"] * 0.70),
         (D["helmet_r"] * 0.90, 0.0)], 22)
    parts.append(([(pz + D["helmet_x"], px, py + D["helmet_z"])
                   for (px, py, pz) in hv], hf))
    out["helmet"] = mesh.join(*parts)

    body = []
    body.append(shapes.rounded_box(D["shoulder_x"], 0.0, D["helmet_z"] - 190.0,
                         230.0, 2 * D["shoulder_w"], 200.0))
    for sgn in (-1.0, 1.0):
        body.append(mesh.pipe(
            [(D["shoulder_x"] - 40.0, sgn * D["shoulder_w"] * 0.8,
              D["helmet_z"] - 170.0),
             (1560.0, sgn * 150.0, D["helmet_z"] - 230.0),
             (1420.0, sgn * 110.0, D["helmet_z"] - 240.0)],
            D["arm_r"], 8))
        body.append(mesh.pipe(
            [(1780.0, sgn * 120.0, 330.0),
             (D["knee_x"], sgn * 140.0, 430.0),
             (D["foot_x"], sgn * 110.0, 380.0)],
            D["leg_r"], 8))
    out["driver"] = mesh.join(*body)
    return out


def _service():
    """Jack points, tow hooks and the wear plank -- the small hardware that
    tells you this is a car that gets worked on between sessions."""
    out = {}
    parts = []
    for x in (420.0, spec.POWERTRAIN["gearbox_x"] + 460.0):
        under = chassis.surface_point(x, -90.0)
        v, f = mesh.cylinder(0.0, 130.0, BD["jack_r"], 12)
        parts.append(([(pz + x, py, px + under[2] - 40.0)
                       for (px, py, pz) in v], f))
    out["jack_points"] = mesh.join(*parts)

    hooks = []
    for (x, z) in ((260.0, BD["tow_z_front"]),
                   (spec.POWERTRAIN["gearbox_x"] + 560.0, BD["tow_z_rear"])):
        v, f = mesh.ring_torus(x, 74.0, BD["tow_r"], 16, 8)
        hooks.append(([(px, py, pz + z) for (px, py, pz) in v], f))
    out["tow_hooks"] = mesh.join(*hooks)
    return out
