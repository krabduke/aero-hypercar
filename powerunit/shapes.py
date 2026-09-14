"""Shapes that are not boxes.

Nothing on an engine is a rectangular prism. A casting has draft so it will
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
    whole casting. Nothing is cast with a sharp edge: a corner that sharp is a
    stress raiser and a crack starter, and the mould could not fill it. Every
    edge gets a radius now, which is both correct and where most of this
    model's missing geometry was hiding.

    `r` is the radius on the vertical edges, `rz` the one top and bottom
    (defaults to r, clamped to fit).
    """
    r = max(0.2, min(r, sx / 2 - 0.05, sy / 2 - 0.05))
    rz = r if rz is None else rz
    rz = max(0.2, min(rz, sz / 2 - 0.05))
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    tan = math.tan(math.radians(draft))

    # vertical stations: a quarter-round at the bottom, the straight flank,
    # then a quarter-round at the top
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
    for i in range(n_fins):
        f = (i + 0.5) / n_fins
        # `side` puts the fin stack on the face that actually sees air: a
        # battery slung under the engine rejects heat downwards, and fins
        # pointing up into the crankcase are just a hidden slab
        zf = cz + side * (sz / 2 + fin_h / 2)
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
    n_st = 21
    for i in range(n_st):
        f = i / (n_st - 1)
        x = x0 + (x1 - x0) * f
        hw = hw0 + (hw1 - hw0) * f
        # the well is deepest around sump_x
        d = depth * (0.42 + 0.58 * math.exp(-((x - sump_x) / (sump_w)) ** 2))
        ring = []
        n_a = 40
        for k in range(n_a):
            a = 2 * math.pi * k / n_a
            ca, sa = math.cos(a), math.sin(a)
            p = 2.0 / 3.0
            y = hw * math.copysign(abs(ca) ** p, ca)
            z = (d / 2) * math.copysign(abs(sa) ** p, sa)
            ring.append((x, y, z_top - d / 2 + z))
        rings.append(ring)
    return _loft_closed(rings)


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


def bearing_shell(x, r_in, wall, width, arc_seg=40, chamfer=0.8,
                  groove=False, groove_w=5.0, groove_d=0.9, tang=True,
                  sgn=1.0):
    """One half of a plain bearing, the way a real shell is made.

    A shell is not a half-tube. It is a steel back with a thin lining, so
    every edge is chamfered where the lining is relieved; the upper half
    carries a circumferential oil groove fed from the block gallery; and there
    is a tang pressed out of the back at one parting face so it cannot spin in
    its housing. That detail is the whole reason the part is recognisable.

    `sgn` puts it above (+1) or below (-1) the journal.
    """
    hw = width / 2.0
    c = min(chamfer, wall * 0.35, hw * 0.25)
    r_o = r_in + wall
    sect = [(-hw + c, r_in)]
    if groove:
        g = groove_w / 2.0
        sect += [(-g - 0.6, r_in), (-g, r_in + groove_d),
                 (g, r_in + groove_d), (g + 0.6, r_in)]
    sect += [(hw - c, r_in), (hw, r_in + c),
             (hw, r_o - c), (hw - c, r_o),
             (-hw + c, r_o), (-hw, r_o - c), (-hw, r_in + c)]

    angles = [math.pi * i / arc_seg for i in range(arc_seg + 1)]
    if sgn < 0:
        angles.reverse()
    rings = []
    for a in angles:
        ca, sa = math.cos(a), math.sin(a)
        rings.append([(px + x, r * ca, sgn * r * sa) for (px, r) in sect])
    parts = [_loft_closed(rings)]

    if tang:
        # pressed out of the steel back at the parting face, sitting in its
        # notch in the housing
        parts.append(rounded_box(x, r_o + 0.7, sgn * (hw * 0.42),
                                 width * 0.34, 2.0, 3.2, 0.5, seg=4))
    return mesh.join(*parts)


