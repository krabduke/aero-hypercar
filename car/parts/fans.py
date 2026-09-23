"""The fans. This is the part that makes the car what it is.

Two electrically driven fans pull air out of the sealed underfloor plenum.
Because they move a roughly fixed mass flow, the suction they generate barely
depends on road speed -- so unlike a wing, they still work in a hairpin.

The fans lie on their sides at the tail, axes along the car, and blow straight
back over the diffuser's exit, the way the Chaparral 2J's and the Brabham
BT46B's did. Each is fed by an intake rising out of a slot in the floor just
aft of the axle and turning into its face (`floor.floor_fan_throat_*`).

They used to stand on vertical axes and blow upward into a scroll meant to
turn the air aft to an exit 213 mm BELOW the plane it left the stators at: a
duct that bent 214 mm tighter than it was deep and folded 128 mm through
itself. A fan that blows the way the air has to leave needs no turn at all.

Sizing. 650 kg over the ~5.5 m2 the skirts seal is 1.2 kPa of suction, and
the fan only has to carry away what leaks in under the skirts -- a few cubic
metres a second at a few millimetres of gap. So the fans are 340 mm, not
520: two of them pass 8 m3/s at 50 m/s through the disc, which is margin for
worn skirts and kerbs, and fit between the diffuser and the rear endplates.

Everything is built in a fan frame -- axial `a` along +x from the disc,
radius `r` about the axis -- and placed by `_lathe` and `_at`.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import airfoil

F = spec.FAN
E = spec.FAN_EXHAUST
R = F["duct_r"]            # the duct's bore over the rotor


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
        out[f"fan_rotor_{tag}"] = ((cx, cy, cz), (1.0, 0.0, 0.0), spin,
                                   "spin")
    return out


def build():
    out = {}
    ducts, motors, stators = [], [], []
    for (tag, cx, cy, cz, spin) in centres():
        ducts.append(_shroud(cx, cy, cz))
        out[f"fan_rotor_{tag}"] = _rotor(cx, cy, cz, spin)
        stators.append(_stators(cx, cy, cz, spin))
        out[f"fan_nozzle_{tag}"] = _nozzle(cx, cy, cz)
        motors.append(_motor(cx, cy, cz))
    out["fanduct"] = mesh.join(*ducts)
    out["fan_stators"] = mesh.join(*stators)
    out["fan_motors"] = mesh.join(*motors)
    return out


# --------------------------------------------------------------------------
# the fan frame
# --------------------------------------------------------------------------

def _lathe(cx, cy, cz, profile, segments=48):
    """Revolve an (axial, radius) profile about the fan's own axis."""
    v, f = mesh.revolve_closed(list(profile), segments)
    return [(px + cx, py + cy, pz + cz) for (px, py, pz) in v], f


def _at(cx, cy, cz, a, r, ang):
    return (cx + a, cy + r * math.cos(ang), cz + r * math.sin(ang))


# Axial stations, from the disc: the bellmouth lip, the rotor, the stators,
# the end of the shroud, and the nozzle's exit.
A_LIP, A_ROTOR, A_STATOR, A_SHROUD = -80.0, 0.0, 58.0, 70.0
A_EXIT = E["exit_a"]


def _shroud(cx, cy, cz):
    """The duct over the rotor, with a bellmouth lip so the flow does not
    separate off a square edge on its way in."""
    return _lathe(cx, cy, cz, [
        (A_LIP, R + 26.0), (A_LIP + 10.0, R + 10.0), (-54.0, R),
        (A_SHROUD, R), (A_SHROUD, R + 8.0), (-54.0, R + 8.0),
        (A_LIP + 14.0, R + 16.0), (A_LIP + 4.0, R + 30.0),
    ], 64)


def _nozzle(cx, cy, cz):
    """Straight on from the shroud, contracting slightly to the exit.

    The exit's area is set in spec.FAN_EXHAUST; a small contraction keeps the
    jet attached to the nozzle wall at part speed without backing pressure up
    against the fan.
    """
    re = E["exit_r"]
    return _lathe(cx, cy, cz, [
        (A_SHROUD - 4.0, R), (A_EXIT, re), (A_EXIT, re + 6.0),
        (A_SHROUD - 4.0, R + 8.0),
    ], 64)


def _blade(spin):
    """One twisted, raked fan blade, in the fan frame about the +x axis.

    Blade angle falls with radius so the axial velocity is uniform across the
    disc: beta = atan(Va / (omega r)). Built from that relation rather than
    from two numbers picked by eye, so changing the rpm changes the twist.
    """
    r0 = F["hub_r"] - 6.0
    r1 = R - 4.0
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
            verts.append((A_ROTOR + axial, r * math.cos(ang),
                          r * math.sin(ang)))
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
    """Nose cone, hub and blades -- one spinning assembly."""
    parts = [_lathe(cx, cy, cz, [
        (A_LIP + 10.0, 0.0), (A_LIP + 22.0, F["hub_r"] * 0.55),
        (-34.0, F["hub_r"]), (30.0, F["hub_r"]), (30.0, 0.0),
    ], 32)]
    for k in range(F["blades"]):
        a = 2 * math.pi * k / F["blades"]
        v, f = _blade(spin)
        ca, sa = math.cos(a), math.sin(a)
        parts.append(([(px + cx, py * ca - pz * sa + cy, py * sa + pz * ca + cz)
                       for (px, py, pz) in v], f))
    return mesh.join(*parts)


def _stators(cx, cy, cz, spin):
    """Outlet guide vanes: the rotor leaves the flow swirling, which is
    wasted energy and a yaw torque, so it is straightened before the exit.
    They are also what holds the motor in the middle of the duct, so they
    run from the motor's case into the shroud."""
    parts = []
    r0, r1 = F["hub_r"] - 4.0, R + 3.0
    sect = airfoil.section_points(14, 0.09, 0.06)
    n = len(sect)
    for k in range(F["stator_vanes"]):
        base = 2 * math.pi * k / F["stator_vanes"] + math.pi / F["blades"]
        verts = []
        for t in (0.0, 1.0):
            r = r0 + (r1 - r0) * t
            twist = math.radians(-24.0 * (1.0 - t)) * spin
            ct, st = math.cos(twist), math.sin(twist)
            for (u, v) in sect:
                du, dv = (u - 0.3) * 48.0, v * 48.0
                tang = du * ct - dv * st
                axial = du * st + dv * ct
                ang = base + tang / max(r, 1.0)
                verts.append(_at(cx, cy, cz, A_STATOR + axial, r, ang))
        faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        faces.append(tuple(range(n - 1, -1, -1)))
        faces.append(tuple(range(n, 2 * n)))
        parts.append((verts, faces))
    return mesh.join(*parts)


def _motor(cx, cy, cz):
    """The motor, in the tail cone behind the rotor, on the stators.

    Hub-mounted like any electric ducted fan: it turns the rotor directly and
    its speed is set by the power electronics, which is what lets the fan run
    flat out in a hairpin and back off on a straight. It used to stand on
    top of a vertical fan, and a shaft and a pair of bevels off the gearbox
    drove the same rotor as well -- two drives for one fan.
    """
    hr = F["hub_r"]
    return _lathe(cx, cy, cz, [
        (30.5, 0.0), (30.5, hr - 2.0), (34.0, hr), (150.0, hr),
        (A_EXIT - 10.0, hr * 0.38), (A_EXIT - 4.0, 0.0),
    ], 40)
