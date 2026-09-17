"""Momentum and geometric-envelope screening, not CFD or a pressure correlation."""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                            # noqa: E402

MM = 0.001
RHO = spec.RHO


def flow(fan, exhaust, rho=RHO):
    values = (rho, fan["diameter"], fan["hub_r"], fan["axial_velocity"],
              fan["n"], exhaust["exit_w"], exhaust["exit_h"])
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("Flow inputs must be finite and positive")
    if fan["n"] != int(fan["n"]) or fan["hub_r"] >= fan["diameter"] / 2:
        raise ValueError("Invalid fan count or hub radius")
    # duct_r, not diameter/2. FAN carries both: "diameter" 520 is the ROTOR,
    # "duct_r" 280 is the shroud, and the 20 mm between them is tip clearance.
    # Continuity is set by the passage the air flows through, which is the
    # duct -- the rotor sweeps slightly less than the duct passes, and the
    # difference leaks over the tips rather than vanishing. Sizing the annulus
    # off the rotor made it 0.195 m2 against a 0.229 m2 nozzle and reported a
    # 17.4 % mismatch that was two definitions of "annulus", not a real one.
    annulus = math.pi * ((fan["duct_r"] * MM) ** 2
                         - (fan["hub_r"] * MM) ** 2)
    area = exhaust["exit_w"] * exhaust["exit_h"] * MM ** 2
    volume = annulus * fan["axial_velocity"]
    return {"annulus_m2": annulus, "exit_m2": area,
            "area_mismatch": abs(area / annulus - 1),
            "volume_m3_s": volume, "mass_kg_s": rho * volume,
            "total_mass_kg_s": fan["n"] * rho * volume,
            "exit_m_s": volume / area}


def exit_frame(theta, cant, side=1):
    if not all(math.isfinite(v) for v in (theta, cant)):
        raise ValueError("Exit angles must be finite")
    if not 0 <= theta <= 90 or not 0 <= cant < 90 or side not in (-1, 1):
        raise ValueError("Invalid exit angles or side")
    pitch, yaw = math.radians(theta), side * math.radians(cant)
    axis = (math.cos(pitch) * math.cos(yaw),
            math.cos(pitch) * math.sin(yaw), math.sin(pitch))
    width = (-math.sin(yaw), math.cos(yaw), 0.0)
    height = (-math.sin(pitch) * math.cos(yaw),
              -math.sin(pitch) * math.sin(yaw), math.cos(pitch))
    return axis, width, height


def main():
    result = flow(spec.FAN, spec.FAN_EXHAUST)
    for name, value in result.items():
        print(f"{name:24s} {value:12.6f}")

if __name__ == "__main__":
    main()
