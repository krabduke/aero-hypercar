"""The underfloor as what it is: a duct.

A panel method solves EXTERNAL flow. The underbody is internal -- air enters
at the floor's leading edge, is squeezed, and leaves through the diffuser --
and modelling it as the outside of a closed body puts a Kutta condition on a
blunt base and an arbitrary circulation with it. Asked that way it gave the
diffuser exit Cp +0.73, which is a stagnation point where the exit of a
diffuser should be near ambient.

So: one-dimensional channel flow, which is the standard first model for a duct
and is what the shape actually is.

    continuity      v(x) . A(x) = Q
    Bernoulli       p(x) + rho v(x)^2 / 2 = p_total, along a streamline
    the inlet       total pressure is the freestream's, less an inlet loss
    the outlet      static pressure is set by what is behind the car: the
                    base, and the fan if it is running

Q is whatever makes the exit condition true, and everything follows from it.
This is a model with three assumptions in it -- no separation, uniform flow
across the section, and a stated exit pressure -- and all three are stated.
The diffuser's own limit is checked rather than assumed: a duct that expands
faster than about seven degrees of half-angle separates and recovers nothing.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                        # noqa: E402
from parts import floor as fl                      # noqa: E402

MM = 0.001
F = spec.FLOOR
RHO = 1.225


def height(x, entry=None):
    """Underfloor height at x, in mm. `entry` overrides the height the floor
    starts at -- the one number that decides venturi or no venturi."""
    e = 78.0 if entry is None else entry
    if x <= F["throat_x"]:
        f = (x - F["x0"]) / (F["throat_x"] - F["x0"])
        return e - (e - F["throat_z"]) * f ** 1.3 + 18.0
    if x <= F["diffuser_x"]:
        return F["throat_z"] + 18.0
    f = (x - F["diffuser_x"]) / (F["x1"] - F["diffuser_x"])
    return (F["throat_z"] + 18.0
            + (F["diffuser_exit_z"] - F["throat_z"]) * f ** 1.25)


def duct(n=400, entry=None):
    x = np.linspace(F["x0"], F["x1"], n)
    h = np.array([height(v, entry) for v in x])
    w = np.array([2 * fl.half_width(v) for v in x])
    return x, h, w, (h * w) * MM * MM        # area in m2


def solve(v_inf, entry=None, cp_exit=-0.15, inlet_loss=0.08, fan_dp=0.0):
    """Pressure along the underfloor.

    `cp_exit` is what the diffuser discharges into -- the car's base, which
    sits below ambient. `fan_dp` is the pressure the fan adds to the circuit,
    which lowers the exit pressure the duct sees and so pulls more through it.
    """
    x, h, w, A = duct(entry=entry)
    q = 0.5 * RHO * v_inf * v_inf
    p_total = q * (1.0 - inlet_loss)              # relative to ambient
    p_exit = cp_exit * q - fan_dp
    # Bernoulli from inlet total to the exit static gives the exit speed, and
    # continuity gives the rest
    v_exit = math.sqrt(max(2.0 * (p_total - p_exit) / RHO, 0.0))
    Q = v_exit * A[-1]
    v = Q / A
    p = p_total - 0.5 * RHO * v * v
    return {"x": x, "h": h, "w": w, "A": A, "v": v, "cp": p / q,
            "Q": Q, "q": q, "v_inf": v_inf}


def downforce(r):
    """Newtons, from the pressure under the floor's plan area."""
    dx = np.gradient(r["x"]) * MM
    return float(np.sum(-r["cp"] * r["q"] * r["w"] * MM * dx))


def diffuser_half_angle(entry=None):
    h0 = height(F["diffuser_x"], entry)
    h1 = height(F["x1"], entry)
    return math.degrees(math.atan(0.5 * (h1 - h0) / (F["x1"] - F["diffuser_x"])))


def main():
    v = 250 / 3.6
    plan = ((F["x1"] - F["x0"]) * 2 * F["half_w"]) * MM * MM
    print("\nUNDERFLOOR AS A DUCT")
    print(f"  {v*3.6:.0f} km/h, exit into a base at Cp -0.15, 8 % inlet loss")
    print(f"  diffuser half-angle {diffuser_half_angle():.1f} deg "
          f"(over about 7 it separates and recovers nothing)\n")
    print("   entry   gap in -> throat   throat Cp   mean Cp   downforce   CL.A")
    for entry, label in ((None, "as built"), (150.0, "150 mm"),
                         (200.0, "200 mm"), (260.0, "260 mm"),
                         (320.0, "320 mm")):
        r = solve(v, entry)
        i = int(np.argmin(np.abs(r["x"] - F["throat_x"])))
        d = downforce(r)
        h0, ht = height(F["x0"] + 1, entry), height(F["throat_x"], entry)
        print(f"   {label:8s} {h0:5.0f} -> {ht:3.0f} mm    {r['cp'][i]:+7.2f}"
              f"   {r['cp'].mean():+7.2f}   {d/9.81:7.0f} kg   {d/r['q']:5.2f}")
    print()
    print(f"  the spec says cla_floor = {spec.AERO['cla_floor']:.2f}, which is "
          f"{100*spec.AERO['cla_floor']/(spec.AERO['cla_floor']+spec.AERO['cla_wings']):.0f} % of this car's")
    print("  downforce and has never been computed by anything until now")


if __name__ == "__main__":
    main()
