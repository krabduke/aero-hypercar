"""What the underfloor actually makes, solved rather than assumed.

spec.AERO["cla_floor"] = 3.35 is 57 per cent of this car's downforce and it
has never been computed by anything. This computes it: the car's centreline
section, in ground effect, in a two-dimensional panel method fine enough to
resolve the gap -- which is the one thing the three-dimensional solve cannot
do, because a floor 10 mm off the road with 200 mm panels faces its own image
at a thirtieth of a panel width.

Two dimensions is the right tool and not a consolation: a duct's section is
what sets its pressure. What two dimensions cannot give is the spillage round
the floor's edges, so the answer here is an upper bound on the real thing, and
the edge factor that turns one into the other is stated rather than hidden.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                            # noqa: E402
from parts import floor as fl, chassis                 # noqa: E402
from panel2d import Section2D                          # noqa: E402

MM = 0.001
F = spec.FLOOR


def underfloor_height(x, throat_entry=None):
    """The gap between road and underbody at station x, in mm.

    `throat_entry` overrides the height the floor starts at, which is the one
    number that decides whether this is a venturi or just a diffuser.
    """
    if x <= F["x0"]:
        hw, zb, zt, n, bias = chassis._sample(spec.BODY, x)
        return max(zb, 30.0)
    entry = 78.0 if throat_entry is None else throat_entry
    if x <= F["throat_x"]:
        f = (x - F["x0"]) / (F["throat_x"] - F["x0"])
        return entry - (entry - F["throat_z"]) * f ** 1.3 + 18.0
    if x <= F["diffuser_x"]:
        return F["throat_z"] + 18.0
    f = (x - F["diffuser_x"]) / (F["x1"] - F["diffuser_x"])
    return (F["throat_z"] + 18.0
            + (F["diffuser_exit_z"] - F["throat_z"]) * f ** 1.25)


def section(n=140, throat_entry=None):
    """The car's centreline silhouette, clockwise from the tail."""
    x0, x1 = 0.0, F["x1"]
    b = np.linspace(0, math.pi, n + 1)
    xs = x0 + (x1 - x0) * 0.5 * (1 - np.cos(b))        # bunched at both ends
    lower = np.array([underfloor_height(x, throat_entry) for x in xs])
    upper = []
    for x in xs:
        hw, zb, zt, nn, bias = chassis._sample(spec.BODY, min(x, spec.BODY[-1][0]))
        upper.append(max(zt, lower[list(xs).index(x)] + 40.0)
                     if False else zt)
    upper = np.array(upper)
    upper = np.maximum(upper, lower + 40.0)
    # clockwise from the tail: back along the bottom to the nose, then over
    # the top to the tail again
    X = np.concatenate([xs[::-1], xs[1:]])
    Y = np.concatenate([lower[::-1], upper[1:]])
    # close it
    X = np.append(X, X[0]); Y = np.append(Y, Y[0])
    return X * MM, Y * MM


def run(throat_entry=None, v=250/3.6, n=200):
    """Solve and return the pressure along the underbody.

    The section's Cl is NOT reported. The car's rear is a blunt base, not a
    sharp trailing edge, so the Kutta condition applied there is arbitrary and
    the circulation it picks is arbitrary with it. What the solve does say,
    and says well, is the pressure under the floor -- which is the question.
    """
    X, Y = section(n, throat_entry)
    s = Section2D(X, Y, ground=True).solve(0.0, v)
    half = len(s.cx) // 2
    xs = s.cx[:half] / MM                       # back to mm, tail -> nose
    cp = s.cp[:half]
    ell = s.ell[:half]
    order = np.argsort(xs)
    return {"x": xs[order], "cp": cp[order], "ell": ell[order], "v": v}


def at(r, x_mm):
    return float(np.interp(x_mm, r["x"], r["cp"]))


def floor_downforce(r):
    """Downforce per metre of span from the floor region, in newtons."""
    q = 0.5 * 1.225 * r["v"] * r["v"]
    m = (r["x"] >= F["x0"]) & (r["x"] <= F["x1"])
    return float(np.sum(-r["cp"][m] * r["ell"][m])) * q


def main():
    v = 250/3.6
    print("\nUNDERFLOOR, SOLVED IN TWO DIMENSIONS WITH THE ROAD")
    print(f"  {v*3.6:.0f} km/h, centreline section, ground plane on")
    print("  (the section Cl is not quoted: the car's rear is a blunt base, so")
    print("   the Kutta condition there -- and the circulation it picks -- is")
    print("   arbitrary. The pressure under the floor is the question.)\n")
    cases = [(None, "as built"), (150.0, "150 mm entry"),
             (200.0, "200 mm entry"), (260.0, "260 mm entry")]
    print("   case            gap mm        Cp at the floor at x =")
    print("                  in -> throat   1400   2000   2600   3400   4000   4400")
    for entry, label in cases:
        r = run(entry, v)
        h0 = underfloor_height(F["x0"] + 1, entry)
        ht = underfloor_height(F["throat_x"], entry)
        cps = "  ".join(f"{at(r, x):+5.2f}" for x in
                        (1400, 2000, 2600, 3400, 4000, 4400))
        print(f"   {label:14s} {h0:4.0f} -> {ht:3.0f}    {cps}")
    print()
    print("   case            downforce per metre of span, over the floor")
    for entry, label in cases:
        r = run(entry, v)
        d = floor_downforce(r)
        print(f"   {label:14s} {d:8.0f} N/m")
    print()
    print("  'as built' has the entry BELOW the throat, so")
    print("  78 - (78 - 96) f^1.3 + 18 RISES instead of falling: 96 to 114 mm.")
    print("  The floor never converges. There is no venturi -- only a diffuser")
    print("  with a long flat inlet in front of it.")


if __name__ == "__main__":
    main()
