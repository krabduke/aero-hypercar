"""Generate viewer/parts.json from build/parts.csv and car/spec.py."""

import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "car"))
import spec
import tunnel_config  # noqa: E402  # noqa: E402

GROUPS = [
    ("01 Bodywork",            "Bodywork",   "#5A6066"),
    ("02 Floor and Diffuser",  "Floor",      "#46505A"),
    ("03 Wings",               "Wings",      "#6E7A86"),
    ("04 Wheels and Brakes",   "Wheels",     "#3E4246"),
    ("05 Suspension",          "Suspension", "#7C8690"),
    ("06 Fan System",          "Fans",       "#C06A30"),
    ("07 Power Unit",          "Power unit", "#A8763E"),
    ("08 Cooling and Energy",  "Cooling",    "#4E6E7A"),
    ("09 Aero Detail",         "Aero detail", "#8A929A"),
    ("10 Cockpit",             "Cockpit",    "#9A5A52"),
    ("11 Structure and Service", "Structure", "#6A6E72"),
]


def main():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "build", "parts.csv"))))
    groups = []
    for key, label, colour in GROUPS:
        mine = [r for r in rows if r["collection"] == key]
        if not mine:
            continue
        groups.append({"key": key, "label": label, "color": colour,
                       "parts": len(mine),
                       "faces": sum(int(r["faces"]) for r in mine)})
    def pivot(r):
        """Objects that rotate carry their own origin and axis, so the viewer
        can spin a fan about its own shaft and hinge a flap about its own
        hinge line rather than about the middle of the car."""
        if not r.get("pivot_x_mm"):
            return None
        return {"p": [float(r["pivot_x_mm"]), float(r["pivot_y_mm"]),
                      float(r["pivot_z_mm"])],
                "axis": [float(r["axis_x"]), float(r["axis_y"]),
                         float(r["axis_z"])],
                "spin": float(r["spin"]) if r.get("spin") else 1.0,
                "role": r.get("role") or "spin"}

    parts = {}
    for r in rows:
        e = {"g": r["collection"], "mat": r["material"],
             "x0": float(r["x_min_mm"]), "x1": float(r["x_max_mm"]),
             "f": int(r["faces"])}
        pv = pivot(r)
        if pv:
            e["pivot"] = pv
        parts[r["name"]] = e

    speeds = [60, 80, 100, 130, 160, 200, 250, 300]
    grip = [{"kph": k, "ours": spec.lateral_g(k), "f1": spec.f1_lateral_g(k)}
            for k in speeds]
    radii = [20, 30, 45, 60, 90, 120, 180]
    corners = [{"r": r, "ours": spec.corner_speed_kph(r),
                "f1": spec.f1_corner_speed_kph(r)} for r in radii]

    out = {
        "name": spec.NAME, "class": spec.CLASS,
        "length": spec.LENGTH, "width": spec.WIDTH, "height": spec.HEIGHT,
        "wheelbase": spec.WHEELBASE, "mass": spec.MASS_KG,
        "cla": spec.cla(), "cda": spec.cda(),
        "fan_kg": spec.FAN["downforce_kg"],
        "power_kw": 935.0, "hp": 935.0 * 1.341,
        "top_speed": spec.top_speed_kph(),
        "g_limit": spec.DRIVER_G_LIMIT,
        "f1": spec.F1,
        "grip": grip, "corners": corners,
        "palette": {k: {"rgb": list(v[0]), "metal": v[1], "rough": v[2]}
                    for k, v in spec.PALETTE.items()},
        "groups": groups, "parts": parts,
        "tunnel": tunnel_config.config(),
    }
    p = os.path.join(ROOT, "viewer", "parts.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"  -> {p}  ({len(parts)} parts, {len(groups)} groups)")


if __name__ == "__main__":
    main()
