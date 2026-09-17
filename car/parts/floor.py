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
    out.update(_diffuser())
    out.update(_strakes())
    out.update(_skirts())
    out.update(_inlet_lip())
    out.update(_plenum())
    return out


def _loft(rings, capped=True):
    m = len(rings[0])
    verts = [v for ring in rings for v in ring]
    faces = []
    for i in range(len(rings) - 1):
        for j in range(m):
            a = i * m + j
            b = i * m + (j + 1) % m
            faces.append((a, b, b + m, a + m))
    if capped:
        faces.append(tuple(range(m - 1, -1, -1)))
        base = (len(rings) - 1) * m
        faces.append(tuple(range(base, base + m)))
    return verts, faces


def _inlet_lip():
    """The floor's leading edge: a rolled lip that meters the inlet.

    Everything downstream of it is set by how much air this lets in. A cut
    edge spills, stalls the tunnel inlet at low ride height and throws the
    ride-height sensitivity up; a rolled lip turns the flow smoothly down
    into the contraction and keeps the inlet attached across the range.
    """
    rings = []
    for i in range(6):
        y = (half_width(F["x0"]) - 22.0) * (2.0 * i / 5.0 - 1.0)
        # a rounded roll: entry face curves down and under to meet the floor
        sect = []
        for j in range(21):
            a = math.pi / 2.0 * j / 20.0
            r = 16.0
            sect.append((F["x0"] + 16.0 - r * math.cos(a),
                         _floor_z(F["x0"]) + 16.0 - r + r * math.sin(a),
                         y))
        sect.append((F["x0"] + 16.0 + 6.0,
                     _floor_z(F["x0"]) + 1.0, y))
        rings.append([(px, pz, py) for (px, pz, py) in sect])
    return {"floor_inlet_lip": _loft(rings)}


def _plenum():
    out = {}
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        rings = []
        for i in range(65):
            x = F["x0"] + (F["x1"] - F["x0"]) * i / 64.0
            y = sgn * (half_width(x) - 28.0)
            z = _floor_z(x)
            rings.append([(x, y - 4.0, 10.0), (x, y + 4.0, 10.0),
                          (x, y + 4.0, z + 6.0), (x, y - 4.0, z + 6.0)])
        out[f"floor_plenum_edge_{side}"] = _loft(rings)
        rings = []
        fan = spec.FAN
        for i in range(25):
            t = i / 24.0
            e = t * t * (3.0 - 2.0 * t)
            x = fan["x"] - 240.0 + 240.0 * t
            z = fan["plenum_z0"] + (fan["z"] - fan["plenum_z0"]) * e
            r = fan["plenum_r"] * (1.0 + 0.12 * (1.0 - t) ** 2)
            rings.append([(x, sgn * fan["y"] + r * math.cos(a),
                           z + r * math.sin(a))
                          for a in [2.0 * math.pi * j / 48.0 for j in range(48)]])
        inner = [[(x, sgn * fan["y"] + (y - sgn * fan["y"]) * 0.97,
                   zc + (z - zc) * 0.97)
                  for x, y, z in ring]
                 for ring, zc in zip(rings, [
                     fan["plenum_z0"] + (fan["z"] - fan["plenum_z0"])
                     * (i / 24.0) ** 2 * (3.0 - 2.0 * i / 24.0)
                     for i in range(25)])]
        out[f"floor_fan_throat_{side}"] = _loft(rings + list(reversed(inner)) + [rings[0]], False)
    return out


