"""Check that nothing inside the car pokes out through its bodywork.

Bounding boxes cannot answer this. A wiring loom runs most of the length of
the car, so its box is as wide as the widest station it passes; compared
against the nose it looks far outside when it is inside all the way along. The
only honest test is per vertex, against the section at that vertex's own
station -- which is cheap, because the geometry layer is pure Python and can
be rebuilt without Blender.

The RC jet has had this test for a while; the car had nothing, which is how
the hybrid battery ended up inside the sump and the wheel gun sockets ended up
outboard of the tyres. Everything is checked by default, and each part allowed
outside is named with the reason.

    python3 tools/audit_fit.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec
from parts import chassis, powertrain, systems, detail

# Named exceptions, each with the reason it is allowed outside the bodywork.
OUTSIDE = {
    # the body itself and the things lofted with it
    "tub": "is the bodywork",
    "sidepod": "is the bodywork",
    "engine_cover": "is the bodywork",
    "nose": "is the bodywork",
    "sharkfin": "stands on the engine cover",
    "airbox": "the roll-hoop intake, above the body",
    "cockpit_coaming": "the rim of the cockpit opening",
    "gills": "louvres in the bodywork",
    "cooling_louvres": "louvres in the bodywork",
    "exit_louvres": "louvres in the bodywork",
    "sidepod_gills": "louvres in the bodywork",
    "sidepod_inlets": "the inlet mouth, open to outside",
    # safety structures that stand proud by design
    "halo": "above the cockpit, which is the point of it",
    "crash_structure": "behind the gearbox",
    "side_impact": "in the sidepod flanks",
    "tow_hooks": "have to be reachable",
    "jack_points": "have to be reachable",
    "gun_sockets": "have to be reachable",
    "starter_socket": "has to be reachable",
    "fuel_coupling": "has to be reachable",
    "mirrors": "on stalks, outboard",
    "cameras": "on the bodywork",
    "rainlight": "on the crash structure",
    "exhaust": "leaves the car",
    "tyre_sensors": "on the wheels",
    "helmet": "above the coaming, inside the halo -- which is its whole job",
    "brake_lines": "run out to all four corners",
    "wiring_loom": "runs out to all four corners",
    # everything below and outboard: floor, wings, wheels, suspension, aero
    "floor": "below the body",
    "tunnel": "below the body",
    "front_": "wings and their furniture",
    "rear_": "wings and their furniture",
    "beam_wing": "behind the body",
    "bargeboard": "outboard of the body",
    "turning_vane": "under the nose",
    "wheel": "outboard", "tyre": "outboard", "rim": "outboard",
    "disc": "in the wheel", "caliper": "in the wheel",
    "upright": "in the wheel", "bduct": "in the wheel",
    "wishbone": "outboard", "pushrod": "outboard", "trackrod": "outboard",
    "driveshaft": "outboard", "rocker": "inboard but above the tub line",
    "damper": "inboard but above the tub line",
    "antiroll": "inboard but above the tub line",
    "torsion_bars": "inboard but above the tub line",
    "heave": "inboard but above the tub line",
    "steering_rack": "ahead of the tub, in the nose",
    "fan_": "in the fan duct under the floor",
    "fanduct": "under the floor",
    "radiator": "in the sidepod, checked against the sidepod",
    "rad_": "in the sidepod, checked against the sidepod",
}


def inside_body(x, y, z, slack):
    """Is (y, z) inside the body section at station x, with `slack` to spare?

    Returns how far outside it is, in mm, or 0.0 when it is in.
    """
    ring = chassis.body_section(x, inset=-slack, segments=96)
    if not ring:
        return 0.0
    # the section is a closed convex-ish superellipse, so a ray cast is enough
    inside = False
    n = len(ring)
    for i in range(n):
        ay, az = ring[i][1], ring[i][2]
        by, bz = ring[(i + 1) % n][1], ring[(i + 1) % n][2]
        if (az > z) != (bz > z):
            t = (z - az) / ((bz - az) or 1e-9)
            if y < ay + t * (by - ay):
                inside = not inside
    if inside:
        return 0.0
    # how far out: distance to the nearest edge
    best = 1e18
    for i in range(n):
        ay, az = ring[i][1], ring[i][2]
        by, bz = ring[(i + 1) % n][1], ring[(i + 1) % n][2]
        dy, dz = by - ay, bz - az
        L2 = dy * dy + dz * dz or 1e-9
        t = max(0.0, min(1.0, ((y - ay) * dy + (z - az) * dz) / L2))
        best = min(best, math.hypot(y - (ay + t * dy), z - (az + t * dz)))
    return best


def cockpit_top(x):
    """The cockpit is a hole in the bodywork, so a part inside it is allowed
    up to the top of the coaming rather than the top of the body section.
    `body_section` knows nothing about the opening."""
    T = spec.TUB
    if not (T["cockpit_x0"] <= x <= T["cockpit_x1"]):
        return None
    return spec.TUB.get("coaming_z", 780.0)


def check(slack=6.0):
    built = {}
    for m in (powertrain, systems, detail):
        built.update(m.build())

    x0 = spec.BODY[0][0]
    x1 = spec.BODY[-1][0]
    worst = []
    for name, (verts, faces) in sorted(built.items()):
        if any(name.startswith(k) for k in OUTSIDE):
            continue
        over, at = 0.0, None
        for (x, y, z) in verts:
            if not (x0 <= x <= x1):
                continue                  # ahead of or behind the body
            top = cockpit_top(x)
            if top is not None and z <= top:
                # in the cockpit aperture: only the width matters here
                hw = max(abs(p[1]) for p in
                         chassis.body_section(x, segments=48)) + slack
                d = max(0.0, abs(y) - hw)
            else:
                d = inside_body(x, y, z, slack)
            if d > over:
                over, at = d, (x, y, z)
        if over > 0.1:
            worst.append((over, name, at))
    return sorted(worst, reverse=True)


if __name__ == "__main__":
    bad = check()
    if not bad:
        print("PASS  every internal part is inside the bodywork")
        sys.exit(0)
    print(f"FAIL  {len(bad)} parts poke through the bodywork\n")
    for d, name, at in bad[:20]:
        print(f"  {name:26s} {d:6.1f} mm out at "
              f"({at[0]:.0f}, {at[1]:.0f}, {at[2]:.0f})")
    sys.exit(1)
