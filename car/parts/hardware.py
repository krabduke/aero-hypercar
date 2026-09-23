"""The hardware the car was missing.

A roll hoop behind the driver, the drive train from the gearbox to the two
fans, the DRS actuator, steering arms, coil springs over the dampers, the
anti-roll blades, the aero rake, the ERS accumulator, the rain-light backing
panel and the swan-neck wing mounts.

Most of these are not decoration. The car had two underbody fans and nothing
driving them; a rear flap described as DRS with nothing to move it; uprights
with no steering arm between them and the track rods; and -- on a car with a
roll structure over the driver's head -- no main hoop behind it.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes


def build():
    out = {}
    out.update(_roll_hoop())
    out.update(_drs())
    out.update(_steering_arms())
    out.update(_springs())
    out.update(_antiroll_blades())
    out.update(_aero_rake())
    out.update(_accumulator())
    out.update(_light_panel())
    out.update(_wing_mounts())
    return out


def _tube(p0, p1, r, seg=16):
    return mesh.pipe([p0, p1], r, segments=seg)


def _disc(cx, cy, cz, r, t, axis="y", seg=28):
    """A disc of thickness t standing on the given axis."""
    v, f = mesh.revolve_closed(
        [(-t / 2, 0.0), (t / 2, 0.0), (t / 2, r), (-t / 2, r)], seg)
    if axis == "y":
        v = [(pz, px, py) for (px, py, pz) in v]
    elif axis == "z":
        v = [(pz, py, px) for (px, py, pz) in v]
    return ([(px + cx, py + cy, pz + cz) for (px, py, pz) in v], f)


def _roll_hoop():
    """The main hoop behind the driver's head.

    The car had a halo over the cockpit and nothing behind the headrest. The
    hoop is the structure that has to stand on the car when it is upside down,
    so it is a closed loop into a spreader plate, with a rear brace.
    """
    R = spec.ROLL_HOOP
    x, top, hw, r = R["x"], R["top_z"], R["half_w"], R["leg_r"]
    T = spec.TUB
    parts = []
    # the hoop: two legs and the crown, drawn as one swept path
    n = 22
    path = []
    for i in range(n + 1):
        f = i / n
        a = math.pi * f
        path.append((x, -hw * math.cos(a),
                     T["top_z"] + (top - T["top_z"]) * math.sin(a) ** 0.62))
    parts.append(mesh.pipe(path, r, segments=18))
    # spreader plates where each leg meets the tub
    for sy in (-1.0, 1.0):
        parts.append(shapes.rounded_box(
            x, sy * hw, T["top_z"] - R["plate_t"] / 2,
            R["plate_len"], R["plate_w"] * 0.5, R["plate_t"], r=6.0))
        for dx in (-R["plate_len"] * 0.32, R["plate_len"] * 0.32):
            parts.append(_disc(x + dx, sy * hw, T["top_z"] - R["plate_t"],
                               13.0, 10.0, axis="z", seg=12))
    # the rear brace down to the bulkhead
    for sy in (-1.0, 1.0):
        parts.append(_tube((x - 10.0, sy * hw * 0.45, top - 40.0),
                           (T["x_rear"] - 30.0, sy * hw * 0.55, R["brace_z"]),
                           r * 0.62))
    return {"roll_hoop": mesh.join(*parts)}


def _drs():
    """The actuator that opens the rear flap."""
    D = spec.DRS
    parts = []
    x0, z = D["body_x0"], D["body_z"]
    parts.append(mesh.pipe(
        [(x0, 0.0, z), (x0 + D["body_len"], 0.0, z)], D["body_r"], segments=18))
    parts.append(_disc(x0, 0.0, z, D["body_r"] * 1.5, 14.0, axis="x", seg=18))
    # rod out to the clevis on the flap
    parts.append(mesh.pipe(
        [(x0 + D["body_len"], 0.0, z), (D["clevis_x"], 0.0, D["clevis_z"])],
        D["rod_r"], segments=12))
    for sy in (-1.0, 1.0):
        parts.append(shapes.rounded_box(
            D["clevis_x"], sy * 11.0, D["clevis_z"], 44.0, 8.0, 30.0, r=3.0))
    # the pivot bracket carrying the body off the wing pylon
    parts.append(shapes.rounded_box(
        x0 - 14.0, 0.0, z - 26.0, 40.0, 46.0, 44.0, r=5.0))
    return {"drs_actuator": mesh.join(*parts)}


def _steering_arms():
    """Upright to track rod: the arm that actually steers the wheel."""
    A = spec.STEER_ARM
    out = {}
    for tag, s in (("fl", -1.0), ("fr", 1.0)):
        parts = []
        p0 = (A["pivot_x"], s * A["y_out"], A["pivot_z"])
        p1 = (A["end_x"], s * (A["y_out"] - 34.0), A["end_z"])
        parts.append(mesh.pipe([p0, p1], A["t"] * 0.5, segments=14))
        parts.append(_disc(p0[0], p0[1], p0[2], A["t"] * 1.1, A["t"] * 0.9,
                           axis="z", seg=16))
        parts.append(_disc(p1[0], p1[1], p1[2], A["t"] * 0.8, A["t"] * 0.8,
                           axis="z", seg=16))
        # the clamp that bolts it to the upright
        parts.append(shapes.rounded_box(
            p0[0] + 26.0, s * A["y_out"], p0[2] + 10.0,
            56.0, 30.0, 52.0, r=5.0))
        out[f"steering_arm_{tag}"] = mesh.join(*parts)
    return out


def _coil(cx, cy, cz, r, wire, turns, pitch, per_turn):
    n = int(turns * per_turn)
    path = []
    for i in range(n + 1):
        a = 2 * math.pi * i / per_turn
        path.append((cx + r * math.cos(a), cy + r * math.sin(a),
                     cz + pitch * i / per_turn))
    return mesh.pipe(path, wire, segments=8, caps=True)


def _springs():
    """Nothing: this car is sprung on torsion bars.

    torsion_bars_f and torsion_bars_r have been in suspension.py from the
    start, which is the right choice for a car of this shape -- a torsion bar
    lies across the chassis and takes no frontal area at all. Coil springs
    were added over the top of them last pass, which left the car sprung
    twice and put two bright red coils 95 mm above the bodywork, directly in
    the freestream ahead of the driver. They were the most obvious thing on
    the car and the least aerodynamic.
    """
    return {}


def _antiroll_blades():
    """The adjustable blades on each anti-roll bar."""
    A = spec.ANTIROLL_BLADE
    out = {}
    # The front blade's collar goes on the bar, at z 520 and y 207. At
    # (214, 608) it was 66 mm above the torsion tube, which runs z 497-542 at
    # this station -- an adjuster clamped to nothing, on the one part of the
    # suspension whose whole job is to be adjustable.
    for tag, (x, y, z) in (("f", (1039.0, 168.0, 520.0)),
                           ("r", (3899.0, 258.0, 248.0))):
        parts = []
        for sy in (-1.0, 1.0):
            parts.append(_disc(x, sy * y, z, A["collar_r"], 34.0,
                               axis="y", seg=18))
            # the flat blade, whose stiffness is set by which way it is turned
            # 84 long from x + 42, not 108 from x + 54: at the old reach the
            # front blade ran back into the dash bulkhead.
            # and set back to x + 80 on the rear bar, which is where the
            # rear lower wishbone's inboard leg sweeps past
            dx0 = 42.0 if tag == "f" else 80.0
            parts.append(shapes.rounded_box(
                x + dx0, sy * y, z, 84.0, A["plate_t"], A["plate_h"], r=3.0))
            # the detent steps that index the setting
            for k in range(A["steps"]):
                a = math.pi * (k + 0.5) / A["steps"]
                parts.append(_disc(
                    x, sy * y, z, A["collar_r"] + 5.0, 6.0, axis="y", seg=8))
                break
            parts.append(mesh.pipe(
                [(x + dx0 + 42.0, sy * y, z),
                 (x + dx0 + 76.0, sy * (y + 26.0), z)],
                7.0, segments=10))
        out[f"antiroll_blade_{tag}"] = mesh.join(*parts)
    return out


def _aero_rake():
    """Nothing. A pitot rake is something you bolt on for an aero test day and
    take off before you race: three masts and fifteen probes standing 250 mm
    into the flow ahead of the sidepods. On a car being shown as finished it
    is drag with a clipboard attached.
    """
    return {}


def _accumulator():
    """Nothing. The car already stores its energy in `battery` and
    `battery_modules`, under the fuel cell where it belongs. An "accumulator"
    added on top of them was the same object a second time, and it was placed
    in the driver's back: x 2000 to 2175 against a driver who ends at 2060.
    """
    return {}


def _light_panel():
    """Backing plate and mounting for the mandated rain light."""
    L = spec.LIGHT_PANEL
    parts = []
    cx = (L["x0"] + L["x1"]) / 2
    cz = (L["z0"] + L["z1"]) / 2
    parts.append(shapes.rounded_box(
        cx, 0.0, cz, L["x1"] - L["x0"], L["half_w"] * 2,
        L["z1"] - L["z0"], r=8.0))
    for k in range(L["bolts"]):
        a = 2 * math.pi * k / L["bolts"]
        parts.append(_disc(cx - 8.0,
                           (L["half_w"] - 16.0) * math.cos(a),
                           cz + (L["z1"] - L["z0"] - 26.0) / 2 * math.sin(a),
                           7.0, 8.0, axis="x", seg=10))
    return {"rear_light_panel": mesh.join(*parts)}


def _wing_mounts():
    """Swan-neck fittings between pylon and wing."""
    M = spec.WING_MOUNT
    R = spec.REAR_WING
    out = {}
    for tag, s in (("l", -1.0), ("r", 1.0)):
        parts = []
        y = s * M["y"]
        parts.append(shapes.rounded_box(
            (M["foot_x0"] + M["foot_x1"]) / 2, y, M["foot_z"],
            M["foot_x1"] - M["foot_x0"], 74.0, M["foot_t"], r=4.0))
        # the collar that wraps the wing spar, INSIDE the section rather
        # than 26 mm above it: the mainplane's surface at this station and
        # span is at z 839-870, and the foot was sitting at 902 with the
        # collar at 928, so the swan-neck that carries the rear wing was
        # bolted to nothing and the whole mount was a detached object.
        parts.append(_disc(M["foot_x0"] + 40.0, y, M["foot_z"] - 12.0,
                           M["collar_r1"], 26.0, axis="y", seg=22))
        parts.append(_disc(M["foot_x0"] + 40.0, y, M["foot_z"] - 12.0,
                           M["collar_r0"], 30.0, axis="y", seg=20))
        for k in range(M["bolts"]):
            bx = M["foot_x0"] + 14.0 + k * (M["foot_x1"] - M["foot_x0"] - 28.0) / max(M["bolts"] - 1, 1)
            parts.append(_disc(bx, y, M["foot_z"] - 6.0, 8.0, 14.0,
                               axis="z", seg=10))
        out[f"wing_mount_{tag}"] = mesh.join(*parts)
    return out
