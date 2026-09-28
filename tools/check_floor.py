"""Is the floor a sealed plenum, and can the fans hold it?

This used to ask whether the underfloor was a venturi -- a duct converging
to a throat and expanding through a diffuser -- and it was, and it did not
matter. The aero study ran it through OpenFOAM (model-gallery/aero): open
at the front, each tunnel swallowed the air the car drove into, the fans
could not draw it, and with the fans off the floor LIFTED. With them on,
the 811 kg they made came from 4 m3/s forced through an intake choked to
-31 kPa at the fan's face: 380 kW of fan work for a pair of fans rated 38.

So the floor is closed now, the way the Chaparral 2J's and the Brabham
BT46B's were: side skirts, a front skirt across the tunnels' mouths and a
rear one across their exits. Each side is a plenum the fans hold at a set
suction. Its downforce is that suction times its plan area, the same at
every speed, and the only air the fans have to move is what leaks in under
the skirts -- a fraction of a cubic metre a second, which is why a sealed
fan car needs so little power. This checks each link of that:

  1. the plenum is closed: skirts down both edges from the front seal to
     the rear one, both seals spanning plank to skirt, and each fan's
     intake opening inside it;
  2. its area and where its load lands, from the built floor;
  3. the leak: every metre of seal, at a worn skirt's clearance, at the
     set suction;
  4. the fan: its flow covers the leak with margin for a skirt lifting on a
     kerb, its pressure coefficient is one an axial fan reaches, and its
     power is inside what the hybrid system gives it.

    python3 tools/check_floor.py
"""

import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "car"))

import spec                                    # noqa: E402
from parts import floor as fl                  # noqa: E402

F, FAN, P = spec.FLOOR, spec.FAN, spec.PLENUM
MM = 0.001
N = 800

# The highest pressure coefficient, dP / (rho U_tip^2), that a single-stage
# axial fan is credited with here. Industrial high-pressure axial fans reach
# 0.25-0.35 at their design point; past that it is a two-stage or a
# centrifugal machine.
PSI_MAX = 0.32
# A skirt that has ridden a kerb is not sealed: the fan has to carry at
# least this multiple of the running leak to hold suction through it.
FLOW_MARGIN = 2.0


def plenum():
    """Plan area of each side's plenum (plank edge to skirt, front seal to
    rear), its centroid, and the length of seal round it."""
    x0, x1 = fl.SEAL_FRONT_X, fl.SEAL_REAR_X
    a = m = side = 0.0
    prev = None
    for i in range(N):
        x = x0 + (x1 - x0) * (i + 0.5) / N
        w = fl.half_width(x) - 19.0 - F["tunnel_inner_y"]
        dx = (x1 - x0) / N
        a += w * dx
        m += w * dx * x
        y = fl.half_width(x) - 19.0
        if prev is not None:
            side += math.hypot(dx, y - prev)
        prev = y
    ends = 2 * (fl.half_width(x0) - 19.0 - F["tunnel_inner_y"])
    plank = x1 - x0                 # the plank runs on the road, a seal too
    return a * MM * MM, m / a, (side + plank) * MM, ends * MM


