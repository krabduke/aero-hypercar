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
import airfoil

F = spec.FAN


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

        # plenum throat feeding the fan from the tunnels
        z_in = F["plenum_z0"]
        ducts.append(mesh.pipe([(cx - 620.0, cy * 0.55, z_in),
                                (cx - 260.0, cy * 0.85, z_in + 100.0),
                                (cx - 60.0, cy, cz - 30.0)],
                               F["plenum_r"], 16))

        out[f"fan_rotor_{tag}"] = _rotor(cx, cy, cz, spin)
        stators.append(_stators(cx, cy, cz, spin))

        mv, mf = mesh.tube(-54.0, 54.0, 0.0, 62.0, 22)
        motors.append([(pz + cx, py + cy, px + cz + 150.0)
                       for (px, py, pz) in mv])
        motors[-1] = (motors[-1], mf)

    out["fanduct"] = mesh.join(*ducts)
    out["fan_stators"] = mesh.join(*stators)
    out["fan_motors"] = mesh.join(*motors)
    return out


# --------------------------------------------------------------------------

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
