"""Front and rear wings, endplates, pylons."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

FW = spec.FRONT_WING
RW = spec.REAR_WING


def build():
    out = {}
    out.update(_front())
    out.update(_rear())
    return out


def _front():
    """Four-element front wing. The stack is what makes the aero balance
    adjustable without changing the floor, which is the expensive end."""
    out = {}
    elems = []
    for k in range(FW["elements"]):
        frac = k / max(FW["elements"] - 1, 1)
        chord = FW["chord"] * (0.46 + 0.54 * (1 - frac))
        x = FW["x"] + k * (FW["chord"] * 0.20)
        z = FW["z"] + k * (FW["gap"] + 14.0)
        aoa = FW["aoa_root"] + (FW["aoa_tip"] - FW["aoa_root"]) * frac
        elems.append(common.wing_element(
            x, z, FW["span"], chord, aoa, thickness=0.085, camber=0.075,
            taper=0.86, aoa_tip=aoa + 5.0))
    out["front_wing"] = mesh.join(*elems)

    plates = []
    for sgn in (-1.0, 1.0):
        y = sgn * FW["span"] / 2
        plates.append(common.plate(FW["x"] - 80.0, FW["x"] + FW["chord"] + 40.0,
                                   y, 20.0, FW["endplate_h"], FW["endplate_t"],
                                   sweep_top=70.0))
    out["front_endplates"] = mesh.join(*plates)
    return out


def _rear():
    """Two-element rear wing on swan-neck pylons, shown in its loaded
    (non-DRS) position."""
    out = {}
    elems = []
    for k in range(RW["elements"]):
        chord = RW["chord"] * (1.0 - 0.42 * k)
        x = RW["x"] + k * RW["chord"] * 0.46
        z = RW["z"] + k * (RW["gap"] + 26.0)
        aoa = RW["aoa"] + k * 12.0
        elems.append(common.wing_element(
            x, z, RW["span"], chord, aoa, thickness=0.10, camber=0.085,
            taper=0.95))
    out["rear_wing"] = mesh.join(*elems)

    plates = []
    for sgn in (-1.0, 1.0):
        y = sgn * RW["span"] / 2
        plates.append(common.plate(RW["x"] - 120.0, RW["x"] + RW["chord"] + 90.0,
                                   y, RW["z"] - 230.0, RW["z"] + 150.0,
                                   RW["endplate_t"], sweep_top=40.0))
    out["rear_endplates"] = mesh.join(*plates)

    pylons = []
    for sgn in (-1.0, 1.0):
        path = [(RW["x"] + 60.0, sgn * 170.0, RW["z"] - 40.0),
                (RW["x"] - 60.0, sgn * 150.0, RW["z"] - 300.0),
                (RW["x"] - 190.0, sgn * 120.0, RW["z"] - 430.0)]
        pylons.append(mesh.pipe(path, RW["pylon_t"], spec.RES["pipe"]))
    out["rear_pylons"] = mesh.join(*pylons)
    return out
