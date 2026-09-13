"""Floor, venturi tunnels, diffuser, strakes and skirts.

The tunnels are the car's main downforce source below 200 km/h once the fans
are discounted, and the skirts are what let the fans seal them.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

F = spec.FLOOR


def build():
    out = {}
    out.update(_plank())
    out.update(_tunnels())
    out.update(_strakes())
    out.update(_skirts())
    return out


def _floor_z(x):
    """Underfloor height: flat under the nose, pinched at the throat, then
    expanding hard through the diffuser."""
    if x <= F["throat_x"]:
        f = (x - F["x0"]) / (F["throat_x"] - F["x0"])
        return 78.0 - (78.0 - F["throat_z"]) * f ** 1.3 + 18.0
    if x <= F["diffuser_x"]:
        return F["throat_z"] + 18.0
    f = (x - F["diffuser_x"]) / (F["x1"] - F["diffuser_x"])
    return F["throat_z"] + 18.0 + (F["diffuser_exit_z"] - F["throat_z"]) * f ** 1.25


def _plank():
    """The reference plane -- a flat plank down the centreline between the
    tunnels, which is what actually sets ride height."""
    v, f = mesh.box((F["x0"] + F["x1"]) / 2, 0.0, 26.0,
                    F["x1"] - F["x0"], F["tunnel_inner_y"] * 2, 16.0)
    return {"floor_plank": (v, f)}


def _tunnels():
    """Two venturi tunnels: inlet, throat, then the diffuser ramp."""
    out = {}
    n = 22
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        rings = []
        for i in range(n):
            t = i / (n - 1)
            x = F["x0"] + (F["x1"] - F["x0"]) * t
            z_roof = _floor_z(x)
            y_in = sgn * F["tunnel_inner_y"]
            y_out = sgn * (F["tunnel_inner_y"] + F["tunnel_half_w"] * 2)
            # section: floor plate, outer wall up, roof, inner wall down
            rings.append([
                (x, y_in, 10.0), (x, y_out, 10.0),
                (x, y_out, z_roof), (x, y_in, z_roof),
            ])
        verts = [v for r in rings for v in r]
        faces = []
        for i in range(n - 1):
            a, b = i * 4, (i + 1) * 4
            for s in range(4):
                s2 = (s + 1) % 4
                faces.append((a + s, a + s2, b + s2, b + s))
        faces.append((3, 2, 1, 0))
        base = (n - 1) * 4
        faces.append((base, base + 1, base + 2, base + 3))
        out[f"tunnel_{side}"] = (verts, faces)
    return out


def _strakes():
    """Vertical fences inside each tunnel, keeping the flow attached through
    the diffuser expansion."""
    parts = []
    for sgn in (-1.0, 1.0):
        for k in range(F["n_strakes"]):
            y = sgn * (F["tunnel_inner_y"] + 60.0
                       + k * (F["tunnel_half_w"] * 2 - 90.0) / F["n_strakes"])
            x0 = F["throat_x"] - 300.0
            x1 = F["x1"] - 90.0
            parts.append(common.plate(x0, x1, y, 12.0, _floor_z(x1) - 26.0, 7.0,
                                      sweep_top=_floor_z(x1) - _floor_z(x0) - 60.0))
    return {"floor_strakes": mesh.join(*parts)}


def _skirts():
    """Sliding skirts down each tunnel edge. Without them the fans cannot hold
    a pressure difference under the car, and the whole concept fails."""
    parts = []
    for sgn in (-1.0, 1.0):
        y = sgn * (F["tunnel_inner_y"] + F["tunnel_half_w"] * 2)
        parts.append(common.plate(F["x0"] + 120.0, F["x1"] - 60.0, y,
                                  -F["skirt_depth"] + 12.0, 40.0, 12.0))
    return {"floor_skirts": mesh.join(*parts)}
