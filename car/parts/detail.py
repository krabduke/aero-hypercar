"""Body detail: cooling exits, wing pylons, suspension fairings, the crash
structures, and the driver.

These are the parts that separate a shape from a car. Each one is placed on
the actual body surface via `chassis.surface_point` / `chassis.sidepod_point`
rather than at a guessed offset, so nothing floats above the skin or sinks
into it when the section changes along the car.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import chassis, common, wheels

BD = spec.BODY_DETAIL
FW = spec.FRONT_WING
S = spec.SUSP
W = spec.WHEEL
F = spec.FLOOR


def build():
    out = {}
    out.update(_gills())
    out.update(_nose())
    out.update(_crash_structures())
    out.update(_airbox())
    out.update(_driver())
    out.update(_service())
    return out


# --------------------------------------------------------------------------

def _gills():
    """Louvre banks venting the radiators and the engine bay.

    Air that goes into a sidepod has to come out somewhere; on a real car that
    exit is a bank of louvres, and it is one of the most recognisable pieces
    of surface detail there is.
    """
    # Each bank is a louvred panel on the cover: slats across the flow,
    # leaning aft, over a dark recess. They were 120 mm blocks laid along
    # the flow and canted off the skin, and from any distance a row of them
    # read as a line of thorns.
    parts = []
    for (x0, x1, ang, n, span, h) in BD["gills"]:
        for mirror in (1.0, -1.0):
            a = ang if mirror > 0 else 180.0 - ang
            parts.append(shapes.louvre_panel(
                chassis.skin_point, x0, x1, a - span / 2, a + span / 2,
                n, h=h, lean=24.0, t=3.0, m=8, base=1.3))

    # The sidepod's exits are exit_louvres_l/r (systems.py). A second set was
    # built here on the same flanks at nearly the same stations, so every
    # sidepod carried two overlapping grids of blades.
    return {"gills": mesh.join(*parts)}


def _nose():
    """The pylons that carry the front wing, and the cape under the nose.

    A front wing bolted to nothing is the giveaway that a model was never
    thought through. These two pylons are what hold it, and the cape is the
    sculpted underside that turns the flow outboard around the front tyre.
    """
    out = {}
    px_x = BD["nose_pylon_x"]
    # The pylons that carry the front wing are built by wings.py, which is
    # the module that owns the wing and the only one that knows about
    # FW["arch"] -- it lands them on the arched mainplane, 25 mm above where
    # this copy put them. Both were being built under the same name, so
    # assembly made two sets of pylons 25 mm apart and renamed the second.

    capes = []
    for sgn in (-1.0, 1.0):
        rows = []
        n_f, n_g = 13, 11
        for i in range(n_f):
            f = i / (n_f - 1)
            x = BD["cape_x0"] + (BD["cape_x1"] - BD["cape_x0"]) * f
            under = chassis.surface_point(x, -90.0)
            row = []
            for j in range(n_g):
                g = j / (n_g - 1)
                y = sgn * BD["cape_y"] * g * (0.5 + 0.5 * f)
                # the cape is a curved shelf, not a wedge: it turns the flow
                # coming off the nose down and outboard, so it droops on a
                # curve and rolls over at its outer edge
                drop = 34.0 * (0.4 + 0.6 * f) * g ** 1.35
                row.append((x, y, under[2] + 8.0 - drop))
            rows.append(row)
        capes.append(_grid_skin(rows, 9.0, rim=2))
    out["nose_cape"] = mesh.join(*capes)
    return out


def _grid_skin(rows, t, rim=0):
    """Give a grid of stations thickness in z and close it into a solid.

    With `rim` the thickness rolls to nothing over that many cells from the
    boundary, so the panel has an edge radius instead of a knife edge.
    """
    nr, nc = len(rows), len(rows[0])

    def half_t(i, j):
        if not rim:
            return t / 2
        d = min(min(i, nr - 1 - i, j, nc - 1 - j) / float(rim), 1.0)
        return (t / 2) * math.sqrt(max(0.0, 1.0 - (1.0 - d) ** 2))

    lo = [(x, y, z - half_t(i, j))
          for i, row in enumerate(rows) for j, (x, y, z) in enumerate(row)]
    hi = [(x, y, z + half_t(i, j))
          for i, row in enumerate(rows) for j, (x, y, z) in enumerate(row)]
    verts = lo + hi
    off = len(lo)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i * nc + j
            faces.append((k, k + nc, k + nc + 1, k + 1))
            faces.append((off + k, off + k + 1, off + k + nc + 1,
                          off + k + nc))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i * nc + j
            faces.append((k, k + nc, off + k + nc, off + k) if j == 0
                         else (k + nc, k, off + k, off + k + nc))
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i * nc + j
            faces.append((k + 1, k, off + k, off + k + 1) if i == 0
                         else (k, k + 1, off + k + 1, off + k))
    return verts, faces


def faired_leg(p0, p1, sect, chord):
    """Sweep an aerofoil section along a suspension leg, chord streamwise.

    Every suspension member on a modern car is a wing section: a round tube at
    300 km/h is pure drag and produces nothing. suspension.py builds its arms
    with this rather than with pipes.
    """
    verts = []
    for p in (p0, p1):
        for (u, v) in sect:
            verts.append((p[0] + (u - 0.35) * chord, p[1], p[2] + v * chord))
    n = len(sect)
    faces = []
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((i, i2, n + i2, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    return verts, faces


def _crash_structures():
    """Side impact tubes and the rear crash box behind the gearbox."""
    out = {}
    sides = []
    # Straight out from the tub's flank to the sidepod's outer wall, square
    # to both, between the inlet duct (which ends at x 1910) and the
    # radiator (which starts at 2134), under the fuel coupling. They ran
    # diagonally from x 1740, so their flat inner ends swung 60 mm into the
    # tub, and their front edges stood in the inlet duct and the bargeboards.
    r = BD["crash_r"]
    xs = 2000.0
    ring = chassis.body_section(xs, segments=360)
    for sgn in (-1.0, 1.0):
        for zz in (250.0, 378.0):
            y_in = max(p[1] for p in ring
                       if p[1] > 0 and abs(p[2] - zz) < r * 0.78 * 0.82)
            b = chassis.sidepod_point(xs, sgn * 0.94, 0.0, -r)
            a = (xs, sgn * y_in, zz)
            # an oval, so it crushes along its length instead of buckling
            # sideways, wound thicker at the outboard end where the load
            # comes in
            sides.append(shapes.swept_profile(
                [a, (xs, (a[1] + b[1]) * 0.5, zz), (xs, b[1], zz)],
                shapes.rounded_polygon(
                    [(-r * 0.98, -r * 0.78), (r * 0.98, -r * 0.78),
                     (r * 0.98, r * 0.78), (-r * 0.98, r * 0.78)],
                    r * 0.62, seg=6),
                scale=[(0.82, 0.82), (0.93, 0.93), (1.0, 1.0)], subdiv=5))
    out["side_impact"] = mesh.join(*sides)

    x = spec.POWERTRAIN["gearbox_x"] + spec.POWERTRAIN["gearbox_len"]
    z = spec.POWERTRAIN["gearbox_z"]
    # tapered to stay inside the engine cover, which narrows faster than it
    # The rear impact structure: a tapered cone with crush initiators rolled
    # into it, so it starts folding at a known load instead of choosing its
    # own failure mode, and a mounting flange onto the gearbox.
    parts = []
    prof = []
    for i in range(13):
        f = i / 12.0
        prof.append((x + 340.0 * f,
                     118.0 - 60.0 * f + (5.0 if i % 3 == 1 else 0.0)))
    loop = [(px, r - 5.0) for (px, r) in prof] + list(reversed(prof))
    cv, cf = mesh.revolve_closed(loop, 34)
    parts.append((cv, cf))
    parts.append(mesh.flange(x, 100.0, 146.0, 14.0, 8, bolt_r=7.0))
    # Three struts from the flange forward to the gearbox's tail, across the
    # 42 mm between them that the rear anti-roll bar crosses in. The
    # structure used to stand there attached to nothing but the bodywork
    # that happened to pass through it; placed low and on the centreline top
    # they clear the bar above and the driveshafts either side.
    x_gb = spec.POWERTRAIN["gearbox_front_x"] + spec.POWERTRAIN["gearbox_len"]
    for (sy, sz) in ((-70.0, -110.0), (70.0, -110.0), (0.0, 112.0)):
        parts.append(mesh.pipe([(x_gb - 12.0, sy, sz), (x + 6.0, sy, sz)],
                               12.0, 16))
    # the rain light and the jacking point live on the back of it
    parts.append(shapes.rounded_box(x + 352.0, 0.0, 20.0, 26.0, 90.0, 60.0,
                                    9.0, seg=6))
    v, f = mesh.join(*parts)
    out["crash_structure"] = ([(px, py, pz + z) for (px, py, pz) in v], f)
    return out


def _airbox():
    """Roll-hoop air intake feeding the engine, and its plenum duct."""
    out = {}
    x = BD["airbox_x"]
    w, h = BD["airbox_w"], BD["airbox_h"]
    L = BD["airbox_len"]
    top = chassis.surface_point(x, 90.0)
    # The scoop stands proud at the roll hoop and is swallowed by the engine
    # cover within its own length -- it is an intake, not a second fuselage.
    ctrl = ((-40.0, w, h, 24.0), (-24.0, w * 1.04, h * 1.02, 22.0),
            (L * 0.10, w * 0.97, h * 0.92, 16.0),
            (L * 0.22, w * 0.90, h * 0.82, 8.0),
            (L * 0.40, w * 0.77, h * 0.64, -14.0),
            (L * 0.62, w * 0.62, h * 0.46, -40.0),
            (L * 0.82, w * 0.47, h * 0.31, -70.0),
            (L, w * 0.34, h * 0.20, -96.0),
            # ...and on into the engine. The airbox stopped at x 2400 with
            # the engine's front face at 2868, so the one thing on the car
            # whose entire job is to feed the engine fed 470 mm of air.
            (L + 240.0, w * 0.30, h * 0.18, -112.0),
            (L + 500.0, w * 0.27, h * 0.16, -128.0),
            (L + 700.0, w * 0.25, h * 0.15, -164.0))
    rows = []
    for (dx, sw, sh, dz) in ctrl:
        ring = []
        for i in range(34):
            a = 2 * math.pi * i / 34
            p = 2.0 / 2.8
            ca, sa = math.cos(a), math.sin(a)
            ring.append((x + dx,
                         sw * math.copysign(abs(ca) ** p, ca),
                         top[2] - 20.0 + dz
                         + sh * math.copysign(abs(sa) ** p, sa)))
        rows.append(ring)
    out["airbox"] = common.loft(rows)
    return out


def _driver():
    """A driver in the seat. Everything above the coaming is what sets the
    scale of a single-seater; without it the cockpit reads as a slot.

    This used to be one rounded box and four eight-sided pipes -- 292
    vertices for a human being, in a cockpit where the steering wheel he is
    holding has 2,812. His arms ended 90 mm short of the wheel, he had no
    hands, and he was not wearing the head-and-neck restraint that is the
    reason the halo above him has anything to hold on to.
    """
    out = {}
    D = BD["driver"]
    R = D["helmet_r"]
    hx, hz = D["helmet_x"], D["helmet_z"]

    # ---- helmet: a smooth shell, a visor let into its face, a spoiler ----
    #
    # The shell was a revolve with a visor made of a bent pipe laid across
    # the front and a second pipe for the chin: the pipes' ends stood off the
    # sides like ears, and it read as a toy. A helmet is one smooth shell,
    # a little longer behind than in front and narrower than it is tall, with
    # the visor a tinted panel following its face.
    # the back no longer than it was: the headrest is right behind it
    ax_f, ax_b, by, cz = R * 0.98, R * 0.95, R * 0.90, R * 1.0

    def shell(d, off=0.0):
        dx, dy, dz = d
        a = ax_f if dx < 0 else ax_b
        t = 1.0 / math.sqrt((dx / a) ** 2 + (dy / by) ** 2 + (dz / cz) ** 2)
        return (hx + dx * (t + off), dy * (t + off), hz + dz * (t + off))

    parts = []
    n_lat, n_lon = 26, 44
    verts, faces = [shell((0.0, 0.0, -1.0))], []
    for i in range(1, n_lat):
        el = -math.pi / 2 + math.pi * i / n_lat
        for j in range(n_lon):
            az = 2 * math.pi * j / n_lon
            verts.append(shell((math.cos(el) * math.cos(az),
                                math.cos(el) * math.sin(az), math.sin(el))))
    verts.append(shell((0.0, 0.0, 1.0)))
    top = len(verts) - 1
    for j in range(n_lon):
        j2 = (j + 1) % n_lon
        faces.append((0, 1 + j2, 1 + j))
        faces.append((top, 1 + (n_lat - 2) * n_lon + j,
                      1 + (n_lat - 2) * n_lon + j2))
    for i in range(n_lat - 2):
        for j in range(n_lon):
            j2 = (j + 1) % n_lon
            a0, a1 = 1 + i * n_lon, 1 + (i + 1) * n_lon
            faces.append((a0 + j, a0 + j2, a1 + j2, a1 + j))
    parts.append((verts, faces))
    # the spoiler on the back of the crown, and two intake vents on top,
    # each let 1 mm into the shell they sit on
    parts.append(shapes.rounded_box(hx + R * 0.74, 0.0, hz + R * 0.60,
                                    R * 0.42, R * 0.86, R * 0.07,
                                    R * 0.03, seg=5))
    for sgn in (-1.0, 1.0):
        vx, vy, vz = shell((-0.2, sgn * 0.30, 0.93))
        parts.append(shapes.rounded_box(vx, vy, vz, R * 0.40, R * 0.20,
                                        R * 0.12, R * 0.05, seg=5))
    # the visor: a tinted panel standing a millimetre proud of the face,
    # 140 degrees wide and from just below eye level to the brow, as a grid
    # over the shell so it follows the face
    n_a, n_e = 28, 8
    vv, vf = [], []
    for k in range(n_a + 1):
        az = math.radians(180.0 - 70.0 + 140.0 * k / n_a)
        for off in (0.8, 3.0):
            for m_ in range(n_e + 1):
                e = math.radians(-10.0 + 36.0 * m_ / n_e)
                vv.append(shell((math.cos(e) * math.cos(az),
                                 math.cos(e) * math.sin(az), math.sin(e)), off))
    L = 2 * (n_e + 1)

    def vid(k, layer, m_):
        return k * L + layer * (n_e + 1) + m_
    for k in range(n_a):
        for m_ in range(n_e):
            vf.append((vid(k, 1, m_), vid(k + 1, 1, m_), vid(k + 1, 1, m_ + 1),
                       vid(k, 1, m_ + 1)))
            vf.append((vid(k, 0, m_ + 1), vid(k + 1, 0, m_ + 1),
                       vid(k + 1, 0, m_), vid(k, 0, m_)))
        for m_ in (0, n_e):
            vf.append((vid(k, 0, m_), vid(k + 1, 0, m_), vid(k + 1, 1, m_),
                       vid(k, 1, m_)))
    for k in (0, n_a):
        for m_ in range(n_e):
            vf.append((vid(k, 0, m_), vid(k, 0, m_ + 1), vid(k, 1, m_ + 1),
                       vid(k, 1, m_)))
    out["helmet_visor"] = (vv, vf)
    out["helmet"] = mesh.join(*parts)

    # ---- body ----
    body = []
    # torso: shoulders wide, waist narrow, chest deep -- lofted, not a box.
    # It is lofted along the line of his back, from the shoulders down and
    # forward to the hips: a single-seater driver lies reclined with his
    # feet up at the pedals, so his head is the aft end of him, not the
    # front. The rings are built across that line, with the chest facing up
    # and forward.
    sx, sz = D["shoulder_x"], D["shoulder_z"]
    px_, pz_ = D["hip_x"], D["hip_z"]
    (ux, uz), (nx, nz), L = _torso_frame()
    rings = []
    for (t, hw, hh) in TORSO:
        cx_, cz_ = sx + ux * L * t, sz + uz * L * t
        ring = []
        for i in range(26):
            a_ = 2 * math.pi * i / 26
            ca, sa = math.cos(a_), math.sin(a_)
            e = 2.0 / 2.6
            w = TORSO_DEPTH * hh * math.copysign(abs(sa) ** e, sa)
            ring.append((cx_ + nx * w,
                         D["shoulder_w"] * hw
                         * math.copysign(abs(ca) ** e, ca),
                         cz_ + nz * w))
        rings.append(ring)
    body.append(shapes._loft_closed(rings))
    # neck: from the base of the skull down to the top of the chest
    body.append(mesh.pipe([(hx + 30.0, 0.0, hz - R * 0.78),
                           (sx - 10.0, 0.0, sz + 40.0)],
                          [R * 0.40, R * 0.54], 20, subdiv=3))
    # HANS: the collar the belts trap against the shoulders, with the two
    # tethers to the helmet. The halo exists to protect a head that this
    # holds on to a neck.
    for sgn in (-1.0, 1.0):
        body.append(shapes.rounded_box(
            sx - 40.0, sgn * D["shoulder_w"] * 0.64, sz + 70.0,
            110.0, D["shoulder_w"] * 0.38, 36.0, 14.0, seg=6))
        body.append(mesh.pipe(
            [(hx + R * 0.55, sgn * R * 0.52, hz - R * 0.30),
             (sx - 40.0, sgn * D["shoulder_w"] * 0.50, sz + 90.0)],
            7.0, 12, subdiv=2))
    body.append(shapes.rounded_box(sx - 90.0, 0.0, sz + 60.0,
                                   80.0, D["shoulder_w"] * 1.00, 32.0,
                                   12.0, seg=6))

    # arms: shoulder, elbow, wrist, and a hand on the wheel rim
    wheel_x = 1333.0
    for sgn in (-1.0, 1.0):
        shoulder = (sx - 10.0, sgn * D["shoulder_w"] * 0.84, sz + 30.0)
        elbow = (1570.0, sgn * 174.0, 548.0)
        wrist = (wheel_x + 46.0, sgn * 126.0, 594.0)
        body.append(_limb(shoulder, elbow, wrist,
                          D["arm_r"], D["arm_r"] * 0.78, D["arm_r"] * 0.58))
        # the hand, closed round the rim
        hand = []
        hand.append(shapes.rounded_box(wheel_x + 22.0, sgn * 118.0, 592.0,
                                       56.0, 46.0, 88.0, 18.0, seg=6))
        for k in range(4):
            hand.append(mesh.pipe(
                [(wheel_x + 6.0, sgn * 112.0, 566.0 + k * 20.0),
                 (wheel_x - 14.0, sgn * 104.0, 562.0 + k * 20.0)],
                9.0, 10, subdiv=2))
        body.append(mesh.join(*hand))

    # legs: hip, knee, ankle, and a boot on the pedal. Nearly straight, the
    # way they are in a single-seater: the knees stay low, under the front
    # dampers and torsion bars on top of the tub, and the shins run through
    # the dash bulkhead's aperture into the footwell.
    for sgn in (-1.0, 1.0):
        hip = (px_ + 10.0, sgn * 100.0, pz_ + 10.0)
        knee = (D["knee_x"], sgn * 118.0, D["knee_z"])
        ankle = (D["foot_x"] + 40.0, sgn * 96.0, 330.0)
        body.append(_limb(hip, knee, ankle,
                          D["leg_r"], D["leg_r"] * 0.66, D["leg_r"] * 0.46))
        body.append(shapes.rounded_box(D["foot_x"] + 4.0, sgn * 92.0, 312.0,
                                       110.0, 72.0, 56.0, 18.0, seg=6))
    out["driver"] = mesh.join(*body)
    return out


# The torso's sections along the line from the shoulders (t 0) to the hips
# (t 1): (t, half-width, half-depth) as fractions of shoulder_w and
# TORSO_DEPTH.
TORSO = ((-0.10, 0.62, 0.50), (0.00, 0.94, 0.80), (0.14, 1.00, 0.96),
         (0.36, 0.94, 1.00), (0.60, 0.78, 0.86), (0.86, 0.84, 0.88),
         (1.04, 0.76, 0.74), (1.14, 0.52, 0.44))
TORSO_DEPTH = 108.0
_E = 2.6                                # the sections' superellipse power


def _torso_frame():
    """(along, chest normal, length): the unit vector from the shoulders to
    the hips, the one the chest faces along (up and forward), and the
    distance between them -- all in the x-z plane."""
    D = BD["driver"]
    sx, sz = D["shoulder_x"], D["shoulder_z"]
    L = math.hypot(sx - D["hip_x"], sz - D["hip_z"])
    ux, uz = (D["hip_x"] - sx) / L, (D["hip_z"] - sz) / L
    nx, nz = uz, -ux
    if nz < 0.0:
        nx, nz = -nx, -nz
    return (ux, uz), (nx, nz), L


def chest_point(t, y, lift=0.0):
    """The point on the front of the driver's torso at station t and
    lateral offset y, lifted `lift` off the skin along the chest normal.
    The harness is laid on this, so the belts lie on the driver rather than
    at a height picked for a driver who sat somewhere else."""
    D = BD["driver"]
    (ux, uz), (nx, nz), L = _torso_frame()
    for (t0, w0, h0), (t1, w1, h1) in zip(TORSO, TORSO[1:]):
        if t <= t1:
            f = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
            hw, hh = w0 + (w1 - w0) * f, h0 + (h1 - h0) * f
            break
    Y = D["shoulder_w"] * hw
    q = min(abs(y) / Y, 0.999) ** _E
    w = TORSO_DEPTH * hh * (1.0 - q) ** (1.0 / _E) + lift
    cx_ = D["shoulder_x"] + ux * L * t
    cz_ = D["shoulder_z"] + uz * L * t
    return (cx_ + nx * w, y, cz_ + nz * w), (nx, 0.0, nz)


def _limb(a, b, c, r0, r1, r2):
    """An arm or a leg: two tapered segments with a joint between them.

    A limb drawn as one pipe from shoulder to wrist passes straight through
    the bodywork, has no elbow, and ends in nothing. This bends at the joint,
    tapers along its length, and puts a ball at the joint so the two segments
    meet in a shape rather than a crease.
    """
    parts = [mesh.pipe([a, b], [r0, r1], 20, subdiv=4),
             mesh.pipe([b, c], [r1, r2], 20, subdiv=4)]
    jv, jf = mesh.revolve_closed(
        [(-r1, 0.0), (-r1 * 0.7, r1 * 0.72), (0.0, r1 * 1.02),
         (r1 * 0.7, r1 * 0.72), (r1, 0.0)], 20)
    parts.append(([(px + b[0], py + b[1], pz + b[2])
                   for (px, py, pz) in jv], jf))
    return mesh.join(*parts)


def _service():
    """Jack points, tow hooks and the wear plank -- the small hardware that
    tells you this is a car that gets worked on between sessions."""
    out = {}
    SV = spec.SERVICE
    parts = []
    for x in (420.0, spec.POWERTRAIN["gearbox_x"] + 460.0):
        under = chassis.surface_point(x, -90.0)
        z0 = under[2] - 8.0

        def place(v):
            return [(pz + x, py, px + z0) for (px, py, pz) in v]

        def lathe(profile, seg=28):
            v, f = mesh.revolve_closed(list(profile), seg)
            return (place(v), f)

        r = BD["jack_r"]
        puck = SV["jack_puck_r"]
        # A jack point is a socket, not a peg: the jack's spigot goes UP into
        # it and takes the car's weight on the cross pin, so what is modelled
        # is the bore, the bell mouth that finds it, the pin, and the way the
        # load is spread into the floor -- a bare cylinder hanging under the
        # car is the one shape it cannot be.
        parts.append(lathe([
            (0.0, r + 3.0), (0.0, r + 12.0), (9.0, r + 12.0),
            (16.0, r + 3.0), (100.0, r + 3.0), (100.0, r - 5.0),
            (18.0, r - 5.0), (9.0, r - 1.0), (0.0, r + 3.0)]))
        # the cross pin the spigot latches behind
        pv, pf = mesh.cylinder(-r - 6.0, r + 6.0, 6.0, 12)
        parts.append((place([(pz + 70.0, px, py) for (px, py, pz) in pv]), pf))
        # the load-spreading pad bonded to the floor above it, and the
        # gussets that take the bending out of the bore
        parts.append(lathe([
            (96.0, 0.0), (96.0, puck + 22.0), (108.0, puck + 16.0),
            (108.0, 0.0)], 30))
        rib_r = (r + 3.0 + puck + 20.0) / 2
        for k in range(4):
            a = math.pi / 2 * k + math.pi / 4
            gv, gf = mesh.box(0.0, 0.0, 0.0, 44.0, 5.0,
                              puck + 20.0 - (r + 3.0))
            ca, sa = math.cos(a), math.sin(a)
            gv = [(px + 74.0, py * ca - (pz + rib_r) * sa,
                   py * sa + (pz + rib_r) * ca)
                  for (px, py, pz) in gv]
            parts.append((place(gv), gf))
        # the retaining strap: what stops the jack dropping out of the socket
        sv, sf = mesh.ring_torus(86.0, r + 6.0, SV["jack_strap_w"] * 0.18,
                                 24, 8)
        parts.append((place(sv), sf))
    out["jack_points"] = mesh.join(*parts)

    hooks = []
    for (x, z) in ((260.0, BD["tow_z_front"]),
                   (spec.POWERTRAIN["gearbox_x"] + 560.0, BD["tow_z_rear"])):
        v, f = mesh.ring_torus(x, 74.0, BD["tow_r"], 16, 8)
        hooks.append(([(px, py, pz + z) for (px, py, pz) in v], f))
    out["tow_hooks"] = mesh.join(*hooks)
    return out
