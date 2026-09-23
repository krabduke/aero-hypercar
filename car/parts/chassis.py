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
import shapes
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

    # The inlet mouth.
    #
    # It was a length of plain pipe -- mesh.tube, two stations, constant
    # radius -- standing on the leading edge of the sidepod. An inlet is the
    # opposite of that: the whole of its job happens in its section. The lip
    # is rolled over so the flow stays attached at yaw, the duct contracts
    # from mouth to throat, and a splitter vane divides the radiator feed
    # from the flow going over the top of it.
    I = spec.INLET
    mouths = []
    for sgn in (-1.0, 1.0):
        parts = []
        hw0 = (I["y1"] - I["y0"]) / 2
        hz0 = (I["z1"] - I["z0"]) / 2
        yc = sgn * (I["y0"] + I["y1"]) / 2
        zc = (I["z0"] + I["z1"]) / 2
        lip, wall, tf = I["lip_r"], I["wall"], I["throat_f"]
        nseg = 30
        rings = []
        for (x, sw, sh, rr) in ((I["x_lip"] - lip, 0.90, 0.90, 0.0),
                                (I["x_lip"], 1.00, 1.00, 0.0),
                                (I["x_lip"] + lip * 1.6, 1.00, 1.00, 1.0),
                                (I["x_throat"], tf, tf * 1.06, 1.0)):
            outer, inner = [], []
            for k in range(nseg):
                ang = 2 * math.pi * k / nseg
                ca, sa = math.cos(ang), math.sin(ang)
                ow = hw0 * sw + (wall if rr else 0.0)
                oh = hz0 * sh + (wall if rr else 0.0)
                outer.append((x, yc + ow * ca, zc + oh * sa))
                inner.append((x, yc + (hw0 * sw - wall * rr) * ca,
                              zc + (hz0 * sh - wall * rr) * sa))
            rings.append((outer, inner))
        verts, faces = [], []
        for (o, i) in rings:
            verts.extend(o); verts.extend(i)
        per = 2 * nseg
        for r in range(len(rings) - 1):
            b0, b1 = r * per, (r + 1) * per
            for k in range(nseg):
                k2 = (k + 1) % nseg
                faces.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
                faces.append((b0 + nseg + k2, b0 + nseg + k,
                              b1 + nseg + k, b1 + nseg + k2))
        for k in range(nseg):
            k2 = (k + 1) % nseg
            faces.append((k2, k, nseg + k, nseg + k2))
            bb = (len(rings) - 1) * per
            faces.append((bb + k, bb + k2, bb + nseg + k2, bb + nseg + k))
        parts.append((verts, faces))
        parts.append(shapes.rounded_box(
            (I["x_lip"] + I["x_throat"]) / 2, yc, zc,
            I["x_throat"] - I["x_lip"], hw0 * 1.7, I["vane_t"],
            r=I["vane_t"] * 0.4))
        mouths.append(mesh.join(*parts))
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
        # the opening closes just short of x1; at f * 1.1 it closed 50 mm
        # sooner, on the back of the driver's helmet
        w = min(T["cockpit_half_w"], hw * 0.80) * math.sin(math.pi * min(f * 1.04, 1.0)) ** 0.35
        z = z_top - 22.0
        path_l.append((x, -w, z))
        path_r.append((x, w, z))
        # the opening closes a little ahead of x1; past that the lip used to
        # carry on down the centreline as a tail behind the driver's head
        if f > 0.5 and w == 0.0:
            break
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
        # thickest around a third of the way back, closing towards the
        # trailing edge, which is where a section's thickness actually goes
        t = D["sharkfin_t"] * (0.30 + 0.94 * math.sin(math.pi * f ** 0.62))
        zt = max(z_tip, z_base + 4.0)
        # A fin is a vertical wing: it only does anything in yaw, and it can
        # only do it with a section. As a flat card of constant thickness it
        # stalled at the first degree of slip.
        h = zt - z_base
        for (dy, dz) in _fin_section(t, h):
            verts.append((x, dy, z_base + dz))
    m = len(_fin_section(1.0, 1.0))
    for i in range(n - 1):
        a, b = i * m, (i + 1) * m
        for s in range(m):
            s2 = (s + 1) % m
            faces.append((a + s, a + s2, b + s2, b + s))
    faces.append(tuple(range(m - 1, -1, -1)))
    base = (n - 1) * m
    faces.append(tuple(range(base, base + m)))
    return {"sharkfin": (verts, faces)}


