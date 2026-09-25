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
    # the sidepods are opened under the upper bulges, where the charge pipes
    # come down through their tops to the throttles
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        out[f"cut:sidepod_{side}"] = mesh.join(out[f"cut:sidepod_{side}"],
                                               _bulge_hollow(sgn))
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


SEG_BODY = 144          # enough points round a section to carry the bulges

# The body's skin. It was a solid from nose to tail, so the seat, the driver,
# the engine and everything else in the car were inside a block of carbon,
# and every one of them "touched" the body whether or not anything held it.
SKIN = 6.0


def body_stations():
    """The stations the body is lofted through: the table's, and more
    through the bulges, so their ends are round."""
    B = BULGES[0]
    return sorted(set(_stations(spec.BODY, 68))
                  | {B["x0"] + (B["x1"] - B["x0"]) * i / 28 for i in range(29)})


def body_ring(x, inset=0.0):
    """The body's section at x as meshed: the table's, with the bulges."""
    return _bulged(body_section(x, inset=inset, segments=SEG_BODY), x, inset)


def _body():
    xs = body_stations()
    rings = [body_ring(x) for x in xs]
    # the space inside the skin, over the length where there is room for one
    inner = [body_ring(x, SKIN) for x in xs[2:-2]]
    # and the cockpit opening through the top of it, under the coaming's lip
    rim = cockpit_outline()
    opening = []
    for (x, w, z) in rim:
        w = max(w - 9.0, 1.0)
        opening.append([(x, -w, z - 90.0), (x, w, z - 90.0),
                        (x, w, z + 160.0), (x, -w, z + 160.0)])
    return {"tub": common.loft(rings),
            "cut:tub": mesh.join(common.loft(inner), common.loft(opening))}


# --------------------------------------------------------------------------
# bulges in the engine cover
#
# Each turbo's charge pipe leaves the vee over its bank's cam cover and comes
# down outboard of it to the throttle on the plenum's outboard face; that
# loop stands 100 mm outside the cover and above the sidepod. Low down, the
# engine's oil cooler stands 30 mm outside the flank. The car was shaped
# round an engine without either -- its ancillaries were never vendored --
# so the cover now bulges over both, both sides, as a twin-turbo car's does.
#
# A bulge is part of the body's own skin, not a separate shell: each body
# section is the union of the section and the bulges at its station, found
# along rays from the section's centre, so the skin is one surface with no
# wall of its own inside the engine bay.

BULGES = [
    # x0, x1, |y| centre, half-width, z centre, half-height, exponent, taper
    {"x0": 2990.0, "x1": 3490.0, "yc": 300.0, "hy": 105.0,
     "zc": 515.0, "hz": 140.0, "n": 3.0, "taper": 0.35},     # charge pipes
    # the oil cooler, and forward of it the water pump's return stub
    {"x0": 2950.0, "x1": 3430.0, "yc": 250.0, "hy": 64.0,
     "zc": 235.0, "hz": 74.0, "n": 2.6, "taper": 0.3},
]


def _bulge_half(Bg, x, inset):
    t = (x - Bg["x0"]) / (Bg["x1"] - Bg["x0"])
    if not 0.0 < t < 1.0:
        return None
    f = math.sin(math.pi * t) ** Bg["taper"]
    return Bg["hy"] * f - inset, Bg["hz"] * f - inset


def bulge_contains(x, y, z, slack=0.0, inset=0.0):
    for Bg in BULGES:
        h = _bulge_half(Bg, x, inset - slack)
        if h is None or h[0] <= 0 or h[1] <= 0:
            continue
        u = abs(abs(y) - Bg["yc"]) / h[0]
        v = abs(z - Bg["zc"]) / h[1]
        if u ** Bg["n"] + v ** Bg["n"] <= 1.0:
            return True
    return False


