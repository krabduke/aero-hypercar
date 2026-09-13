"""Monocoque tub, nose, sidepods, engine cover, airbox, halo, cockpit."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

T = spec.TUB
N = spec.NOSE
S = spec.SIDEPOD
H = spec.HALO
SEG = 40


def build():
    out = {}
    out.update(_tub())
    out.update(_nose())
    out.update(_sidepods())
    out.update(_engine_cover())
    out.update(_halo())
    out.update(_cockpit())
    return out


def _tub():
    """Survival cell: narrow and deep at the front, wide and shallow where the
    fuel cell and engine mounts are."""
    rings = []
    n = 16
    for i in range(n):
        f = i / (n - 1)
        x = T["x_front"] + (T["x_rear"] - T["x_front"]) * f
        hw = T["half_w_front"] + (T["half_w_rear"] - T["half_w_front"]) * (f ** 0.75)
        top = T["top_z"] - 130.0 * max(0.0, (f - 0.55) / 0.45) ** 1.4
        rings.append(common.super_section(x, hw, T["floor_z"], top, 3.0, SEG))
    return {"tub": common.loft(rings)}


def _nose():
    """Slender nose on a raised tip, so the front wing works in clean air and
    the floor gets fed from underneath."""
    rings = []
    n = 14
    for i in range(n):
        f = i / (n - 1)
        x = N["tip_x"] + (N["base_x"] - N["tip_x"]) * f
        hw = N["tip_half_w"] + (T["half_w_front"] - N["tip_half_w"]) * (f ** 1.35)
        z_lo = N["tip_z"] - 46.0 * f - 120.0 * f ** 2
        z_hi = N["tip_z"] + 34.0 + (N["base_z"] - N["tip_z"]) * f
        rings.append(common.super_section(x, hw, z_lo, z_hi, 2.5, SEG))
    return {"nose": common.loft(rings)}


def _sidepods():
    """Sidepod with an undercut: the inlet feeds the radiators, and everything
    below the shoulder is shaped to keep the tunnel inlets fed."""
    out = {}
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        rings = []
        n = 14
        for i in range(n):
            f = i / (n - 1)
            x = S["x0"] + (S["x1"] - S["x0"]) * f
            grow = math.sin(math.pi * min(f * 1.15, 1.0)) ** 0.55
            hw = 120.0 + (S["max_half_w"] - 120.0) * grow * 0.5
            yc = sgn * (S["max_half_w"] * 0.62)
            z_lo = 120.0 + 40.0 * f
            z_hi = S["top_z"] - 120.0 * f ** 1.6
            ring = common.super_section(x, hw, z_lo, z_hi, 2.9, SEG)
            rings.append([(px, py + yc, pz) for (px, py, pz) in ring])
        out[f"sidepod_{side}"] = common.loft(rings)
    return out


def _engine_cover():
    """Cover and airbox over the engine, tapering to the rear wing."""
    rings = []
    n = 14
    x0, x1 = T["cockpit_x1"] - 60.0, spec.POWERTRAIN["gearbox_x"] + 300.0
    for i in range(n):
        f = i / (n - 1)
        x = x0 + (x1 - x0) * f
        hw = 250.0 - 150.0 * f ** 1.5
        z_lo = 220.0
        z_hi = 790.0 - 300.0 * f ** 1.3
        rings.append(common.super_section(x, hw, z_lo, z_hi, 2.7, SEG))
    cover = common.loft(rings)

    # roll hoop and airbox intake above the driver
    ax = T["cockpit_x1"] - 40.0
    av, af = mesh.revolve_open(
        [(0.0, 0.0), (0.0, 145.0), (-190.0, 160.0), (-190.0, 0.0)], 28,
        cap_start=True, cap_end=True)
    av = [(ax - pz, py, 700.0 + px) for (px, py, pz) in av]
    return {"engine_cover": cover, "airbox": (av, af)}


def _halo():
    """Titanium halo. Not required by any rulebook here, but a 388 km/h car
    with 7 g corners is not a place to omit driver protection."""
    parts = []
    xf, xr, z, hw, r = H["x_front"], H["x_rear"], H["z"], H["half_w"], H["tube_r"]
    for sgn in (-1.0, 1.0):
        path = [(xr, sgn * hw * 0.62, z - 250.0),
                (xr - 180.0, sgn * hw, z - 60.0),
                (xf + 220.0, sgn * hw * 0.90, z),
                (xf, sgn * 60.0, z - 30.0)]
        parts.append(mesh.pipe(path, r, spec.RES["pipe"]))
    parts.append(mesh.pipe([(xf, 0.0, z - 30.0), (xf - 40.0, 0.0, z - 230.0)],
                           r * 1.1, spec.RES["pipe"]))
    return {"halo": mesh.join(*parts)}


def _cockpit():
    out = {}
    sx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2
    out["seat"] = mesh.box(sx + 90.0, 0.0, 300.0, 620.0, 380.0, 300.0)
    wv, wf = mesh.tube(-26.0, 26.0, 62.0, 118.0, 26)
    wv = [(pz + T["cockpit_x0"] + 120.0, py, px + 560.0) for (px, py, pz) in wv]
    out["steering"] = (wv, wf)
    return out
