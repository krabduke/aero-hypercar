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
import shapes

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
        for stem in ("tyre", "rim", "wheelcover", "disc", "wheelnut",
                     "hub", "wheel_stud"):
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
        out[f"brake_pad_{tag}"] = _pads(x, y, z, w)
        out[f"upright_{tag}"] = _upright(x, y, z, w)
        out[f"hub_{tag}"] = _hub(x, y, z, w)
        out[f"wheel_stud_{tag}"] = _studs(x, y, z, w)
        out[f"wheelnut_{tag}"] = _nut(x, y, z, w)
        out[f"tether_{tag}"] = _tether(x, y, z, w, tag)
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


def ball_joints(x, y):
    """The upright's upper and lower ball joints: where the wishbones'
    outboard ends are, and so where the upright's arms have to reach.

    One definition, used by the wishbones and the upright. They had one
    each: the upright's arms went to the front axle's lower height on all
    four corners and to a different lateral station, so the rear uprights
    ended 90 mm below their lower wishbones, in the floor strake, carrying
    nothing."""
    front = abs(x - S["front_x"]) < abs(x - S["rear_x"])
    low = S["lower_z"] if front else S["lower_z_rear"]
    return (x, y * 0.77, S["upper_z"]), (x, y * 0.77, low)


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


BARREL_T = 5.0     # mm, the rim barrel's wall


def _rim(x, y, z, w):
    """Barrel with a drop centre, an outer flange and `spokes` spokes."""
    hw = w / 2
    parts = []
    # A shell BARREL_T thick under the tyre-side surface: flanges, bead
    # seats and the drop well. The inside used to be one straight line at
    # bead_r - 10, which the drop well dipped 20 mm below -- a profile that
    # crossed itself, with the well a separate lobe hanging under the rim.
    t = BARREL_T
    barrel = _lathe(x, y, z, [
        (-hw * 0.96, W["flange_r"]), (-hw * 0.90, W["flange_r"]),
        (-hw * 0.90, W["bead_r"]), (-hw * 0.55, W["drop_r"]),
        (hw * 0.30, W["drop_r"]), (hw * 0.90, W["bead_r"]),
        (hw * 0.90, W["flange_r"]), (hw * 0.96, W["flange_r"]),
        (hw * 0.96, W["bead_r"] - t), (hw * 0.90, W["bead_r"] - t),
        (hw * 0.30, W["drop_r"] - t), (-hw * 0.55, W["drop_r"] - t),
        (-hw * 0.90, W["bead_r"] - t), (-hw * 0.96, W["bead_r"] - t),
    ])
    parts.append(barrel)

    s = _sgn(y)
    face_y = s * hw * 0.52                # spoke face, set in from the flange
    hub = _lathe(x, y, z, [
        (face_y - s * 30.0, 0.0), (face_y - s * 30.0, W["hub_r"]),
        (face_y + s * 16.0, W["hub_r"]), (face_y + s * 16.0, 0.0)])
    parts.append(hub)

    # the spokes run from inside the hub to inside the barrel, which they
    # join; they started 12 mm off the hub and stopped 13 mm short of the
    # barrel, seven blades in the air per wheel
    f_face = abs(face_y) / hw
    r_barrel = (W["drop_r"] - t) + (W["bead_r"] - W["drop_r"]) * (
        (f_face - 0.30) / 0.60)
    for k in range(W["spokes"]):
        a = 2 * math.pi * k / W["spokes"]
        parts.append(_spoke(x, y, z, a, face_y, s,
                            r0=W["hub_r"] - 4.0, r1=r_barrel + 3.0))
    return mesh.join(*parts)


