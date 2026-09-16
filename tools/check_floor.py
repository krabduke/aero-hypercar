"""Is the underfloor actually a venturi?

This car's headline is ground effect and 57 per cent of its downforce is
attributed to the floor. For any of that to be true the underbody has to be a
converging-diverging duct: area falling to a throat, then a diffuser gentle
enough to stay attached. None of that was ever checked, and it was not true.

`_floor_z` read

    78.0 - (78.0 - throat_z) * f**1.3 + 18.0

with throat_z = 96, which is 96 + 18 f^1.3 -- it RISES, 96 mm to 114. The
minimum area sat at the floor's own leading edge, 1210 cm2 against 1347 at the
diffuser, so the duct was inlet-limited: everything downstream was expansion
and the suction peak sat at the entry, which is the least useful and the most
ride-height-sensitive place to put it. The docstring said "pinched at the
throat" and the arithmetic did the opposite.

    python3 tools/check_floor.py
"""

import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "car"))

import spec                                    # noqa: E402
from parts import floor as fl                  # noqa: E402

F = spec.FLOOR
N = 600

# A diffuser steeper than about seven degrees of half-angle separates, and a
# separated diffuser recovers nothing -- it is a hole in the back of the car.
MAX_HALF_ANGLE = 7.5
# And one that expands by more than about three in area will not hold on
# however gentle the angle.
MAX_EXPANSION = 3.2


def main():
    xs = [F["x0"] + (F["x1"] - F["x0"]) * i / (N - 1) for i in range(N)]
    h = [fl._floor_z(x) for x in xs]
    w = [2 * fl.half_width(x) for x in xs]
    a = [hi * wi for hi, wi in zip(h, w)]
    i = a.index(min(a))

    half = math.degrees(math.atan(
        0.5 * (fl._floor_z(F["x1"]) - fl._floor_z(F["diffuser_x"]))
        / (F["x1"] - F["diffuser_x"])))

    print(f"\nUNDERFLOOR  ({F['x0']:.0f} to {F['x1']:.0f} mm)")
    print(f"   roof height        {h[0]:.0f} mm at the inlet, "
          f"{fl._floor_z(F['throat_x']):.0f} at the throat station, "
          f"{h[-1]:.0f} at the exit")
    print(f"   area               {a[0]/100:.0f} cm2 inlet, "
          f"{min(a)/100:.0f} at x={xs[i]:.0f}, {a[-1]/100:.0f} exit")
    print(f"   contraction        {a[0]/min(a):.2f}")
    print(f"   expansion          {a[-1]/min(a):.2f}")
    print(f"   diffuser half-angle {half:.1f} deg")

    ok = True
    def fail(m):
        nonlocal ok
        ok = False
        print("   x  " + m)

    if i == 0:
        fail("the narrowest section is the INLET -- this is not a venturi, it "
             "is a diffuser with a long flat inlet, and the duct is "
             "inlet-limited")
    if xs[i] < F["throat_x"] * 0.9:
        fail(f"the throat is at x={xs[i]:.0f}, well ahead of where the "
             f"geometry says it is ({F['throat_x']:.0f})")
    if a[0] / min(a) < 1.02:
        fail("the duct does not converge at all")
    if a[-1] / min(a) > MAX_EXPANSION:
        fail(f"the diffuser expands {a[-1]/min(a):.2f} times, past the {MAX_EXPANSION} "
             "a duct will hold on to")
    if half > MAX_HALF_ANGLE:
        fail(f"the diffuser opens at {half:.1f} deg, past the {MAX_HALF_ANGLE} "
             "at which it separates")

    print("\n" + "=" * 62)
    print("PASS  the underfloor is a duct that converges then expands" if ok
          else "FAIL  the underfloor is not a venturi")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
