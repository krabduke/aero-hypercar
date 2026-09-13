"""Power unit, gearbox, radiators, battery and fuel cell.

The engine is the RX-8V from the sibling project, imported and positioned --
not re-modelled. It is mounted as a fully stressed member between the tub and
the gearbox, which is why the car can be this short.
"""

import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes

PT = spec.POWERTRAIN


def _load_engine():
    """Import the power-unit generators with powerunit/ ahead on the path, so
    their modules resolve their own `spec` rather than the car's."""
    saved = {k: v for k, v in sys.modules.items()
             if k in ("spec", "mesh", "airfoil") or k.startswith("parts")}
    for k in list(saved):
        del sys.modules[k]
    pu = os.path.join(HERE, "powerunit")
    sys.path.insert(0, pu)
    try:
        espec = importlib.import_module("spec")
        espec.RES.update({"revolve": 26, "small_revolve": 12, "pipe": 8})
        mods = [importlib.import_module(f"parts.{m}") for m in
                ("block", "bottomend", "heads", "induction", "turbo",
                 "hybrid", "drive")]
        built = {}
        for m in mods:
            built.update(m.build())
        return built, espec
    finally:
        sys.path.remove(pu)
        for k in list(sys.modules):
            if k in ("spec", "mesh", "airfoil") or k.startswith("parts"):
                del sys.modules[k]
        sys.modules.update(saved)


def build():
    out = {}
    built, espec = _load_engine()
    # the engine's +x is its crank axis; the car's +x is rearward, and the
    # engine sits with its flywheel toward the gearbox
    parts = []
    for name, (verts, faces) in built.items():
        parts.append(([(x + PT["engine_x"], y, z + PT["engine_z"])
                       for (x, y, z) in verts], faces))
    out["engine"] = mesh.join(*parts)

    gx = PT["gearbox_x"]
    gv, gf = mesh.tube(gx, gx + PT["gearbox_len"], 0.0, PT["gearbox_r"], 32)
    out["gearbox"] = ([(px, py, pz + PT["gearbox_z"]) for (px, py, pz) in gv],
                      gf)
    # A radiator drawn as a solid block is the laziest part on a car. These
    # are cores: tubes with fin packs between them, in a frame, with header
    # tanks top and bottom and the hoses that feed them.
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        x, y, z = PT["rad_x"], sgn * PT["rad_y"], PT["rad_z"]
        sx, sy, sz = PT["radiator"]
        out[f"radiator_{tag}"] = shapes.core(x, y, z, sx, sy, sz,
                                             n_tubes=16, n_fins=30)
        tanks = []
        for dz in (-sz / 2 - 26.0, sz / 2 + 26.0):
            tanks.append(shapes.rounded_box(x, y, z + dz, sx * 0.98,
                                            sy * 1.25, 46.0, 18.0))
        out[f"rad_tanks_{tag}"] = mesh.join(*tanks)
        hoses = []
        for dz, xe in ((-sz / 2 - 26.0, -1.0), (sz / 2 + 26.0, 1.0)):
            hoses.append(mesh.pipe(
                [(x + sx * 0.42 * xe, y, z + dz),
                 (x + sx * 0.70 * xe, y * 0.62, z + dz * 0.7),
                 (PT["engine_x"], y * 0.28, PT["engine_z"] + dz * 0.5)],
                34.0, 12))
        out[f"rad_hoses_{tag}"] = mesh.join(*hoses)

    bx, by, bz = PT["battery_x"], 0.0, PT["battery_z"]
    sx, sy, sz = PT["battery"]
    out["battery"] = shapes.finned_case(bx, by, bz, sx, sy, sz,
                                        n_fins=12, fin_h=9.0, fin_t=4.0,
                                        r=14.0, side=-1.0)
    mods = []
    for i in range(5):
        f = (i + 0.5) / 5
        mods.append(shapes.rounded_box(bx - sx / 2 + sx * f, by, bz,
                                       sx / 6.2, sy * 0.8, sz * 0.7, 6.0))
    out["battery_modules"] = mesh.join(*mods)

    # a fuel cell is a bladder in a shaped bay, not a cuboid
    fx, fy, fz = PT["fuel_x"], 0.0, 330.0
    sx, sy, sz = PT["fuel"]
    out["fuel_cell"] = shapes.rounded_box(fx, fy, fz, sx, sy, sz,
                                          r=60.0, seg=6, draft=3.0)
    out["fuel_fittings"] = mesh.join(
        mesh.pipe([(fx + sx * 0.3, 0.0, fz + sz * 0.5),
                   (fx + sx * 0.6, 0.0, fz + sz * 0.62)], 24.0, 10),
        shapes.rounded_box(fx - sx * 0.3, 0.0, fz + sz * 0.5 + 18.0,
                           110.0, 110.0, 36.0, 12.0))
    return out
