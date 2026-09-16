"""The VX-1 as a closed quadrilateral surface -- and why it is NOT wired in.

This panels the car the way tools/panel_geom.py panels the aeroplane, and the
aeroplane's solver will not solve it. That is not a bug in either; it is a
statement about the two shapes, and the measurement is at the bottom of this
file so it can be re-taken rather than believed.

A panel method with a ground plane works by mirroring every panel in z = 0.
That means each panel on the floor faces its own image across twice the ride
height, and the influence matrix is near-singular when a panel faces another
one much closer than its own width. On this car:

    closest panel to its own ground image     0.035 panel widths
    front wing elements 1 and 2 to each other 0.38  panel widths
    median panel                              89 mm

The floor is 10 mm off the ground and its panels are 200 to 500 mm across.
To put a floor panel one width from its own image it would have to be 20 mm
across, and the floor is 5.5 square metres: about 14,000 panels on the floor
alone, before the wings' 16 mm slot gaps, which want panels smaller still.
A dense direct solve is O(N cubed); at 14,000 panels that is 9 x 10^11
operations, which is not a thing a browser does while you move a slider.

So it is a question of SCALE RATIO, and the two models are not alike:

    aeroplane   smallest feature / model length   10 mm / 440 mm    1 : 44
    car         smallest feature / model length   10 mm / 4560 mm   1 : 456

The aeroplane's smallest aerodynamic feature is resolvable at a thousand
panels. The car's is not, by a factor of ten in each direction. Real car
aerodynamics panel codes run 50,000 to 200,000 panels with iterative solvers
and multipole acceleration; that is a different program, not a bigger number
in this one.

The car therefore keeps the solver it has -- a vortex lattice for the eight
wing elements and source panels for the body -- which is cruder, and is not
made less crude by replacing it with something that cannot be solved. What
this file is for is the measurement: if the car's ride height, slot gaps or
the solver ever change, `python3 tools/panel_geom.py` says so in numbers.
"""

import math

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec                                        # noqa: E402
from parts import chassis, floor as floor_part     # noqa: E402
from panelgeom import (MM, Geom, orient, solid_angle, surface, trim,
                       control, _centroid, _size)  # noqa: E402


def lofted(g, name, rings, cap_front=True, cap_back=True, axis=None):
    """A closed body from a list of rings of equal length.

    `axis(x)` gives a point inside the section at station x, which is what the
    winding is derived against. Without one the rings' own centroid is used,
    which is right for anything star-shaped about its middle.
    """
    n, m = len(rings), len(rings[0])
    grid = []
    for i in range(n - 1):
        row = []
        for j in range(m):
            k = (j + 1) % m
            row.append([rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]])
        grid.append(row)

    def ref(q):
        x = sum(p[0] for p in q) / 4.0
        if axis:
            return axis(x)
        i = min(range(n), key=lambda t: abs(rings[t][0][0] - x))
        return [sum(p[c] for p in rings[i]) / m for c in range(3)]

    g.patch(name, orient(grid, ref), n - 1, m, wrap_j=True, body=name)
    for (ring, want, tag) in ((rings[0], -1, "front"), (rings[-1], 1, "back")):
        if (tag == "front" and not cap_front) or (tag == "back" and not cap_back):
            continue
        c = [sum(p[k] for p in ring) / m for k in range(3)]
        inner = [c[0] - want * 1.0, c[1], c[2]]
        row = [[ring[j], ring[(j + 1) % m], c, c] for j in range(m)]
        g.patch(f"{name}_{tag}", orient([row], lambda q: inner), 1, m,
                wrap_j=True, body=name)


def body(g, n_x=16, n_theta=14):
    """Tub, nose and engine cover, off the same loft the bodywork uses."""
    x0, x1 = spec.BODY[0][0], spec.BODY[-1][0]
    rings = []
    for i in range(n_x):
        f = 0.5 * (1 - math.cos(math.pi * i / (n_x - 1)))
        rings.append(chassis.body_section(x0 + (x1 - x0) * f, segments=n_theta))

    def axis(x):
        hw, zb, zt, nn, bias = chassis._sample(spec.BODY, x)
        return [x, 0.0, (zb + zt) / 2 + bias * (zt - zb) * 0.5]

    lofted(g, "body", rings, axis=axis)