def _bulged(ring, x, inset):
    """A body section with the bulges at its station joined to it."""
    if not any(_bulge_half(Bg, x, inset) for Bg in BULGES):
        return ring
    zc = sum(p[2] for p in ring) / len(ring)
    out = []
    for (px, py, pz) in ring:
        dy, dz = py, pz - zc
        r0 = math.hypot(dy, dz)
        if r0 < 1e-6:
            out.append((px, py, pz))
            continue
        uy, uz = dy / r0, dz / r0
        # march out along the ray while inside a bulge
        r = r0
        step = 4.0
        while bulge_contains(x, uy * (r + step), zc + uz * (r + step), inset=inset):
            r += step
            if r > r0 + 400.0:
                break
        if r > r0:
            # refine the edge
            lo, hi = r, r + step
            for _ in range(8):
                mid = 0.5 * (lo + hi)
                if bulge_contains(x, uy * mid, zc + uz * mid, inset=inset):
                    lo = mid
                else:
                    hi = mid
            r = lo
        out.append((px, uy * r, zc + uz * r))
    return out


def _bulge_hollow(sgn):
    """The inside of the upper bulge, as a solid, on one side."""
    Bg = BULGES[0]
    xs = [Bg["x0"] + (Bg["x1"] - Bg["x0"]) * i / 24 for i in range(2, 23)]
    rings = []
    for x in xs:
        hy, hz = _bulge_half(Bg, x, SKIN)
        p = 2.0 / Bg["n"]
        rings.append([(x, sgn * (Bg["yc"] + hy * math.copysign(abs(math.cos(a)) ** p, math.cos(a))),
                       Bg["zc"] + hz * math.copysign(abs(math.sin(a)) ** p, math.sin(a)))
                      for a in (2.0 * math.pi * i / 40 for i in range(40))])
    return common.loft(rings)


def _sidepod_section(x, segments=40, inset=0.0):
    """Sidepod section: rounded outboard, flat inboard against the body, and
    an undercut lower surface that climbs aft to feed the tunnel."""
    y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, x)
    y_in, y_out = y_in + inset, max(y_out - inset, y_in + inset + 1.0)
    z_bot, z_top = z_bot + inset, max(z_top - inset, z_bot + inset + 1.0)
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


def sidepod_floor(x, y, roof=False):
    """Height of the inside of the sidepod's floor skin at (x, |y|), or of
    its roof."""
    ring = _sidepod_section(x, segments=160, inset=SKIN)
    zc = sum(q[2] for q in ring) / len(ring)
    side = [p for p in ring if (p[2] > zc) == roof]
    return min(side, key=lambda p: abs(p[1] - abs(y)))[2]


def _sidepods():
    out = {}
    xs = _stations(spec.SIDEPOD_TABLE, 30)
    for side, sgn in (("l", -1.0), ("r", 1.0)):
        rings = []
        for x in xs:
            r = _sidepod_section(x)
            rings.append([(px, sgn * py, pz) for (px, py, pz) in r])
        out[f"sidepod_{side}"] = common.loft(rings)
        # A sidepod is a duct: air in at the mouth, through the radiator,
        # out of the louvres. It was a solid with the radiator buried in it.
        # The bore runs out through the front face, which is the mouth.
        inner = []
        for x in [xs[0] - 10.0] + xs[1:-2]:
            r = _sidepod_section(max(x, xs[0]), inset=SKIN)
            inner.append([(x, sgn * py, pz) for (_px, py, pz) in r])
        out[f"cut:sidepod_{side}"] = common.loft(inner)

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


def cockpit_outline(n=18):
    """Half-width and rim height of the cockpit opening at n stations.

    The opening closes just short of x1; at f * 1.1 it closed 50 mm sooner,
    on the back of the driver's helmet. Past the closing station the list
    stops -- the lip used to carry on down the centreline as a tail.
    """
    x0, x1 = T["cockpit_x0"], T["cockpit_x1"]
    out = []
    for i in range(n):
        f = i / (n - 1)
        x = x0 + (x1 - x0) * f
        hw, z_bot, z_top, ex, bias = _sample(spec.BODY, x)
        w = (min(T["cockpit_half_w"], hw * 0.80)
             * math.sin(math.pi * min(f * 1.04, 1.0)) ** 0.35)
        out.append((x, w, z_top - 22.0))
        if f > 0.5 and w == 0.0:
            break
    return out