def main():
    fails = []

    def check(ok, good, bad):
        print(("   ok  " if ok else "   x   ") + (good if ok else bad))
        if not ok:
            fails.append(bad)

    built = fl.build()
    print("\nTHE PLENUM IS CLOSED")
    sk = built["floor_skirts"][0]
    sx = [v[0] for v in sk]
    check(min(sx) <= fl.SEAL_FRONT_X and max(sx) >= fl.SEAL_REAR_X,
          f"side skirts run x {min(sx):.0f}-{max(sx):.0f}, seal to seal",
          f"side skirts run x {min(sx):.0f}-{max(sx):.0f}, short of the seals "
          f"at {fl.SEAL_FRONT_X:.0f} and {fl.SEAL_REAR_X:.0f}")
    for end in ("front", "rear"):
        v = built[f"floor_skirt_{end}"][0]
        ys = [abs(p[1]) for p in v]
        x = fl.SEAL_FRONT_X if end == "front" else fl.SEAL_REAR_X
        y_sk = fl.half_width(x) - 19.0
        check(min(ys) <= F["tunnel_inner_y"] and max(ys) >= y_sk,
              f"{end} skirt spans y {min(ys):.0f}-{max(ys):.0f}, plank to side skirt",
              f"{end} skirt spans y {min(ys):.0f}-{max(ys):.0f}, not plank "
              f"({F['tunnel_inner_y']:.0f}) to side skirt ({y_sk:.0f})")
        check(min(p[2] for p in v) <= 0.5,
              f"{end} skirt rides the road", f"{end} skirt does not reach the road")
    for side in ("l", "r"):
        v = built[f"floor_fan_throat_{side}"][0]
        z0 = min(p[2] for p in v)
        low = [p for p in v if p[2] < z0 + 10.0]      # its mouth
        xs = [p[0] for p in low]
        ys = [abs(p[1]) for p in low]
        inside = (min(xs) > fl.SEAL_FRONT_X and max(xs) < fl.SEAL_REAR_X
                  and max(ys) < fl.half_width(max(xs)) - 19.0)
        check(inside, f"fan intake {side} opens inside the plenum, x "
              f"{min(xs):.0f}-{max(xs):.0f}",
              f"fan intake {side} opens outside the plenum")

    area, xc, seal_side, seal_ends = plenum()
    wb = spec.REAR_AXLE_X - spec.FRONT_AXLE_X
    front = (spec.REAR_AXLE_X - xc) / wb
    dp = P["suction_pa"]
    kg = 2 * area * dp / 9.81
    print("\nWHAT IT MAKES")
    print(f"   plan area   {area:.2f} m2 a side, {2 * area:.2f} both")
    print(f"   centroid    x {xc:.0f}, so {front * 100:.1f} % of its load on the front axle")
    print(f"   at {dp / 1000:.1f} kPa  {kg:.0f} kg, at every speed")
    # The CFD measures 14 % under suction x plan area: the plan area counts
    # the tunnel walls, skirts and strakes, which carry no suction, and the
    # pressure is not quite uniform near the intakes.
    check(abs(kg - FAN["downforce_kg"]) / kg < 0.15,
          f"spec's fan downforce {FAN['downforce_kg']:.0f} kg is within 15 % of "
          f"suction x area (the rest is the CFD's measure of the floor round it)",
          f"spec's fan downforce {FAN['downforce_kg']:.0f} kg against {kg:.0f} kg "
          f"from suction x area")

    print("\nTHE LEAK")
    v_jet = math.sqrt(2 * dp / spec.RHO)
    per_m = P["skirt_cd"] * P["skirt_gap"] * MM * v_jet
    seal = seal_side + seal_ends
    q_leak = per_m * seal
    print(f"   seal        {seal:.2f} m a side ({seal_side:.2f} along the skirt "
          f"and the plank, {seal_ends:.2f} across the ends)")
    print(f"   leak        {q_leak:.2f} m3/s a side through a {P['skirt_gap']:.1f} mm "
          f"worn clearance at {v_jet:.0f} m/s")

    print("\nTHE FAN")
    annulus = math.pi * ((FAN["duct_r"] * MM) ** 2 - (FAN["hub_r"] * MM) ** 2)
    q_fan = annulus * FAN["axial_velocity"]
    mouth = P["mouth_m2"]
    loss = P["intake_k"] * 0.5 * spec.RHO * (q_fan / mouth) ** 2
    exit_head = 0.5 * spec.RHO * (q_fan / (math.pi * (spec.FAN_EXHAUST["exit_r"] * MM) ** 2)) ** 2
    dp_fan = dp + loss + exit_head
    u_tip = FAN["rpm"] * 2 * math.pi / 60 * FAN["diameter"] / 2 * MM
    psi = dp_fan / (spec.RHO * u_tip ** 2)
    shaft = FAN["n"] * q_fan * dp_fan / P["fan_eta"] / 1000.0
    check(abs(dp_fan / P["fan_rise_pa"] - 1) < 0.05,
          f"the blades are twisted for {P['fan_rise_pa'] / 1000:.1f} kPa, the "
          f"rise this duty needs", f"the blades are twisted for "
          f"{P['fan_rise_pa'] / 1000:.1f} kPa and the duty needs "
          f"{dp_fan / 1000:.2f}")
    print(f"   design      {q_fan:.2f} m3/s at {dp_fan / 1000:.2f} kPa "
          f"({dp / 1000:.1f} held, {loss:.0f} Pa intake, {exit_head:.0f} Pa jet)")
    check(q_fan >= FLOW_MARGIN * q_leak,
          f"flow {q_fan:.2f} m3/s is {q_fan / q_leak:.1f} x the leak: it holds "
          f"suction with a skirt off the road",
          f"flow {q_fan:.2f} m3/s is only {q_fan / q_leak:.1f} x the leak, under "
          f"{FLOW_MARGIN:.1f}")
    check(psi <= PSI_MAX,
          f"pressure coefficient {psi:.2f} at {u_tip:.0f} m/s tip speed, under "
          f"{PSI_MAX}", f"pressure coefficient {psi:.2f} is past {PSI_MAX}: "
          f"an axial fan at {u_tip:.0f} m/s cannot make {dp_fan / 1000:.1f} kPa")
    check(shaft <= FAN["power_kw"] * 1.001,
          f"shaft power {shaft:.1f} kW both fans at design flow, inside the "
          f"{FAN['power_kw']:.0f} kW rated", f"shaft power {shaft:.1f} kW past "
          f"the {FAN['power_kw']:.0f} kW rated")
    run = FAN["n"] * q_leak * dp_fan / P["fan_eta"] / 1000.0
    print(f"   running     {run:.1f} kW at the running leak, both fans")

    print("\n" + "=" * 62)
    print("PASS  the floor is a sealed plenum the fans can hold"
          if not fails else f"FAIL  {len(fails)} problem(s) with the plenum")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
