"""Floor, venturi tunnels, diffuser, strakes and skirts.

The tunnels are the car's main downforce source below 200 km/h once the fans
are discounted, and the skirts are what let the fans seal them.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common

F = spec.FLOOR


def build():
    out = {}
    out.update(_surface())
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


def half_width(x):
    """The floor's half width at station x, from the plan table.

    Linear between stations with a smoothstep, so the edge is a curve rather
    than a chain of straight segments -- a flat-sided floor is the clearest
    sign a shape was never developed.
    """
    tbl = spec.FLOOR_PLAN
    if x <= tbl[0][0]:
        return tbl[0][1]
    if x >= tbl[-1][0]:
        return tbl[-1][1]
    for i in range(len(tbl) - 1):
        x0, w0 = tbl[i]
        x1, w1 = tbl[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            t = t * t * (3 - 2 * t)
            return w0 + (w1 - w0) * t
    return tbl[-1][1]


def _surface():
    """The floor panel itself: a plate following the plan outline, with the
    tunnel roof line giving it thickness and the edge rolled up slightly.

    The old version was a rectangle running the full length at full width,
    which put the floor straight through both rear tyres.
    """
    n = 34
    xs = [F["x0"] + (F["x1"] - F["x0"]) * i / (n - 1) for i in range(n)]
    rings = []
    for x in xs:
        hw = half_width(x)
        z_lo = 10.0
        z_hi = max(z_lo + 14.0, _floor_z(x) * 0.35 + 14.0)
        rings.append([(x, -hw, z_lo), (x, hw, z_lo),
                      (x, hw, z_hi), (x, -hw, z_hi)])
    verts = [v for r in rings for v in r]
    faces = []
    for i in range(n - 1):
        a, b = i * 4, (i + 1) * 4
        for s_ in range(4):
            s2 = (s_ + 1) % 4
            faces.append((a + s_, a + s2, b + s2, b + s_))
    faces.append((3, 2, 1, 0))
    base = (n - 1) * 4
    faces.append((base, base + 1, base + 2, base + 3))
    return {"floor_surface": (verts, faces)}


def _plank():
    """The reference plane -- a flat plank down the centreline between the
    tunnels, which is what actually sets ride height."""
    v, f = shapes.rounded_box((F["x0"] + F["x1"]) / 2, 0.0, 26.0,
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
            # the tunnel's outer wall follows the floor edge, so the tunnel
            # narrows where the floor waists in around the rear tyre
            y_out = sgn * max(half_width(x) - 34.0, F["tunnel_inner_y"] + 60.0)
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
            x0 = F["throat_x"] - 300.0
            x1 = F["x1"] - 90.0
            span = max(half_width(x1) - 34.0, F["tunnel_inner_y"] + 60.0)
            y = sgn * (F["tunnel_inner_y"] + 50.0
                       + k * (span - F["tunnel_inner_y"] - 100.0)
                       / max(F["n_strakes"] - 1, 1))
            parts.append(common.plate(x0, x1, y, 12.0, _floor_z(x1) - 26.0, 7.0,
                                      sweep_top=_floor_z(x1) - _floor_z(x0) - 60.0))
    half = len(parts) // 2
    return {f"floor_strake_{'lr'[i // half]}{i % half + 1}": m
            for i, m in enumerate(parts)}


def _skirts():
    """Sliding skirts down each floor edge, following the plan outline.

    Without them the fans cannot hold a pressure difference under the car, and
    the whole concept fails. A straight skirt would stand out past the floor
    wherever the floor waists in.
    """
    parts = []
    x0, x1 = F["x0"] + 120.0, F["x1"] - 60.0
    n = 26
    t = 12.0
    for sgn in (-1.0, 1.0):
        rows = []
        for i in range(n):
            x = x0 + (x1 - x0) * i / (n - 1)
            y = sgn * (half_width(x) - 22.0)
            rows.append((x, y))
        verts = []
        for (x, y) in rows:
            verts.append((x, y - t / 2, 0.0))
            verts.append((x, y + t / 2, 0.0))
            verts.append((x, y + t / 2, F["skirt_depth"] + 14.0))
            verts.append((x, y - t / 2, F["skirt_depth"] + 14.0))
        faces = []
        for i in range(n - 1):
            a, b = i * 4, (i + 1) * 4
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((a + k, a + k2, b + k2, b + k))
        faces.append((3, 2, 1, 0))
        base = (n - 1) * 4
        faces.append((base, base + 1, base + 2, base + 3))
        parts.append((verts, faces))
    return {"floor_skirts": mesh.join(*parts)}