def _floor_z(x):
    """Underfloor height: flat under the nose, pinched at the throat, then
    expanding hard through the diffuser."""
    if x <= F["throat_x"]:
        f = (x - F["x0"]) / (F["throat_x"] - F["x0"])
        e = F["entry_z"]
        return e - (e - F["throat_z"]) * f ** 1.3 + 18.0
    if x <= F["diffuser_x"]:
        return F["throat_z"] + 18.0
    f = (x - F["diffuser_x"]) / (F["x1"] - F["diffuser_x"])
    expansion = (f * f / 0.30 if f < 0.15 else f - 0.075) / 0.925
    return F["throat_z"] + 18.0 + (F["diffuser_exit_z"] - F["throat_z"]) * expansion


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
    n = 60
    xs = [F["x0"] + (F["x1"] - F["x0"]) * i / (n - 1) for i in range(n)]
    rings = []
    for x in xs:
        hw = half_width(x)
        z_lo = 10.0
        z_hi = max(z_lo + 14.0, _floor_z(x) * 0.35 + 14.0)
        # The floor edge is rolled up, not cut square: that roll is what
        # seals the edge and stops the outboard flow spilling under. A
        # four-point section could not express it.
        d = z_hi - z_lo
        sect = [(-hw, z_lo), (hw, z_lo), (hw + 9.0, z_lo + d * 0.55),
                (hw, z_hi), (-hw, z_hi), (-hw - 9.0, z_lo + d * 0.55)]
        loop = shapes.rounded_polygon(
            sect, [d * 0.30, d * 0.30, d * 0.45, d * 0.30,
                   d * 0.30, d * 0.45], seg=4)
        rings.append([(x, py, pz) for (py, pz) in loop])
    verts = [v for r in rings for v in r]
    m = len(rings[0])
    faces = []
    for i in range(n - 1):
        a, b = i * m, (i + 1) * m
        for s_ in range(m):
            s2 = (s_ + 1) % m
            faces.append((a + s_, a + s2, b + s2, b + s_))
    faces.append(tuple(range(m - 1, -1, -1)))
    base = (n - 1) * m
    faces.append(tuple(range(base, base + m)))
    return {"floor_surface": (verts, faces)}


def _plank():
    """The reference plane -- a flat plank down the centreline between the
    tunnels, which is what actually sets ride height."""
    # The plank is bolted UNDER the floor and its underside is the reference
    # plane -- it is the lowest thing on the car. It used to sit at z 18-34,
    # entirely inside the floor panel above it, with the titanium skids buried
    # in there too, ready to throw sparks from inside the bodywork.
    parts = [shapes.rounded_box((F["x0"] + F["x1"]) / 2, 0.0, 6.0,
                                F["x1"] - F["x0"], F["tunnel_inner_y"] * 2,
                                12.0, 5.0, seg=6)]
    # The titanium skids let into it. They are the things that actually touch
    # the ground and throw the sparks, and they are inspected for wear after
    # the race, so they are countersunk into the plank on their own bolts.
    span = F["x1"] - F["x0"]
    for i in range(6):
        x = F["x0"] + span * (0.18 + 0.13 * i)
        for sgn in (-1.0, 1.0):
            y = sgn * F["tunnel_inner_y"] * 0.62
            # let into the plank so the two wear together, which is the
            # whole point of them
            parts.append(shapes.rounded_box(x, y, 3.0, 110.0, 76.0, 6.0,
                                            4.0, seg=6))
            for dx in (-34.0, 34.0):
                bv, bf = mesh.revolve_closed(
                    [(0.0, 0.0), (5.0, 0.0), (5.0, 9.0), (2.0, 11.0),
                     (0.0, 11.0)], 12)
                parts.append(([(px + x + dx, py + y, pz + 6.0)
                               for (pz, py, px) in bv], bf))
    return {"floor_plank": mesh.join(*parts)}


def _tunnels():
    """Two venturi tunnels: inlet, throat, then the diffuser ramp.

    The section was a rectangle -- four points, so however many stations it
    was lofted through it stayed a box with a sloping lid. A venturi tunnel is
    a moulded duct: the roof arches, the keel side is shallow and the outboard
    side deep so the low pressure sits where the floor is widest, and every
    corner has a radius because that is where the flow would otherwise
    separate first.
    """
    out = {}
    n = 40
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
            rings.append(_tunnel_section(x, y_in, y_out, 10.0, z_roof))
        verts = [v for r in rings for v in r]
        m = len(rings[0])
        faces = []
        for i in range(n - 1):
            a, b = i * m, (i + 1) * m
            for s in range(m):
                s2 = (s + 1) % m
                faces.append((a + s, a + s2, b + s2, b + s))
        faces.append(tuple(range(m - 1, -1, -1)))
        base = (n - 1) * m
        faces.append(tuple(range(base, base + m)))
        out[f"tunnel_{side}"] = (verts, faces)
    return out


