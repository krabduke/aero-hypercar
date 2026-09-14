"""Intake plenum, velocity stacks, throttle."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

SM = spec.RES["small_revolve"]
from parts import common

I = spec.INTAKE
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_plenum())
    out.update(_trumpets())
    return out


def _plenum():
    """A plenum outboard of each bank, feeding that bank's four ports.

    See the note in `spec.INTAKE`: the hot vee puts the intake ports on the
    outside of the heads, so this is where the air has to come from.
    """
    out = {}
    for bank, tag in ((0, "l"), (1, "r")):
        sgn = -1.0 if bank == 0 else 1.0
        y = sgn * I["plenum_y"]
        v, f = mesh.tube(-I["plenum_len"] / 2, I["plenum_len"] / 2,
                         0.0, I["plenum_r"], SEG)
        v = [(x, py + y, pz + I["plenum_z"]) for (x, py, pz) in v]
        out[f"plenum_{tag}"] = (v, f)
        # throttle body on the front face of each
        tv, tf = mesh.tube(-I["plenum_len"] / 2 - 62.0, -I["plenum_len"] / 2,
                           I["throttle_r"] - 7.0, I["throttle_r"], 32)
        tv = [(x, py + y, pz + I["plenum_z"]) for (x, py, pz) in tv]
        out[f"throttle_{tag}"] = (tv, tf)
    return out


def _trumpets():
    """One velocity stack per cylinder, standing inside its bank's plenum and
    pointing at that cylinder's runner mouth."""
    parts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        sgn = -1.0 if bank == 0 else 1.0
        prof = [(0.0, I["trumpet_r_in"]),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"]),
                (I["trumpet_len"], I["trumpet_r_out"]),
                (I["trumpet_len"], I["trumpet_r_out"] - 3.0),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"] - 3.0),
                (0.0, I["trumpet_r_in"] - 3.0)]
        tv, tf = mesh.revolve_closed(prof, 26)
        # the lathe runs along its own +x; the stack points inboard, from the
        # outboard wall of the plenum towards the runner mouth
        tv = [(pz + x,
               sgn * (I["plenum_y"] + I["plenum_r"] * 0.6 - px),
               py + I["plenum_z"])
              for (px, py, pz) in tv]
        parts.append((tv, tf))
    return {"trumpets": mesh.join(*parts)}