def _fin_section(t, h, n=11):
    """One vertical slice of the fin: full thickness where it meets the
    engine cover, thinning as it rises, rolled over at the top edge.

    A fin of constant thickness with a cut top is a card. The taper is what
    keeps the tip from being a slab of dead weight a metre above the roll
    hoop, and the roll is what stops the top edge shedding its own vortex.
    """
    def w(f):
        return t * (1.0 - 0.58 * f ** 1.3)
    pts = []
    top = 0.86
    for i in range(n):                      # up the right-hand face
        f = top * i / (n - 1)
        pts.append((w(f) / 2, h * f))
    rt = w(top) / 2
    for k in range(1, 6):                   # roll over the top
        a = (math.pi / 2) * k / 6
        pts.append((rt * math.cos(a), h * top + rt * 1.9 * math.sin(a)))
    pts.append((0.0, h * top + rt * 1.9))
    for k in range(5, 0, -1):
        a = (math.pi / 2) * k / 6
        pts.append((-rt * math.cos(a), h * top + rt * 1.9 * math.sin(a)))
    for i in range(n - 1, -1, -1):          # down the left-hand face
        f = top * i / (n - 1)
        pts.append((-w(f) / 2, h * f))
    return pts


def _halo():
    """One continuous hoop and one central pillar.

    This was built as two separate half-loops that both terminated at the same
    point on the centreline, so the two tubes ran into and through each other
    at the front -- which is what a halo must never be, because the whole
    point of it is that it is a single closed loop with nothing to come apart.
    It is one swept path now, from the left rear mount, round the front, to
    the right rear mount, with a single pillar down the middle.
    """
    out = {}
    xf, xr, z, hw, r = H["x_front"], H["x_rear"], H["z"], H["half_w"], H["tube_r"]
    apex = (xf, 0.0, z)
    span = xr - xf
    oval = [(r * 0.62 * math.cos(2 * math.pi * i / 32),
             r * 1.18 * math.sin(2 * math.pi * i / 32)) for i in range(32)]

    path = []
    for sgn in (-1.0, 1.0):
        side = [(xr, sgn * hw * 0.62, z - 262.0),      # rear mount, on the tub
                (xr - 90.0, sgn * hw * 0.90, z - 120.0),
                (xr - 210.0, sgn * hw, z - 46.0),
                (xf + 300.0, sgn * hw * 0.95, z - 8.0),
                (xf + 120.0, sgn * hw * 0.58, z - 16.0),
                (xf + 52.0, sgn * hw * 0.22, z - 27.0)]
        path.extend(side if sgn < 0 else [apex] + list(reversed(side)))
    # The hoop is a teardrop in section too, deeper than it is wide, for the
    # same reason as the pillar: it has to pass a 125 kN load and be as small
    # as possible in the driver's sightline.
    out["halo"] = shapes.swept_profile(
        path, shapes.teardrop_section(r * 1.9, r * 2.6, 24), subdiv=3)

    # the pillar: it carries the load straight down into the tub's front
    # bulkhead, and it is the only thing in a driver's forward view, which is
    # why it is as slender as it is allowed to be
    # It is the only thing in the driver's forward view, so it is as narrow
    # in plan as it is allowed to be and deep fore-and-aft to make up the
    # section -- a teardrop, not a round tube, which would both block more of
    # the view and shed a wake straight into the airbox.
    out["halo_pillar"] = shapes.swept_profile(
        [apex, (apex[0] - 6.0, 0.0, z - 140.0),
         (apex[0] - 18.0, 0.0, z - 338.0)],
        shapes.teardrop_section(r * 1.35, r * 3.4, 28),
        scale=[(1.0, 1.0), (1.05, 1.10), (1.18, 1.30)], subdiv=6)

    mounts = []
    for sgn in (-1, 1):
        mounts.append(shapes.rounded_box(xr, sgn * hw * 0.62, z - 310.0,
                                         70.0, 58.0, 60.0, 10.0))
    mounts.append(shapes.rounded_box(apex[0] - 18.0, 0.0, z - 320.0,
                                     58.0, 70.0, 56.0, 10.0))
    out["halo_mounts"] = mesh.join(*mounts)
    return out


