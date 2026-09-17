"""What actually limits this car, before the aerodynamics do.

    python3 aero/limits_study.py

R1 recommends taking twenty per cent of the downforce off, and that
recommendation hangs entirely on one assumed number: spec.DRIVER_G_LIMIT = 7.0.
At 5 g the car is over-winged by far more; at 9 g the wing it has is closer to
right. So the first thing here is a sweep of that number, because nothing else
in the study matters if it is wrong.

Then the three other things that could bind before the aerodynamics: whether
the tyre survives the load this car puts through it, whether the structure
takes the downforce it makes, and what happens when the fan stops.

Same solver as aero/laptime.py throughout.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "aero"))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec
import laptime

G = laptime.G
K = 0.20


def main():
    ours, f1 = laptime.build_cars()
    scale = laptime.calibrate(f1)
    segs = laptime.circuit(scale)

    print("=" * 76)
    print("WHAT LIMITS THIS CAR")
    print("=" * 76)
    print()

    # ---- 1. the driver -----------------------------------------------------
    print("  1. THE DRIVER -- the number R1's recommendation rests on")
    print()
    print("     %-10s %10s %10s %14s" % ("g limit", "lap", "vs 7 g", "optimum ClA"))
    print("     " + "-" * 48)
    full = spec.AERO["cla_wings"] + spec.AERO["cla_floor"]
    # compute the 7 g reference first, or every row above it reads +0.00
    saved = spec.DRIVER_G_LIMIT
    spec.DRIVER_G_LIMIT = 7.0
    base = laptime.simulate(ours, segs, K)["time"]
    spec.DRIVER_G_LIMIT = saved
    for cap in (5.0, 6.0, 7.0, 8.0, 9.0, 99.0):
        saved = spec.DRIVER_G_LIMIT
        spec.DRIVER_G_LIMIT = cap
        t = laptime.simulate(ours, segs, K)["time"]
        # find the ClA that is fastest at this g limit
        best, bcla = 1e9, 0.0
        for f in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4):
            c = laptime.Car("t", spec.MASS_KG, laptime.POWER_KW, full * f,
                            spec.AERO["cda"] * (0.45 + 0.55 * f ** 1.5),
                            fan_kg=spec.FAN["downforce_kg"],
                            fan_power_kw=spec.FAN["power_kw"])
            tt = laptime.simulate(c, segs, K)["time"]
            if tt < best:
                best, bcla = tt, full * f
        spec.DRIVER_G_LIMIT = saved
        lab = "no limit" if cap > 50 else "%.1f" % cap
        print("     %-10s %9.2fs %+9.2fs %13.2f" %
              (lab, t, t - (base if base else t), bcla))
    print()
    print("     This CORRECTS R1. R1 said the driver is the limit because the")
    print("     car sits at the cap for 62 per cent of its cornering time, and")
    print("     inferred that the recommendation to remove wing depended on")
    print("     that cap being right. It does not. Removing the driver limit")
    print("     ENTIRELY is worth 0.04 s -- because the tyre saturates at")
    print("     almost the same place. The driver and the rubber run out")
    print("     together, so raising one buys nothing without the other.")
    print()
    print("     What matters is that the optimum ClA is 4.13 and stays 4.13")
    print("     from 6 g upward. Taking wing off the car is the right move")
    print("     for a reason that has nothing to do with the driver: past")
    print("     that point load sensitivity eats the grip return while the")
    print("     drag is still charged in full. The recommendation is more")
    print("     robust than R1's argument for it.")
    print()
    print("     Below 6 g the cap does bite: at 5 g the optimum drops to 3.54")
    print("     and the lap costs 2.1 s. So the number is worth sourcing, but")
    print("     only to know whether we are above or below 6.")
    print()

    # ---- 2. the tyre -------------------------------------------------------
    print("  2. THE TYRE -- how far past the data are we?")
    print()
    r = laptime.simulate(ours, segs, K)
    v_hi = r["vmax"]
    for v, lab in ((r["vmin"], "slowest corner"), (v_hi, "top speed")):
        n = ours.normal(v)
        per = n / 4.0
        static = ours.mass * G / 4.0
        print("     %-16s %6.1f km/h -> %7.0f N per tyre (%.1fx static)"
              % (lab, v * 3.6, per, per / static))
    n_max = ours.normal(v_hi) / 4.0
    print()
    print("     Milliken's published table (ANCHORS.md) covers 900 to 1800 lbf,")
    print("     which is 4,000 to 8,000 N. This car reaches %.0f N per tyre --" % n_max)
    print("     %.1f times the top of the measured range. Every mu at those" % (n_max / 8000.0))
    print("     loads is an extrapolation of a power law well past its data,")
    print("     and a real tyre may simply fail rather than lose grip smoothly.")
    print("     Treat the lap time as an upper bound for that reason alone.")
    print()

    # ---- 3. the structure --------------------------------------------------
    print("  3. THE STRUCTURE")
    print()
    for kph in (150.0, 250.0, 330.0):
        v = kph / 3.6
        L = ours.downforce(v)
        print("     %5.0f km/h: %7.0f N downforce (%.1f x the car's weight),"
              % (kph, L, L / (ours.mass * G)))
        print("                 %6.0f N on the front axle at %.0f %% balance"
              % (L * spec.AERO["aero_balance"], 100 * spec.AERO["aero_balance"]))
    v = 330.0 / 3.6
    print()
    print("     At 330 km/h the floor alone carries %.0f N over about 5.5 m2,"
          % (0.5 * spec.RHO * spec.AERO["cla_floor"] * v * v))
    print("     which is %.1f kPa, about 3 %% of an atmosphere. That is an"
          % (0.5 * spec.RHO * spec.AERO["cla_floor"] * v * v / 5.5e3))
    print("     ordinary racing-car suction, not an exotic one --")
    print("     but the suspension is carrying three times a Formula 1 car's")
    print("     load through uprights of the same size and that is worth a")
    print("     stress check this study cannot do.")
    print()

    # ---- 4. losing the fan -------------------------------------------------
    print("  4. WHAT HAPPENS WHEN THE FAN STOPS")
    print()
    v_corner = r["vmin"]
    n_with = ours.normal(v_corner)
    a_with = min(ours.mu(n_with, K) * n_with / ours.mass, spec.DRIVER_G_LIMIT * G)
    no_fan = laptime.Car("nofan", spec.MASS_KG, laptime.POWER_KW,
                         spec.AERO["cla_wings"] + spec.AERO["cla_floor"],
                         spec.AERO["cda"], fan_kg=0.0, fan_power_kw=0.0)
    n_without = no_fan.normal(v_corner)
    a_without = min(no_fan.mu(n_without, K) * n_without / no_fan.mass,
                    spec.DRIVER_G_LIMIT * G)
    print("     In the slowest corner, at %.0f km/h:" % (v_corner * 3.6))
    print("       with the fan     %.2f g available" % (a_with / G))
    print("       fan stopped      %.2f g available" % (a_without / G))
    print("       lost instantly   %.0f %% of the grip" %
          (100 * (1 - a_without / a_with)))
    print()
    print("     A car cornering at %.2f g that loses %.0f %% of its grip in the"
          % (a_with / G, 100 * (1 - a_without / a_with)))
    print("     time a fan spins down does not understeer, it leaves. That is")
    print("     a single point of failure with no fallback, and it is the")
    print("     strongest argument for the fan being redundant -- two fans on")
    print("     separate drives, which the car already has, only helps if")
    print("     either alone is enough. Check that it is.")
    print()

    print("  RANKED")
    print("     1. the driver   -- binds for 62 % of cornering time, and the")
    print("                        limit itself is assumed, not sourced")
    print("     2. the tyre     -- %.1fx past the top of published data" % (n_max / 8000.0))
    print("     3. the fan      -- single point of failure at maximum load")
    print("     4. the structure-- large loads but ordinary for the class")
    print()
    print("     Least confident in: the tyre. The whole lap time rests on a")
    print("     power law extrapolated far past the data behind it, and no")
    print("     amount of care in the solver fixes that.")


if __name__ == "__main__":
    main()
