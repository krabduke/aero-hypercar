"""Does this car actually beat a Formula 1 car, and by how much.

    python3 aero/laptime.py

A quasi-steady point-mass lap simulation -- the standard three-pass method,
not anything invented here. Both cars are run through identical physics on an
identical circuit, because the only defensible output is the difference
between them; the absolute number belongs to the synthetic track.

The part that decides the answer is tyre load sensitivity, and it is the part
a naive version leaves out. A tyre's coefficient of friction falls as vertical
load rises, so a car making several times its own weight in downforce does not
convert that downforce into grip one for one. docs/research/ANCHORS.md fixes
the exponent from Milliken's table -- Fy/Fz of 1.10 at 900 lbf falling to 0.97
at 1800 lbf, which is k = 0.181 across a doubling -- against a general rule of
Fz^0.7 to Fz^0.9, so the honest band is 0.15 to 0.25. spec.TYRE_LOAD_SENS says
0.12, which is outside that band on the optimistic side and would flatter this
car; the sweep below uses the sourced band instead and reports both ends.

The other thing that decides it is that the fan's download does not scale with
V^2. It is there at 40 km/h exactly as much as at 300, which is why a fan car
wins in slow corners and why the advantage has to be reported by corner type
rather than as one number.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "car"))

import spec

G = 9.80665
RHO = spec.RHO

# Our car's crank power. spec.top_speed_kph() already assumes 935 kW and takes
# 10 % off it for driveline and fans, so that is the established figure.
POWER_KW = 935.0

# The load-sensitivity band, from ANCHORS. Reported at both ends, always.
K_BAND = (0.15, 0.25)


class Car:
    def __init__(self, name, mass, power_kw, cla, cda, fan_kg=0.0,
                 fan_power_kw=0.0, mu_ref=None):
        self.name = name
        self.mass = mass
        self.power = power_kw * 1000.0
        self.cla = cla
        self.cda = cda
        self.fan_n = fan_kg * G
        self.fan_power = fan_power_kw * 1000.0
        self.mu_ref = mu_ref if mu_ref is not None else spec.F1["mu"]
        # the reference load the coefficient is quoted at: static, per tyre
        self.fz_ref = mass * G / 4.0

    def mu(self, normal_total, k):
        """Coefficient at this vertical load, per tyre."""
        fz = max(normal_total / 4.0, 1.0)
        return self.mu_ref * (fz / self.fz_ref) ** (-k)

    def downforce(self, v):
        return 0.5 * RHO * self.cla * v * v + self.fan_n

    def drag(self, v):
        return 0.5 * RHO * self.cda * v * v

    def normal(self, v):
        return self.mass * G + self.downforce(v)

    def lat_capability(self, v, k):
        """Lateral acceleration available at this speed, m/s^2."""
        n = self.normal(v)
        a = self.mu(n, k) * n / self.mass
        return min(a, spec.DRIVER_G_LIMIT * G)

    def corner_speed(self, radius, k):
        """Fastest steady speed through a corner of this radius."""
        v = 30.0
        for _ in range(60):
            a = self.lat_capability(v, k)
            vn = math.sqrt(max(a * radius, 1e-6))
            if abs(vn - v) < 1e-4:
                break
            v = 0.5 * (v + vn)
        return v

    def tractive(self, v):
        """Force available at the wheels, after the fan takes its share."""
        usable = max(self.power - self.fan_power, 1.0) * 0.90   # driveline
        return usable / max(v, 5.0)

    def accel(self, v, lat_used, k):
        """Longitudinal acceleration with `lat_used` of the ellipse spent."""
        n = self.normal(v)
        grip = self.mu(n, k) * n
        frac = min(lat_used, 0.999)
        long_grip = grip * math.sqrt(1.0 - frac * frac)
        f = min(self.tractive(v), long_grip) - self.drag(v)
        return f / self.mass

    def brake(self, v, lat_used, k):
        """Braking deceleration, positive. Downforce helps here too, and that
        gain is as large as the cornering one and usually forgotten."""
        n = self.normal(v)
        grip = self.mu(n, k) * n
        frac = min(lat_used, 0.999)
        long_grip = grip * math.sqrt(1.0 - frac * frac)
        return (long_grip + self.drag(v)) / self.mass


# --------------------------------------------------------------------------
# The circuit
# --------------------------------------------------------------------------
# Synthetic, and stated as synthetic. It is NOT a real named circuit: quoting
# one would mean quoting corner radii nobody here can source. It is a
# representative mix of corner types with straights between them, calibrated
# so that the spec.F1 reference car laps it in 90 s -- a typical F1 lap. The
# meaningful output is the delta between the two cars on the same track.
#
# (length_m, radius_m); radius None is a straight.
SLOW, MEDIUM, FAST = (25.0, 60.0), (80.0, 160.0), (200.0, 400.0)


def circuit(straight_scale=1.0):
    segs = []
    plan = [
        ("straight", 900.0), ("slow", 45.0), ("straight", 240.0),
        ("medium", 120.0), ("straight", 180.0), ("fast", 260.0),
        ("straight", 420.0), ("slow", 30.0), ("straight", 150.0),
        ("medium", 95.0), ("fast", 330.0), ("straight", 300.0),
        ("slow", 55.0), ("straight", 210.0), ("medium", 140.0),
        ("straight", 260.0), ("fast", 220.0), ("straight", 340.0),
        ("slow", 38.0), ("straight", 190.0), ("medium", 110.0),
    ]
    for kind, val in plan:
        if kind == "straight":
            segs.append((val * straight_scale, None, "straight"))
        else:
            # arc length for a sensible turn angle at that radius
            angle = {"slow": 2.1, "medium": 1.4, "fast": 0.8}[kind]
            segs.append((val * angle, val, kind))
    return segs


def simulate(car, segs, k, ds=5.0):
    """Three passes: corner limits, then accelerate, then brake into them."""
    xs, lim, kind = [], [], []
    for length, radius, knd in segs:
        n = max(int(length / ds), 1)
        vlim = car.corner_speed(radius, k) if radius else 1.0e9
        for _ in range(n):
            xs.append(length / n)
            lim.append(vlim)
            kind.append(knd)
    n = len(xs)
    v = [min(l, 120.0) for l in lim]

    for _ in range(6):
        start = v[-1]
        # forward: accelerate
        for i in range(n):
            prev = v[i - 1] if i else start
            lat = (prev * prev / (lim[i] * lim[i])) if lim[i] < 1e8 else 0.0
            a = car.accel(prev, min(lat, 1.0), k)
            v[i] = min(lim[i], math.sqrt(max(prev * prev + 2 * a * xs[i], 1.0)))
        # backward: brake into what is coming
        for i in range(n - 1, -1, -1):
            nxt = v[(i + 1) % n]
            lat = (nxt * nxt / (lim[i] * lim[i])) if lim[i] < 1e8 else 0.0
            b = car.brake(v[i], min(lat, 1.0), k)
            v[i] = min(v[i], math.sqrt(max(nxt * nxt + 2 * b * xs[i], 1.0)))
        if abs(v[-1] - start) < 0.5:
            break

    t = sum(xs[i] / max(v[i], 1.0) for i in range(n))
    by = {}
    for i in range(n):
        d = by.setdefault(kind[i], [0.0, 0.0])
        d[0] += xs[i] / max(v[i], 1.0)
        d[1] += xs[i]
    converged = abs(v[-1] - v[0]) < 5.0
    return {"time": t, "v": v, "kind": kind, "by": by,
            "vmin": min(v), "vmax": max(v),
            "gmax": max(car.lat_capability(x, k) for x in v) / G,
            "converged": converged}


def build_cars():
    ours = Car("VX-1 Vortex", spec.MASS_KG, POWER_KW,
               spec.AERO["cla_wings"] + spec.AERO["cla_floor"],
               spec.AERO["cda"], fan_kg=spec.FAN["downforce_kg"],
               fan_power_kw=spec.FAN["power_kw"])
    f1 = Car("Formula 1 reference", spec.F1["mass"], spec.F1["power_kw"],
             spec.F1["cla"], spec.F1["cda"])
    return ours, f1


def calibrate(f1, k=0.18):
    """Stretch the straights until the reference car laps in 90 s."""
    lo, hi = 0.3, 3.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        t = simulate(f1, circuit(mid), k)["time"]
        if t < 90.0:
            lo = mid
        else:
            hi = mid
        if abs(t - 90.0) < 0.05:
            break
    return 0.5 * (lo + hi)


def main():
    ours, f1 = build_cars()
    scale = calibrate(f1)
    segs = circuit(scale)
    total = sum(s[0] for s in segs)

    print("=" * 74)
    print("LAP SIMULATION -- %s against a Formula 1 car" % ours.name)
    print("=" * 74)
    print()
    print("Circuit: synthetic, %.0f m, calibrated so the reference car laps in"
          % total)
    print("90 s. It is not a real named circuit and the absolute time means")
    print("nothing; the delta between two cars on the same track is the result.")
    print()
    print("  %-22s %14s %14s" % ("", ours.name, "F1 reference"))
    print("  " + "-" * 52)
    rows = [
        ("mass, kg", ours.mass, f1.mass),
        ("power, kW", POWER_KW, f1.power / 1000.0),
        ("ClA", ours.cla, f1.cla),
        ("CdA", ours.cda, f1.cda),
        ("fan download, kg", ours.fan_n / G, 0.0),
    ]
    for label, a, b in rows:
        print("  %-22s %14.2f %14.2f" % (label, a, b))
    print()

    print("  LAP TIMES")
    print("  %-26s %10s %10s %10s" % ("load sensitivity k", ours.name[:10],
                                      "F1", "delta"))
    print("  " + "-" * 58)
    results = {}
    for k in K_BAND:
        ro = simulate(ours, segs, k)
        rf = simulate(f1, segs, k)
        results[k] = (ro, rf)
        print("  k = %-22.2f %9.2fs %9.2fs %9.2fs" %
              (k, ro["time"], rf["time"], ro["time"] - rf["time"]))
    print()

    k = K_BAND[1]                      # report the detail at the pessimistic end
    ro, rf = results[k]
    print("  WHERE THE TIME COMES FROM (at the pessimistic k = %.2f)" % k)
    print("  Note that a large share of the gain is on the straights and is")
    print("  power, not aerodynamics: 935 kW against 750. Under a ruleset with")
    print("  no fuel-flow or energy limit that is legitimate, but it should not")
    print("  be reported as an aerodynamic result.")
    print("  %-12s %10s %10s %10s %10s" %
          ("section", "ours", "F1", "delta", "of total"))
    print("  " + "-" * 56)
    tot_delta = ro["time"] - rf["time"]
    for knd in ("slow", "medium", "fast", "straight"):
        a = ro["by"].get(knd, [0, 0])[0]
        b = rf["by"].get(knd, [0, 0])[0]
        share = (100.0 * (a - b) / tot_delta) if abs(tot_delta) > 1e-6 else 0.0
        print("  %-12s %9.2fs %9.2fs %9.2fs %9.0f%%" % (knd, a, b, a - b, share))
    print()

    print("  %-26s %12s %12s" % ("", ours.name[:12], "F1"))
    print("  " + "-" * 52)
    print("  %-26s %11.1f %12.1f" % ("min corner speed, km/h",
                                     ro["vmin"] * 3.6, rf["vmin"] * 3.6))
    print("  %-26s %11.1f %12.1f" % ("top speed, km/h",
                                     ro["vmax"] * 3.6, rf["vmax"] * 3.6))
    print("  %-26s %11.2f %12.2f" % ("max lateral g", ro["gmax"], rf["gmax"]))
    print("  %-26s %11s %12s" % ("converged",
                                 "yes" if ro["converged"] else "NO",
                                 "yes" if rf["converged"] else "NO"))
    print()

    cap = spec.DRIVER_G_LIMIT
    if ro["gmax"] >= cap - 0.01:
        print("  THE DRIVER IS THE LIMIT, NOT THE CAR. Lateral acceleration is")
        print("  clamped at %.1f g for %s. Past that point more downforce buys"
              % (cap, ours.name))
        print("  nothing and its drag is pure loss -- which is a design")
        print("  finding, not a modelling artefact.")
        print()
    print("  Assumptions: mu_ref %.2f for both cars, same rubber. Load"
          % ours.mu_ref)
    print("  sensitivity swept over the sourced band %.2f-%.2f; spec says"
          % K_BAND)
    print("  %.2f, which is outside it on the optimistic side." %
          spec.TYRE_LOAD_SENS)


if __name__ == "__main__":
    main()
