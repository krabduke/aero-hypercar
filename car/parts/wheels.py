"""Wheels, tyres, brake discs, calipers and uprights."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

W = spec.WHEEL
SEG = spec.RES["revolve"]


def corners():
    """(tag, x, y, width, outer diameter) for each of the four corners."""
    out = []
    for (tag, x, track, w, od) in (
            ("fl", 0.0, spec.TRACK_FRONT, W["front_w"], W["front_od"]),
            ("fr", 0.0, spec.TRACK_FRONT, W["front_w"], W["front_od"]),
            ("rl", spec.WHEELBASE, spec.TRACK_REAR, W["rear_w"], W["rear_od"]),
            ("rr", spec.WHEELBASE, spec.TRACK_REAR, W["rear_w"], W["rear_od"])):
        sgn = -1.0 if tag.endswith("l") else 1.0
        out.append((tag, x, sgn * track / 2, w, od))
    return out


def build():
    out = {}
    tyres, rims, discs, calipers, uprights = [], [], [], [], []
    for (tag, x, y, w, od) in corners():
        z = od / 2
        tyres.append(_lathe_y(x, y, z, [
            (-w / 2, W["rim_d"] / 2), (-w / 2 * 0.86, od / 2 - 6.0),
            (0.0, od / 2), (w / 2 * 0.86, od / 2 - 6.0),
            (w / 2, W["rim_d"] / 2)], closed_inner=True))
        rims.append(_lathe_y(x, y, z, [
            (-w / 2 * 0.92, W["rim_d"] / 2 - 30.0), (-w / 2 * 0.92, W["rim_d"] / 2),
            (w / 2 * 0.92, W["rim_d"] / 2), (w / 2 * 0.92, W["rim_d"] / 2 - 30.0)]))
        discs.append(_lathe_y(x, y, z, [
            (-W["disc_t"] / 2, 92.0), (-W["disc_t"] / 2, W["disc_r"]),
            (W["disc_t"] / 2, W["disc_r"]), (W["disc_t"] / 2, 92.0)]))
        cv, cf = mesh.box(x, y - (w * 0.18) * (1 if y > 0 else -1),
                          z + W["caliper_r"], 150.0, 70.0, 90.0)
        calipers.append((cv, cf))
        uv, uf = mesh.box(x, y * 0.80, z, 120.0, 90.0, spec.SUSP["upright_h"])
        uprights.append((uv, uf))
    out["tyres"] = mesh.join(*tyres)
    out["wheelrims"] = mesh.join(*rims)
    out["discs"] = mesh.join(*discs)
    out["calipers"] = mesh.join(*calipers)
    out["uprights"] = mesh.join(*uprights)
    return out


def _lathe_y(x, y, z, profile, closed_inner=False):
    """Revolve a (across, radius) profile about the wheel's own +y axis."""
    prof = list(profile)
    if closed_inner:
        prof = prof + [(profile[-1][0], W["rim_d"] / 2 - 2.0),
                       (profile[0][0], W["rim_d"] / 2 - 2.0)]
    v, f = mesh.revolve_closed(prof, SEG)
    return [(pz + x, px + y, py + z) for (px, py, pz) in v], f