def gear_ring(x0, x1, r_root, r_tip, n_teeth, r_bore, chamfer=1.2):
    """A toothed ring -- a starter ring gear, or a drive gear.

    Six points per tooth: root, up the flank, across the tip and back down,
    which is what a spur tooth looks like from the end. A smooth cylinder
    where the starter engages says nobody thought about starting it.
    """
    pts = []
    for t in range(n_teeth):
        a0 = 2 * math.pi * t / n_teeth
        p = 2 * math.pi / n_teeth
        for (f, r) in ((0.00, r_root), (0.16, r_root), (0.30, r_tip),
                       (0.50, r_tip), (0.64, r_root), (0.84, r_root)):
            a = a0 + p * f
            pts.append((r * math.cos(a), r * math.sin(a)))
    n = len(pts)
    bore = [(r_bore * math.cos(2 * math.pi * i / n),
             r_bore * math.sin(2 * math.pi * i / n)) for i in range(n)]

    verts, faces = [], []
    for (xx, ring, shrink) in ((x0, pts, 1.0), (x0 + chamfer, pts, 1.0),
                               (x1 - chamfer, pts, 1.0), (x1, pts, 1.0)):
        for (y, z) in ring:
            verts.append((xx, y * shrink, z * shrink))
    # the chamfer rings pull in slightly at the two outer stations
    for k in (0, 3):
        for i in range(n):
            (xx, y, z) = verts[k * n + i]
            verts[k * n + i] = (xx, y * 0.985, z * 0.985)
    for (xx, ring) in ((x0, bore), (x1, bore)):
        for (y, z) in ring:
            verts.append((xx, y, z))
    OD = [0, n, 2 * n, 3 * n]
    BI, BO = 4 * n, 5 * n
    for i in range(n):
        j = (i + 1) % n
        for k in range(3):                       # outside, through the face
            a, b = OD[k], OD[k + 1]
            faces.append((a + i, a + j, b + j, b + i))
        faces.append((BI + j, BI + i, OD[0] + i, OD[0] + j))     # front face
        faces.append((OD[3] + j, OD[3] + i, BO + i, BO + j))     # rear face
        faces.append((BI + i, BI + j, BO + j, BO + i))           # bore
    return verts, faces


def core(cx, cy, cz, sx, sy, sz, n_plates=12, r=3.0, gap=1.4, axis="x",
         side_ties=2):
    """A stacked-plate heat-exchanger core: an oil cooler and an
    air-to-water charge cooler are both this -- a pack of thin plates with a
    gap between each so the two fluids alternate, clamped between end bars.

    The plate pack is what makes it read as a cooler. A smooth box says a
    brick was bolted where a core should be.
    """
    parts = []
    span = sx if axis == "x" else sy
    thick = span / (n_plates * (1.0 + gap))
    for i in range(n_plates):
        f = (i + 0.5) / n_plates
        off = -span / 2 + span * f
        if axis == "x":
            parts.append(rounded_box(cx + off, cy, cz, thick, sy * 0.94,
                                     sz * 0.92, r=min(r, thick * 1.6), seg=4))
        else:
            parts.append(rounded_box(cx, cy + off, cz, sx * 0.94, thick,
                                     sz * 0.92, r=min(r, thick * 1.6), seg=4))
    # tie bars clamp the pack at each end
    for s in (1.0, -1.0):
        if axis == "x":
            parts.append(rounded_box(cx, cy + sy * 0.5 * s, cz + sz * 0.5 * s,
                                     sx * 1.04, thick * 2.2, thick * 2.2, 1.2,
                                     seg=4))
        else:
            parts.append(rounded_box(cx + sx * 0.5 * s, cy, cz + sz * 0.5 * s,
                                     thick * 2.2, sy * 1.04, thick * 2.2, 1.2,
                                     seg=4))
    return mesh.join(*parts)


def volute(x_c, r_start, r_end, sect_r0, sect_r1, seg=48, sect=14, axis="x"):
    """A pump scroll: a passage whose area grows with the angle it has swept.

    A centrifugal pump housing is a spiral, not a cylinder -- the section has
    to get bigger as more flow joins it, or the impeller just churns. The step
    where the big end meets the small end is the cutwater.
    """
    rings = []
    for k in range(seg):
        f = k / seg
        a = 2 * math.pi * f
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