def _tunnel_section(x, y_in, y_out, z_floor, z_roof):
    """One cross-section of a tunnel: flat floor, arched roof, filleted."""
    h = z_roof - z_floor
    w = y_out - y_in
    z_keel = z_floor + h * 0.52
    z_wall = z_floor + h * 0.90
    pts = [(y_in, z_floor), (y_out, z_floor), (y_out, z_wall)]
    # the roof, as a Bezier arch from the outer wall over to the keel
    crown = (y_in + w * 0.46, z_floor + h * 1.04)
    for k in range(1, 13):
        u = k / 12.0
        pts.append((
            (1 - u) ** 2 * y_out + 2 * (1 - u) * u * crown[0] + u * u * y_in,
            (1 - u) ** 2 * z_wall + 2 * (1 - u) * u * crown[1]
            + u * u * z_keel))
    r = min(abs(w) * 0.10, h * 0.26)
    loop = shapes.rounded_polygon(pts, [r, r] + [0.0] * (len(pts) - 2), seg=5)
    return [(x, py, pz) for (py, pz) in loop]


def _diffuser():
    """What the diffuser has that the tunnel loft does not.

    `_tunnels` already carries the expansion ramp, because the roof follows
    `_floor_z` all the way to x1 and that is where the ramp lives. What it
    does not give is the three things that decide whether the ramp works: a
    trailing edge that is an edge rather than the place a surface stopped,
    fences inside the expansion to stop the flow spilling sideways out of it,
    and the kick that turns the last of the ramp into load instead of letting
    it dump straight into the base.

    A diffuser that separates makes no downforce at all, and it separates at
    the corners first, which is what the fences are for.
    """
    out = {}
    x_d, x_e = F["diffuser_x"], F["x1"]

    def plate(pts_lo, pts_hi, t):
        """A thin vertical plate through two polylines, `t` thick in y."""
        verts, faces = [], []
        n = len(pts_lo)
        for sgn in (-1.0, 1.0):
            base = len(verts)
            for (x, y, z) in pts_lo:
                verts.append((x, y + sgn * t / 2, z))
            for (x, y, z) in reversed(pts_hi):
                verts.append((x, y + sgn * t / 2, z))
            m = 2 * n
            if sgn < 0:
                faces.append(tuple(range(base, base + m)))
            else:
                faces.append(tuple(range(base + m - 1, base - 1, -1)))
        m = 2 * n
        for i in range(m):
            j = (i + 1) % m
            faces.append((i, j, m + j, m + i))
        return verts, faces

    # the fences: two a side inside the expansion, standing off the tunnel
    # roof, tallest at the exit where the section is deepest
    fences = []
    for sgn in (-1.0, 1.0):
        for frac in (0.34, 0.68):
            y = sgn * (F["tunnel_inner_y"] +
                       (F["tunnel_half_w"] - F["tunnel_inner_y"]) * frac)
            lo, hi = [], []
            for i in range(9):
                t = i / 8.0
                x = x_d + (x_e - x_d) * t
                z = _floor_z(x)
                lo.append((x, y, 8.0))
                hi.append((x, y, z - 6.0 * (1.0 - t) - 2.0))
            fences.append(plate(lo, hi, F["strake_t"] * 0.7))
    out["diffuser_fences"] = mesh.join(*fences)

    # the trailing edge: a real lip across both tunnel exits, not the end of
    # a loft. 18 mm deep, which is what gives the ramp something to work
    # against instead of bleeding into the base pressure.
    lips = []
    for sgn in (-1.0, 1.0):
        y_in = sgn * F["tunnel_inner_y"]
        y_out = sgn * max(half_width(x_e) - 34.0, F["tunnel_inner_y"] + 60.0)
        z = _floor_z(x_e)
        lo = [(x_e - 6.0, y_in, z), (x_e - 6.0, y_out, z)]
        hi = [(x_e - 6.0, y_in, z - 18.0), (x_e - 6.0, y_out, z - 18.0)]
        verts = [(x, y, zz) for (x, y, zz) in lo] + \
                [(x, y, zz) for (x, y, zz) in hi]
        verts += [(x + 7.0, y, zz) for (x, y, zz) in lo] + \
                 [(x + 7.0, y, zz) for (x, y, zz) in hi]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4),
             (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
        lips.append((verts, f))
    out["diffuser_lip"] = mesh.join(*lips)

    # and the kick: the last 120 mm of ramp turned up, so the expansion ends
    # on a defined angle rather than running out of car
    kicks = []
    for sgn in (-1.0, 1.0):
        y_in = sgn * F["tunnel_inner_y"]
        y_out = sgn * max(half_width(x_e) - 34.0, F["tunnel_inner_y"] + 60.0)
        rings = []
        for i in range(5):
            t = i / 4.0
            x = x_e - 120.0 + 120.0 * t
            z = _floor_z(x) - 22.0 * t * t
            rings.append([(x, y_in, z), (x, y_out, z),
                          (x, y_out, z + 5.0), (x, y_in, z + 5.0)])
        verts = [v for r in rings for v in r]
        faces = []
        for i in range(4):
            a, b = i * 4, (i + 1) * 4
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((a + k, a + k2, b + k2, b + k))
        faces.append((3, 2, 1, 0))
        faces.append((16, 17, 18, 19))
        kicks.append((verts, faces))
    out["diffuser_kick"] = mesh.join(*kicks)
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
            # A diffuser strake is not a flat plate on edge. It has to hold
            # the flow against a roof that is climbing away from it, so it
            # turns gently outboard as it goes back, its top follows the
            # tunnel roof rather than running level, and it is thickest a
            # third of the way along like any other loaded section.
            turn = 20.0 + 16.0 * k / max(F["n_strakes"] - 1, 1)
            cam = [(x0 + (x1 - x0) * i / 12.0,
                    y + sgn * turn * (i / 12.0) ** 1.7) for i in range(13)]
            # turning_vane's `t` is a fraction of chord, and the chord here
            # is the strake's whole 2.2 m length: at t=0.075 these came out
            # 218 mm thick. A diffuser strake is a 9 mm carbon fence.
            chord = math.dist(cam[0], cam[-1]) or 1.0
            parts.append(shapes.turning_vane(
                cam, 10.0, _floor_z(x1) - 24.0, t=F["strake_t"] / chord,
                # twist is degrees of plan rotation about the leading edge,
                # and on a 2.2 m chord six degrees throws the trailing edge
                # 227 mm sideways between the floor and the roof. What a
                # strake actually does is lean out a little as it rises, so
                # it follows the flow spreading into the diffuser.
                twist=0.0, lean=sgn * 14.0, n_z=16, n_chord=44,
                top_cut=lambda u, x0=x0, x1=x1: (
                    _floor_z(x0 + (x1 - x0) * u) - 24.0)))
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
        # A skirt is a blade with a replaceable wear strip along the bottom
        # and a rebate up the back where it slides in its carrier. Square in
        # section it would jam, and it would seal on a sharp corner that
        # lasted about one lap.
        h = F["skirt_depth"] + 14.0
        sect = [(-t / 2, 0.0), (t / 2, 0.0), (t / 2, h * 0.30),
                (t / 2 - 3.5, h * 0.36), (t / 2 - 3.5, h * 0.80),
                (t / 2, h * 0.86), (t / 2, h), (-t / 2, h)]
        loop = shapes.rounded_polygon(sect, [3.5, 3.5, 2.0, 1.5, 1.5, 2.0,
                                             3.0, 3.0], seg=3)
        rings = []
        for (x, y) in rows:
            rings.append([(x, y + dy, dz) for (dy, dz) in loop])
        m = len(rings[0])
        verts = [v for r in rings for v in r]
        faces = []
        for i in range(n - 1):
            a, b = i * m, (i + 1) * m
            for k in range(m):
                k2 = (k + 1) % m
                faces.append((a + k, a + k2, b + k2, b + k))
        faces.append(tuple(range(m - 1, -1, -1)))
        base = (n - 1) * m
        faces.append(tuple(range(base, base + m)))
        parts.append((verts, faces))
    return {"floor_skirts": mesh.join(*parts)}
