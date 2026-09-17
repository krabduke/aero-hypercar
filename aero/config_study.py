"""Is this the right car, given the ruleset says almost nothing?

    python3 aero/config_study.py

The lap simulation answers "how fast is this car". This answers the question
underneath it: given four wheels, a combustion or hybrid engine and a lap to
complete, is the car we have the one worth building? Every number here comes
out of the same solver `aero/laptime.py` uses, so nothing can disagree with
the headline result by construction.

The finding that drives everything else is already visible in the lap sim:
lateral acceleration clamps at the driver's 7 g through every slow and medium
corner. When the driver is the limit, downforce past that point buys no grip
and its drag is a straight loss -- so the interesting question is not how much
more downforce can be made, but how much of it is doing anything.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "aero"))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec
import laptime

K = 0.20                       # middle of the sourced band, ANCHORS.md


def run(mass=None, cla=None, cda=None, fan_kg=None, fan_kw=None,
        mu=None, power=None, segs=None, scale=None):
    ours = laptime.Car(
        "trial",
        mass if mass is not None else spec.MASS_KG,
        power if power is not None else laptime.POWER_KW,
        cla if cla is not None else spec.AERO["cla_wings"] + spec.AERO["cla_floor"],
        cda if cda is not None else spec.AERO["cda"],
        fan_kg=fan_kg if fan_kg is not None else spec.FAN["downforce_kg"],
        fan_power_kw=fan_kw if fan_kw is not None else spec.FAN["power_kw"],
        mu_ref=mu)
    return laptime.simulate(ours, segs, K)


def main():
    _, f1 = laptime.build_cars()
    scale = laptime.calibrate(f1)
    segs = laptime.circuit(scale)
    base = run(segs=segs)
    base_t = base["time"]

    print("=" * 76)
    print("CONFIGURATION STUDY -- is this the right car?")
    print("=" * 76)
    print()
    print("  Baseline: %.0f kg, ClA %.2f, CdA %.2f, fan %.0f kg on %.0f kW."
          % (spec.MASS_KG, spec.AERO["cla_wings"] + spec.AERO["cla_floor"],
             spec.AERO["cda"], spec.FAN["downforce_kg"], spec.FAN["power_kw"]))
    print("  Lap %.2f s. Load sensitivity k = %.2f throughout." % (base_t, K))
    print()

    # ---- 1. how much of the lap is the driver, not the car? --------------
    print("  1. WHO IS THE LIMIT")
    n = len(base["v"])
    at_cap = 0
    car = laptime.Car("x", spec.MASS_KG, laptime.POWER_KW,
                      spec.AERO["cla_wings"] + spec.AERO["cla_floor"],
                      spec.AERO["cda"], fan_kg=spec.FAN["downforce_kg"],
                      fan_power_kw=spec.FAN["power_kw"])
    cap = spec.DRIVER_G_LIMIT * laptime.G
    corner = 0
    for i, v in enumerate(base["v"]):
        if base["kind"][i] == "straight":
            continue
        corner += 1
        nrm = car.normal(v)
        raw = car.mu(nrm, K) * nrm / car.mass
        if raw >= cap - 1e-6:
            at_cap += 1
    print("     %.0f %% of the car's time in corners is spent at the driver's"
          % (100.0 * at_cap / max(corner, 1)))
    print("     %.1f g limit, with the tyres able to give more." % spec.DRIVER_G_LIMIT)
    print()

    # ---- 2. what is the downforce actually worth? ------------------------
    print("  2. IS 5.90 ClA USEFUL?")
    print("     %-14s %10s %10s" % ("ClA", "lap", "vs base"))
    full = spec.AERO["cla_wings"] + spec.AERO["cla_floor"]
    for f in (0.6, 0.8, 1.0, 1.2, 1.4):
        cla = full * f
        # drag scales with the wing part of the aero, roughly as ClA^1.5
        cda = spec.AERO["cda"] * (0.45 + 0.55 * f ** 1.5)
        t = run(cla=cla, cda=cda, segs=segs)["time"]
        print("     %-14.2f %9.2fs %+9.2fs" % (cla, t, t - base_t))
    print()

    # ---- 3. the fan ------------------------------------------------------
    print("  3. HOW MUCH FAN")
    print("     %-10s %-10s %10s %10s" % ("kg", "kW", "lap", "vs base"))
    for kg, kw in ((0, 0), (325, 26), (650, 62), (975, 110), (1300, 172)):
        t = run(fan_kg=kg, fan_kw=kw, segs=segs)["time"]
        print("     %-10d %-10d %9.2fs %+9.2fs" % (kg, kw, t, t - base_t))
    print()

    # ---- 4. mass ---------------------------------------------------------
    print("  4. MASS")
    print("     %-10s %10s %10s" % ("kg", "lap", "vs base"))
    for m in (550, 625, 700, 800, 900):
        t = run(mass=m, segs=segs)["time"]
        print("     %-10d %9.2fs %+9.2fs" % (m, t, t - base_t))
    print()

    # ---- 5. tyres --------------------------------------------------------
    print("  5. TYRES -- the lever nobody has pulled")
    print("     No tyre regulations at all. Load sensitivity is a contact-")
    print("     pressure effect, so a wider tyre at the same load runs cooler")
    print("     and keeps more of its mu. Treating width as a multiplier on")
    print("     mu_ref, which is the crude but defensible first order:")
    print("     %-16s %10s %10s" % ("mu_ref", "lap", "vs base"))
    for mu in (1.75, 1.90, 2.05, 2.20):
        t = run(mu=mu, segs=segs)["time"]
        print("     %-16.2f %9.2fs %+9.2fs" % (mu, t, t - base_t))
    print()

    print("  6. POWER")
    print("     %-10s %10s %10s" % ("kW", "lap", "vs base"))
    for p in (750, 935, 1100, 1300):
        t = run(power=p, segs=segs)["time"]
        print("     %-10d %9.2fs %+9.2fs" % (p, t, t - base_t))
    print()
    print("  All figures from the same solver as aero/laptime.py, k = %.2f."
          % K)


if __name__ == "__main__":
    main()
