"""Wheels, tyres, brake discs, calipers and uprights.

A wheel is the most repeated object on the car and the one a viewer looks at
longest, so it is built as real hardware: a rim with a drop centre and spokes,
a ventilated carbon disc, a six-pot caliper with its pistons showing, and an
upright with the pickup points the wishbones actually land on.

Everything here works in the wheel's own frame -- axis along y, radius in the
x-z plane -- and `_place` moves it to the corner.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

W = spec.WHEEL
S = spec.SUSP
SEG = spec.RES["revolve"]


def corners():
    """(tag, x, y, width, outer diameter) for each of the four corners."""
    out = []
    for (tag, x, track, w, od) in (
            ("fl", spec.FRONT_AXLE_X, spec.TRACK_FRONT,
             W["front_w"], W["front_od"]),
            ("fr", spec.FRONT_AXLE_X, spec.TRACK_FRONT,
             W["front_w"], W["front_od"]),
            ("rl", spec.REAR_AXLE_X, spec.TRACK_REAR,
             W["rear_w"], W["rear_od"]),
            ("rr", spec.REAR_AXLE_X, spec.TRACK_REAR,
             W["rear_w"], W["rear_od"])):
        sgn = -1.0 if tag.endswith("l") else 1.0
        out.append((tag, x, sgn * track / 2, w, od))
    return out


def pivots():
    """Everything that turns with a wheel turns about that wheel's own axis."""
    out = {}
    for (tag, x, y, w, od) in corners():
        hub = (x, y, od / 2)
        for stem in ("tyre", "rim", "wheelcover", "disc", "wheelnut"):
            out[f"{stem}_{tag}"] = (hub, (0.0, 1.0, 0.0), 1.0, "spin")
    return out


def build():
    out = {}
    for (tag, x, y, w, od) in corners():
        z = od / 2
        out[f"tyre_{tag}"] = _tyre(x, y, z, w, od)
        out[f"rim_{tag}"] = _rim(x, y, z, w)
        out[f"wheelcover_{tag}"] = _cover(x, y, z, w)
        out[f"disc_{tag}"] = _disc(x, y, z, w)
        out[f"caliper_{tag}"] = _caliper(x, y, z, w)
        out[f"upright_{tag}"] = _upright(x, y, z, w)
        out[f"wheelnut_{tag}"] = _nut(x, y, z, w)
    return out


# --------------------------------------------------------------------------
# Frame helpers. The wheel spins about y; `a` is measured in the x-z plane.
# --------------------------------------------------------------------------

def _place(verts, x, y, z):
    return [(px + x, py + y, pz + z) for (px, py, pz) in verts]


def _lathe(x, y, z, profile, closed=True, segments=SEG):
    """Revolve an (across, radius) profile about the wheel's own +y axis."""
    v, f = (mesh.revolve_closed(list(profile), segments) if closed
            else mesh.revolve_open(list(profile), segments,
                                   cap_start=True, cap_end=True))
    return _place([(pz, px, py) for (px, py, pz) in v], x, y, z), f


def _sgn(y):
    return 1.0 if y > 0 else -1.0


# --------------------------------------------------------------------------

def _tyre(x, y, z, w, od):
    """Slick carcass: bead seat, sidewall bulge, shoulder radius, crown.

    A slick has no tread pattern, but it is not a cylinder either -- the
    shoulder radius is what puts the contact patch where it is under camber.
    """
    hw = w / 2
    sh = hw * W["shoulder_frac"]
    bead = W["bead_r"]
    bulge = bead + W["bulge"]
    crown = od / 2
    prof = [
        (-hw * 0.96, bead),
        (-hw * 0.99, bulge),
        (-hw * 0.94, crown - 26.0),
        (-sh, crown - 5.0),
        (-sh * 0.5, crown),
        (sh * 0.5, crown),
        (sh, crown - 5.0),
        (hw * 0.94, crown - 26.0),
        (hw * 0.99, bulge),
        (hw * 0.96, bead),
        (hw * 0.90, bead - 3.0),
        (-hw * 0.90, bead - 3.0),
    ]
    tyre = _lathe(x, y, z, prof)
    # raised sidewall lettering band on the outboard face only
    s = _sgn(y)
    r0, h = W["lettering_r"], W["lettering_h"]
    band = _lathe(x, y, z, [
        (s * hw * 0.955, r0 - 22.0), (s * (hw * 0.955 + h), r0 - 20.0),
        (s * (hw * 0.955 + h), r0 + 20.0), (s * hw * 0.955, r0 + 22.0)])
    return mesh.join(tyre, band)


