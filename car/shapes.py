"""Shapes that are not boxes.

Nothing on a fast vehicle is a rectangular prism. A casting has draft so it will
leave the mould, a radius on every edge because a sharp internal corner is a
crack waiting to happen, ribs where it needs stiffness, and bosses where
something bolts to it. An electronics case has fins because it has to get rid
of heat, and a connector because something plugs into it.

These are the primitives for that. They cost a few more vertices than
`mesh.box` and they are the difference between a model of an engine and a pile
of blocks the right size.
"""

import math

import mesh


def rounded_box(cx, cy, cz, sx, sy, sz, r=6.0, seg=6, draft=0.0, rz=None):
    """A cast box: filleted on all twelve edges, with draft.

    The first version rounded the four vertical edges and left the top and
    bottom as sharp rims -- two rings of twenty points, forty vertices for a
    whole casting. Nothing on this car is moulded with a sharp edge: a corner
    that sharp is a stress raiser in metal and delaminates in carbon, and the
    tool could not fill it. Every edge gets a radius now.

    Draft is the taper a moulding needs to come out of its tool -- a degree or
    two, always narrowing away from the parting line.

    `r` is the radius on the vertical edges, `rz` the one top and bottom
    (defaults to r, clamped to fit).
    """
    r = max(0.2, min(r, sx / 2 - 0.05, sy / 2 - 0.05))
    rz = r if rz is None else rz
    rz = max(0.2, min(rz, sz / 2 - 0.05))
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    tan = math.tan(math.radians(draft))

    caps = max(2, seg // 2)
    levels = []
    for i in range(caps + 1):                       # bottom fillet
        a = (math.pi / 2) * i / caps
        levels.append((-hz + rz * (1 - math.cos(a)), rz * math.sin(a)))
    for i in range(1, caps + 1):                    # top fillet
        a = (math.pi / 2) * i / caps
        levels.append((hz - rz * (1 - math.sin(a)), rz * math.cos(a)))

    rings = []
    for (z, inset) in levels:
        shrink = rz - inset
        t = tan * (z + hz)
        ax = max(hx - t - shrink, 0.05)
        ay = max(hy - t - shrink, 0.05)
        rr = max(min(r, ax - 0.02, ay - 0.02), 0.02)
        ring = []
        for (sgx, sgy) in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            ox, oy = sgx * (ax - rr), sgy * (ay - rr)
            a0 = math.atan2(sgy, sgx) - math.pi / 4
            for i in range(seg + 1):
                a = a0 + (math.pi / 2) * i / seg
                ring.append((cx + ox + rr * math.cos(a),
                             cy + oy + rr * math.sin(a), cz + z))
        rings.append(ring)
    return _loft_closed(rings)


def shaped_panel(outline, y, t, bow=None, rim_seg=5, rim=1.0, axis="y"):
    """A panel with a shape and an edge, which is what an endplate really is.

    `common.plate` made every vertical surface on this car a four-point
    rectangle extruded 8 vertices thick -- endplates, floor strakes, brake
    duct fences, bargeboards, all of them. Real aerodynamic furniture is cut
    to a profile, rolled over at the edges (a knife edge on carbon chips the
    first time it touches anything, and sheds a vortex you did not ask for),
    and bowed across its span because a flat plate does not turn flow.

    `outline` is the perimeter as [(x, z), ...] going round once; it must be
    star-shaped about its own centroid, which every panel on this car is.
    `bow(fx, fz) -> dy` displaces the panel laterally, with fx and fz the
    normalised position inside the outline's bounding box.
    """
    n = len(outline)
    cx = sum(p[0] for p in outline) / n
    cz = sum(p[1] for p in outline) / n
    x0 = min(p[0] for p in outline); x1 = max(p[0] for p in outline)
    z0 = min(p[1] for p in outline); z1 = max(p[1] for p in outline)
    sx = (x1 - x0) or 1.0
    sz = (z1 - z0) or 1.0

    # outward normal at each perimeter point, from its two neighbours
    norms = []
    for i in range(n):
        ax, az = outline[i - 1]
        bx, bz = outline[(i + 1) % n]
        tx, tz = bx - ax, bz - az
        m = math.hypot(tx, tz) or 1.0
        nx, nz = tz / m, -tx / m
        # point it away from the centroid
        if (outline[i][0] - cx) * nx + (outline[i][1] - cz) * nz < 0:
            nx, nz = -nx, -nz
        norms.append((nx, nz))

    def place(px, pz, dy):
        f = bow(( px - x0) / sx, (pz - z0) / sz) if bow else 0.0
        return (px, y + dy + f, pz) if axis == "y" else (px, pz, y + dy + f)

    rings = []
    for k in range(rim_seg + 1):
        a = -math.pi / 2 + math.pi * k / rim_seg
        dy = (t / 2) * math.sin(a)
        back = (t / 2) * rim * (1 - math.cos(a))
        ring = []
        for i in range(n):
            px, pz = outline[i]
            nx, nz = norms[i]
            ring.append(place(px - nx * back, pz - nz * back, dy))
        rings.append(ring)

    verts = [v for r in rings for v in r]
    faces = []
    for k in range(rim_seg):
        a, b = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    # the two flat faces, fanned from a centre point
    for (base, dy, flip) in ((0, -t / 2, True), (rim_seg * n, t / 2, False)):
        c = len(verts)
        verts.append(place(cx, cz, dy))
        for i in range(n):
            j = (i + 1) % n
            faces.append((c, base + j, base + i) if flip
                         else (c, base + i, base + j))
    return verts, faces


def panel_outline(pts, subdiv=3):
    """Resample a coarse outline so the panel has a curve, not corners.

    Four corners make a rectangle however thick you extrude it. Running a
    Catmull-Rom through the control points gives the swept leading edge and
    rolled trailing corner a real panel is cut to.
    """
    n = len(pts)
    out = []
    for i in range(n):
        p0 = pts[i - 1]; p1 = pts[i]
        p2 = pts[(i + 1) % n]; p3 = pts[(i + 2) % n]
        for k in range(subdiv):
            u = k / subdiv
            u2, u3 = u * u, u * u * u
            out.append(tuple(
                0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * u +
                       (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * u2 +
                       (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * u3)
                for d in (0, 1)))
    return out


def _loft_closed(rings):
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((a + j, a + j2, b + j2, b + j))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (len(rings) - 1) * n
    faces.append(tuple(range(base, base + n)))
    return verts, faces


def finned_case(cx, cy, cz, sx, sy, sz, n_fins=9, fin_h=7.0, fin_t=3.0,
                r=5.0, axis="x", side=1.0):
    """A case with cooling fins across it.

    Power electronics and a battery pack both have to reject heat, and both do
    it with extruded fins. A smooth slab says the designer never thought about
    it.
    """
    parts = [rounded_box(cx, cy, cz, sx, sy, sz, r, draft=1.5)]
    span = sx if axis == "x" else sy
    # over the flat of the top only: the end fins used to stand over the
    # case's rounded, drafted ends, where the top has already fallen away
    edge = r + fin_t / 2 + math.tan(math.radians(1.5)) * sz
    for i in range(n_fins):
        f = (edge + (span - 2 * edge) * (i + 0.5) / n_fins) / span
        # `side` puts the fin stack on the face that actually sees air: a
        # battery slung under the engine rejects heat downwards, and fins
        # pointing up into the crankcase are just a hidden slab
        # a tenth of the fin into the case: the case is drafted and its
        # edges rounded, so its top is below sz / 2 and fins standing on
        # sz / 2 hovered over it, attached to nothing
        zf = cz + side * (sz / 2 + fin_h / 2 - fin_h * 0.1)
        if axis == "x":
            parts.append(rounded_box(cx - sx / 2 + span * f, cy, zf,
                                     fin_t, sy * 0.92, fin_h, 1.2))
        else:
            parts.append(rounded_box(cx, cy - sy / 2 + span * f, zf,
                                     sx * 0.92, fin_t, fin_h, 1.2))
    return mesh.join(*parts)


def connector(cx, cy, cz, sx=26.0, sy=18.0, sz=14.0, pins=6):
    """A plug housing with pins in it. Everything electrical has one."""
    parts = [rounded_box(cx, cy, cz, sx, sy, sz, 2.5)]
    for i in range(pins):
        f = (i + 0.5) / pins
        v, fc = mesh.cylinder(0.0, sx * 0.45, 1.6, 6)
        v = [(px + cx + sx * 0.2, py + cy - sy * 0.32 + sy * 0.64 * f, pz + cz)
             for (px, py, pz) in v]
        parts.append((v, fc))
    return mesh.join(*parts)


def bolt_boss(cx, cy, cz, r=9.0, h=10.0, seg=10):
    """A raised pad with a bolt hole, where something fastens to a casting."""
    return mesh.revolve_open(
        [(0.0, r * 0.42), (0.0, r), (h * 0.6, r * 0.92), (h, r * 0.78),
         (h, r * 0.42)], seg, cap_start=True, cap_end=True)


def ribbed_cover(x0, x1, half_w, z_base, height, n_ribs=7, rib_h=5.0,
                 rib_w=7.0, crown=0.35, seg=14):
    """A cast cover: a crowned top, draft down the sides, and ribs across it.

    A cam cover is not a lid. It is a casting under a bolt flange, domed so it
    clears the valve gear, ribbed so it does not drum, with a bolt boss at
    every fastener.
    """
    parts = []
    n = 18
    rings = []
    for x in (x0, x0 + (x1 - x0) * 0.06, x1 - (x1 - x0) * 0.06, x1):
        t = 0.0 if x in (x0, x1) else 1.0
        hw = half_w * (0.90 + 0.10 * t)
        h = height * (0.72 + 0.28 * t)
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ca, sa = math.cos(a), math.sin(a)
            p = 2.0 / 2.6
            y = hw * math.copysign(abs(ca) ** p, ca)
            z = h * math.copysign(abs(sa) ** p, sa)
            ring.append((x, y, z_base + h * crown + z))
        rings.append(ring)
    parts.append(_loft_closed(rings))
    for i in range(n_ribs):
        f = (i + 0.5) / n_ribs
        x = x0 + (x1 - x0) * f
        parts.append(rounded_box(x, 0.0, z_base + height * (crown + 0.92),
                                 rib_w, half_w * 1.55, rib_h, 1.5))
    return mesh.join(*parts)


def tapered_pan(x0, x1, hw0, hw1, z_top, depth, sump_w, sump_x, seg=4):
    """A sump: a wide rail at the block face falling into a narrow keel.

    The oil has to end up somewhere the pickup can reach it under braking, so
    a real dry-sump pan is a shallow tray with a deep local well, not a
    rectangular tank bolted to the bottom of the engine.
    """
    rings = []
    n_st = 9
    for i in range(n_st):
        f = i / (n_st - 1)
        x = x0 + (x1 - x0) * f
        hw = hw0 + (hw1 - hw0) * f
        # the well is deepest around sump_x
        d = depth * (0.42 + 0.58 * math.exp(-((x - sump_x) / (sump_w)) ** 2))
        ring = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            ca, sa = math.cos(a), math.sin(a)
            p = 2.0 / 3.0
            y = hw * math.copysign(abs(ca) ** p, ca)
            z = (d / 2) * math.copysign(abs(sa) ** p, sa)
            ring.append((x, y, z_top - d / 2 + z))
        rings.append(ring)
    return _loft_closed(rings)


def fairing(path, chord, thickness=0.30, n_sec=14):
    """Sweep a streamlined section along a path.

    Anything exposed to the airstream on a fast vehicle is a teardrop, not a
    tube: a cylinder has roughly ten times the drag of a streamlined section
    of the same thickness, and it sheds a wake that ruins whatever is behind
    it.
    """
    import airfoil
    sect = airfoil.section_points(n_sec, thickness, 0.0)
    n = len(sect)
    verts = []
    for p in path:
        for (u, v) in sect:
            verts.append((p[0] + (u - 0.35) * chord, p[1], p[2] + v * chord))
    faces = []
    for j in range(len(path) - 1):
        a, b = j * n, (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((a + i, a + i2, b + i2, b + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (len(path) - 1) * n
    faces.append(tuple(range(base, base + n)))
    return verts, faces


def louvre_bank(x0, x1, y, z0, z1, n, blade_l, blade_h, t=2.0, cant=22.0):
    """A bank of angled blades over an exit duct."""
    parts = []
    for i in range(n):
        f = (i + 0.5) / n
        x = x0 + (x1 - x0) * f
        z = z0 + (z1 - z0) * f
        v, fc = rounded_box(0.0, 0.0, 0.0, blade_l, t, blade_h, t * 0.45)
        a = math.radians(cant)
        ca, sa = math.cos(a), math.sin(a)
        v = [(px * ca - pz * sa + x, py + y, px * sa + pz * ca + z)
             for (px, py, pz) in v]
        parts.append((v, fc))
    return mesh.join(*parts)


def core(cx, cy, cz, sx, sy, sz, n_tubes=18, n_fins=34):
    """A heat exchanger core: tubes with fin packs between them, in a frame.

    A radiator drawn as a solid block is the single laziest part on a car.
    """
    parts = [rounded_box(cx, cy, cz, sx, sy, sz, 4.0)]
    for i in range(n_tubes):
        f = (i + 0.5) / n_tubes
        parts.append(rounded_box(cx, cy, cz - sz / 2 + sz * f,
                                 sx * 1.01, sy * 0.96, sz / n_tubes * 0.42, 1.0))
    for i in range(n_fins):
        f = (i + 0.5) / n_fins
        parts.append(rounded_box(cx - sx / 2 + sx * f, cy, cz,
                                 sx / n_fins * 0.3, sy * 0.9, sz * 0.94, 0.6))
    return mesh.join(*parts)


def _resample(pts, n):
    """Resample a polyline to n points, evenly by arc length."""
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.dist(pts[i], pts[i - 1]))
    total = d[-1] or 1.0
    out, j = [], 0
    for i in range(n):
        s = total * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        span = (d[j + 1] - d[j]) or 1.0
        u = (s - d[j]) / span
        out.append(tuple(pts[j][k] + (pts[j + 1][k] - pts[j][k]) * u
                         for k in range(len(pts[0]))))
    return out


def _half_thickness(u, t):
    """NACA four-digit thickness distribution: round at the nose, maximum at
    30 percent, closing to a point at the tail."""
    return 5 * t * (0.2969 * math.sqrt(max(u, 0.0)) - 0.1260 * u
                    - 0.3516 * u * u + 0.2843 * u ** 3 - 0.1015 * u ** 4)


def turning_vane(camber, z_bot, z_top, t=0.085, twist=0.0, lean=0.0,
                 n_z=9, n_chord=26, top_cut=None, serrate=0, serr_depth=0.0):
    """A vane with an aerofoil section, twisted up its height.

    A turning vane is a lifting surface. Its whole job is to carry a side load
    and push a wake sideways, and a flat rectangle with a knife edge on both
    sides cannot do that -- it stalls at the first degree of yaw and sheds off
    both edges at once. So: a cambered plan section with a rounded nose and a
    closing tail, twisted from root to tip because the flow angle changes with
    height, cut to a profile along the top, and optionally serrated along the
    foot so it sheds a row of small vortices rather than one big one.

    `camber` is the plan camber line [(x, y), ...] at the root. `twist` is
    degrees of plan rotation about the leading edge from root to tip, `lean`
    the lateral shift over the same span.
    """
    base = _resample(camber, n_chord)
    x_le, y_le = base[0]
    chord = math.dist(base[0], base[-1]) or 1.0

    rings = []
    for k in range(n_z):
        fz = k / (n_z - 1)
        a = math.radians(twist * fz)
        ca, sa = math.cos(a), math.sin(a)
        line = []
        for (px, py) in base:
            dx, dy = px - x_le, py - y_le
            line.append((x_le + dx * ca - dy * sa,
                         y_le + dx * sa + dy * ca + lean * fz))
        loop = []
        for surf in (1, -1):
            rng = range(n_chord) if surf > 0 else range(n_chord - 2, 0, -1)
            for i in rng:
                u = i / (n_chord - 1)
                # plan normal from the neighbours
                p0 = line[max(i - 1, 0)]
                p1 = line[min(i + 1, n_chord - 1)]
                tx, ty = p1[0] - p0[0], p1[1] - p0[1]
                m = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / m, tx / m
                h = _half_thickness(u, t) * chord * surf
                # `top_cut` is the vane's top edge. It used to be applied to
                # the topmost ring only, so every ring below it stayed at the
                # full height and the surface folded back on itself wherever
                # the cut dropped -- a diffuser strake with a 90 mm roof over
                # it was 318 mm tall two rings down. The cut is the ceiling,
                # so every ring is a fraction of the way up to it.
                z_hi = z_top if top_cut is None else top_cut(u)
                z = z_bot + (z_hi - z_bot) * fz
                if serrate and k == 0 and serr_depth:
                    z += serr_depth * (0.5 - 0.5 * math.cos(
                        2 * math.pi * serrate * u)) 
                loop.append((line[i][0] + nx * h, line[i][1] + ny * h, z))
        rings.append(loop)
    return _loft_closed(rings)


def _frame(direction):
    """An orthonormal frame with +x along `direction`."""
    m = math.dist((0, 0, 0), direction) or 1.0
    t = tuple(d / m for d in direction)
    up = (0.0, 0.0, 1.0)
    if abs(t[2]) > 0.94:
        up = (0.0, 1.0, 0.0)
    n = (t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2],
         t[0] * up[1] - t[1] * up[0])
    mn = math.dist((0, 0, 0), n) or 1.0
    n = tuple(c / mn for c in n)
    b = (t[1] * n[2] - t[2] * n[1], t[2] * n[0] - t[0] * n[2],
         t[0] * n[1] - t[1] * n[0])
    return t, n, b


def orient(verts, origin, direction):
    """Map geometry built about the origin with its axis along +x onto a
    world point and direction."""
    t, n, b = _frame(direction)
    return [(origin[0] + t[0] * px + n[0] * py + b[0] * pz,
             origin[1] + t[1] * px + n[1] * py + b[1] * pz,
             origin[2] + t[2] * px + n[2] * py + b[2] * pz)
            for (px, py, pz) in verts]


def rod_end(origin, direction, r=12.0, seg=18, cheek=5.0):
    """A spherical rod end: the joint every suspension member actually ends in.

    A wishbone does not weld to the upright. It ends in a spherical bearing --
    a ball with a through hole, captured in a race, held between the two
    cheeks of a clevis, on a threaded shank that screws into the leg and sets
    the length. Model the leg as a bare tube and you have drawn the one part
    of the corner nobody ever has to adjust.

    `direction` points outward, away from the member.
    """
    parts = []
    # the ball, with its flats where the race is relieved
    bv, bf = mesh.revolve_closed(
        [(-r * 0.52, 0.0), (-r * 0.52, r * 0.62), (-r * 0.30, r * 0.92),
         (0.0, r), (r * 0.30, r * 0.92), (r * 0.52, r * 0.62),
         (r * 0.52, 0.0)], seg)
    parts.append((bv, bf))
    # the race around it
    parts.append(mesh.revolve_closed(
        [(-r * 0.56, r * 0.66), (r * 0.56, r * 0.66),
         (r * 0.56, r * 1.30), (r * 0.34, r * 1.42),
         (-r * 0.34, r * 1.42), (-r * 0.56, r * 1.30)], seg))
    # the two clevis cheeks either side of it
    for sgn in (-1.0, 1.0):
        cv, cf = mesh.revolve_closed(
            [(0.0, r * 0.42), (cheek, r * 0.42), (cheek, r * 1.34),
             (cheek * 0.4, r * 1.50), (0.0, r * 1.50)], seg)
        parts.append(([(px * sgn + sgn * r * 0.62, py, pz)
                       for (px, py, pz) in cv], cf))
        # and the pin through them
    parts.append(mesh.revolve_closed(
        [(-r * 1.34, 0.0), (r * 1.34, 0.0), (r * 1.34, r * 0.34),
         (r * 1.20, r * 0.46), (-r * 1.20, r * 0.46),
         (-r * 1.34, r * 0.34)], max(10, seg // 2)))
    # the threaded shank back into the member, with a lock nut on it
    parts.append(mesh.revolve_closed(
        [(-r * 2.30, 0.0), (-r * 0.60, 0.0), (-r * 0.60, r * 0.78),
         (-r * 1.05, r * 0.62), (-r * 1.30, r * 0.62),
         (-r * 1.30, r * 0.50), (-r * 2.30, r * 0.46)], seg))
    nv, nf = mesh.revolve_closed(
        [(-r * 1.72, r * 0.46), (-r * 1.36, r * 0.46),
         (-r * 1.36, r * 0.86), (-r * 1.72, r * 0.86)], 6)
    parts.append((nv, nf))
    v, f = mesh.join(*parts)
    # built along +x with the shank at -x; `direction` points outward
    return orient([(-px, py, pz) for (px, py, pz) in v], origin,
                  tuple(-d for d in direction)), f


def suspension_link(p0, p1, section, chord0, chord1=None, n_sta=9,
                    end_r=12.0, ends=(True, True), waist=0.90):
    """A suspension member: a faired leg with a rod end on each end.

    The leg is waisted in the middle -- the bending moment is at the ends, so
    that is where the section is deepest -- and it tapers, because the two
    ends do not carry the same load.
    """
    chord1 = chord0 if chord1 is None else chord1
    d = tuple(p1[k] - p0[k] for k in range(3))
    n = len(section)
    rings = []
    for j in range(n_sta):
        f = j / (n_sta - 1)
        # pull the leg in at both ends so the rod ends are proud of it
        g = 0.06 + 0.88 * f
        p = tuple(p0[k] + d[k] * g for k in range(3))
        c = (chord0 + (chord1 - chord0) * f) * (
            waist + (1.0 - waist) * abs(2 * f - 1) ** 1.5)
        rings.append([(p[0] + (u - 0.35) * c, p[1], p[2] + v * c)
                      for (u, v) in section])
    parts = [_loft_closed(rings)]
    if ends[0]:
        parts.append(rod_end(p0, tuple(-c for c in d), end_r))
    if ends[1]:
        parts.append(rod_end(p1, d, end_r))
    return mesh.join(*parts)


def rounded_polygon(pts, radii, seg=5):
    """Fillet the corners of a closed 2D polygon.

    A duct section, a bulkhead outline or a tunnel cross-section drawn as a
    rectangle is a rectangle however many stations you loft it through. Every
    one of these is a moulded shape with a radius in every corner, and the
    radius is not cosmetic: it is where the laminate can actually turn.
    """
    n = len(pts)
    if isinstance(radii, (int, float)):
        radii = [radii] * n
    out = []
    for i in range(n):
        p = pts[i]
        a = pts[i - 1]
        b = pts[(i + 1) % n]
        va = (a[0] - p[0], a[1] - p[1])
        vb = (b[0] - p[0], b[1] - p[1])
        la = math.hypot(*va) or 1.0
        lb = math.hypot(*vb) or 1.0
        ua = (va[0] / la, va[1] / la)
        ub = (vb[0] / lb, vb[1] / lb)
        cosang = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))
        ang = math.acos(cosang)
        if ang < 1e-6 or abs(math.pi - ang) < 1e-6 or radii[i] <= 0:
            out.append(p)
            continue
        # how far back along each leg the tangent points sit
        back = min(radii[i] / math.tan(ang / 2), la * 0.48, lb * 0.48)
        t0 = (p[0] + ua[0] * back, p[1] + ua[1] * back)
        t1 = (p[0] + ub[0] * back, p[1] + ub[1] * back)
        for k in range(seg + 1):
            u = k / seg
            # quadratic Bezier through the corner: a fillet in all but name
            out.append((
                (1 - u) ** 2 * t0[0] + 2 * (1 - u) * u * p[0] + u * u * t1[0],
                (1 - u) ** 2 * t0[1] + 2 * (1 - u) * u * p[1] + u * u * t1[1]))
    return out


def swept_profile(path, section, scale=None, subdiv=1, caps=True):
    """Sweep an arbitrary closed 2D section along a 3D path.

    `mesh.pipe` can only sweep a circle, so every structural member on this
    car that used it came out round: the halo pillar, the wing pylons, the
    side impact tubes. None of those are round. The pillar is a teardrop
    because it sits in the driver's forward view and has to be narrow in plan
    and deep in profile; a pylon is an aerofoil; a crash tube is an oval so it
    crushes progressively rather than buckling sideways.

    `section` is [(u, v), ...] in the plane normal to the path, and `scale`
    an optional per-path-point (su, sv).
    """
    if subdiv > 1 and len(path) >= 2:
        dense, sc = [], []
        for i in range(len(path) - 1):
            for k in range(subdiv):
                f = k / subdiv
                dense.append(tuple(path[i][j]
                                   + (path[i + 1][j] - path[i][j]) * f
                                   for j in range(3)))
                if scale:
                    sc.append(tuple(scale[i][j]
                                    + (scale[i + 1][j] - scale[i][j]) * f
                                    for j in range(2)))
        dense.append(tuple(path[-1]))
        if scale:
            sc.append(tuple(scale[-1]))
        path, scale = dense, (sc if scale else None)

    tangents = []
    for i in range(len(path)):
        if i == 0:
            t = [path[1][k] - path[0][k] for k in range(3)]
        elif i == len(path) - 1:
            t = [path[-1][k] - path[-2][k] for k in range(3)]
        else:
            t = [path[i + 1][k] - path[i - 1][k] for k in range(3)]
        tangents.append(mesh._normalise(t))

    seed = (0.0, 0.0, 1.0)
    if abs(sum(a * b for a, b in zip(seed, tangents[0]))) > 0.9:
        seed = (0.0, 1.0, 0.0)
    normal = mesh._normalise(mesh._cross(tangents[0], seed))

    # Pin the sign of the starting normal to a fixed rule.
    #
    # Parallel transport carries this first frame the whole way along the
    # path, so whatever the section's orientation is here, it is everywhere.
    # A cross product is orientation-reversing: mirror the path in y and the
    # normal comes out negated, not mirrored -- so a part and its twin get
    # their sections rotated 180 degrees relative to each other. That is why
    # the two rear wing pylons were 58 mm from being mirror images, with one
    # teardrop pointing forwards and the other back. Choosing the sign from
    # the geometry rather than from the cross product makes the frame
    # mirror-equivariant, because a reflection preserves the z and x
    # components this tests.
    for axis in ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        d = sum(a * b for a, b in zip(normal, axis))
        if abs(d) > 1e-9:
            if d < 0.0:
                normal = tuple(-c for c in normal)
            break

    n = len(section)
    verts = []
    for i, p in enumerate(path):
        t = tangents[i]
        d = sum(a * b for a, b in zip(normal, t))
        normal = mesh._normalise(tuple(normal[k] - d * t[k] for k in range(3)))
        binormal = mesh._cross(t, normal)
        su, sv = scale[i] if scale else (1.0, 1.0)
        for (u, v) in section:
            verts.append(tuple(p[k] + normal[k] * u * su + binormal[k] * v * sv
                               for k in range(3)))
    faces = []
    for i in range(len(path) - 1):
        a, b = i * n, (i + 1) * n
        for s in range(n):
            s2 = (s + 1) % n
            faces.append((a + s, a + s2, b + s2, b + s))
    if caps:
        faces.append(tuple(range(n - 1, -1, -1)))
        base = (len(path) - 1) * n
        faces.append(tuple(range(base, base + n)))
    return verts, faces


def teardrop_section(width, depth, n=30, tail=1.9):
    """A teardrop: round at the nose, drawn out to a point at the tail.

    This is the section a strut in a flow wants: it has the frontal area of
    the round tube it replaces and roughly a fifth of its drag, because the
    flow closes behind it instead of separating.
    """
    pts = []
    for i in range(n):
        u = i / n
        a = 2 * math.pi * u
        r = 1.0 - 0.5 * (1 - math.cos(a)) ** 0.5 * 0.0
        # parametrise nose-to-tail so the tail closes
        c = (1 - math.cos(a)) / 2.0                 # 0 at nose, 1 at tail
        thick = math.sin(a)
        pts.append((depth * (c * tail / (1 + (tail - 1) * c) - 0.32),
                    width * thick * (1 - c) ** 0.62 * 0.5))
    return pts


def _loft_ring_pairs(rings, closed=False):
    """Loft a sequence of equal-length rings; wrap the ends if `closed`."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    m = len(rings) if closed else len(rings) - 1
    for i in range(m):
        a, b = i * n, ((i + 1) % len(rings)) * n
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((a + j, a + j2, b + j2, b + j))
    return verts, faces


def volute(x_c, r_start, r_end, sect_r0, sect_r1, seg=48, sect=14, axis="x",
           hand=1.0):
    """A pump scroll: a passage whose area grows with the angle it has swept.

    A centrifugal pump housing is a spiral, not a cylinder -- the section has
    to get bigger as more flow joins it, or the impeller just churns. The step
    where the big end meets the small end is the cutwater.
    """
    rings = []
    for k in range(seg):
        f = k / seg
        # `hand` reverses the spiral. A scroll is chiral: its mirror image is
        # the opposite hand, so the left and right brake drums have to be
        # wound opposite ways or they are the same part twice, which is what
        # left them 2.8 mm from mirroring.
        a = 2 * math.pi * f * hand
        R = r_start + (r_end - r_start) * f
        rt = sect_r0 + (sect_r1 - sect_r0) * f
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for i in range(sect):
            ph = 2 * math.pi * i / sect
            rr = R + rt * math.sin(ph)
            ax = rt * math.cos(ph)
            if axis == "x":
                ring.append((x_c + ax, rr * ca, rr * sa))
            else:
                ring.append((rr * ca, rr * sa, x_c + ax))
        rings.append(ring)
    return _loft_ring_pairs(rings, closed=True)


def louvre_panel(at, x0, x1, u0, u1, n, h=12.0, lean=22.0, t=3.0, m=10,
                 base=1.0, skin=1.2, margin=10.0):
    """A louvred vent laid on a surface: a dark recess panel and a row of
    slats across the flow, each leaning aft, standing on it.

    `at(x, u, offset)` is a point on the surface at station x and cross
    parameter u (a clock angle, a height fraction -- whatever the surface
    is parameterised by), `offset` mm out from it. The slats span u0..u1 and
    stand at n stations from x0 to x1; the panel runs `margin` beyond them
    fore and aft.

    A louvre is a slot in a surface with a blade over it. The ones on this
    car were small bricks stuck on the skin along the flow, and from any
    distance they read as a scatter of thorns.
    """
    def slab(rows):
        # rows: [[outer..], [inner..]] per station -> a closed loft of
        # 4-point sections along u
        verts, faces = [], []
        k = len(rows[0])
        for ring in rows:
            verts.extend(ring)
        for i in range(len(rows) - 1):
            a, b = i * k, (i + 1) * k
            for j in range(k):
                j2 = (j + 1) % k
                faces.append((a + j, a + j2, b + j2, b + j))
        last = (len(rows) - 1) * k
        faces.append(tuple(range(k - 1, -1, -1)))
        faces.append(tuple(last + j for j in range(k)))
        return verts, faces

    parts = []
    xa, xb = x0 - margin, x1 + margin
    # the recess panel: a grid over the surface, not straight lines from end
    # to end, which on a curved cover sink into it in the middle
    nx = max(2, int((xb - xa) / 20.0))
    us = [u0 + (u1 - u0) * j / m for j in range(m + 1)]
    xs = [xa + (xb - xa) * i / nx for i in range(nx + 1)]
    lo = [[at(x, u, base) for u in us] for x in xs]
    hi = [[at(x, u, base + skin) for u in us] for x in xs]
    verts, faces = [], []
    W = m + 1

    def vid(layer, i, j):
        return layer * (nx + 1) * W + i * W + j
    for grid in (lo, hi):
        for row in grid:
            verts.extend(row)
    for i in range(nx):
        for j in range(m):
            faces.append((vid(1, i, j), vid(1, i + 1, j), vid(1, i + 1, j + 1),
                          vid(1, i, j + 1)))
            faces.append((vid(0, i, j + 1), vid(0, i + 1, j + 1),
                          vid(0, i + 1, j), vid(0, i, j)))
    for i in range(nx):                         # the two long edges
        for j in (0, m):
            faces.append((vid(0, i, j), vid(0, i + 1, j), vid(1, i + 1, j),
                          vid(1, i, j)))
    for j in range(m):                          # the two short ends
        for i in (0, nx):
            faces.append((vid(0, i, j), vid(0, i, j + 1), vid(1, i, j + 1),
                          vid(1, i, j)))
    parts.append((verts, faces))
    lx = h * math.tan(math.radians(lean))
    top = base + skin
    for i in range(n):
        x = x0 + (x1 - x0) * i / max(n - 1, 1)
        rows = []
        for j in range(m + 1):
            u = u0 + (u1 - u0) * j / m
            rows.append([at(x, u, top - 0.4), at(x + t, u, top - 0.4),
                         at(x + t + lx, u, top + h), at(x + lx, u, top + h)])
        parts.append(slab(rows))
    return mesh.join(*parts)
