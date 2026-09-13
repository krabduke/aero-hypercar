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
    """Four-element front wing, each element a separate lofted surface.

    The shape that matters is the spanwise one. Across the regulated neutral
    centre section the mainplane runs flat and almost unloaded; outboard of
    that it washes in to its tip incidence and rises towards the endplate, so
    the tip vortex is thrown outside the front tyre rather than into it.
    """
    out = {}
    half = FW["span"] / 2
    neutral = FW["neutral_half_w"]
    n_span = 15

    for k, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        stations = []
        tip = half * span_f
        for j in range(n_span):
            f = -1.0 + 2.0 * j / (n_span - 1)
            y = tip * f
            t = abs(y)
            # outboard fraction: 0 across the neutral section, 1 at the tip
            o = 0.0 if t <= neutral else (t - neutral) / max(tip - neutral, 1.0)
            o = o * o * (3 - 2 * o)          # smoothstep, so there is no crease
            chord = c_r + (c_t - c_r) * o
            aoa = aoa_r + (aoa_t - aoa_r) * o
            z = FW["z"] + dz + rise * o
            if k == 0:
                # the mainplane arches over the nose: highest on centreline
                z += FW["arch"] * max(0.0, 1.0 - (t / neutral) ** 2)
            stations.append((y, FW["x"] + dx, z, chord, aoa))
        name = "front_wing_main" if k == 0 else f"front_flap_{k}"
        out[name] = common.lofted_element(stations, thickness=0.085,
                                          camber=0.075)

    out.update(_front_endplates())

    # cascade winglets above the outboard wing
    cas = []
    for sgn in (-1.0, 1.0):
        for (dx, dz, span, chord, aoa) in FW["cascades"]:
            cas.append(common.wing_element(
                FW["x"] + dx, FW["z"] + dz, span, chord, aoa,
                thickness=0.08, camber=0.08, n_span=5, taper=0.8,
                y0=sgn * (half - FW["cascade_inset"] - span / 2)))
    out["front_cascades"] = mesh.join(*cas)

    # the Y250 vortex vanes either side of the neutral centre section
    vanes = []
    for sgn in (-1.0, 1.0):
        vanes.append(common.plate(FW["x"] + 30.0, FW["x"] + FW["chord"] - 40.0,
                                  sgn * neutral, FW["z"] + 20.0,
                                  FW["z"] + 150.0, 7.0, sweep_top=44.0))
    out["front_y250_vanes"] = mesh.join(*vanes)
    return out


def _front_endplates():
    """Endplate, footplate and dive planes.

    The endplate is not a flat card: its lower edge rolls outboard into a
    footplate, which is what actually turns the flow around the outside of the
    front tyre -- the single dirtiest thing on the car.
    """
    out = {}
    half = FW["span"] / 2
    x0 = FW["x"] + FW["endplate_x0"]
    x1 = FW["x"] + FW["endplate_x1"]
    z0 = 16.0
    t = FW["endplate_t"]
    fh = FW["footplate_h"]
    # The top edge follows the flap stack: low ahead of the mainplane, rising
    # over each flap in turn, so the plate encloses the elements instead of
    # standing past them as a rectangle.
    tops = [(0.00, z0 + 96.0), (0.22, z0 + 150.0), (0.48, z0 + 250.0),
            (0.74, z0 + FW["endplate_h"]), (1.00, z0 + FW["endplate_h"] - 44.0)]
    plates, planes = [], []
    for sgn in (-1.0, 1.0):
        y = sgn * half
        rows = []
        # lower rows roll outboard into the footplate; the upper edge follows
        # `tops`, interpolated at the same chordwise stations
        for (lvl, dy) in ((0.0, sgn * 46.0), (0.30, sgn * 12.0),
                          (0.66, 0.0), (1.0, 0.0)):
            row = []
            for (f, z_top) in tops:
                x = x0 + (x1 - x0) * f
                z_lo = z0 + (fh if lvl > 0.0 else 0.0) * min(lvl / 0.30, 1.0)
                z = z_lo + (z_top - z_lo) * max(0.0, (lvl - 0.30) / 0.70)
                row.append((x, y + dy * (1.0 - 0.3 * f), z))
            rows.append(row)
        plates.append(_skin(rows, t, sgn))

        for k in range(FW["diveplanes"]):
            zz = z0 + fh + 40.0 + k * 62.0
            # a dive plane hangs off the outer face of the endplate; it must
            # stay inside the legal width, which half + span/2 did not
            planes.append(common.wing_element(
                FW["x"] + 30.0 + k * 40.0, zz, 92.0, 160.0 - k * 30.0,
                20.0 + k * 4.0, thickness=0.07, camber=0.09, n_span=4,
                taper=0.7, y0=sgn * (half + 44.0)))
    out["front_endplates"] = mesh.join(*plates)
    out["front_diveplanes"] = mesh.join(*planes)
    return out


def _skin(rows, t, sgn):
    """Give a grid of stations thickness in y, and close it into a solid."""
    nr, nc = len(rows), len(rows[0])
    inner = [(x, y - sgn * t / 2, z) for row in rows for (x, y, z) in row]
    outer = [(x, y + sgn * t / 2, z) for row in rows for (x, y, z) in row]
    verts = inner + outer
    off = len(inner)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i * nc + j
            faces.append((k, k + 1, k + nc + 1, k + nc))
            faces.append((off + k, off + k + nc, off + k + nc + 1,
                          off + k + 1))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i * nc + j
            quad = ((k, k + nc, off + k + nc, off + k) if j == 0 else
                    (k + nc, k, off + k, off + k + nc))
            faces.append(quad)
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i * nc + j
            quad = ((k + 1, k, off + k, off + k + 1) if i == 0 else
                    (k, k + 1, off + k + 1, off + k))
            faces.append(quad)
    return verts, faces


def rear_element(k):
    """(x, z, chord, aoa) for rear wing element k -- one definition, used by
    the geometry, the hinge table and the aero solver alike."""
    chord = RW["chord"] * (1.0 - 0.42 * k)
    x = RW["x"] + k * RW["chord"] * 0.46
    z = RW["z"] + k * (RW["gap"] + 26.0)
    aoa = RW["aoa"] + k * 12.0
    return x, z, chord, aoa


def pivots():
    """Hinge lines for every element that moves.

    Each movable element pivots about its own leading edge, so a slider in the
    viewer changes the element's incidence exactly the way the real actuator
    would -- and the aero solver is fed the same angle.
    """
    out = {}
    for k, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        if k == 0:
            continue                      # the mainplane is fixed
        out[f"front_flap_{k}"] = ((FW["x"] + dx, 0.0, FW["z"] + dz),
                                  (0.0, 1.0, 0.0), 1.0, "hinge")
    x, z, chord, aoa = rear_element(1)
    out["rear_flap"] = ((x, 0.0, z), (0.0, 1.0, 0.0), 1.0, "hinge")
    return out


def _rear():
    """Two-element rear wing on swan-neck pylons, shown in its loaded
    (non-DRS) position. The flap is its own object hinged at its leading edge,
    because it moves: this is the DRS element."""
    out = {}
    for k in range(RW["elements"]):
        x, z, chord, aoa = rear_element(k)
        el = common.wing_element(x, z, RW["span"], chord, aoa,
                                 thickness=0.10, camber=0.085, taper=0.95)
        out["rear_wing_main" if k == 0 else "rear_flap"] = el

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