def _cockpit():
    out = {}
    sx = (T["cockpit_x0"] + T["cockpit_x1"]) / 2
    out["seat"] = _seat(sx + 110.0)
    out["steering"] = _wheel(T["cockpit_x0"] + 140.0, 570.0)
    # headrest / roll structure padding
    out["headrest"] = shapes.rounded_box(T["cockpit_x1"] - 40.0, 0.0, 620.0, 220.0, 300.0, 130.0)
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


def _seat_floor(cx, x):
    """Underside of the seat's bucket at station x: it rises 40 mm aft."""
    f = (x - (cx - 320.0)) / 640.0
    return 300.0 - 96.0 + 40.0 * (1.0 - math.cos(math.pi * f)) / 2


def _seat(cx):
    """The seat is moulded to the driver, which is the whole point of it.

    It was a 640 x 360 x 290 rounded box. A real seat is a carbon shell with
    a deep bucket, bolsters up each side that stop the driver moving under
    4 g of cornering, a raised lip at the back, slots the harness passes
    through, and lifting handles -- it comes out of the car with the driver
    in it.
    """
    parts = []
    rings = []
    n = 13
    for i in range(n):
        f = i / (n - 1)
        x = cx - 320.0 + 640.0 * f
        # the bucket deepens towards the back of the seat and the bolsters
        # rise with it
        hw = 150.0 + 60.0 * math.sin(math.pi * min(1.0, f * 1.15))
        floor_z = _seat_floor(cx, x)
        bol = 60.0 + 130.0 * f ** 1.4
        sect = [(-hw, floor_z), (hw, floor_z),
                (hw + 22.0, floor_z + bol * 0.55),
                (hw + 14.0, floor_z + bol),
                (hw - 10.0, floor_z + bol - 6.0),
                (hw - 10.0, floor_z + 26.0),
                (-hw + 10.0, floor_z + 26.0),
                (-hw + 10.0, floor_z + bol - 6.0),
                (-hw - 14.0, floor_z + bol),
                (-hw - 22.0, floor_z + bol * 0.55)]
        loop = shapes.rounded_polygon(sect, 16.0, seg=4)
        rings.append([(x, py, pz) for (py, pz) in loop])
    parts.append(shapes._loft_closed(rings))
    # harness slots: the shoulder belts come through the back of the shell
    for sgn in (-1.0, 1.0):
        parts.append(shapes.rounded_box(cx + 296.0, sgn * 92.0, 470.0,
                                        30.0, 76.0, 26.0, 8.0, seg=5))
    # The seat base: two cross-car pedestals it sits on, bonded to the tub
    # floor. The bucket is 130-180 mm above the floor -- the loom and the
    # extinguisher run under it -- and nothing held it there: its only
    # contact with the tub was the tips of its lifting handles brushing the
    # side walls. The pedestals stand inside y +/-60, clear of the loom's
    # lane at y 120, and each corner comes down to the floor where the floor
    # is, since it falls away aft and dishes towards the centreline.
    for (xa, xb), floor in (((1460.0, 1520.0), (76.4, 76.4, 73.6, 73.6)),
                            ((1830.0, 1890.0), (60.1, 60.1, 57.7, 57.7))):
        top = [_seat_floor(cx, x) + 4.0 for x in (xa, xb)]
        # corners in mesh.box's order, so its face winding holds
        v = [(xa, -60.0, floor[0]), (xb, -60.0, floor[2]),
             (xb, 60.0, floor[3]), (xa, 60.0, floor[1]),
             (xa, -60.0, top[0]), (xb, -60.0, top[1]),
             (xb, 60.0, top[1]), (xa, 60.0, top[0])]
        parts.append((v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                          (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]))
    # lifting handles, because the seat leaves the car with the driver in it.
    # They loop up, not out: out to y 245 they were 5 mm into the side
    # impact tubes, which pass the bolsters 20 mm outboard.
    for sgn in (-1.0, 1.0):
        parts.append(mesh.pipe(
            [(cx + 120.0, sgn * 210.0, 400.0),
             (cx + 160.0, sgn * 216.0, 452.0),
             (cx + 200.0, sgn * 210.0, 400.0)], 11.0, 16, subdiv=3))
    return mesh.join(*parts)


