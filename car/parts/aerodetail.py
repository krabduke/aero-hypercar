"""Flow-conditioning hardware and the small parts a real car carries.

Bargeboards, turning vanes, floor edge fences and edge wings, the beam wing,
brake ducts, mirrors, cameras, rain light and exhaust. None of these are
decoration: each one exists because of what the air does to the part behind it.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common, wheels

BB = spec.BARGEBOARD
TV = spec.TURNING_VANE
FE = spec.FLOOR_EDGE
BW = spec.BEAM_WING
BD = spec.BRAKE_DUCT
D = spec.DETAIL


def build():
    out = {}
    out.update(_bargeboards())
    out.update(_turning_vanes())
    out.update(_floor_edge())
    out.update(_beam_wing())
    out.update(_brake_ducts())
    out.update(_details())
    return out


def _curved_vane(x0, x1, y0, y1, z0, z1, t, bow=0.0, n=10):
    """A vane that curves in plan -- the whole point of a turning vane is that
    it is not flat, so it can turn the flow instead of just splitting it."""
    verts, faces = [], []
    for i in range(n):
        f = i / (n - 1)
        x = x0 + (x1 - x0) * f
        y = y0 + (y1 - y0) * f + bow * math.sin(math.pi * f)
        zb = z0 + (z1 - z0) * 0.0
        zt = z1
        for (yy, zz) in ((y - t / 2, zb), (y + t / 2, zb),
                         (y + t / 2, zt), (y - t / 2, zt)):
            verts.append((x, yy, zz))
    for i in range(n - 1):
        a, b = i * 4, (i + 1) * 4
        for s in range(4):
            s2 = (s + 1) % 4
            faces.append((a + s, a + s2, b + s2, b + s))
    faces.append((3, 2, 1, 0))
    base = (n - 1) * 4
    faces.append((base, base + 1, base + 2, base + 3))
    return verts, faces


def _bargeboards():
    """Stacked bargeboards ahead of the sidepod. They pull the front tyre wake
    outboard so it does not get swallowed by the sidepod inlet or the floor."""
    parts = []
    for sgn in (-1.0, 1.0):
        for k in range(BB["elements"]):
            f = k / max(BB["elements"] - 1, 1)
            y = sgn * (BB["y"] - k * BB["gap"] * 0.55)
            x0 = BB["x0"] + k * 46.0
            x1 = BB["x1"] - k * 24.0
            z0 = BB["z0"] + k * 26.0
            z1 = BB["z1"] - k * 46.0
            parts.append(_curved_vane(x0, x1, y, y + sgn * 62.0, z0, z1,
                                      BB["t"], bow=sgn * 34.0))
    return {"bargeboards": mesh.join(*parts)}


def _turning_vanes():
    """Vanes under the nose, conditioning the flow that feeds the floor."""
    parts = []
    for sgn in (-1.0, 1.0):
        for k in range(TV["elements"]):
            y = sgn * (TV["y"] - k * 60.0)
            parts.append(_curved_vane(TV["x0"] + k * 60.0, TV["x1"],
                                      y, y + sgn * 40.0,
                                      TV["z0"], TV["z1"] - k * 48.0,
                                      TV["t"], bow=sgn * 22.0))
    return {"turning_vanes": mesh.join(*parts)}


def _floor_edge():
    """Floor edge fences and an edge wing. The fences stop the low pressure
    under the floor from pulling air in from outside and destroying the seal --
    which is the same job the skirts do further inboard."""
    out = {}
    fences = []
    from parts.floor import half_width
    for sgn in (-1.0, 1.0):
        for k in range(FE["fences"]):
            f = k / max(FE["fences"] - 1, 1)
            x0 = FE["x0"] + (FE["x1"] - FE["x0"]) * f * 0.82
            parts_x1 = x0 + 300.0
            # sit on the floor's own edge, which waists in around the rear
            # tyre. At a fixed half_w the aft fences ran into both wheels.
            y = sgn * (min(half_width(x0), half_width(parts_x1))
                       - 34.0 - k * 20.0)
            fences.append(_curved_vane(x0, parts_x1, y, y - sgn * 40.0,
                                       10.0, 10.0 + FE["fence_h"],
                                       FE["t"], bow=-sgn * 16.0))
    out["floor_fences"] = mesh.join(*fences)

    wings = []
    for sgn in (-1.0, 1.0):
        x_w = FE["x1"] - FE["wing_chord"]
        wings.append(common.wing_element(
            x_w, 96.0, FE["wing_span"], FE["wing_chord"], 8.0,
            thickness=0.07, camber=0.05, n_span=6, taper=0.7,
            y0=sgn * (half_width(x_w) - FE["wing_span"] / 2 - 40.0)))
    out["floor_edge_wings"] = mesh.join(*wings)
    return out


def _beam_wing():
    """Beam wing below the rear wing. It works the diffuser exit and the rear
    wing together -- each makes the other more effective."""
    elems = []
    for k in range(BW["elements"]):
        elems.append(common.wing_element(
            BW["x"] + k * BW["chord"] * 0.42, BW["z"] + k * 46.0,
            BW["span"], BW["chord"] * (1.0 - 0.3 * k),
            BW["aoa"] + k * 8.0, thickness=0.09, camber=0.07,
            n_span=7, taper=0.92))
    return {"beam_wing": mesh.join(*elems)}


def _brake_ducts():
    """Brake ducts and drums at each corner. At this downforce the brakes are
    doing a great deal of work, and the drums also shield the wheel wake."""
    parts = []
    for (tag, x, y, w, od) in wheels.corners():
        front = tag.startswith("f")
        r = BD["front_r"] if front else BD["rear_r"]
        z = od / 2
        sgn = -1.0 if y < 0 else 1.0
        v, f = mesh.tube(-BD["width"] / 2, BD["width"] / 2, r - 26.0, r, 30)
        v = [(px + x, py + y - sgn * w * 0.30, pz + z) for (px, py, pz) in v]
        # tube axis is +x; rotate so it lies about the wheel's +y axis
        v = [(px, py, pz) for (px, py, pz) in v]
        vv, ff = mesh.tube(-BD["width"] / 2, BD["width"] / 2, r - 26.0, r, 30)
        vv = [(pz + x, px + y - sgn * w * 0.30, py + z) for (px, py, pz) in vv]
        parts.append((vv, ff))
        # inlet scoop facing forward
        iv, if_ = shapes.rounded_box(x - r * 0.72, y - sgn * w * 0.34, z - r * 0.30,
                           150.0, 54.0, BD["inlet_h"])
        parts.append((iv, if_))
    return {"brake_ducts": mesh.join(*parts)}


def _details():
    out = {}
    mirrors = []
    for sgn in (-1.0, 1.0):
        stalk = mesh.pipe([(D["mirror_x"] - 40.0, sgn * 150.0, D["mirror_z"] - 40.0),
                           (D["mirror_x"], sgn * D["mirror_y"], D["mirror_z"])],
                          13.0, 10)
        mirrors.append(stalk)
        mv, mf = shapes.rounded_box(D["mirror_x"] + 24.0, sgn * (D["mirror_y"] + 18.0),
                          D["mirror_z"] + 8.0, 62.0, 30.0, 86.0)
        mirrors.append((mv, mf))
    out["mirrors"] = mesh.join(*mirrors)

    cams = []
    for sgn in (-1.0, 1.0):
        cv, cf = shapes.rounded_box(D["camera_x"], sgn * 130.0, D["camera_z"], 130.0, 46.0, 46.0)
        cams.append((cv, cf))
    cv, cf = shapes.rounded_box(spec.TUB["cockpit_x1"] + 90.0, 0.0, 820.0, 150.0, 60.0, 52.0)
    cams.append((cv, cf))
    out["cameras"] = mesh.join(*cams)

    lv, lf = shapes.rounded_box(D["rainlight_x"], 0.0, D["rainlight_z"], 44.0, 96.0, 70.0)
    out["rainlight"] = (lv, lf)

    ex = []
    v, f = mesh.tube(D["exhaust_x"], D["exhaust_x"] + 130.0,
                     D["exhaust_r"] - 9.0, D["exhaust_r"], 26)
    ex.append(([(px, py, pz + D["exhaust_z"]) for (px, py, pz) in v], f))
    for sgn in (-1.0, 1.0):
        wv, wf = mesh.tube(D["exhaust_x"] + 20.0, D["exhaust_x"] + 96.0,
                           26.0, 34.0, 20)
        wv = [(px, py + sgn * 132.0, pz + D["wastegate_z"])
              for (px, py, pz) in wv]
        ex.append((wv, wf))
    out["exhaust"] = mesh.join(*ex)

    # engine cover cooling louvres
    lv2 = []
    for k in range(6):
        x = 3180.0 + k * 96.0
        for sgn in (-1.0, 1.0):
            b, bf = shapes.rounded_box(x, sgn * 128.0, 520.0 - k * 22.0, 70.0, 8.0, 36.0)
            lv2.append((b, bf))
    out["cooling_louvres"] = mesh.join(*lv2)
    return out
