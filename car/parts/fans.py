"""The fans. This is the part that makes the car what it is.

Two electrically driven fans pull air out of the sealed underfloor plenums.
Because they move a roughly fixed mass flow, the suction they generate barely
depends on road speed -- so unlike a wing, they still work in a hairpin.

The fan axis is vertical: the fans pull air up out of the floor and exhaust it
rearwards. Everything here is built in that frame. An earlier version built the
hub and shroud about z but arrayed the blades about x, so the blades formed a
disc in the wrong plane entirely -- they were pitched to blow along the car,
not through the floor.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
import airfoil

F = spec.FAN
E = spec.FAN_EXHAUST


def centres():
    """(tag, x, y, z, spin sign) for each fan.

    The two fans turn opposite ways. A single direction would leave a net yaw
    torque on the car every time the fan speed changed, which is the last thing
    you want mid-corner.
    """
    return [("l", F["x"], -F["y"], F["z"], 1.0),
            ("r", F["x"], F["y"], F["z"], -1.0)]


def pivots():
    """Parts that turn, and what they turn about: (point, axis).

    assemble.py moves each of these objects' mesh data onto its pivot and puts
    the pivot in the object's transform, so the exported glTF node rotates in
    place. Without it every part pivots about the world origin.
    """
    out = {}
    for (tag, cx, cy, cz, spin) in centres():
        out[f"fan_rotor_{tag}"] = ((cx, cy, cz), (0.0, 0.0, 1.0), spin,
                                   "spin")
    return out


def build():
    out = {}
    ducts, motors, stators = [], [], []
    for (tag, cx, cy, cz, spin) in centres():
        # shroud, with a bellmouth inlet lip so the flow does not separate off
        # a square edge on its way in
        ducts.append(_shroud(cx, cy, cz))

        # The fan is fed from the floor by `floor.floor_fan_throat_*`, a
        # hollow duct rising from the plenum just aft of the axle into the
        # shroud's bellmouth. There was a second one here: a 300 mm solid
        # bar from 620 mm ahead of the fan, through the gearbox, the rear
        # dampers, rockers, torsion bars and anti-roll bar and both
        # driveshafts, to the same bellmouth.

        out[f"fan_rotor_{tag}"] = _rotor(cx, cy, cz, spin)
        stators.append(_stators(cx, cy, cz, spin))
        out[f"fan_scroll_{tag}"] = _scroll(cx, cy, cz)
        out[f"fan_nozzle_{tag}"] = _nozzle(cx, cy, cz)

        # The motor.
        #
        # It was a solid cylinder -- one mesh.tube with a zero inner radius,
        # two stations, no features at all -- which is the single crudest
        # object on a car built entirely around what these two drive. A motor
        # of this size is a finned case between two end bells, with a terminal
        # block and feet it actually bolts down through.
        M = spec.FAN_MOTOR
        mz = cz + 128.0
        motors.append(_lathe_z(cx, cy, mz, [
            (-62.0, 0.0), (-62.0, M["bell_r"]), (-52.0, M["bell_r"]),
            (-46.0, M["bore_r"] * 2.1), (46.0, M["bore_r"] * 2.1),
            (52.0, M["bell_r"]), (62.0, M["bell_r"]), (62.0, 0.0),
        ], 30))
        # cooling fins round the case
        for k in range(M["fins"]):
            fz = -40.0 + 80.0 * (k + 0.5) / M["fins"]
            motors.append(_lathe_z(cx, cy, mz, [
                (fz - 2.2, M["bore_r"] * 2.1),
                (fz - 2.2, M["bore_r"] * 2.1 + M["fin_h"]),
                (fz + 2.2, M["bore_r"] * 2.1 + M["fin_h"]),
                (fz + 2.2, M["bore_r"] * 2.1),
            ], 30))
        # output shaft down to the rotor hub
        motors.append(_lathe_z(cx, cy, mz, [
            (-96.0, 0.0), (-96.0, M["bore_r"] * 0.62),
            (-56.0, M["bore_r"] * 0.62), (-56.0, 0.0)], 18))
        # terminal block on the side, and the feet
        tw, th, tt = M["term"]
        tv, tf = shapes.rounded_box(cx, cy + M["bell_r"] + th / 2, mz,
                                    tw, th, tt, r=3.0)
        motors.append((tv, tf))
        for sx in (-1.0, 1.0):
            fv, ff = shapes.rounded_box(
                cx + sx * (M["bell_r"] - 6.0), cy, mz - 58.0,
                M["foot_w"], M["foot_w"] * 2.4, 16.0, r=3.0)
            motors.append((fv, ff))

    out["fanduct"] = mesh.join(*ducts)
    out["fan_stators"] = mesh.join(*stators)
    out["fan_motors"] = mesh.join(*motors)
    return out


# --------------------------------------------------------------------------

def _open_loft(rings):
    n = len(rings[0])
    verts = [p for ring in rings for p in ring]
    faces = [(j * n + i, j * n + (i + 1) % n,
              (j + 1) * n + (i + 1) % n, (j + 1) * n + i)
             for j in range(len(rings) - 1) for i in range(n)]
    return verts, faces


def _exhaust_rings(cx, cy, cz):
    side = -1.0 if cy < 0.0 else 1.0
    theta = math.radians(E["theta"])
    cant = side * math.radians(E["cant"])
    axis = (math.cos(theta) * math.cos(cant),
            math.cos(theta) * math.sin(cant), math.sin(theta))
    start = (cx, cy, cz + 70.0)
    end = (E["exit_x"], side * E["exit_y"], E["exit_z"])
    p1 = (cx, cy, start[2] + E["scroll_r"])
    p2 = tuple(end[k] - E["scroll_r"] * axis[k] for k in range(3))
    rings = []
    for j in range(17):
        t = j / 16.0
        s = 1.0 - t
        centre = tuple(s ** 3 * start[k] + 3.0 * s * s * t * p1[k]
                       + 3.0 * s * t * t * p2[k] + t ** 3 * end[k]
                       for k in range(3))
        tangent = tuple(3.0 * s * s * (p1[k] - start[k])
                        + 6.0 * s * t * (p2[k] - p1[k])
                        + 3.0 * t * t * (end[k] - p2[k])
                        for k in range(3))
        length = math.sqrt(sum(v * v for v in tangent))
        tx, ty, tz = (v / length for v in tangent)
        width = (-math.sin(cant), math.cos(cant), 0.0)
        height = (ty * width[2] - tz * width[1],
                  tz * width[0] - tx * width[2],
                  tx * width[1] - ty * width[0])
        length = math.sqrt(sum(v * v for v in height))
        height = tuple(v / length for v in height)
        blend = t * t * (3.0 - 2.0 * t)
        ring = []
        for i in range(32):
            a = 2.0 * math.pi * i / 32.0
            ca, sa = math.cos(a), math.sin(a)
            edge = max(abs(ca), abs(sa))
            u = ca * ((1.0 - blend) * (F["duct_r"] - 22.0)
                      + blend * E["exit_w"] / (2.0 * edge))
            v = sa * ((1.0 - blend) * (F["duct_r"] - 22.0)
                      + blend * E["exit_h"] / (2.0 * edge))
            ring.append(tuple(centre[k] + u * width[k] + v * height[k]
                              for k in range(3)))
        rings.append(ring)
    return rings


def _scroll(cx, cy, cz):
    return _duct(_exhaust_rings(cx, cy, cz)[:13])


def _nozzle(cx, cy, cz):
    return _duct(_exhaust_rings(cx, cy, cz)[12:])


def _closed_loft(rings):
    """Loft a stack of rings and wrap the last one back onto the first."""
    n, m = len(rings[0]), len(rings)
    verts = [p for ring in rings for p in ring]
    faces = []
    for j in range(m):
        j2 = (j + 1) % m
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((j * n + i, j * n + i2, j2 * n + i2, j2 * n + i))
    return verts, faces


def _duct(rings, wall=6.0):
    """A duct with a wall: the outer surface, the bore, and a rim at each end.

    The scroll and the nozzle were open tubes -- a single surface of zero
    thickness with two free rims, 64 loose edges each. The fan's exhaust is
    the part of this car that makes the downforce it is built around, and it
    was a sheet you could see the back of.
    """
    inner = []
    for ring in rings:
        n = len(ring)
        c = tuple(sum(p[k] for p in ring) / n for k in range(3))
        r = sum(math.dist(p, c) for p in ring) / n
        k = max(0.25, (r - wall) / r) if r > 0.0 else 0.0
        inner.append([tuple(c[j] + (p[j] - c[j]) * k for j in range(3))
                      for p in ring])
    return _closed_loft(rings + list(reversed(inner)))


def _lathe_z(cx, cy, cz, profile, segments=36):
    """Revolve an (along-axis, radius) profile about the fan's own +z axis."""
    v, f = mesh.revolve_closed(list(profile), segments)
    return [(py + cx, pz + cy, px + cz) for (px, py, pz) in v], f