def _cockpit_surround():
    """Cockpit opening coaming, sunk into the body top."""
    rim = cockpit_outline()
    parts = [mesh.pipe(mesh.smooth_path([(x, sgn * w, z) for (x, w, z) in rim],
                                        4), 15.0, 16)
             for sgn in (-1.0, 1.0)]
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
        # rooted 10 mm into the cover, so it is bonded to the cover's faceted
        # mesh along its whole length and not to the smooth line it is lofted
        # from; the cover now stands well clear of the gearbox under it
        z_base = z_top - 10.0
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
    #
    # Through a spline, not straight between the thirteen waypoints: swept
    # straight it came out as a polygon, a hoop with visible corners.
    out["halo"] = shapes.swept_profile(
        mesh.smooth_path(path, 10), shapes.teardrop_section(r * 1.9, r * 2.6, 24))

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
    out["headrest"] = _headrest()
    return out


def _headrest():
    """The energy-absorbing pads round the helmet, in the cockpit opening.

    A single-seater's headrest is a U of foam: a pad each side of the helmet
    and one behind it, filling the opening up to the rim so the head has
    something to hit in every direction but forward. It was a box 220 mm
    long centred behind the cockpit, which put its front face 66 mm inside
    the back of the driver's head; moved behind the helmet, the same box was
    52 mm into his shoulders. The pads stand above the shoulders and inside
    the rim, and each station's width is the opening's own.
    """
    D = spec.BODY_DETAIL["driver"]
    hx, R = D["helmet_x"], D["helmet_r"]
    rim = cockpit_outline(40)
    z0 = D["shoulder_z"] + 108.0        # above the shoulders and the HANS

    def at(x):
        for (xa, wa, za), (xb, wb, zb) in zip(rim, rim[1:]):
            if xa <= x <= xb:
                f = (x - xa) / (xb - xa)
                return wa + (wb - wa) * f, za + (zb - za) * f
        return rim[-1][1], rim[-1][2]

    def loft(stations, section):
        rings = []
        for x in stations:
            w, z_rim = at(x)
            loop = shapes.rounded_polygon(section(w, z_rim - 18.0), 8.0,
                                          seg=3)
            rings.append([(x, py, pz) for (py, pz) in loop])
        return shapes._loft_closed(rings)

    parts = []
    y_in = R + 6.0                      # clear of the helmet's side
    for sgn in (-1.0, 1.0):
        def side(w, top, sgn=sgn):
            y_out = max(y_in + 24.0, w - 8.0)
            pts = [(y_in, z0), (y_out, z0), (y_out, top), (y_in, top)]
            return [(sgn * py, pz) for (py, pz) in pts][::int(sgn)]
        parts.append(loft([hx - 90.0 + 30.0 * k for k in range(9)], side))

    def back(w, top):
        y = max(y_in + 24.0, w - 8.0)
        return [(-y, z0), (y, z0), (y, top), (-y, top)]
    helmet_back = hx + R * 1.04
    parts.append(loft([helmet_back + 4.0 + 12.0 * k for k in range(5)], back))
    return mesh.join(*parts)


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


def _meshed_point(xs, section, segs, centre, x, angle_deg, standoff):
    """The point at (x, angle) on a skin lofted through `section(x)` rings at
    stations `xs`, AS MESHED -- flat between stations and between segments --
    and `standoff` mm out along its normal."""
    i = 0
    while i < len(xs) - 2 and xs[i + 1] < x:
        i += 1
    tx = (x - xs[i]) / ((xs[i + 1] - xs[i]) or 1.0)
    a = math.radians(angle_deg) % (2 * math.pi)
    f = a / (2 * math.pi) * segs
    j = int(f) % segs
    ta = f - int(f)
    r0, r1 = section(xs[i]), section(xs[i + 1])
    j2 = (j + 1) % segs

    def lerp(p, q, t):
        return tuple(p[k] + (q[k] - p[k]) * t for k in range(3))
    a0 = lerp(r0[j], r0[j2], ta)
    a1 = lerp(r1[j], r1[j2], ta)
    p = lerp(a0, a1, tx)
    du = tuple(lerp(r0[j2], r1[j2], tx)[k] - lerp(r0[j], r1[j], tx)[k]
               for k in range(3))
    dx = tuple(a1[k] - a0[k] for k in range(3))
    n = (dx[1] * du[2] - dx[2] * du[1], dx[2] * du[0] - dx[0] * du[2],
         dx[0] * du[1] - dx[1] * du[0])
    m = math.sqrt(sum(c * c for c in n)) or 1.0
    n = tuple(c / m for c in n)
    cy, cz = centre(x)
    if n[1] * (p[1] - cy) + n[2] * (p[2] - cz) < 0.0:
        n = tuple(-c for c in n)
    return tuple(p[k] + n[k] * standoff for k in range(3))


