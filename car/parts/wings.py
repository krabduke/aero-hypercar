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
        # footplate: turns the flow out around the front tyre, which is the
        # single dirtiest thing on the car
        plates.append(common.plate(FW["x"] + 60.0, FW["x"] + FW["chord"] + 30.0,
                                   y + sgn * 44.0, 16.0, 62.0, 8.0))
    out["front_endplates"] = mesh.join(*plates)

    # cascade winglets above the outboard wing
    cas = []
    for sgn in (-1.0, 1.0):
        for k in range(2):
            cas.append(common.wing_element(
                FW["x"] + 120.0 + k * 90.0, FW["z"] + 150.0 + k * 62.0,
                420.0, 150.0 - k * 34.0, 16.0 + k * 6.0,
                thickness=0.08, camber=0.08, n_span=5, taper=0.8,
                y0=sgn * (FW["span"] / 2 - 250.0)))
    out["front_cascades"] = mesh.join(*cas)

    # the Y250 vortex vanes either side of the neutral centre section
    vanes = []
    for sgn in (-1.0, 1.0):
        vanes.append(common.plate(FW["x"] + 30.0, FW["x"] + FW["chord"] - 40.0,
                                  sgn * 250.0, FW["z"] + 20.0, FW["z"] + 150.0,
                                  7.0, sweep_top=44.0))
    out["front_y250_vanes"] = mesh.join(*vanes)
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

    # swan-neck pylons: they meet the mainplane on its UPPER surface, so the
    # working (lower) surface is left completely undisturbed
    pylons = []
    for sgn in (-1.0, 1.0):
        path = [(RW["x"] + 90.0, sgn * 150.0, RW["z"] + 62.0),
                (RW["x"] + 30.0, sgn * 148.0, RW["z"] + 10.0),
                (RW["x"] - 70.0, sgn * 140.0, RW["z"] - 300.0),
                (RW["x"] - 200.0, sgn * 118.0, RW["z"] - 440.0)]
        pylons.append(mesh.pipe(path, RW["pylon_t"], spec.RES["pipe"]))
    out["rear_pylons"] = mesh.join(*pylons)

    # endplate louvres, bleeding the pressure difference at the tip to cut the
    # tip vortex and the drag that comes with it
    lv = []
    for sgn in (-1.0, 1.0):
        y = sgn * RW["span"] / 2
        for k in range(5):
            lv.append(mesh.box(RW["x"] - 60.0 + k * 52.0, y,
                               RW["z"] + 96.0 - k * 14.0, 40.0, 14.0, 56.0))
    out["rear_louvres"] = mesh.join(*lv)

    # gurney on the flap trailing edge
    g = []
    g.append(mesh.box(RW["x"] + RW["chord"] * 0.46 + RW["chord"] * 0.58 * 0.5,
                      0.0, RW["z"] + RW["gap"] + 26.0 + 34.0,
                      12.0, RW["span"] * 0.96, 26.0))
    out["rear_gurney"] = mesh.join(*g)
    return out