def floor(g, n_x=18, n_theta=None):
    """The floor plate, off the same sections the visible floor is lofted
    from, so the shape the air sees is the shape on screen."""
    F = spec.FLOOR
    import shapes
    rings = []
    for i in range(n_x):
        x = F["x0"] + (F["x1"] - F["x0"]) * i / (n_x - 1)
        hw = floor_part.half_width(x)
        z_lo = 10.0
        z_hi = max(z_lo + 14.0, floor_part._floor_z(x) * 0.35 + 14.0)
        d = z_hi - z_lo
        sect = [(-hw, z_lo), (hw, z_lo), (hw + 9.0, z_lo + d * 0.55),
                (hw, z_hi), (-hw, z_hi), (-hw - 9.0, z_lo + d * 0.55)]
        loop = shapes.rounded_polygon(
            sect, [d * 0.30, d * 0.30, d * 0.45, d * 0.30,
                   d * 0.30, d * 0.45], seg=2)
        rings.append([(x, py, pz) for (py, pz) in loop])
    lofted(g, "floor", rings)


def wheel(g, name, xc, yc, r, width, n_a=10, n_w=3):
    """One wheel: a cylinder with rounded shoulders, standing clear of the
    ground by a few millimetres.

    Clear of it on purpose. Every panel has an image in z = 0; a panel
    touching the plane touches its own image, which is a singularity in the
    influence matrix rather than a contact patch.
    """
    lift = 6.0
    rings = []
    prof = [(-0.5, 0.86), (-0.42, 0.98), (-0.2, 1.0), (0.2, 1.0),
            (0.42, 0.98), (0.5, 0.86)]
    for (fy, fr) in prof:
        ring = []
        for j in range(n_a):
            a = 2 * math.pi * j / n_a
            ring.append((xc + r * fr * math.cos(a),
                         yc + fy * width,
                         r + lift + r * fr * math.sin(a)))
        rings.append(ring)
    # the loft runs across the wheel, so its "stations" are spanwise
    n, m = len(rings), n_a
    grid = []
    for i in range(n - 1):
        row = []
        for j in range(m):
            k = (j + 1) % m
            row.append([rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]])
        grid.append(row)
    centre = [xc, yc, r + lift]
    g.patch(name, orient(grid, lambda q: centre), n - 1, m, wrap_j=True,
            body=name)
    for (ring, sgn) in ((rings[0], -1), (rings[-1], 1)):
        c = [sum(p[k] for p in ring) / m for k in range(3)]
        inner = [c[0], c[1] - sgn * 1.0, c[2]]
        row = [[ring[j], ring[(j + 1) % m], c, c] for j in range(m)]
        g.patch(f"{name}_{'in' if sgn < 0 else 'out'}",
                orient([row], lambda q: inner), 1, m, wrap_j=True, body=name)


# ------------------------------------------------------------------- wings

def _wing_element(g, name, stations, m=14):
    """One closed inverted aerofoil element, tip to tip.

    A car's wing is an aerofoil at a negative angle of attack, so the twist
    handed to `surface` is the spec's own `aoa`: in that convention a positive
    twist puts the trailing edge BELOW the leading edge, which is what a rear
    wing does and why it pushes down.
    """
    surface(g, name, stations, m=m)


def front_wing(g, n_span=4, m=9):
    FW = spec.FRONT_WING
    half = FW["span"] / 2.0
    neutral = FW["neutral_half_w"]
    out = []
    for e, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(FW["stack"]):
        tip = half * span_f
        st = []
        for j in range(n_span + 1):
            f = -1.0 + 2.0 * j / n_span
            y = tip * f
            t = abs(y)
            o = 0.0 if t <= neutral else (t - neutral) / max(tip - neutral, 1.0)
            o = o * o * (3 - 2 * o)
            chord = c_r + (c_t - c_r) * o
            aoa = aoa_r + (aoa_t - aoa_r) * o
            z = FW["z"] + dz + rise * o
            st.append((FW["x"] + dx, y, z, chord, 0.10, aoa))
        _wing_element(g, f"front_{e}", st, m=m)
        out.append((f"front_{e}", st))
    return out


def rear_wing(g, n_span=5, m=11):
    RW = spec.REAR_WING
    out = []
    for i in range(RW["elements"]):
        chord = RW["chord"] * (1.0 - 0.42 * i)
        aoa = RW["aoa"] + 9.0 * i
        z = RW["z"] + i * (RW["chord"] * 0.30)
        x = RW["x"] + i * (RW["chord"] * 0.34)
        st = []
        for j in range(n_span + 1):
            y = RW["span"] / 2.0 * (-1.0 + 2.0 * j / n_span)
            st.append((x, y, z, chord, 0.09, aoa))
        _wing_element(g, f"rear_{i}", st, m=m)
        out.append((f"rear_{i}", st))
    return out


