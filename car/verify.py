"""Check the built car against spec.py, and against the Formula 1 car it is
meant to beat.

Dimensions are measured out of build/parts.csv. The performance numbers come
from the first-order model in spec.py -- load-sensitive tyres, fan downforce
independent of speed, and a driver g-limit, because without those three the
model happily predicts twenty lateral g.
"""

import csv, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import spec  # noqa: E402


class Check:
    def __init__(self):
        self.fails, self.n = [], 0

    def band(self, label, got, lo, hi, unit="", note=""):
        self.n += 1
        if lo <= got <= hi:
            print(f"  ok  {label:40s} {got:9.2f}{unit}  [{lo:g}..{hi:g}] {note}")
            return True
        self.fails.append(f"{label}: {got:.2f}{unit} outside [{lo:g}..{hi:g}]")
        return False

    def true(self, label, cond, detail=""):
        self.n += 1
        if cond:
            print(f"  ok  {label:40s} {detail}")
            return True
        self.fails.append(f"{label}: {detail}")
        return False


def main():
    path = os.path.join(ROOT, "build", "parts.csv")
    if not os.path.exists(path):
        print("build/parts.csv missing -- run `make build` first")
        return 1
    rows = list(csv.DictReader(open(path)))
    by = {r["name"]: r for r in rows}
    f = lambda r, k: float(r[k])
    c = Check()

    print("\nDIMENSIONS")
    x0 = min(f(r, "x_min_mm") for r in rows); x1 = max(f(r, "x_max_mm") for r in rows)
    y0 = min(f(r, "y_min_mm") for r in rows); y1 = max(f(r, "y_max_mm") for r in rows)
    z0 = min(f(r, "z_min_mm") for r in rows); z1 = max(f(r, "z_max_mm") for r in rows)
    c.band("overall length", x1 - x0, 4000.0, 5600.0, " mm")
    c.band("overall width", y1 - y0, 1500.0, 2100.0, " mm")
    c.band("overall height", z1 - z0, 800.0, 1300.0, " mm")
    c.band("wheelbase", spec.WHEELBASE, 2800.0, 3700.0, " mm")
    c.band("front track", spec.TRACK_FRONT, 1400.0, 1800.0, " mm")
    c.true("track is inside overall width",
           spec.TRACK_FRONT + spec.WHEEL["front_w"] <= spec.WIDTH + 60.0,
           f"{spec.TRACK_FRONT + spec.WHEEL['front_w']:.0f} vs {spec.WIDTH:.0f} mm")
    c.band("rake (rear minus front ride height)",
           spec.RIDE_HEIGHT_REAR - spec.RIDE_HEIGHT_FRONT, 10.0, 70.0, " mm",
           "feeds the tunnels")

    print("\nMASS AND BALANCE")
    c.band("mass", spec.MASS_KG, 600.0, 850.0, " kg",
           f"F1 minimum {spec.F1['mass']:.0f} kg")
    c.band("rear weight distribution", spec.MASS_DIST_REAR * 100, 52.0, 62.0, " %")
    c.band("centre of gravity height", spec.CG_HEIGHT, 200.0, 340.0, " mm")
    c.true("lighter than the F1 minimum", spec.MASS_KG < spec.F1["mass"],
           f"{spec.F1['mass'] - spec.MASS_KG:.0f} kg advantage")

    print("\nAERODYNAMICS")
    c.band("total ClA", spec.cla(), 4.5, 7.0, "",
           f"F1 reference {spec.F1['cla']:.2f}")
    c.band("ClA with active aero shed", spec.cla(drs=True), 3.0, 6.0, "")
    c.band("lift-to-drag at full downforce", spec.cla() / spec.cda(), 2.5, 5.0, "")
    c.band("aero balance", spec.AERO["aero_balance"] * 100, 40.0, 50.0, " %front")
    c.band("fan downforce", spec.FAN["downforce_kg"], 300.0, 1200.0, " kg",
           "near constant with speed")
    c.band("fan power draw", spec.FAN["power_kw"] * spec.FAN["n"] / 2, 20.0, 120.0,
           " kW", "from the hybrid system")

    print("\nGRIP -- the whole point")
    for kph in (80, 150, 250):
        ours, theirs = spec.lateral_g(kph), spec.f1_lateral_g(kph)
        c.true(f"out-grips F1 at {kph} km/h", ours > theirs,
               f"{ours:.2f} g vs {theirs:.2f} g  (+{(ours/theirs-1)*100:.0f} %)")
    c.true("biggest advantage is at low speed",
           (spec.lateral_g(80)/spec.f1_lateral_g(80)) >
           (spec.lateral_g(250)/spec.f1_lateral_g(250)),
           "which is what a fan buys you")
    c.band("peak sustained lateral g", spec.lateral_g(250), 0.0,
           spec.DRIVER_G_LIMIT, " g", "driver limit")

    print("\nCORNER SPEEDS vs F1")
    for r in (25, 60, 120):
        a, b = spec.corner_speed_kph(r), spec.f1_corner_speed_kph(r)
        c.true(f"faster through an R{r} m corner", a > b + 1.0,
               f"{a:.0f} vs {b:.0f} km/h  (+{a-b:.0f})")

    print("\nPOWER")
    c.band("power to weight", spec.power_to_weight(), 0.95, 1.8, " kW/kg",
           f"F1 {spec.f1_power_to_weight():.2f}")
    c.band("top speed", spec.top_speed_kph(), 300.0, 450.0, " km/h")
    c.true("more power per kilogram than F1",
           spec.power_to_weight() > spec.f1_power_to_weight(),
           f"+{(spec.power_to_weight()/spec.f1_power_to_weight()-1)*100:.0f} %")

    print("\nCOMPLETENESS")
    want = ["tub", "nose", "sidepod_l", "sidepod_r", "engine_cover", "airbox",
            "halo", "seat", "floor_plank", "tunnel_l", "tunnel_r",
            "floor_strakes", "floor_skirts", "front_wing", "front_endplates",
            "rear_wing", "rear_endplates", "rear_pylons", "tyres", "wheelrims",
            "discs", "calipers", "uprights", "wishbones", "pushrods",
            "driveshafts", "fanduct", "fan_rotors", "fan_motors", "engine",
            "gearbox", "radiators", "battery", "fuel_cell"]
    missing = [w for w in want if w not in by]
    c.true("key components present", not missing, f"{len(want)} checked")
    for m in missing:
        c.fails.append(f"missing component: {m}")
    c.true("every object has a material", all(r["material"] for r in rows),
           f"{len(rows)} objects")
    c.true("no empty meshes", all(int(r["verts"]) > 0 for r in rows), "all non-empty")

    print("\n" + "=" * 70)
    if c.fails:
        print(f"FAIL  {len(c.fails)} of {c.n} checks")
        for x in c.fails:
            print("   x " + x)
        return 1
    print(f"PASS  all {c.n} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
