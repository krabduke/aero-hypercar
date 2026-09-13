"""Wishbones, pushrods, pullrods, rockers, track rods and driveshafts.

Front is pushrod and rear is pullrod, which is the usual arrangement: it puts
the front springs high where there is room above the driver's feet, and the
rear springs low where the gearbox casing can carry them.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import wheels

S = spec.SUSP
P = spec.RES["pipe"]


def build():
    out = {}
    arms, rods, rockers, shafts = [], [], [], []
    for (tag, x, y, w, od) in wheels.corners():
        front = tag.startswith("f")
        inb_y = S["inboard_front_y"] if front else S["inboard_rear_y"]
        sgn = -1.0 if y < 0 else 1.0
        hub = (x, y * 0.80, od / 2)

        # upper and lower wishbones, each a pair of legs to the tub
        for (z_out, z_in) in ((S["upper_z"], S["upper_z"] + 40.0),
                              (S["lower_z"], S["lower_z"] + 10.0)):
            outb = (x, y * 0.74, z_out)
            for dx in (-190.0, 190.0):
                inb = (x + dx, sgn * inb_y, z_in)
                arms.append(mesh.pipe([outb, inb], S["arm_r"], P))

        # push/pull rod into a rocker on the chassis
        if front:
            rod = [(x, y * 0.74, S["lower_z"]), (x + 120.0, sgn * inb_y, 560.0)]
            rockers.append(mesh.box(x + 130.0, sgn * inb_y, 580.0, 150.0, 40.0, 120.0))
        else:
            rod = [(x, y * 0.74, S["upper_z"] + 60.0),
                   (x - 150.0, sgn * inb_y, 180.0)]
            rockers.append(mesh.box(x - 160.0, sgn * inb_y, 180.0, 150.0, 40.0, 120.0))
        rods.append(mesh.pipe(rod, S["rod_r"], P))

        # track rod / toe link
        trk_x = x + (-230.0 if front else 200.0)
        rods.append(mesh.pipe([(x, y * 0.74, S["lower_z"] + 70.0),
                               (trk_x, sgn * inb_y * 0.8, S["lower_z"] + 90.0)],
                              S["rod_r"] * 0.8, P))

        if not front:
            shafts.append(mesh.pipe([(x, sgn * 180.0, od / 2),
                                     (x, y * 0.78, od / 2)], 26.0, P))

    out["wishbones"] = mesh.join(*arms)
    out["pushrods"] = mesh.join(*rods)
    out["rockers"] = mesh.join(*rockers)
    out["driveshafts"] = mesh.join(*shafts)
    return out
