"""Screen the fan exhaust: its flow balance, and whether its duct can exist.

The flow half is conservation: finite numbers, and a nozzle whose area
matches the annulus feeding it (aero/fan_exhaust.py).

The geometric half asks the question this file used to be credited with and
did not ask. The fan blows straight up out of its stators; the exit is a
460 x 498 mm mouth aimed 28 degrees above horizontal, 280 mm aft of the fan's
axis. The duct between them is swept along a curve from one to the other, and
a swept duct can only turn as tightly as it is deep: where the centreline's
radius of curvature is smaller than the section's half-depth, the inside of
the bend passes back through itself. Three numbers say whether that happens:

  - the section's half-depth less the centreline's radius, at the tightest
    point of the bend;
  - how far any section's inside edge reaches back past the one before it,
    which is the duct folding through itself; and
  - how far the exit's lower lip lies below the plane the air leaves the
    stators at. Air leaving a fan upwards cannot reach a mouth below it
    without turning back down through more than a right angle.

Each is a defect when it is above zero. As built, all three are: the duct is
an open design defect, not a modelling slip. Fixing it means raising the exit
above the beam wing or turning the fans to blow aft, and either one moves
other parts of the car. Until that is decided, the measured values are held
in KNOWN as a ratchet -- the check fails if the duct gets any worse, and says
when a figure is fixed.

    python3 tools/check_fan_exhaust.py
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "aero"))
sys.path.insert(0, os.path.join(HERE, "car"))
import fan_exhaust as analysis            # noqa: E402
from parts import fans                    # noqa: E402

# The duct as built: the worst value over both fans, in mm. Each may only go
# down.
KNOWN = {
    "bend_tighter_than_duct": 214.2,
    "fold": 128.4,
    "exit_below_stators": 212.6,
}


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return [x / n for x in a]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def geometry(cx, cy, cz):
    rings = fans._exhaust_rings(cx, cy, cz)
    cen = [[sum(p[k] for p in r) / len(r) for k in range(3)] for r in rings]
    bend = -1e9
    for i in range(1, len(rings) - 1):
        a, b, c = cen[i - 1], cen[i], cen[i + 1]
        n = _cross(_sub(b, a), _sub(c, a))
        area2 = math.sqrt(_dot(n, n))
        if area2 < 1e-9:
            continue
        radius = (math.dist(a, b) * math.dist(b, c) * math.dist(a, c)
                  / (2.0 * area2))
        # the section's depth towards the centre of the bend
        inward = _unit(_sub([(a[k] + c[k]) / 2 for k in range(3)], b))
        depth = max(_dot(_sub(p, b), inward) for p in rings[i])
        bend = max(bend, depth - radius)
    fold = 0.0
    for i in range(1, len(rings)):
        t = _unit(_sub(cen[i], cen[i - 1]))
        fold = max(fold, -min(_dot(_sub(p, cen[i - 1]), t) for p in rings[i]))
    stator_top = max(v[2] for v in fans._stators(cx, cy, cz, 1.0)[0])
    return {"bend_tighter_than_duct": bend, "fold": fold,
            "exit_below_stators": stator_top - min(p[2] for p in rings[-1])}


def main():
    failures = []
    result = analysis.flow(analysis.spec.FAN, analysis.spec.FAN_EXHAUST)
    if not all(math.isfinite(value) for value in result.values()):
        failures.append("non-finite flow result")
    if result["area_mismatch"] > 0.05:
        failures.append(f"exit/annulus area mismatch "
                        f"{result['area_mismatch']:.2%} > 5%")
    print(f"flow  exit {result['exit_m2']:.3f} m2 against an annulus of "
          f"{result['annulus_m2']:.3f} m2, {result['exit_m_s']:.1f} m/s out")

    worst = {k: -1e9 for k in KNOWN}
    for _tag, cx, cy, cz, _spin in fans.centres():
        for k, v in geometry(cx, cy, cz).items():
            worst[k] = max(worst[k], v)
    print("duct, worst of the two fans (a defect above zero):")
    for k, v in worst.items():
        state = "ok" if v <= 0.0 else "OPEN"
        print(f"  {state:4s}  {k:24s} {v:7.1f} mm   known {KNOWN[k]:.1f}")
        if v > max(KNOWN[k], 0.0) + 0.5:
            failures.append(f"{k} got worse: {KNOWN[k]:.1f} -> {v:.1f} mm")
        elif v <= 0.0 < KNOWN[k]:
            print(f"        {k} is fixed -- set its KNOWN value to 0")
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        print(f"FAIL  {len(failures)} problem(s) with the fan exhaust")
    elif any(v > 0.0 for v in worst.values()):
        print("PASS  the exhaust flow balances; its duct is an open design "
              "defect, held where it is")
    else:
        print("PASS  the exhaust flow balances and its duct can be built")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
