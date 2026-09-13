"""Panelise the solid parts of the car for the flow solve.

A vortex lattice makes lift but it is invisible to the air everywhere else: a
lattice of wings alone lets the flow pass straight through the tub, the
sidepods and the wheels. Streamlines drawn from it wrap the wings and ignore
the car, which is not what a car does to the air.

So the solid body gets source panels. A source panel pushes flow out of
itself; solve the strengths so that the normal velocity vanishes on every
panel and the body becomes solid. This is the classical Hess-Smith
arrangement, at its lowest order: each panel is represented by a point source
of strength sigma*area at its centroid, which is accurate when panels are
small compared with the distance between them and is what makes the solve
cheap enough to run in a browser.

Panels come from the same station tables the geometry is lofted from, so the
shape the air sees and the shape on screen are the same shape.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "car"))

import spec
from parts import chassis, wheels, floor

MM = 0.001


def _quad(a, b, c, d):
    """Centroid, outward normal and area of one quad, in metres."""
    cx = (a[0] + b[0] + c[0] + d[0]) / 4.0
    cy = (a[1] + b[1] + c[1] + d[1]) / 4.0
    cz = (a[2] + b[2] + c[2] + d[2]) / 4.0
    ux, uy, uz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    vx, vy, vz = d[0] - b[0], d[1] - b[1], d[2] - b[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    mag = math.sqrt(nx * nx + ny * ny + nz * nz)
    if mag < 1e-12:
        return None
    area = 0.5 * mag
    return ([cx * MM, cy * MM, cz * MM],
            [nx / mag, ny / mag, nz / mag],
            area * MM * MM)


def _loft(rings, flip=False):
    """Quads between consecutive rings of equal length."""
    out = []
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        n = len(r0)
        for j in range(n):
            j2 = (j + 1) % n
            q = (_quad(r0[j], r0[j2], r1[j2], r1[j]) if not flip
                 else _quad(r0[j2], r0[j], r1[j], r1[j2]))
            if q:
                out.append(q)
    return out


def _cap(ring, centre, outward_sign):
    """Close a loft's open end with a fan of triangles to the ring centre.

    A source-panel body has to be closed. An open end is a hole, and the solve
    happily blows air through it: with the nose, the tail and both sides of
    every tyre left open, the net source strength came out at 8.8 m3/s on a
    body that should sum to zero.
    """
    out = []
    n = len(ring)
    for j in range(n):
        j2 = (j + 1) % n
        a, b = ring[j], ring[j2]
        q = _quad(a, b, centre, centre)
        if not q:
            continue
        c, nn, ar = q
        # a cap's normal is along the loft axis, pointing out of the body
        nn = [outward_sign[0], outward_sign[1], outward_sign[2]]
        out.append((c, nn, ar))
    return out


def _outward(panels, axis_point):
    """Point every normal away from the body's own axis.

    The loft's winding is not guaranteed consistent once a section table
    changes sign of curvature, and a source panel with an inward normal sucks
    instead of blows.
    """
    fixed = []
    for (c, n, a) in panels:
        dx = c[0] - axis_point[0]
        dy = c[1] - axis_point[1]
        dz = c[2] - axis_point[2]
        if n[0] * dx + n[1] * dy + n[2] * dz < 0:
            n = [-n[0], -n[1], -n[2]]
        fixed.append((c, n, a))
    return fixed


def central_body(n_x=22, n_theta=18):
    """The tub, nose and engine cover, as one lofted surface."""
    x0, x1 = spec.BODY[0][0], spec.BODY[-1][0]
    rings = []
    for i in range(n_x):
        f = i / (n_x - 1)
        f = 0.5 * (1 - math.cos(math.pi * f))       # cluster at nose and tail
        x = x0 + (x1 - x0) * f
        rings.append(chassis.body_section(x, segments=n_theta))
    out = []
    for i in range(len(rings) - 1):
        xa = rings[i][0][0]
        mid = (xa + rings[i + 1][0][0]) / 2
        hw, zb, zt, nn, bias = chassis._sample(spec.BODY, mid)
        zc = (zb + zt) / 2 + bias * (zt - zb) * 0.5
        seg = _loft([rings[i], rings[i + 1]])
        out.extend(_outward(seg, (mid * MM, 0.0, zc * MM)))

    for (ring, sgn) in ((rings[0], (-1.0, 0.0, 0.0)),
                        (rings[-1], (1.0, 0.0, 0.0))):
        x = ring[0][0]
        hw, zb, zt, nn, bias = chassis._sample(spec.BODY, x)
        zc = (zb + zt) / 2 + bias * (zt - zb) * 0.5
        out.extend(_cap(ring, (x, 0.0, zc), sgn))
    return out


def sidepods(n_x=10, n_v=6):
    """Both sidepods, from the undercut table."""
    out = []
    T = spec.SIDEPOD_TABLE
    for sgn in (-1.0, 1.0):
        rings = []
        for i in range(n_x):
            x = T[0][0] + (T[-1][0] - T[0][0]) * i / (n_x - 1)
            ring = []
            # round the section: outboard face, top, inboard, bottom
            for j in range(n_v * 2):
                t = j / (n_v * 2)
                a = 2 * math.pi * t
                fy = 0.5 + 0.5 * math.cos(a)
                fz = 0.5 + 0.5 * math.sin(a)
                ring.append(chassis.sidepod_point(x, sgn * fy, fz))
            rings.append(ring)
        for i in range(len(rings) - 1):
            xm = (rings[i][0][0] + rings[i + 1][0][0]) / 2
            y_in, y_out, zb, zt, nn = chassis._sample(spec.SIDEPOD_TABLE, xm)
            axis = (xm * MM, sgn * (y_in + y_out) / 2 * MM, (zb + zt) / 2 * MM)
            out.extend(_outward(_loft([rings[i], rings[i + 1]]), axis))
        for (ring, nx) in ((rings[0], (-1.0, 0.0, 0.0)),
                           (rings[-1], (1.0, 0.0, 0.0))):
            x = ring[0][0]
            y_in, y_out, zb, zt, nn = chassis._sample(spec.SIDEPOD_TABLE, x)
            out.extend(_cap(ring, (x, sgn * (y_in + y_out) / 2,
                                   (zb + zt) / 2), nx))
    return out


def tyres(n_a=14, n_w=4):
    """The wheels, as cylinders with flat sides.

    A racing car's wheels are roughly a third of its drag and they dominate
    the flow behind the front axle. Leaving them out of the solve would make
    the streamlines behind them meaningless.
    """
    out = []
    W = spec.WHEEL
    for (tag, x, y, w, od) in wheels.corners():
        r = od / 2
        rings = []
        for k in range(n_w + 1):
            yy = y - w / 2 + w * k / n_w
            ring = []
            for j in range(n_a):
                a = 2 * math.pi * j / n_a
                ring.append((x + r * math.cos(a), yy, r + r * math.sin(a)))
            rings.append(ring)
        for i in range(len(rings) - 1):
            ym = (rings[i][0][1] + rings[i + 1][0][1]) / 2
            out.extend(_outward(_loft([rings[i], rings[i + 1]]),
                                (x * MM, ym * MM, r * MM)))
        for (ring, sgn) in ((rings[0], (0.0, -1.0, 0.0)),
                            (rings[-1], (0.0, 1.0, 0.0))):
            out.extend(_cap(ring, (x, ring[0][1], r), sgn))
    return out


def floor_plate(n_x=14, n_y=6):
    """The underfloor, as a thin closed box on the floor's own plan outline.

    A one-sided sheet is not a body: sources on it push air out of one face
    and nothing holds the other, so the solve drives flow straight through the
    ground. The floor is the car's biggest aerodynamic surface, so it is worth
    closing properly.
    """
    out = []
    F = spec.FLOOR
    z_lo, z_hi = 12.0, 34.0
    xs = [F["x0"] + (F["x1"] - F["x0"]) * i / n_x for i in range(n_x + 1)]
    for i in range(n_x):
        x0, x1 = xs[i], xs[i + 1]
        w0, w1 = floor.half_width(x0), floor.half_width(x1)
        for j in range(n_y):
            f0, f1 = -1 + 2 * j / n_y, -1 + 2 * (j + 1) / n_y
            for (z, nz) in ((z_lo, -1.0), (z_hi, 1.0)):
                q = _quad((x0, w0 * f0, z), (x1, w1 * f0, z),
                          (x1, w1 * f1, z), (x0, w0 * f1, z))
                if q:
                    out.append((q[0], [0.0, 0.0, nz], q[2]))
        for (f, ny) in ((-1.0, -1.0), (1.0, 1.0)):
            q = _quad((x0, w0 * f, z_lo), (x1, w1 * f, z_lo),
                      (x1, w1 * f, z_hi), (x0, w0 * f, z_hi))
            if q:
                out.append((q[0], [0.0, ny, 0.0], q[2]))
    # close the two ends
    for (x, nx) in ((xs[0], -1.0), (xs[-1], 1.0)):
        w = floor.half_width(x)
        q = _quad((x, -w, z_lo), (x, w, z_lo), (x, w, z_hi), (x, -w, z_hi))
        if q:
            out.append((q[0], [nx, 0.0, 0.0], q[2]))
    return out


def build():
    panels = central_body() + sidepods() + tyres() + floor_plate()
    return {
        "n": len(panels),
        "c": [v for (c, n, a) in panels for v in c],
        "n_": [v for (c, n, a) in panels for v in n],
        "a": [a for (c, n, a) in panels],
    }


if __name__ == "__main__":
    b = build()
    print(f"{b['n']} body panels")
    tot = sum(b["a"])
    print(f"total wetted area {tot:.2f} m2")
