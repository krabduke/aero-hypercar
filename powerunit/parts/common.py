"""Shared helpers: bank geometry and small hardware."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh


def bank_dir(bank):
    """Unit vector along a bank's bore axis, from the crank centreline up."""
    a = spec.bank_angle_rad(bank)
    return (0.0, math.sin(a), math.cos(a))


def bank_lat(bank):
    """Unit vector across the bore axis, in the y-z plane."""
    a = spec.bank_angle_rad(bank)
    return (0.0, math.cos(a), -math.sin(a))


def bank_point(x, along, lateral=0.0, bank=0):
    """A point `along` mm up the bore axis and `lateral` mm across it."""
    d, l = bank_dir(bank), bank_lat(bank)
    return (x, d[1] * along + l[1] * lateral, d[2] * along + l[2] * lateral)


def along_bank(verts, x, along, bank, lateral=0.0):
    """Move geometry built about the origin onto a bank's bore axis.

    The part is built with its own axis along +x, then rotated so +x becomes
    the bore axis and translated into place -- which is how every cylinder,
    piston, valve and cam lobe in this engine gets positioned.
    """
    a = spec.bank_angle_rad(bank)
    # +x -> bore axis: rotate about +x is wrong, we need +x -> (0, sin a, cos a)
    out = []
    cx, cy, cz = bank_point(x, along, lateral, bank)
    for (px, py, pz) in verts:
        # px runs along the bore axis, (py, pz) is the section plane
        by = math.sin(a) * px + math.cos(a) * py
        bz = math.cos(a) * px - math.sin(a) * py
        out.append((pz + cx, by + cy, bz + cz))
    return out


def bore_tube(x, along0, along1, r_in, r_out, bank, segments=None):
    segments = segments or spec.RES["revolve"]
    v, f = mesh.tube(along0, along1, r_in, r_out, segments)
    return along_bank(v, x, 0.0, bank), f


def cylinder_along(x, along0, along1, r, bank, segments=None):
    segments = segments or spec.RES["small_revolve"]
    v, f = mesh.cylinder(along0, along1, r, segments)
    return along_bank(v, x, 0.0, bank), f


def disc(x, r_in, r_out, thickness, segments=None):
    """A disc lying in the y-z plane at station x (crank-axis parts)."""
    segments = segments or spec.RES["revolve"]
    return mesh.tube(x - thickness / 2, x + thickness / 2, r_in, r_out, segments)


def bolt_circle(x, radius, count, head_r=5.0, head_h=4.0):
    return mesh.bolt_ring(x, radius, count, head_r, head_h, 10)