def _spoke(x, y, z, a, face_y, s, r0, r1):
    """One tapered spoke blade, twisted so it also acts as a fan."""
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
        (y0 - s * 30.0, W["cover_r"] - 12.0), (y0 - s * 30.0, W["cover_r"]),
    ])]
    # radial vanes across the dish, so it reads as a wheel cover and not a lid
    for k in range(W["cover_vanes"]):
        a = 2 * math.pi * k / W["cover_vanes"]
        r0, r1 = W["nut_r"] + 18.0, W["cover_r"] - 16.0
        v, f = shapes.rounded_box(0.0, 0.0, 0.0, (r1 - r0), 9.0, 6.0)
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
        v, f = shapes.rounded_box(0.0, 0.0, 0.0, r_out - r_in - 8.0,
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
            v, fc = shapes.rounded_box(0.0, 0.0, 0.0, 46.0, 40.0, 62.0)
            ca, sa = math.cos(a), math.sin(a)
            v = [((r - 16.0) * ca + px * sa + pz * ca,
                  y0 + side * (W["disc_t"] / 2 + 22.0) + py,
                  (r - 16.0) * sa - px * ca + pz * sa)
                 for (px, py, pz) in v]
            parts.append((_place(v, x, y, z), fc))
    bv, bf = shapes.rounded_box(0.0, y0, r + 26.0, 150.0, 2 * half, 34.0)
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
    # The pads themselves are their own part -- brake_pad_{tag} -- because
    # they are a serviceable friction lining that bolts into the caliper,
    # not a feature moulded into it.
    # The two mounting lugs.
    #
    # A caliper hangs off the upright and this one was bolted to nothing: it
    # sits at z 453-574 wrapped round the top of the disc, and the upright is
    # only 660-635 wide up there -- it does not reach out that far until
    # z 330, where it spans 858 to 728. So the lugs have to come down and
    # inboard to meet it, which is exactly what they do on a real corner.
    for dx in (-58.0, 58.0):
        parts.append(mesh.pipe(
            [(x + dx, y + s * (w * 0.02 + 6.0), z + r * 0.30),
             (x + dx, y * 0.93, z - 12.0),
             (x + dx, s * 800.0, z - 40.0)], 15.0, 12, subdiv=2))

    return mesh.join(*parts)


def _pads(x, y, z, w):
    """The friction pads, one each side of the disc.

    A pad is a serviceable part that slides into the caliper on its own
    backing plate -- it is not a feature moulded into the caliper body, which
    is why it is its own object. Each is a curved shoe spanning the caliper
    arc, with the backing plate, the lining, and the ears that locate it on
    the retaining pins.
    """
    s = _sgn(y)
    arc = math.radians(W["caliper_arc"])
    ri, ro = W["pad_r_in"], W["pad_r_out"]
    t = W["pad_t"]
    y0 = -s * w * 0.02
    parts = []
    for side in (-1.0, 1.0):
        yb = y0 + side * (W["disc_t"] / 2 + 1.5)
        # lining, then the steel backing plate behind it
        for (t0, t1, r0, r1) in ((0.0, t * 0.62, ri, ro),
                                 (t * 0.62, t, ri + 5.0, ro - 3.0)):
            ring = []
            for k in range(W["pad_seg"] * 4 + 1):
                a = math.pi / 2 - arc / 2 + arc * k / (W["pad_seg"] * 4)
                ring.append(a)
            verts, faces = [], []
            n = len(ring)
            for a in ring:
                ca, sa = math.cos(a), math.sin(a)
                for (rr, tt) in ((r0, t0), (r1, t0), (r1, t1), (r0, t1)):
                    verts.append((rr * ca, yb + side * tt, rr * sa))
            for i in range(n - 1):
                b0, b1 = i * 4, (i + 1) * 4
                for j in range(4):
                    j2 = (j + 1) % 4
                    faces.append((b0 + j, b0 + j2, b1 + j2, b1 + j))
            faces.append((3, 2, 1, 0))
            b = (n - 1) * 4
            faces.append((b, b + 1, b + 2, b + 3))
            parts.append((_place(verts, x, y, z), faces))
        # the two ears the retaining pin passes through
        for end in (-1.0, 1.0):
            a = math.pi / 2 + end * arc / 2
            ca, sa = math.cos(a), math.sin(a)
            ev, ef = mesh.cylinder(0.0, t * 0.9, 9.0, 10)
            ev = [(ro * ca + pz, yb + side * px, ro * sa + py)
                  for (px, py, pz) in ev]
            parts.append((_place(ev, x, y, z), ef))
    return mesh.join(*parts)


def _hub(x, y, z, w):
    """Wheel hub and bearing pack, inside the upright.

    The disc bell and the wheel both bolt to this; without it the wheel was
    carried by nothing and the upright was a shell with a hole in it.
    """
    s = _sgn(y)
    R = W["hub_r"]
    y0 = -s * w * 0.04
    parts = []
    # the barrel, with the flange the studs screw into at the outboard end
    parts.append(_lathe(x, y, z, [
        (y0 - s * 96.0, 26.0), (y0 - s * 96.0, R * 0.62),
        (y0 - s * 62.0, R * 0.62), (y0 - s * 62.0, R * 0.80),
        (y0 + s * 30.0, R * 0.80), (y0 + s * 30.0, R * 0.55),
        (y0 + s * 44.0, R * 0.55), (y0 + s * 44.0, R),
        (y0 + s * 58.0, R), (y0 + s * 58.0, 26.0),
    ]))
    # the two bearing races it runs on
    for off in (-64.0, 18.0):
        parts.append(_lathe(x, y, z, [
            (y0 + s * off, R * 0.80), (y0 + s * off, R * 0.98),
            (y0 + s * (off + 30.0), R * 0.98),
            (y0 + s * (off + 30.0), R * 0.80),
        ]))
    # the drive pegs that take torque from the driveshaft
    for k in range(6):
        a = 2 * math.pi * k / 6
        pv, pf = mesh.cylinder(0.0, 26.0, 11.0, 10)
        ca, sa = math.cos(a), math.sin(a)
        rr = R * 0.44
        pv = [(rr * ca + pz, y0 - s * 96.0 - s * px, rr * sa + py)
              for (px, py, pz) in pv]
        parts.append((_place(pv, x, y, z), pf))
    return mesh.join(*parts)


def _studs(x, y, z, w):
    """The stud pattern the wheel is torqued onto."""
    s = _sgn(y)
    R = W["hub_r"]
    y0 = -s * w * 0.04
    parts = []
    for k in range(W.get("stud_n", 6)):
        a = 2 * math.pi * k / W.get("stud_n", 6) + math.pi / 12
        ca, sa = math.cos(a), math.sin(a)
        rr = R * 0.78
        sv, sf = mesh.revolve_closed(
            [(0.0, 0.0), (46.0, 0.0), (46.0, W["stud_r"]),
             (10.0, W["stud_r"]), (10.0, W["stud_r"] * 1.9),
             (0.0, W["stud_r"] * 1.9)], 10)
        sv = [(rr * ca + pz, y0 + s * 44.0 + s * px, rr * sa + py)
              for (px, py, pz) in sv]
        parts.append((_place(sv, x, y, z), sf))
    return mesh.join(*parts)


def _tether(x, y, z, w, tag):
    """The wheel tether: a braided strap from the upright into the tub.

    Mandated so a wheel cannot leave the car in an accident, and absent from
    every corner. Two per corner in the regulations; two here, anchored apart
    so they do not share a load path.
    """
    s = _sgn(y)
    inboard = y - s * (w / 2 + 120.0)
    parts = []
    # the aft strand drops further: at dz -30 it crossed the pushrod on its
    # way in, three vertices deep at x 979, y 504
    for k, (dx, dz) in enumerate(((-150.0, 40.0), (150.0, -130.0))):
        # 0.94 of the wheel's own y: the upright's inner face is at 728 and
        # this anchor was landing at 701, just inboard of the casting it is
        # supposed to be bolted to.
        # low on the upright, under the caliper's mounting lugs
        p0 = (x + dx * 0.25, y * 0.94, z + dz * 0.4 - 92.0)
        # ...into the tub, which is what the docstring says and what the
        # regulation is for. It used to stop at y 680, which is 440 mm short
        # of the survival cell: a tether anchored to the upright at both ends.
        # the front tethers anchor on the survival cell; the rears on the
        # gearbox, which is the structure back there -- at 228 they went
        # straight through the fan duct.
        front = tag.startswith("f")
        anchor = 228.0 if front else 108.0
        # the rears anchor high on the gearbox: the fan duct fills everything
        # under z 448 back there, so a tether across it at hub height goes
        # through the duct, the throat and the fairing.
        zz = (z + dz - 92.0) if front else 396.0
        # the rears anchor forward on the rear impact structure, which is the
        # strong point back there and is clear of the fan
        px1 = x + dx * 0.8 if front else x + abs(dx) * 0.78
        p1 = (px1, s * anchor, zz)
        # the strap itself, flat in section rather than round
        path = [p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2,
                     (p0[2] + p1[2]) / 2 + 14.0), p1]
        parts.append(mesh.pipe(path, 13.0, segments=10))
        # the swaged end fittings at each anchor
        for pt in (p0, p1):
            ev, ef = mesh.revolve_closed(
                [(-14.0, 7.0), (14.0, 7.0), (14.0, 22.0), (6.0, 26.0),
                 (-6.0, 26.0), (-14.0, 22.0)], 14)
            ev = [(pz + pt[0], px + pt[1], py + pt[2]) for (px, py, pz) in ev]
            parts.append((ev, ef))
    return mesh.join(*parts)


