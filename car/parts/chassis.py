"""Bodywork: one continuous central body, undercut sidepods, engine cover,
shark fin, halo and cockpit.

The central body is a single lofted surface from the nose tip to the rear
crash structure, driven by spec.BODY. Building it as one surface rather than
three separate lofts is what lets it be waisted and curvature-continuous --
which is the difference between something that looks aerodynamic and a stack
of tapered boxes.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
from parts import common

SEG = 52
T = spec.TUB
H = spec.HALO
D = spec.DETAIL


def build():
    out = {}
    out.update(_body())
    out.update(_sidepods())
    out.update(_cockpit_surround())
    out.update(_sharkfin())
    out.update(_halo())
    out.update(_cockpit())
    return out


# --------------------------------------------------------------------------

def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t
                  + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def _sample(table, x):
    """Catmull-Rom through a station table, so the surface is smooth between
    the defining stations instead of faceted."""
    if x <= table[0][0]:
        return table[0][1:]
    if x >= table[-1][0]:
        return table[-1][1:]
    i = 0
    while i < len(table) - 2 and table[i + 1][0] < x:
        i += 1
    x0, x1 = table[i][0], table[i + 1][0]
    t = (x - x0) / (x1 - x0)
    i0, i3 = max(i - 1, 0), min(i + 2, len(table) - 1)
    return tuple(_catmull(table[i0][k], table[i][k], table[i + 1][k],
                          table[i3][k], t)
                 for k in range(1, len(table[0])))


def body_section(x, inset=0.0, segments=SEG):
    """Superellipse section with a shoulder bias, so the widest point can sit
    above or below mid-height -- that bias is what gives the body its shoulder
    line instead of a symmetric tube."""
    hw, z_bot, z_top, n, bias = _sample(spec.BODY, x)
    hw = max(hw - inset, 0.5)
    zc = (z_bot + z_top) / 2 + bias * (z_top - z_bot) * 0.5
    hz = max((z_top - z_bot) / 2 - inset, 0.5)
    p = 2.0 / n
    ring = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring.append((x,
                     hw * math.copysign(abs(ca) ** p, ca),
                     zc + hz * math.copysign(abs(sa) ** p, sa)))
    return ring


def _stations(table, n):
    x0, x1 = table[0][0], table[-1][0]
    out = []
    for i in range(n):
        f = i / (n - 1)
        # cosine spacing: more sections where the nose and tail curve hardest
        f = 0.5 * (1 - math.cos(math.pi * f))
        out.append(x0 + (x1 - x0) * f)
    return out


def _body():
    xs = _stations(spec.BODY, 68)
    rings = [body_section(x) for x in xs]
    return {"tub": common.loft(rings)}


def _sidepod_section(x, segments=40):
    """Sidepod section: rounded outboard, flat inboard against the body, and
    an undercut lower surface that climbs aft to feed the tunnel."""
    y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, x)
    yc = (y_in + y_out) / 2
    hy = (y_out - y_in) / 2
    zc = (z_bot + z_top) / 2
    hz = (z_top - z_bot) / 2
    p = 2.0 / n
    ring = []
    for i in range(segments):
        a = 2.0 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        ring.append((x,
                     yc + hy * math.copysign(abs(ca) ** p, ca),
                     zc + hz * math.copysign(abs(sa) ** p, sa)))
    return ring


def _sidepods():
    out = {}
    xs = _stations(spec.SIDEPOD_TABLE, 30)
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        rings = []
        for x in xs:
            r = _sidepod_section(x)
            rings.append([(px, sgn * py, pz) for (px, py, pz) in r])
        out[f"sidepod_{side}"] = common.loft(rings)

    # inlet mouth: a short duct standing proud of the leading edge
    mouths = []
    for sgn in (-1.0, 1.0):
        y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, 1810.0)
        yc = sgn * (y_in + y_out) / 2
        zc = (z_bot + z_top) / 2
        v, f = mesh.tube(1700.0, 1810.0, 76.0, 104.0, 28)
        v = [(px, py + yc, pz + zc) for (px, py, pz) in v]
        mouths.append((v, f))
    out["sidepod_inlets"] = mesh.join(*mouths)
    return out


def _cockpit_surround():
    """Cockpit opening coaming, sunk into the body top."""
    parts = []
    x0, x1 = T["cockpit_x0"], T["cockpit_x1"]
    n = 18
    path_l, path_r = [], []
    for i in range(n):
        f = i / (n - 1)
        x = x0 + (x1 - x0) * f
        hw, z_bot, z_top, ex, bias = _sample(spec.BODY, x)
        w = min(T["cockpit_half_w"], hw * 0.80) * math.sin(math.pi * min(f * 1.1, 1.0)) ** 0.35
        z = z_top - 22.0
        path_l.append((x, -w, z))
        path_r.append((x, w, z))
    parts.append(mesh.pipe(path_l, 15.0, 10))
    parts.append(mesh.pipe(path_r, 15.0, 10))
    return {"cockpit_coaming": mesh.join(*parts)}


def _sharkfin():
    """Shark fin along the engine cover. It keeps the rear wing fed with
    attached flow when the car is yawed, which is most of a lap."""
    x0, x1 = D["sharkfin_x0"], D["sharkfin_x1"]
    n = 16
    verts, faces = [], []
    for i in range(n):
        f = i / (n - 1)
        x = x0 + (x1 - x0) * f
        hw, z_bot, z_top, ex, bias = _sample(spec.BODY, x)
        z_base = z_top - 8.0
        z_tip = D["sharkfin_z"] - 130.0 * f ** 1.6
        t = D["sharkfin_t"] * (1.0 - 0.45 * f)
        verts.append((x, -t / 2, z_base))
        verts.append((x, t / 2, z_base))
        verts.append((x, t / 2, max(z_tip, z_base + 4.0)))
        verts.append((x, -t / 2, max(z_tip, z_base + 4.0)))
    for i in range(n - 1):
        a, b = i * 4, (i + 1) * 4
        for s in range(4):
            s2 = (s + 1) % 4
            faces.append((a + s, a + s2, b + s2, b + s))
    faces.append((3, 2, 1, 0))
    base = (n - 1) * 4
    faces.append((base, base + 1, base + 2, base + 3))
    return {"sharkfin": (verts, faces)}


def _halo():
    parts = []
    xf, xr, z, hw, r = H["x_front"], H["x_rear"], H["z"], H["half_w"], H["tube_r"]
    for sgn in (-1.0, 1.0):
        path = [(xr, sgn * hw * 0.60, z - 268.0),
                (xr - 170.0, sgn * hw, z - 70.0),
                (xf + 240.0, sgn * hw * 0.88, z - 6.0),
                (xf + 60.0, sgn * 90.0, z - 28.0),
                (xf, 0.0, z - 34.0)]
        parts.append(mesh.pipe(path, r, spec.RES["pipe"]))
    parts.append(mesh.pipe([(xf, 0.0, z - 34.0), (xf - 30.0, 0.0, z - 250.0)],
                           r * 1.05, spec.RES["pipe"]))
    return {"halo": mesh.join(*parts)}


def _cockpit():
    out = {}
    sx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2
    out["seat"] = mesh.box(sx + 110.0, 0.0, 300.0, 640.0, 360.0, 290.0)
    wv, wf = mesh.tube(-24.0, 24.0, 58.0, 112.0, 26)
    wv = [(pz + T["cockpit_x0"] + 140.0, py, px + 570.0) for (px, py, pz) in wv]
    out["steering"] = (wv, wf)
    # headrest / roll structure padding
    out["headrest"] = mesh.box(T["cockpit_x1"] - 40.0, 0.0, 620.0, 220.0, 300.0, 130.0)
    return out


def surface_point(x, angle_deg, standoff=0.0):
    """A point on (or just off) the central body at a clock angle.

    Detail parts that lie on the bodywork -- gills, vanes, camera pods -- have
    to start at the surface. Anything placed by eye either floats or sinks,
    and the error changes along the car because the section does.
    """
    hw, z_bot, z_top, n, bias = _sample(spec.BODY, x)
    zc = (z_bot + z_top) / 2 + bias * (z_top - z_bot) * 0.5
    hz = (z_top - z_bot) / 2
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    p = 2.0 / n
    return (x,
            (hw + standoff) * math.copysign(abs(ca) ** p, ca),
            zc + (hz + standoff) * math.copysign(abs(sa) ** p, sa))


def sidepod_point(x, f_y, f_z, standoff=0.0):
    """A point on a sidepod flank: f_y 0 inboard to 1 outboard, f_z 0 low to
    1 high, on the side the caller signs f_y with."""
    y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, abs(x))
    sgn = 1.0 if f_y >= 0 else -1.0
    y = y_in + (y_out - y_in) * abs(f_y)
    z = z_bot + (z_top - z_bot) * f_z
    return (x, sgn * (y + standoff * abs(f_y)), z)