def skin_point(x, angle_deg, standoff=0.0):
    """A point on the body skin AS MESHED, and `standoff` mm out along its
    normal.

    `surface_point` follows the smooth spline through the station table, but
    the skin is lofted through 68 stations of 52 segments each and is flat
    between them -- up to 10 mm inside the spline where the spine climbs over
    the exhaust. A panel laid on the spline there sank into the skin.
    """
    def centre(x):
        hw, z_bot, z_top, nn, bias = _sample(spec.BODY, x)
        return 0.0, (z_bot + z_top) / 2 + bias * (z_top - z_bot) * 0.5
    return _meshed_point(body_stations(), lambda xx: body_ring(xx), SEG_BODY,
                         centre, x, angle_deg, standoff)


def sidepod_skin_point(x, sgn, angle_deg, standoff=0.0):
    """The same for a sidepod's outer skin: angle 0 is its outboard face,
    90 its top."""
    def centre(x):
        y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, x)
        return (y_in + y_out) / 2, (z_bot + z_top) / 2
    p = _meshed_point(_stations(spec.SIDEPOD_TABLE, 30),
                      lambda x: _sidepod_section(x), 40, centre,
                      x, angle_deg, standoff)
    return (p[0], sgn * p[1], p[2])


def sidepod_point(x, f_y, f_z, standoff=0.0):
    """A point on a sidepod flank: f_y 0 inboard to 1 outboard, f_z 0 low to
    1 high, on the side the caller signs f_y with."""
    y_in, y_out, z_bot, z_top, n = _sample(spec.SIDEPOD_TABLE, abs(x))
    sgn = 1.0 if f_y >= 0 else -1.0
    y = y_in + (y_out - y_in) * abs(f_y)
    z = z_bot + (z_top - z_bot) * f_z
    return (x, sgn * (y + standoff * abs(f_y)), z)


# The seat's inside surface along the centreline, (x, z): a pan under the
# thighs and hips, then a back that climbs with the driver's reclined spine
# up to his shoulder blades. It was a flat pan rising 40 mm, which suited a
# driver sitting up -- and one whose hips were where his shoulders are.
SEAT_LINE = ((1370.0, 204.0), (1500.0, 204.0), (1590.0, 240.0),
             (1700.0, 300.0), (1855.0, 380.0), (1950.0, 430.0))
SEAT_X0, SEAT_X1 = SEAT_LINE[0][0], SEAT_LINE[-1][0]


def _seat_floor(cx, x):
    """Underside of the seat's shell at station x."""
    pts = SEAT_LINE
    x = min(max(x, pts[0][0]), pts[-1][0])
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x <= x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0) - 26.0
    return pts[-1][1] - 26.0


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
        x = SEAT_X0 + (SEAT_X1 - SEAT_X0) * f
        # the bolsters stand highest alongside the hips and ribs, where the
        # cornering load goes in, and come down at the shoulders so the arms
        # can reach forward over them
        hw = 170.0 + 26.0 * math.sin(math.pi * f)
        floor_z = _seat_floor(cx, x)
        bol = 60.0 + 130.0 * math.sin(math.pi * f) ** 1.2
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
        parts.append(shapes.rounded_box(1920.0, sgn * 92.0,
                                        _seat_floor(cx, 1920.0) + 14.0,
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
            [(1560.0, sgn * 214.0, 440.0),
             (1600.0, sgn * 218.0, 486.0),
             (1640.0, sgn * 214.0, 450.0)], 11.0, 16, subdiv=3))
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