def _upright(x, y, z, w):
    """Hub barrel plus the arms that reach out to the wishbone and pushrod
    pickups. A box here hides the whole point of a suspension."""
    s = _sgn(y)
    parts = []
    y0 = -s * w * 0.04
    # The barrel stops 2 mm inboard of the brake disc. It ran 28 mm outboard
    # of the wheel's centre line, which is through the disc -- 16 mm of a
    # turning disc and its bell inside the part that carries it. The hub
    # passes out through the barrel's bore to the disc and the wheel.
    #
    # Its bore is the hub's bearings' outer race. At 30 mm it was solid
    # metal round a hub whose bearings run at 49 to 61, so the wheel turned
    # inside the casting that is meant to hold its bearings.
    end = -s * w * 0.02 - s * (W["disc_t"] / 2 + 2.0)
    bore = W["hub_r"] * 0.98
    parts.append(_lathe(x, y, z, [(y0 - s * 90.0, bore),
                                  (y0 - s * 90.0, 72.0),
                                  (end, 86.0),
                                  (end, bore)]))
    inboard = y - s * (w / 2 + 30.0)
    # The arms leave the barrel's outside wall, inboard of the brake disc,
    # and run straight to their pickups. They were pipes from the axle's
    # centre on the disc's own plane, via a midpoint that for the upper arm
    # was below where it started: through the hub, its bearings and the disc.
    # An arm's start is a whole pipe radius outside the bearings, because it
    # runs mostly inboard and its section hangs back toward the axle.
    y_arm = y - s * (w * 0.02 + W["disc_t"] / 2 + 36.0)
    for joint in ball_joints(x, y):
        up = 1.0 if joint[2] > z else -1.0
        parts.append(mesh.pipe([(x, y_arm, z + up * (bore + 38.0)), joint],
                               34.0, 10))
    # steering / toe-link arm, trailing the axle
    dx, dz = 150.0, -40.0
    ln = math.hypot(dx, dz)
    r_st = bore + 30.0
    parts.append(mesh.pipe([(x + dx / ln * r_st, y_arm, z + dz / ln * r_st),
                            (x + dx, inboard, z + dz)], 26.0, 8))
    return mesh.join(*parts)


