"""Shared builders: lofted bodywork sections and aerofoil panels."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import airfoil


def super_section(x, half_w, z_lo, z_hi, n=2.6, segments=40, z_bias=0.0):
    """A superellipse ring in the y-z plane -- the section language for the
    tub, nose and sidepods. n near 2 is an ellipse; higher is slab-sided."""
    zc = (z_lo + z_hi) / 2 + z_bias
    hz = (z_hi - z_lo) / 2
    p = 2.0 / n
    ring = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring.append((x,
                     half_w * math.copysign(abs(ca) ** p, ca),
                     zc + hz * math.copysign(abs(sa) ** p, sa)))
    return ring


def loft(rings, close_front=True, close_rear=True):
    """Skin a list of equal-length rings into a solid."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for s in range(n):
            s2 = (s + 1) % n
            faces.append((a + s, a + s2, b + s2, b + s))
    if close_front:
        faces.append(tuple(range(n - 1, -1, -1)))
    if close_rear:
        base = (len(rings) - 1) * n
        faces.append(tuple(range(base, base + n)))
    return verts, faces


def wing_element(x, z, span, chord, aoa, thickness=0.09, camber=0.055,
                 n_chord=None, n_span=None, taper=1.0, sweep=0.0,
                 aoa_tip=None, y0=0.0):
    """One wing element, spanning +/- span/2 about the car centreline.

    Built as a cambered aerofoil at negative incidence -- a wing on a racing
    car is an upside-down aeroplane wing, so the camber is inverted here rather
    than anywhere else in the code.
    """
    n_chord = n_chord or spec.RES["airfoil_pts"]
    n_span = n_span or spec.RES["wing_stations"]
    sect = airfoil.section_points(n_chord, thickness, camber)
    n_sec = len(sect)
    verts = []
    for j in range(n_span):
        f = j / (n_span - 1)
        y = -span / 2 + span * f
        t = abs(y) / (span / 2)
        c = chord * (1.0 - (1.0 - taper) * t)
        a = math.radians(-(aoa if aoa_tip is None else aoa + (aoa_tip - aoa) * t))
        ca, sa = math.cos(a), math.sin(a)
        xs = x + sweep * t
        for (u, v) in sect:
            du = (u - 0.25) * c
            dv = -v * c                      # inverted aerofoil
            verts.append((xs + du * ca - dv * sa, y + y0,
                          z + du * sa + dv * ca))
    faces = []
    for j in range(n_span - 1):
        a, b = j * n_sec, (j + 1) * n_sec
        for i in range(n_sec):
            i2 = (i + 1) % n_sec
            faces.append((a + i, a + i2, b + i2, b + i))
    faces.append(tuple(range(n_sec - 1, -1, -1)))
    base = (n_span - 1) * n_sec
    faces.append(tuple(range(base, base + n_sec)))
    return verts, faces


def plate(x0, x1, y, z0, z1, t, sweep_top=0.0):
    """A flat vertical plate (endplates, strakes, fences)."""
    hy = t / 2
    pts = [(x0, z0), (x1, z0), (x1, z1 - sweep_top), (x0, z1)]
    verts, faces = [], []
    for (px, pz) in pts:
        verts.append((px, y - hy, pz))
    for (px, pz) in pts:
        verts.append((px, y + hy, pz))
    n = len(pts)
    faces.append(tuple(range(n)))
    faces.append(tuple(range(2 * n - 1, n - 1, -1)))
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, i2, n + i2, n + i))
    return verts, faces