def _shroud(cx, cy, cz):
    r = F["duct_r"]
    return _lathe_z(cx, cy, cz, [
        (-90.0, r - 22.0), (-70.0, r - 30.0),      # bellmouth inlet lip
        (-52.0, r - 24.0), (70.0, r - 22.0),
        (70.0, r), (-90.0, r),
    ])


def _blade(cx, cy, cz, spin):
    """One twisted, raked fan blade.

    Blade angle falls with radius so the axial velocity is uniform across the
    disc: beta = atan(Va / (omega r)). Built from that relation rather than
    from two numbers picked by eye, so changing the rpm changes the twist.
    """
    r0 = F["hub_r"] - 6.0
    r1 = F["duct_r"] - 30.0
    omega = F["rpm"] * 2 * math.pi / 60.0
    sect = airfoil.section_points(22, F["blade_thickness"], F["blade_camber"])
    n = len(sect)
    n_span = 7
    verts = []
    for i in range(n_span):
        t = i / (n_span - 1)
        r = r0 + (r1 - r0) * t
        chord = (F["blade_root_chord"]
                 + (F["blade_tip_chord"] - F["blade_root_chord"]) * t)
        beta = math.atan2(F["axial_velocity"] * 1000.0, omega * r)
        rake = math.radians(F["blade_rake"]) * t * spin
        cb, sb = math.cos(beta), math.sin(beta)
        for (u, v) in sect:
            du = (u - 0.30) * chord
            dv = v * chord
            tang = (du * cb - dv * sb) * spin
            axial = du * sb + dv * cb
            ang = rake + tang / max(r, 1.0)
            verts.append((cx + r * math.cos(ang), cy + r * math.sin(ang),
                          cz + axial))
    faces = []
    for j in range(n_span - 1):
        a, b = j * n, (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((a + i, a + i2, b + i2, b + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (n_span - 1) * n
    faces.append(tuple(range(base, base + n)))
    return verts, faces


def _rotor(cx, cy, cz, spin):
    """Hub, nose cone, blades and back plate -- one spinning assembly."""
    parts = [_lathe_z(cx, cy, cz, [
        (-96.0, 0.0), (-78.0, F["hub_r"] * 0.52),   # inlet nose cone
        (-40.0, F["hub_r"]), (56.0, F["hub_r"]),
        (72.0, F["hub_r"] * 0.70), (72.0, 0.0),
    ], 26)]
    for k in range(F["blades"]):
        a = 2 * math.pi * k / F["blades"]
        v, f = _blade(0.0, 0.0, 0.0, spin)
        v = [(px * math.cos(a) - py * math.sin(a),
              px * math.sin(a) + py * math.cos(a), pz) for (px, py, pz) in v]
        parts.append(([(px + cx, py + cy, pz + cz) for (px, py, pz) in v], f))
    return mesh.join(*parts)


def _stators(cx, cy, cz, spin):
    """Outlet guide vanes. The rotor leaves the flow swirling; the swirl is
    wasted energy and a yaw torque, so it gets straightened before the exit."""
    parts = []
    r0, r1 = F["hub_r"], F["duct_r"] - 26.0
    for k in range(F["stator_vanes"]):
        a = 2 * math.pi * k / F["stator_vanes"] + math.pi / F["blades"]
        rows = []
        for t in (0.0, 1.0):
            r = r0 + (r1 - r0) * t
            twist = math.radians(-26.0 * (1.0 - t)) * spin
            rows.append((r, twist))
        verts = []
        sect = airfoil.section_points(14, 0.09, 0.06)
        n = len(sect)
        for (r, twist) in rows:
            ct, st = math.cos(twist), math.sin(twist)
            for (u, v) in sect:
                du = (u - 0.3) * 74.0
                dv = v * 74.0
                tang = du * ct - dv * st
                axial = du * st + dv * ct
                ang = a + tang / max(r, 1.0)
                verts.append((cx + r * math.cos(ang), cy + r * math.sin(ang),
                              cz + 102.0 + axial))
        faces = []
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((i, i2, n + i2, n + i))
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range(n, 2 * n)))
        parts.append((verts, faces))
    return mesh.join(*parts)
