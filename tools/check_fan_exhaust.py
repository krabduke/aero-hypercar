"""Screen the fan exhaust: its flow balance, and where its jet goes.

The flow half is conservation: finite numbers, and a nozzle whose area
matches the annulus feeding it (aero/fan_exhaust.py).

The geometric half follows the jet. Each fan lies on its side at the tail and
blows straight back along its own axis, so there is no duct to turn -- the
screen is on the free jet after the nozzle. A free jet spreads at about
11.8 degrees half-angle; that cone, from the nozzle's exit to the back of the
car, has to stay off the rear wing's main plane above it, off the ground
below it, and out of the rear endplates outboard of it. The endplates are the
tight one: the cone reaches the corner of an endplate's foot only near its
trailing edge, and that is reported with the margin.

It used to be credited with testing the envelope in 3-D and tested that two
numbers were finite; then, for the vertical fans, it measured a duct that
could not be built. Neither is the case now.

    python3 tools/check_fan_exhaust.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "aero"))
sys.path.insert(0, os.path.join(HERE, "car"))
import fan_exhaust as analysis            # noqa: E402
import spec                               # noqa: E402

HALF_ANGLE = math.radians(11.8)
# How far into an endplate's foot the spreading edge of the jet may reach,
# near its trailing edge, before it counts as blowing on it.
ENDPLATE_ALLOW = 25.0


def _bounds(prefix):
    """(x0, x1, y0, y1, z0, z1) of a part, from the build."""
    import csv
    path = os.path.join(HERE, "build", "parts.csv")
    for r in csv.DictReader(open(path)):
        if r["name"] == prefix:
            return tuple(float(r[k]) for k in ("x_min_mm", "x_max_mm",
                                               "y_min_mm", "y_max_mm",
                                               "z_min_mm", "z_max_mm"))
    return None


def main():
    failures = []
    F, E = spec.FAN, spec.FAN_EXHAUST
    result = analysis.flow(F, E)
    if not all(math.isfinite(value) for value in result.values()):
        failures.append("non-finite flow result")
    if result["area_mismatch"] > 0.05:
        failures.append(f"exit/annulus area mismatch "
                        f"{result['area_mismatch']:.2%} > 5%")
    print(f"flow  exit {result['exit_m2']:.4f} m2 against an annulus of "
          f"{result['annulus_m2']:.4f} m2, {result['exit_m_s']:.1f} m/s out, "
          f"{result['volume_m3_s']:.1f} m3/s a fan")

    x_exit = F["x"] + E["exit_a"]
    yc, zc = F["y"], F["z"]
    wing = _bounds("rear_wing_main")
    plate = _bounds("rear_endplate_r")
    x_end = max(plate[1] if plate else x_exit, wing[1] if wing else x_exit)

    def r_at(x):
        return E["exit_r"] + max(0.0, x - x_exit) * math.tan(HALF_ANGLE)

    # the rear wing's main plane, above: nearest point is straight up
    if wing:
        gap = wing[4] - zc - r_at(min(wing[1], x_end))
        print(f"  {'ok' if gap > 0 else 'FAIL'}  jet below the rear wing, "
              f"{gap:.0f} mm clear at its trailing edge")
        if gap <= 0:
            failures.append(f"jet reaches the rear wing by {-gap:.0f} mm")
    # the ground
    gap = zc - r_at(x_end)
    print(f"  {'ok' if gap > 0 else 'FAIL'}  jet above the ground, "
          f"{gap:.0f} mm clear at x {x_end:.0f}")
    if gap <= 0:
        failures.append(f"jet reaches the ground by {-gap:.0f} mm")
    # the endplate's foot: the corner nearest the axis
    if plate:
        corner = math.hypot(plate[2] - yc, plate[4] - zc)
        worst = r_at(plate[1]) - corner
        state = "ok" if worst <= ENDPLATE_ALLOW else "FAIL"
        print(f"  {state:4s}  jet edge at the endplate's foot, "
              f"{worst:+.0f} mm at its trailing edge (allowed "
              f"{ENDPLATE_ALLOW:.0f})")
        if worst > ENDPLATE_ALLOW:
            failures.append(f"jet blows {worst:.0f} mm into the endplates")

    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        print(f"FAIL  {len(failures)} problem(s) with the fan exhaust")
        return 1
    print("PASS  the exhaust flow balances and the jet clears the car")
    return 0


if __name__ == "__main__":
    sys.exit(main())
