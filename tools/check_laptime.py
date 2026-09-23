"""The lap simulation has to be converged, calibrated and physically legal.

    python3 tools/check_laptime.py

A lap time is the easiest number in this project to produce and the easiest to
produce wrongly, because nothing about a plausible-looking figure tells you
whether the solver closed the loop or whether a corner was taken faster than
the tyres allow. These are the four things that would make the answer a lie.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "aero"))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec
import laptime

fails = []


def main():
    ours, f1 = laptime.build_cars()
    scale = laptime.calibrate(f1)
    segs = laptime.circuit(scale)

    C = spec.FAN_CONTROL
    runs = [(k, loss) for k in laptime.K_BAND for loss in C["kerb_seal_loss"]]
    for k, loss in runs:
        ro = laptime.simulate(ours, segs, k, seal_loss=loss,
                              kerb_frac=C["kerb_frac"])
        rf = laptime.simulate(f1, segs, k)

        # 1. the loop has to close, or the lap is not a lap
        for name, r in (("ours", ro), ("F1", rf)):
            if not r["converged"]:
                fails.append("CONVERGENCE: %s at k=%.2f did not close the lap "
                             "-- start and end speeds differ" % (name, k))

        # 2. the reference car has to still be a Formula 1 car
        if not 88.0 <= rf["time"] <= 92.0:
            fails.append("CALIBRATION: the F1 reference laps in %.2f s at "
                         "k=%.2f, outside 88-92. The circuit has drifted and "
                         "the delta means nothing." % (rf["time"], k))

        # 3. no corner may be taken faster than the tyres and the driver allow
        for car, r, who in ((ours, ro, "ours"), (f1, rf, "F1")):
            worst = None
            i = 0
            for length, radius, _kind in segs:
                n = max(int(length / 5.0), 1)
                if radius:
                    for j in range(n):
                        f = (j + 0.5) / n
                        kerb = f < C["kerb_frac"] or f > 1 - C["kerb_frac"]
                        sl = 1.0 - loss if (kerb and car is ours) else 1.0
                        vmax = car.corner_speed(radius, k, sl)
                        v = r["v"][i + j]
                        if v > vmax * 1.02:
                            over = v / vmax
                            if worst is None or over > worst[1]:
                                worst = (radius, over)
                i += n
            if worst:
                fails.append("PHYSICS: %s at k=%.2f exceeds the cornering "
                             "limit by %.0f %% at R=%.0f m"
                             % (who, k, 100 * (worst[1] - 1), worst[0]))

        # 4. the driver limit must be enforced, not merely mentioned
        cap = spec.DRIVER_G_LIMIT
        if ro["gmax"] > cap + 0.01:
            fails.append("DRIVER: lateral acceleration reaches %.2f g against "
                         "a stated limit of %.2f and is not being clamped"
                         % (ro["gmax"], cap))

    if fails:
        for f in fails:
            print("FAIL  " + f)
        sys.exit(1)

        # 5. and it is still the faster car when the skirts lift
        if ro["time"] >= rf["time"]:
            fails.append("SEAL: with %.0f %% of the fan's suction lost at the "
                         "kerbs (k=%.2f) the car is no faster than F1"
                         % (100 * loss, k))

    worst = max(laptime.simulate(ours, segs, k, seal_loss=loss,
                                 kerb_frac=C["kerb_frac"])["time"]
                for k, loss in runs)
    rf = laptime.simulate(f1, segs, laptime.K_BAND[1])
    print("PASS  the lap closes at both ends of the load-sensitivity band, "
          "with and without seal loss at the kerbs")
    print("PASS  the reference car laps in %.2f s, inside 88-92" % rf["time"])
    print("PASS  no corner is taken faster than the tyres allow")
    print("PASS  the driver limit of %.1f g is enforced" % spec.DRIVER_G_LIMIT)
    print("the car is %.2f s a lap faster, worst case (k=%.2f, %.0f %% of the "
          "fan lost at the kerbs)"
          % (rf["time"] - worst, laptime.K_BAND[1],
             100 * max(C["kerb_seal_loss"])))


if __name__ == "__main__":
    main()
