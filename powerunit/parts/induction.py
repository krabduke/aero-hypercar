"""Intake plenum, velocity stacks, throttle."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

I = spec.INTAKE
SEG = spec.RES["revolve"]


def build():
    out = {}
    out.update(_plenum())
    out.update(_trumpets())
    return out


def _plenum():
    """A single plenum over the vee feeding both banks. It sits above the
    turbos because this is a hot-vee: the hot side is inboard, the cold side
    outboard, so the charge air comes over the top."""
    v, f = mesh.tube(-I["plenum_len"] / 2, I["plenum_len"] / 2,
                     0.0, I["plenum_r"], SEG)
    v = [(x, y, z + I["plenum_z"]) for (x, y, z) in v]
    # throttle body on the front face
    tv, tf = mesh.tube(-I["plenum_len"] / 2 - 62.0, -I["plenum_len"] / 2,
                       I["throttle_r"] - 7.0, I["throttle_r"], 32)
    tv = [(x, y, z + I["plenum_z"]) for (x, y, z) in tv]
    return {"plenum": (v, f), "throttle": (tv, tf)}


def _trumpets():
    """One velocity stack per cylinder, dropping from the plenum into each
    bank's intake port."""
    parts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        prof = [(0.0, I["trumpet_r_in"]), (I["trumpet_len"] * 0.62, I["trumpet_r_in"]),
                (I["trumpet_len"], I["trumpet_r_out"]),
                (I["trumpet_len"], I["trumpet_r_out"] - 3.0),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"] - 3.0),
                (0.0, I["trumpet_r_in"] - 3.0)]
        tv, tf = mesh.revolve_closed(prof, 26)
        tv = [(z, y, px) for (px, y, z) in tv]
        tv = common.along_bank(tv, x, spec.DECK_HEIGHT + spec.HEAD["height"] + 6.0,
                               bank, -spec.HEAD["cam_centres"] * 0.34)
        parts.append((tv, tf))
    return {"trumpets": mesh.join(*parts)}