def _rim(x, y, z, w):
    """Barrel with a drop centre, an outer flange and `spokes` spokes."""
    hw = w / 2
    parts = []
    barrel = _lathe(x, y, z, [
        (-hw * 0.96, W["bead_r"]), (-hw * 0.96, W["flange_r"]),
        (-hw * 0.90, W["flange_r"]), (-hw * 0.90, W["bead_r"]),
        (-hw * 0.55, W["drop_r"]), (hw * 0.30, W["drop_r"]),
        (hw * 0.90, W["bead_r"]), (hw * 0.90, W["flange_r"]),
        (hw * 0.96, W["flange_r"]), (hw * 0.96, W["bead_r"]),
        (hw * 0.94, W["bead_r"] - 10.0), (-hw * 0.94, W["bead_r"] - 10.0),
    ])
    parts.append(barrel)

    s = _sgn(y)
    face_y = s * hw * 0.52                # spoke face, set in from the flange
    hub = _lathe(x, y, z, [
        (face_y - s * 30.0, 0.0), (face_y - s * 30.0, W["hub_r"]),
        (face_y + s * 16.0, W["hub_r"]), (face_y + s * 16.0, 0.0)])
    parts.append(hub)

    for k in range(W["spokes"]):
        a = 2 * math.pi * k / W["spokes"]
        parts.append(_spoke(x, y, z, a, face_y, s))
    return mesh.join(*parts)


def _spoke(x, y, z, a, face_y, s):
    """One tapered spoke blade, twisted so it also acts as a fan."""
    r0, r1 = W["spoke_root_r"], W["drop_r"] - 2.0
    w0, w1 = W["spoke_w_root"] / 2, W["spoke_w_tip"] / 2
    t = W["spoke_t"] / 2
    rings = []
    n = 5
    for i in range(n):
        f = i / (n - 1)
        r = r0 + (r1 - r0) * f
        hw_ = w0 + (w1 - w0) * f
        # the blade twists with radius, so it pumps air out of the brake duct
        tw = math.radians(18.0 * f * s)
        yy = face_y - s * 6.0 * f
        ring = []
        for (du, dv) in ((-hw_, -t), (hw_, -t), (hw_, t), (-hw_, t)):
            ct, st = math.cos(tw), math.sin(tw)
            u, v = du * ct - dv * st, du * st + dv * ct
            # u runs around the rim at radius r, v along the axis
            ang = a + u / max(r, 1.0)
            ring.append((r * math.cos(ang), yy + v, r * math.sin(ang)))
        rings.append(ring)
    verts = [p for ring in rings for p in ring]
    faces = []
    for i in range(n - 1):
        a0, b0 = i * 4, (i + 1) * 4
        for j in range(4):
            j2 = (j + 1) % 4
            faces.append((a0 + j, a0 + j2, b0 + j2, b0 + j))
    faces.append((3, 2, 1, 0))
    base = (n - 1) * 4
    faces.append((base, base + 1, base + 2, base + 3))
    return _place([(px, py, pz) for (px, py, pz) in verts], x, y, z), faces


def _cover(x, y, z, w):
    """The outboard wheel cover. It stops the rim pumping air into the wake,
    which is most of what makes a modern open wheel less dirty than it was."""
    s = _sgn(y)
    hw = w / 2
    y0 = s * hw * 0.93
    dish = W["cover_dish"]
    parts = [_lathe(x, y, z, [
        (y0, W["cover_r"]), (y0, W["cover_r"] - 12.0),
        (y0 - s * dish * 0.5, W["cover_r"] * 0.62),
        (y0 - s * dish, W["nut_r"] + 12.0),
        (y0 - s * (dish - 8.0), W["nut_r"] + 12.0),
        (y0 - s * (dish - 8.0) + s * dish * 0.5, W["cover_r"] * 0.62),
        (y0 - s * 8.0, W["cover_r"] - 12.0), (y0 - s * 8.0, W["cover_r"]),
    ])]
    # radial vanes across the dish, so it reads as a wheel cover and not a lid
    for k in range(W["cover_vanes"]):
        a = 2 * math.pi * k / W["cover_vanes"]
        r0, r1 = W["nut_r"] + 18.0, W["cover_r"] - 16.0
        v, f = mesh.box(0.0, 0.0, 0.0, (r1 - r0), 9.0, 6.0)
        rm = (r0 + r1) / 2
        ca, sa = math.cos(a), math.sin(a)
        v = [(rm * ca + px * ca - pz * sa, y0 - s * dish * 0.55 + py,
              rm * sa + px * sa + pz * ca) for (px, py, pz) in v]
        parts.append((_place(v, x, y, z), f))
    return mesh.join(*parts)