def _nut(x, y, z, w):
    """Centre-lock nut, in the middle of the wheel cover."""
    s = _sgn(y)
    # It sits down in the dish of the wheel cover. It used to be mounted back
    # to front -- threaded spigot outboard, castellated drive face inboard --
    # which stood it 17 mm proud of the tyre and made it the widest object on
    # the car.
    y0 = s * (w / 2 * 0.93 - W["cover_dish"] - 20.0)
    R = W["nut_r"]
    H_ = W["nut_h"]
    parts = []
    # The drive face the gun engages: a castellated ring, not a hex. A gun
    # socket has to find it in a tenth of a second at any clock angle.
    parts.append(mesh.revolve_closed(
        [(0.0, 0.0), (H_ * 0.30, 0.0), (H_ * 0.30, R * 0.42),
         (H_ * 0.22, R * 0.52), (H_ * 0.22, R * 0.86),
         (H_ * 0.34, R * 0.94), (H_ * 0.34, R),
         (H_ * 0.05, R), (0.0, R * 0.90)], 40))
    for i in range(9):
        a = 2 * math.pi * i / 9
        cv, cf = mesh.revolve_closed(
            [(H_ * 0.34, 0.0), (H_, 0.0), (H_, R * 0.19),
             (H_ * 0.80, R * 0.23), (H_ * 0.34, R * 0.23)], 12)
        parts.append(([(px, py + math.cos(a) * R * 0.68,
                        pz + math.sin(a) * R * 0.68)
                       for (px, py, pz) in cv], cf))
    # the captive retainer spring that stops it leaving with the gun
    parts.append(mesh.ring_torus(H_ * 0.10, R * 1.06, R * 0.07, 40, 10))
    # the threaded spigot behind it
    parts.append(mesh.revolve_closed(
        [(-H_ * 1.5, 0.0), (0.0, 0.0), (0.0, R * 0.52),
         (-H_ * 1.5, R * 0.52)], 30))
    v, f = mesh.join(*parts)
    v = [(y0 + s * px, py, pz) for (px, py, pz) in v]
    return _place([(pz, px, py) for (px, py, pz) in v], x, y, z), f
