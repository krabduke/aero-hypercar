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


def _wheel_clashes():
    """(ok, detail) -- does any vertex of a non-corner part lie inside a wheel?

    A wheel is a cylinder about its own y axis. A part is allowed inside it
    only if it belongs to that corner: the hub, brakes, uprights, suspension
    and the brake duct all legitimately live there.
    """
    from parts import (chassis, floor as floormod, wings, wheels, suspension,
                       fans, powertrain, aerodetail, detail)
    # The prefixes have to be the ones the parts are actually called.
    # "brake_duct" matched nothing -- every duct on this car is `bduct_` --
    # and the hub, the steering arm, the tether and the track rod were all
    # missing, though a track rod's outer end bolts to the steering arm and
    # the steering arm bolts to the upright, which is 70 mm inside the rim.
    # A corner's own hardware belongs in its own wheel.
    allowed = ("tyre", "rim", "wheel", "disc", "caliper", "brake_pad",
               "upright", "hub", "wishbone", "pushrod", "pullrod",
               "driveshaft", "bduct_", "rocker", "steering_arm", "tether",
               "trackrod")
    built = {}
    for m in (chassis, floormod, wings, suspension, fans, powertrain,
              aerodetail, detail):
        try:
            built.update(m.build())
        except Exception as exc:                      # pragma: no cover
            return False, f"could not rebuild geometry: {exc}"

    hits = []
    for (tag, cx, cy, cw, od) in wheels.corners():
        r = od / 2
        hw = cw / 2
        cz = od / 2
        for name, (verts, _) in built.items():
            if name.startswith(allowed):
                continue
            for (x, y, z) in verts:
                if abs(y - cy) > hw - 12.0:
                    continue
                if (x - cx) ** 2 + (z - cz) ** 2 < (r - 12.0) ** 2:
                    hits.append(f"{name} into wheel {tag}")
                    break
    if hits:
        return False, "; ".join(sorted(set(hits))[:12])
    return True, "4 corners clear"


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
    c.band("overall width", y1 - y0, 1500.0, 2000.0, " mm")
    # Nothing may stand outboard of the tyres. The pit crew's wheel gun
    # sockets used to, by 24 mm, which made them the widest objects on the
    # car and put it 49 mm over the legal width.
    tyre_y = max(abs(float(r["y_min_mm"])) for r in rows
                 if r["name"].startswith("tyre_"))
    widest = max(rows, key=lambda r: max(abs(float(r["y_min_mm"])),
                                         abs(float(r["y_max_mm"]))))
    c.true("nothing stands outboard of the tyres",
           widest["name"].startswith("tyre_"),
           f"widest is {widest['name']}")
    # The driver's feet have to be behind the front axle line. The pedal box
    # sat 405 mm ahead of it, which is the one place a survival cell is not
    # allowed to put them.
    c.true("driver's feet are behind the front axle",
           float(by["pedal_box"]["x_min_mm"]) >= spec.FRONT_AXLE_X,
           f"pedals from {float(by['pedal_box']['x_min_mm']):.0f} mm, "
           f"axle at {spec.FRONT_AXLE_X:.0f} mm")
    # The plank is the reference plane: it is the lowest thing on the car.
    lowest = min(rows, key=lambda r: float(r["z_min_mm"]))
    c.true("the plank is the lowest part",
           float(by["floor_plank"]["z_min_mm"])
           <= float(lowest["z_min_mm"]) + 0.5,
           f"lowest is {lowest['name']} at "
           f"{float(lowest['z_min_mm']):.1f} mm")
    c.band("overall height", z1 - z0, 800.0, 1300.0, " mm")
    c.band("wheelbase", spec.WHEELBASE, 2800.0, 3700.0, " mm")
    # The axles have to sit ON the car. Left at x = 0 the front axle was at
    # the nose tip: no front overhang, the front wing behind the front wheels,
    # and a 1.4 m tail. Nothing else in the suite noticed.
    fo = spec.FRONT_AXLE_X - x0
    ro = x1 - spec.REAR_AXLE_X
    c.band("front overhang", fo, 400.0, 1400.0, " mm", "nose to front axle")
    c.band("rear overhang", ro, 400.0, 1500.0, " mm", "rear axle to tail")
    c.true("overhangs are balanced", 0.45 < fo / max(ro, 1.0) < 2.2,
           f"front/rear {fo / max(ro, 1.0):.2f}")
    fw = by.get("front_wing_main")
    if fw:
        c.true("front wing is ahead of the front axle",
               float(fw["x_max_mm"]) < spec.FRONT_AXLE_X,
               f"TE at {float(fw['x_max_mm']):.0f} mm, axle at "
               f"{spec.FRONT_AXLE_X:.0f} mm")
    fl = by.get("floor_plank")
    if fl:
        c.true("floor starts behind the front tyre",
               float(fl["x_min_mm"]) > spec.FRONT_AXLE_X
               + spec.WHEEL["front_od"] / 2,
               f"floor from {float(fl['x_min_mm']):.0f} mm")
    c.true("nothing below the track surface", z0 > -1.0,
           f"lowest point {z0:.0f} mm")

    # Nothing but the corner's own hardware may occupy a wheel's space. The
    # fan shrouds sat straight through both rear wheels and every other check
    # passed, because none of them compared one part against another.
    #
    # Bounding boxes are useless here -- the floor and the fan duct both span
    # the car, so their boxes overlap a wheel's box whatever their real shape.
    # The geometry layer is pure Python, so this rebuilds it and tests actual
    # vertices against each wheel's swept cylinder.
    c.true("nothing occupies a wheel's space", *_wheel_clashes())
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

    # The car does not re-model its engine, it vendors the sibling project's
    # generators. That claim is only true while the copy is current, and it
    # had silently fallen 111 parts behind.
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import vendor_engine
        ok_v, why = vendor_engine.check()
    except Exception as exc:
        ok_v, why = False, str(exc)
    c.true("vendored engine is current", ok_v, why)

    print("\nCOMPLETENESS")
    # the nose, tub and engine cover are one continuous lofted surface now,
    # which is what lets the body be waisted and curvature-continuous
    want = ["tub", "sidepod_l", "sidepod_r", "sidepod_inlets", "sharkfin",
            "cockpit_coaming", "halo", "seat", "headrest", "steering",
            "floor_plank", "floor_surface", "tunnel_l", "tunnel_r",
            "floor_strake_l1", "floor_skirts", "floor_fence_l1",
            "front_wing_main", "front_flap_1", "front_flap_3",
            "front_endplate_l", "front_diveplane_l1", "front_y250_vanes",
            "rear_wing_main", "rear_flap", "rear_endplate_r",
            "rear_pylon_l", "rear_louvre_r1", "rear_gurney", "beam_wing",
            "bargeboard_l1", "turning_vane_r1", "floor_edge_wings",
            "mirrors", "cameras", "rainlight", "exhaust", "cooling_louvres",
            "tyre_fl", "tyre_rr", "rim_fl", "wheelcover_fl", "wheelnut_rr",
            "disc_fl", "caliper_fl", "upright_rr",
            "wishbone_fl_upper_fwd", "pushrod_rr", "trackrod_fl",
            "rocker_fl", "driveshaft_rl",
            "dampers_f", "antiroll_f", "torsion_bars_r", "heave_f",
            "steering_rack", "steering_column",
            "bduct_inlet_fl", "bduct_drum_rr", "bduct_fence_fr",
            "brake_lines", "master_cylinders", "pedal_box", "wiring_loom",
            "harness", "dash", "extinguisher", "bulkhead_dash",
            "side_intrusion", "gun_sockets", "tyre_sensors",
            "exit_louvres_l", "fanduct", "fan_rotor_l", "fan_rotor_r",
            "fan_stators", "engine", "gearbox", "radiator_l", "radiator_r",
            "rad_tanks_l", "rad_hoses_r", "battery", "battery_modules",
            "fuel_cell"]
    want = [w for w in want if w not in ("fan_rotors", "rear_wing")]
    missing = [w for w in want if w not in by]
    c.true("key components present", not missing, f"{len(want)} checked")
    for m in missing:
        c.fails.append(f"missing component: {m}")
    c.true("every object has a material", all(r["material"] for r in rows),
           f"{len(rows)} objects")
    # A name in MATERIAL_MAP that is not in PALETTE silently falls back to the
    # default, so a part comes out the wrong material and nothing says so.
    # Caught exactly that on the turbofan: six parts were assigned a
    # "steel_polished" that does not exist -- the palette calls it "steel".
    unknown = sorted({v for v in spec.MATERIAL_MAP.values()
                      if v not in spec.PALETTE})
    c.true("every material name is real", not unknown,
           f"{len(spec.PALETTE)} in palette"
           + (f", unknown: {', '.join(unknown)}" if unknown else ""))
    c.true("no empty meshes", all(int(r["verts"]) > 0 for r in rows), "all non-empty")
    c.true("body is one continuous surface", "nose" not in by and "tub" in by,
           "nose, tub and cover lofted together")
    c.band("object count", len(rows), 60, 400, "", "assemblies")

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