def _wheel(x, z):
    """A steering wheel, which on this car is a control surface.

    It was a plain annulus. The rim is flattened top and bottom so it clears
    the driver's legs and the halo pillar, the spine carries the display, and
    everything the driver changes mid-corner -- clutch bite, differential,
    brake bias, shift -- is on it.
    """
    parts = []
    rim = []
    n = 64
    for i in range(n):
        a = 2 * math.pi * i / n
        # a superellipse, squashed vertically: the "wheel" is not a circle
        e = 2.0 / 3.2
        ry = 112.0 * math.copysign(abs(math.cos(a)) ** e, math.cos(a))
        rz = 84.0 * math.copysign(abs(math.sin(a)) ** e, math.sin(a))
        rim.append((ry, rz))
    rings = []
    for k in range(14):
        b = 2 * math.pi * k / 14
        cb, sb = math.cos(b), math.sin(b)
        ring = []
        for (ry, rz) in rim:
            d = math.hypot(ry, rz) or 1.0
            ring.append((x + 17.0 * sb,
                         ry + ry / d * 17.0 * cb,
                         z + rz + rz / d * 17.0 * cb))
        rings.append(ring)
    # sweep the section round the rim: rings are indexed the other way here
    tube = [[rings[k][i] for k in range(14)] for i in range(n)]
    parts.append(shapes._loft_ring_pairs(tube, closed=True))
    # spine and display
    parts.append(shapes.rounded_box(x, 0.0, z + 6.0, 26.0, 190.0, 120.0,
                                    14.0, seg=6))
    parts.append(shapes.rounded_box(x - 15.0, 0.0, z + 18.0, 8.0, 132.0,
                                    74.0, 5.0, seg=5))
    # rotaries and buttons
    for (dy, dz, rr) in ((-72.0, -34.0, 17.0), (72.0, -34.0, 17.0),
                         (-58.0, 46.0, 13.0), (58.0, 46.0, 13.0)):
        kv, kf = mesh.revolve_closed(
            [(0.0, 0.0), (16.0, 0.0), (16.0, rr * 0.78), (12.0, rr),
             (0.0, rr)], 16)
        parts.append(([(x - px - 13.0, py + dy, pz + z + dz)
                       for (px, py, pz) in kv], kf))
    for i in range(8):
        dy = -84.0 + 24.0 * i
        parts.append(shapes.rounded_box(x - 16.0, dy, z - 8.0, 5.0, 15.0,
                                        15.0, 3.0, seg=4))
    # shift and clutch paddles, behind
    for sgn in (-1.0, 1.0):
        parts.append(shapes.rounded_box(x + 34.0, sgn * 86.0, z - 4.0,
                                        9.0, 44.0, 120.0, 8.0, seg=5))
        parts.append(shapes.rounded_box(x + 52.0, sgn * 60.0, z - 40.0,
                                        9.0, 38.0, 76.0, 8.0, seg=5))
    return mesh.join(*parts)
