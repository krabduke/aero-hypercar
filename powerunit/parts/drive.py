"""Flywheel, clutch, bellhousing, oil and water pumps."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

A = spec.ANCILLARY
SEG = spec.RES["revolve"]


def build():
    x_rear = spec.BLOCK["x_rear"]
    out = {}
    out["flywheel"] = mesh.tube(x_rear + 20.0, x_rear + 20.0 + A["flywheel_t"],
                                0.0, A["flywheel_r"], SEG)
    out["clutch"] = mesh.tube(x_rear + 44.0, x_rear + 62.0,
                              24.0, A["flywheel_r"] * 0.86, SEG)
    out["bellhousing"] = mesh.tube(x_rear + 8.0,
                                   x_rear + 8.0 + A["bellhousing_len"],
                                   A["bellhousing_r"] - 9.0, A["bellhousing_r"], SEG)
    # pumps hung off the front of the block
    pv, pf = mesh.tube(-14.0, 14.0, 0.0, A["oil_pump_r"], 24)
    pv = [(px + spec.BLOCK["x_front"] - 16.0, py - 86.0, pz - 46.0)
          for (px, py, pz) in pv]
    wv, wf = mesh.tube(-16.0, 16.0, 0.0, A["water_pump_r"], 24)
    wv = [(px + spec.BLOCK["x_front"] - 16.0, py + 86.0, pz - 34.0)
          for (px, py, pz) in wv]
    out["pump_oil"] = (pv, pf)
    out["pump_water"] = (wv, wf)
    return out