def beam_wing(g, n_span=4, m=9):
    BW = spec.BEAM_WING
    out = []
    for i in range(BW["elements"]):
        chord = BW["chord"] * (1.0 - 0.34 * i)
        aoa = BW["aoa"] + 7.0 * i
        z = BW["z"] + i * (BW["chord"] * 0.34)
        st = []
        for j in range(n_span + 1):
            y = BW["span"] / 2.0 * (-1.0 + 2.0 * j / n_span)
            st.append((BW["x"] + i * chord * 0.3, y, z, chord, 0.09, aoa))
        _wing_element(g, f"beam_{i}", st, m=m)
        out.append((f"beam_{i}", st))
    return out


def build(clear=0.35):
    g = Geom()
    body(g)
    floor(g)

    W = spec.WHEEL
    for (nm, x, tr, od, wd) in (
            ("wheel_fl", spec.FRONT_AXLE_X,  spec.TRACK_FRONT, W["front_od"], W["front_w"]),
            ("wheel_fr", spec.FRONT_AXLE_X, -spec.TRACK_FRONT, W["front_od"], W["front_w"]),
            ("wheel_rl", spec.REAR_AXLE_X,   spec.TRACK_REAR,  W["rear_od"],  W["rear_w"]),
            ("wheel_rr", spec.REAR_AXLE_X,  -spec.TRACK_REAR,  W["rear_od"],  W["rear_w"])):
        wheel(g, nm, x, tr / 2.0, od / 2.0, wd)

    fw = front_wing(g)
    rw = rear_wing(g)
    bw = beam_wing(g)

    # The controls: the front flap is the outermost front element, DRS opens
    # the rear wing's upper one.
    control(g, "front_flap", fw[-1][0], fw[-1][1], 0.0, 0.0, 1.0,
            axis=(0, 1, 0))
    control(g, "drs", rw[-1][0], rw[-1][1], 0.0, 0.0, 1.0, axis=(0, 1, 0))

    g.trimmed = trim(g, clear)
    return g


def emit(**kw):
    return build(**kw).emit()


def feasibility():
    """Can this car be panelled at a size a direct solve can afford?

    Two numbers decide it, and both are ratios of a gap to a panel:
    how close a floor panel is to its own image in the ground, and how close
    the closest two components are. Under about one panel width the influence
    matrix is near-singular there and the solution is discretisation noise --
    measured on this car at 0.035 and 0.38, which gave Cp = -19,900 and
    doublet strengths of 790 against a freestream of one.
    """
    d = emit()
    n = d["n"]
    quads = d["quads"]
    def panel(i):
        b = i * 12
        pts = [(quads[b+k*3], quads[b+k*3+1], quads[b+k*3+2]) for k in range(4)]
        c = [sum(p[k] for p in pts) / 4.0 for k in range(3)]
        d1 = [pts[2][k] - pts[0][k] for k in range(3)]
        d2 = [pts[3][k] - pts[1][k] for k in range(3)]
        cr = [d1[1]*d2[2]-d1[2]*d2[1], d1[2]*d2[0]-d1[0]*d2[2],
              d1[0]*d2[1]-d1[1]*d2[0]]
        a = 0.5 * math.sqrt(sum(v*v for v in cr))
        return c, math.sqrt(a)
    info = [panel(i) for i in range(n)]
    worst_img, wi = 1e9, -1
    for i, (c, sz) in enumerate(info):
        r = 2.0 * c[2] / sz
        if r < worst_img:
            worst_img, wi = r, i
    name = lambda i: next((p["name"] for p in d["parts"]
                           if p["start"] <= i < p["start"] + p["count"]), "?")
    comp = lambda i: name(i).rsplit("_", 1)[0] if name(i).rsplit("_", 1)[-1] in (
        "root", "tip", "in", "out", "front", "back") else name(i)
    worst_pair, wp = 1e9, ""
    for i in range(n):
        for j in range(i + 1, n):
            if comp(i) == comp(j):
                continue
            ci, si = info[i]
            cj, sj = info[j]
            dd = math.dist(ci, cj) / (0.5 * (si + sj))
            if dd < worst_pair:
                worst_pair, wp = dd, f"{comp(i)} / {comp(j)}"
    sizes = sorted(s for (_c, s) in info)
    print(f"\n{n} panels, {len(d['te'])} trailing edges")
    print(f"  median panel                          {sizes[n // 2] / MM:.0f} mm")
    print(f"  closest panel to its ground image     {worst_img:.3f} panel widths"
          f"   ({name(wi)})")
    print(f"  closest two components                {worst_pair:.2f} panel widths"
          f"   ({wp})")
    ok = worst_img > 1.0 and worst_pair > 0.6
    print("\n" + ("a direct panel solve could answer about this car"
                  if ok else
                  "NOT solvable at this panel count -- see the file's header"))
    return ok


if __name__ == "__main__":
    feasibility()