def _disc(x, y, z, w):
    """Ventilated carbon disc: two friction faces with radial vanes between.

    A solid annulus would be half the mass and none of the cooling; the vanes
    are what the air flows through, and they are visible through the spokes.
    """
    s = _sgn(y)
    ht = W["disc_t"] / 2
    ft = W["disc_face_t"]
    r_in, r_out = 92.0, W["disc_r"]
    y0 = -s * w * 0.02
    parts = [
        _lathe(x, y, z, [(y0 - ht, r_in), (y0 - ht, r_out),
                         (y0 - ht + ft, r_out), (y0 - ht + ft, r_in)]),
        _lathe(x, y, z, [(y0 + ht - ft, r_in), (y0 + ht - ft, r_out),
                         (y0 + ht, r_out), (y0 + ht, r_in)]),
        # bell, bolting the disc to the hub
        _lathe(x, y, z, [(y0 - ht, r_in - 26.0), (y0 - ht, r_in),
                         (y0 + ht, r_in), (y0 + ht, r_in - 26.0)]),
    ]
    for k in range(W["disc_vanes"]):
        a = 2 * math.pi * k / W["disc_vanes"]
        rm = (r_in + r_out) / 2
        v, f = mesh.box(0.0, 0.0, 0.0, r_out - r_in - 8.0,
                        W["disc_t"] - 2 * ft, 7.0)
        ca, sa = math.cos(a), math.sin(a)
        v = [(rm * ca + px * ca - pz * sa, y0 + py,
              rm * sa + px * sa + pz * ca) for (px, py, pz) in v]
        parts.append((_place(v, x, y, z), f))
    return mesh.join(*parts)


def _caliper(x, y, z, w):
    """Six-pot caliper, wrapped round the top of the disc with its pistons and
    pads showing on both sides."""
    s = _sgn(y)
    n = W["caliper_pistons"]
    arc = math.radians(W["caliper_arc"])
    r = W["caliper_r"]
    y0 = -s * w * 0.02
    parts = []
    half = W["disc_t"] / 2 + W["pad_t"] + 22.0
    # body: a curved shoe either side of the disc, bridged over the top
    for side in (-1.0, 1.0):
        for k in range(7):
            f = k / 6
            a = math.pi / 2 - arc / 2 + arc * f
            v, fc = mesh.box(0.0, 0.0, 0.0, 46.0, 40.0, 62.0)
            ca, sa = math.cos(a), math.sin(a)
            v = [((r - 16.0) * ca + px * sa + pz * ca,
                  y0 + side * (W["disc_t"] / 2 + 22.0) + py,
                  (r - 16.0) * sa - px * ca + pz * sa)
                 for (px, py, pz) in v]
            parts.append((_place(v, x, y, z), fc))
    bv, bf = mesh.box(0.0, y0, r + 26.0, 150.0, 2 * half, 34.0)
    parts.append((_place(bv, x, y, z), bf))
    # pistons, pressing the pads onto the disc
    for side in (-1.0, 1.0):
        for k in range(n // 2):
            f = (k + 0.5) / (n // 2)
            a = math.pi / 2 - arc / 2 + arc * f
            pv, pf = mesh.cylinder(0.0, 20.0, 21.0, 12)
            ca, sa = math.cos(a), math.sin(a)
            rr = r - 34.0
            pv = [(rr * ca + pz, y0 + side * (W["disc_t"] / 2 + 2.0)
                   + side * px, rr * sa + py) for (px, py, pz) in pv]
            parts.append((_place(pv, x, y, z), pf))
    # pads
    for side in (-1.0, 1.0):
        for k in range(5):
            f = k / 4
            a = math.pi / 2 - arc / 2 + arc * f
            v, fc = mesh.box(0.0, 0.0, 0.0, 42.0, W["pad_t"], 54.0)
            ca, sa = math.cos(a), math.sin(a)
            rr = r - 30.0
            v = [(rr * ca + px * sa + pz * ca,
                  y0 + side * (W["disc_t"] / 2 + W["pad_t"] / 2) + py,
                  rr * sa - px * ca + pz * sa) for (px, py, pz) in v]
            parts.append((_place(v, x, y, z), fc))
    return mesh.join(*parts)


def _upright(x, y, z, w):
    """Hub barrel plus the arms that reach out to the wishbone and pushrod
    pickups. A box here hides the whole point of a suspension."""
    s = _sgn(y)
    parts = []
    y0 = -s * w * 0.04
    parts.append(_lathe(x, y, z, [(y0 - s * 90.0, 30.0),
                                  (y0 - s * 90.0, 72.0),
                                  (y0 + s * 40.0, 86.0),
                                  (y0 + s * 40.0, 30.0)]))
    inboard = y - s * (w / 2 + 30.0)
    for zz in (S["upper_z"], S["lower_z"]):
        parts.append(mesh.pipe([(x, y + y0, z),
                                (x, (y + inboard) / 2, (z + zz) / 2),
                                (x, inboard, zz)], 34.0, 10))
    # steering / toe-link arm, trailing the axle
    parts.append(mesh.pipe([(x, y + y0, z), (x + 150.0, inboard, z - 40.0)],
                           26.0, 8))
    return mesh.join(*parts)


def _nut(x, y, z, w):
    """Centre-lock nut, in the middle of the wheel cover."""
    s = _sgn(y)
    y0 = s * (w / 2 * 0.93 - W["cover_dish"] + 4.0)
    v, f = mesh.revolve_closed([(y0, 0.0), (y0, W["nut_r"]),
                                (y0 - s * W["nut_h"], W["nut_r"] * 0.88),
                                (y0 - s * W["nut_h"], 0.0)], 6)
    return _place([(pz, px, py) for (px, py, pz) in v], x, y, z), f
