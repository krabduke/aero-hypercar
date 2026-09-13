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
    rads = []
    for sgn in (-1.0, 1.0):
        # Sat upright inside the sidepod, fed by the inlet. An earlier version
        # canted these and the rotation threw them a metre outside the bodywork.
        rv, rf = mesh.box(PT["rad_x"], sgn * PT["rad_y"], PT["rad_z"],
                          *PT["radiator"])
        rads.append((rv, rf))
    out["radiators"] = mesh.join(*rads)
    out["battery"] = mesh.box(PT["battery_x"], 0.0, PT["battery_z"], *PT["battery"])
    out["fuel_cell"] = mesh.box(PT["fuel_x"], 0.0, 330.0, *PT["fuel"])
    return out
