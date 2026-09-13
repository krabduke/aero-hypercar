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
import shapes
import shapes
from parts import wheels, common, detail

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

        # Upper and lower wishbones. Each leg is an aerofoil fairing, not a
        # tube: at 300 km/h a round member is pure drag and produces nothing,
        # and bare pipes are the clearest tell that a model stopped at
        # "roughly the right shape".
        sect = common.section_points(24, spec.BODY_DETAIL["susp_fairing_t"], 0.0)
        chord = spec.BODY_DETAIL["susp_fairing_c"]
        for (z_out, z_in) in ((S["upper_z"], S["upper_z"] + 40.0),
                              (S["lower_z"], S["lower_z"] + 10.0)):
            outb = (x, y * 0.74, z_out)
            for dx in (-190.0, 190.0):
                inb = (x + dx, sgn * inb_y, z_in)
                arms.append(detail.faired_leg(outb, inb, sect, chord))

        # push/pull rod into a rocker on the chassis
        if front:
            rod = [(x, y * 0.74, S["lower_z"]), (x + 120.0, sgn * inb_y, 560.0)]
            rockers.append(shapes.rounded_box(x + 130.0, sgn * inb_y, 580.0, 150.0, 40.0, 120.0))
        else:
            rod = [(x, y * 0.74, S["upper_z"] + 60.0),
                   (x - 150.0, sgn * inb_y, 180.0)]
            rockers.append(shapes.rounded_box(x - 160.0, sgn * inb_y, 180.0, 150.0, 40.0, 120.0))
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
    out.update(_inboard())
    return out


def _inboard():
    """What the pushrod actually pushes: torsion bars, dampers, the
    anti-roll bar and the heave element.

    A pushrod that ends at a box is a pushrod that does nothing. This is the
    part of a racing car's suspension that does the work, and it was missing
    entirely -- there were two boxes labelled "rockers" and nothing else.
    """
    out = {}
    for ax, tag in ((spec.FRONT_AXLE_X, "f"), (spec.REAR_AXLE_X, "r")):
        front = tag == "f"
        inb_y = S["inboard_front_y"] if front else S["inboard_rear_y"]
        z = 560.0 if front else 200.0
        dx = 130.0 if front else -160.0

        dampers = []
        for sgn in (-1.0, 1.0):
            y = sgn * inb_y * 0.55
            body = mesh.pipe([(ax + dx - 150.0, y, z),
                              (ax + dx + 40.0, y, z + 14.0)], 34.0, 12)
            rodv = mesh.pipe([(ax + dx + 40.0, y, z + 14.0),
                              (ax + dx + 130.0, y, z + 22.0)], 13.0, 8)
            dampers.append(body)
            dampers.append(rodv)
        out[f"dampers_{tag}"] = mesh.join(*dampers)

        # torsion bars across the car, and the heave damper on the centreline
        out[f"torsion_bars_{tag}"] = mesh.join(
            mesh.pipe([(ax + dx - 10.0, -inb_y * 0.9, z - 36.0),
                       (ax + dx - 10.0, inb_y * 0.9, z - 36.0)], 21.0, 10))
        out[f"heave_{tag}"] = mesh.join(
            mesh.pipe([(ax + dx - 120.0, 0.0, z + 60.0),
                       (ax + dx + 60.0, 0.0, z + 60.0)], 30.0, 12),
            shapes.rounded_box(ax + dx + 90.0, 0.0, z + 60.0,
                               70.0, 80.0, 60.0, 12.0))

        # anti-roll bar: a blade each side on a cross tube
        arb = [mesh.pipe([(ax + dx - 60.0, -inb_y, z + 96.0),
                          (ax + dx - 60.0, inb_y, z + 96.0)], 15.0, 10)]
        for sgn in (-1.0, 1.0):
            arb.append(shapes.rounded_box(ax + dx - 20.0, sgn * inb_y,
                                          z + 96.0, 110.0, 9.0, 34.0, 4.0))
        out[f"antiroll_{tag}"] = mesh.join(*arb)

    # steering: rack, column and track rods
    ax = spec.FRONT_AXLE_X
    out["steering_rack"] = mesh.join(
        mesh.pipe([(ax - 40.0, -S["inboard_front_y"] * 0.85, 240.0),
                   (ax - 40.0, S["inboard_front_y"] * 0.85, 240.0)], 28.0, 12),
        shapes.rounded_box(ax - 40.0, 0.0, 240.0, 150.0, 220.0, 90.0, 20.0))
    out["steering_column"] = mesh.pipe(
        [(ax - 40.0, 0.0, 270.0), (ax + 420.0, 0.0, 430.0),
         (ax + 620.0, 0.0, 520.0)], 17.0, 10)
    return out
