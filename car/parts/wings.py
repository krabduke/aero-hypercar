"""Front and rear wings, endplates, pylons."""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common

FW = spec.FRONT_WING
RW = spec.REAR_WING


def build():
    out = {}
    out.update(_front())
    out.update(_rear())
    return out


def _front():
    """Four-element front wing, each element a separate lofted surface.

    The shape that matters is the spanwise one. Across the regulated neutral
    centre section the mainplane runs flat and almost unloaded; outboard of
    that it washes in to its tip incidence and rises towards the endplate, so
    the tip vortex is thrown outside the front tyre rather than into it.
    """
    out = {}
    half = FW["span"] / 2
    neutral = FW["neutral_half_w"]
    n_span = 15

    for k, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        stations = []
        tip = half * span_f
        for j in range(n_span):
            f = -1.0 + 2.0 * j / (n_span - 1)
            y = tip * f
            t = abs(y)
            # outboard fraction: 0 across the neutral section, 1 at the tip
            o = 0.0 if t <= neutral else (t - neutral) / max(tip - neutral, 1.0)
            o = o * o * (3 - 2 * o)          # smoothstep, so there is no crease
            chord = c_r + (c_t - c_r) * o
            aoa = aoa_r + (aoa_t - aoa_r) * o
            z = FW["z"] + dz + rise * o
            # The whole stack arches over the nose, not just the mainplane.
            # Arching element 0 alone closed the slot behind it: at the
            # centreline the mainplane rose 44 mm into a flap that had not
            # moved, leaving 12 mm between two surfaces that are 43 mm apart
            # everywhere else. The flaps follow the nose on a real car.
            z += FW["arch"] * max(0.0, 1.0 - (t / neutral) ** 2)
            stations.append((y, FW["x"] + dx, z, chord, aoa))
        name = "front_wing_main" if k == 0 else f"front_flap_{k}"
        out[name] = common.lofted_element(stations, thickness=0.085,
                                          camber=0.075)

    out.update(_front_endplates())

    # the Y250 vortex vanes either side of the neutral centre section
    vanes = []
    c = FW["chord"]
    for sgn in (-1.0, 1.0):
        # stand ON the mainplane's upper surface at the neutral-section edge,
        # not 80 mm above it where the arch has already fallen away
        z0 = FW["z"] + 10.0
        vx0 = FW["x"] + c * FW["y250_x0"]
        vx1 = FW["x"] + c * FW["y250_x1"]
        # This vane is the thing that makes the Y250 vortex: it is a cambered,
        # twisted aerofoil standing where the neutral section ends, and the
        # strength of what it sheds sets up the whole floor behind it. As a
        # flat card it shed nothing in particular.
        cam = [(vx0 + (vx1 - vx0) * i / 8.0,
                sgn * (neutral + 30.0 * (i / 8.0) ** 1.8)) for i in range(9)]
        vanes.append(shapes.turning_vane(
            cam, z0, z0 + FW["y250_h"], t=0.085, twist=sgn * -16.0,
            n_z=8, n_chord=24,
            top_cut=lambda u, z0=z0: z0 + FW["y250_h"] * (1.0 - 0.42 * u)))
    out["front_y250_vanes"] = mesh.join(*vanes)
    return out


def _front_endplates():
    """Endplate, footplate and dive planes.

    The endplate is not a flat card: its lower edge rolls outboard into a
    footplate, which is what actually turns the flow around the outside of the
    front tyre -- the single dirtiest thing on the car.
    """
    out = {}
    half = FW["span"] / 2
    x0 = FW["x"] + FW["endplate_x0"]
    x1 = FW["x"] + FW["endplate_x1"]
    z0 = 16.0
    t = FW["endplate_t"]
    fh = FW["footplate_h"]
    # The top edge follows the flap stack: low ahead of the mainplane, rising
    # over each flap in turn, so the plate encloses the elements instead of
    # standing past them as a rectangle.
    # the top edge follows the flap stack, which rises aft
    tops = [(0.00, z0 + 86.0), (0.22, z0 + 140.0), (0.48, z0 + 218.0),
            (0.74, z0 + FW["endplate_h"]), (1.00, z0 + FW["endplate_h"] - 34.0)]
    # Sampled finely rather than at the four levels and five stations that
    # made this a 40-vertex object: the footplate roll is a curve, and a
    # curve drawn through four points is a chamfer.
    n_lvl, n_f = 15, 21

    def top_at(f):
        for i in range(len(tops) - 1):
            if tops[i][0] <= f <= tops[i + 1][0]:
                (f0, z0_), (f1, z1_) = tops[i], tops[i + 1]
                u = (f - f0) / ((f1 - f0) or 1.0)
                u = u * u * (3 - 2 * u)                 # smooth, not kinked
                return z0_ + (z1_ - z0_) * u
        return tops[-1][1]

    plates, planes = [], []
    for sgn in (-1.0, 1.0):
        y = sgn * half
        rows = []
        # lower rows roll outboard into the footplate; the upper edge follows
        # `tops`, interpolated at the same chordwise stations
        for i in range(n_lvl):
            lvl = i / (n_lvl - 1)
            # the roll: outboard displacement dies away as the plate rises,
            # on a quarter-circle so the footplate meets the plate tangentially
            r = max(0.0, 1.0 - lvl / 0.42)
            dy = sgn * 46.0 * math.sqrt(max(0.0, 1.0 - (1.0 - r) ** 2))
            row = []
            for j in range(n_f):
                f = j / (n_f - 1)
                x = x0 + (x1 - x0) * f
                z_top = top_at(f)
                z_lo = z0 + fh * min(lvl / 0.30, 1.0)
                z = z_lo + (z_top - z_lo) * max(0.0, (lvl - 0.30) / 0.70)
                row.append((x, y + dy * (1.0 - 0.3 * f), z))
            rows.append(row)
        plate = _skin(rows, t, sgn, rim=2)
        # gills in the upper rear panel, bleeding the tyre wake outboard
        plate = mesh.join(plate, shapes.louvre_bank(
            x0 + (x1 - x0) * 0.52, x0 + (x1 - x0) * 0.94,
            y + sgn * (t / 2 + 5.0), z0 + fh + 96.0, z0 + FW["endplate_h"] - 30.0,
            4, 44.0, 13.0, t=3.0, cant=20.0))
        plates.append(plate)

        for k in range(FW["diveplanes"]):
            zz = z0 + fh + 40.0 + k * 62.0
            # a dive plane hangs off the outer face of the endplate; it must
            # stay inside the legal width, which half + span/2 did not
            planes.append(common.wing_element(
                FW["x"] + 30.0 + k * 40.0, zz, FW["diveplane_span"],
                160.0 - k * 30.0, 20.0 + k * 4.0,
                thickness=0.07, camber=0.09, n_span=4, taper=0.7,
                y0=sgn * (half + FW["diveplane_span"] / 2 + 6.0)))
    for i, m in enumerate(plates):
        out[f"front_endplate_{'lr'[i]}"] = m
    half = len(planes) // 2
    for i, m in enumerate(planes):
        out[f"front_diveplane_{'lr'[i // half]}{i % half + 1}"] = m
    return out


def _skin(rows, t, sgn, rim=0):
    """Give a grid of stations thickness in y, and close it into a solid.

    With `rim` the thickness falls to nothing over that many cells from the
    boundary, on a circular profile, so the two skins meet in a roll instead
    of a knife edge. Carbon is laid up over a radius; it cannot be brought to
    a point, and an edge that sharp chips the first time it touches a kerb.
    """
    nr, nc = len(rows), len(rows[0])

    def half_t(i, j):
        if not rim:
            return t / 2
        d = min(i, nr - 1 - i, j, nc - 1 - j) / float(rim)
        d = min(d, 1.0)
        return (t / 2) * math.sqrt(max(0.0, 1.0 - (1.0 - d) ** 2))

    inner = [(x, y - sgn * half_t(i, j), z)
             for i, row in enumerate(rows) for j, (x, y, z) in enumerate(row)]
    outer = [(x, y + sgn * half_t(i, j), z)
             for i, row in enumerate(rows) for j, (x, y, z) in enumerate(row)]
    verts = inner + outer
    off = len(inner)
    faces = []
    for i in range(nr - 1):
        for j in range(nc - 1):
            k = i * nc + j
            faces.append((k, k + 1, k + nc + 1, k + nc))
            faces.append((off + k, off + k + nc, off + k + nc + 1,
                          off + k + 1))
    for i in range(nr - 1):
        for j in (0, nc - 1):
            k = i * nc + j
            quad = ((k, k + nc, off + k + nc, off + k) if j == 0 else
                    (k + nc, k, off + k, off + k + nc))
            faces.append(quad)
    for j in range(nc - 1):
        for i in (0, nr - 1):
            k = i * nc + j
            quad = ((k + 1, k, off + k, off + k + 1) if i == 0 else
                    (k, k + 1, off + k + 1, off + k))
            faces.append(quad)
    return verts, faces


def rear_element(k):
    """(x, z, chord, aoa) for rear wing element k.

    spec.rear_elements() is the one definition, shared with aero/analyse.py
    and tools/tunnel_config.py so the mesh, the hinge table and both solvers
    are looking at the same wing.
    """
    return spec.rear_elements()[k]


def pivots():
    """Hinge lines for every element that moves.

    Each movable element pivots about its own leading edge, so a slider in the
    viewer changes the element's incidence exactly the way the real actuator
    would -- and the aero solver is fed the same angle.
    """
    out = {}
    for k, (dx, dz, c_r, c_t, span_f, aoa_r, aoa_t, rise) in enumerate(
            FW["stack"]):
        if k == 0:
            continue                      # the mainplane is fixed
        # on the centreline, where the whole stack is lifted by the arch
        out[f"front_flap_{k}"] = ((FW["x"] + dx, 0.0,
                                   FW["z"] + dz + FW["arch"]),
                                  (0.0, 1.0, 0.0), 1.0, "hinge")
    # the leading edge, not the quarter chord the element is placed by --
    # a DRS flap swings about its front spar
    x, z = spec.chord_point(*rear_element(1), 0.0)
    out["rear_flap"] = ((x, 0.0, z), (0.0, 1.0, 0.0), 1.0, "hinge")
    return out


def _rear():
    """Two-element rear wing on swan-neck pylons, shown in its loaded
    (non-DRS) position. The flap is its own object hinged at its leading edge,
    because it moves: this is the DRS element."""
    out = {}
    for k in range(RW["elements"]):
        x, z, chord, aoa = rear_element(k)
        el = common.wing_element(x, z, RW["span"], chord, aoa,
                                 thickness=0.10, camber=0.085, taper=0.95)
        out["rear_wing_main" if k == 0 else "rear_flap"] = el

    for i, sgn in enumerate((-1.0, 1.0)):
        out[f"rear_endplate_{'lr'[i]}"] = _rear_endplate(sgn)

    # swan-neck pylons: they meet the mainplane on its UPPER surface, so the
    # working (lower) surface is left completely undisturbed
    pylons = []
    for sgn in (-1.0, 1.0):
        # the top of the neck is put ON the mainplane's chord line, at the
        # quarter chord where the spar is, so the section closes round it --
        # a fixed offset from RW["z"] left it floating once the element was
        # rotated the right way up
        mx, mz = spec.chord_point(*spec.rear_elements()[0], 0.25)
        # only the top end follows the wing; the foot stays on the crash
        # structure where it always was
        path = [(mx, sgn * 150.0, mz),
                (mx - 60.0, sgn * 148.0, mz - 52.0),
                (RW["x"] - 70.0, sgn * 140.0, RW["z"] - 300.0),
                (RW["x"] - 200.0, sgn * 118.0, RW["z"] - 440.0)]
        # A swan neck is a wing section on edge: it is carrying the whole
        # rear wing load in bending and standing in the flow that feeds the
        # beam wing, so its own wake matters.
        t = RW["pylon_t"]
        pylons.append(shapes.swept_profile(
            path, shapes.teardrop_section(t * 1.7, t * 5.4, 26),
            scale=[(1.0, 1.0), (1.02, 1.05), (1.10, 1.16), (1.16, 1.24)],
            subdiv=6))
    for i, m in enumerate(pylons):
        out[f"rear_pylon_{'lr'[i]}"] = m

    # Endplate louvres, bleeding the pressure difference at the tip to cut the
    # tip vortex and the drag that comes with it. On the OUTER face of the
    # plate, stepping up and aft along the flap's trailing edge -- which is
    # where the pressure difference across the plate is largest, and which is
    # outboard of the wing rather than inside its tip.
    lv = []
    te_x, te_z = spec.chord_point(*spec.rear_elements()[-1], 1.0)
    for sgn in (-1.0, 1.0):
        y = sgn * (RW["span"] / 2 + 22.0)
        for k in range(5):
            lv.append(shapes.rounded_box(te_x - 250.0 + k * 52.0, y,
                               te_z - 60.0 + k * 22.0, 40.0, 14.0, 56.0))
    # louvres are individually cut slots, not one lump
    half = len(lv) // 2
    for i, m in enumerate(lv):
        out[f"rear_louvre_{'lr'[i // half]}{i % half + 1}"] = m

    out["rear_gurney"] = _gurney(1, height=17.0, t=2.2, foot_from=0.72)
    return out


def _gurney(k, height, t, foot_from, n_span=36, gap_end=14.0):
    """The gurney on element k, standing on that element's own trailing edge.

    A gurney is a lip perpendicular to the chord on the PRESSURE side, which
    on an inverted wing is the top. It works by parking a pair of counter-
    rotating vortices behind the trailing edge, which moves the rear
    stagnation point and loads the whole underside -- so where it sits and
    which way it faces is the entire point, and a box floated near the back
    of the wing is not one.

    It is built from the element's own section rather than placed by hand:
    the foot is the aerofoil surface from `foot_from` chord back to the
    trailing edge, laminated on at `t` thick and feathered out at its
    forward edge the way a bonded strip is.
    """
    import airfoil
    x0, z0, chord0, aoa = rear_element(k)
    tc, mc, taper = 0.10, 0.085, 0.95
    span = RW["span"]

    def surface(xc):
        """(u, v) on the pressure side -- the aerofoil's lower branch, which
        is uppermost once the section is inverted."""
        yt = airfoil.naca_thickness(xc, tc)
        yc, dyc = airfoil.camber_line(xc, mc)
        th = math.atan(dyc)
        return (xc + yt * math.sin(th), yc - yt * math.cos(th))

    # section in the chord frame (du along the chord, dv off the pressure
    # face), walked as a closed loop: foot underside aft, up the back of the
    # lip, over its radius, down the front, then the foot's outer face
    # forward again.
    n_foot, n_face, n_cap = 9, 4, 5

    def section(c):
        def at(xc, off=0.0):
            u, v = surface(xc)
            du, dv = (u - 0.25) * c, -v * c
            if off:
                e = 1e-3
                u1, v1 = surface(min(xc + e, 1.0))
                u0, v0 = surface(max(xc - e, 0.0))
                tu, tv = (u1 - u0) * c, -(v1 - v0) * c
                m = math.hypot(tu, tv) or 1.0
                du, dv = du - tv / m * off, dv + tu / m * off
            return (du, dv)

        loop = []
        for i in range(n_foot):                       # bonded face, fwd -> TE
            loop.append(at(foot_from + (1.0 - foot_from) * i / (n_foot - 1)))
        top = at(1.0, t)
        for i in range(1, n_face + 1):                # up the trailing face
            loop.append((top[0], top[1] + height * i / n_face))
        base = loop[-1]
        for i in range(1, n_cap):                     # radiused tip
            a = math.pi * i / n_cap
            loop.append((base[0] - t * math.sin(a), base[1] + t * 0.5 * (1 - math.cos(a))))
        for i in range(n_face - 1, 0, -1):            # down the front face
            loop.append((top[0] - t, top[1] + height * i / n_face))
        for i in range(n_foot):                       # outer face, TE -> fwd
            f = 1.0 - i / (n_foot - 1)
            xc = foot_from + (1.0 - foot_from) * f
            loop.append(at(xc, t * (0.12 + 0.88 * f ** 0.6)))
        return loop

    # same datum and the same direction of rotation as the element it stands
    # on -- see common.wing_element
    a = math.radians(aoa)
    ca, sa = math.cos(a), math.sin(a)
    verts, n_sec = [], None
    for j in range(n_span):
        f = j / (n_span - 1)
        y = -span / 2 + gap_end + (span - 2 * gap_end) * f
        c = chord0 * (1.0 - (1.0 - taper) * abs(y) / (span / 2))
        sec = section(c)
        n_sec = len(sec)
        for (du, dv) in sec:
            verts.append((x0 + 0.25 * c + du * ca - dv * sa, y,
                          z0 + du * sa + dv * ca))
    faces = []
    for j in range(n_span - 1):
        a0, b0 = j * n_sec, (j + 1) * n_sec
        for i in range(n_sec):
            i2 = (i + 1) % n_sec
            faces.append((a0 + i, a0 + i2, b0 + i2, b0 + i))
    faces.append(tuple(range(n_sec - 1, -1, -1)))
    base = (n_span - 1) * n_sec
    faces.append(tuple(range(base, base + n_sec)))
    return verts, faces


def _rear_endplate(sgn):
    """A rear endplate, cut to a profile rather than left as a rectangle.

    Its job is to stop the low pressure under the wing from being fed by air
    rolling round the tip. So: it runs well forward of the mainplane leading
    edge, it is cut away at the top rear where the tip vortex has already
    escaped and the plate is only drag, it rolls outboard along its trailing
    edge to push that vortex away from the diffuser, and the upper rear panel
    is louvred to bleed the pressure difference off gradually instead of
    letting it dump off the trailing edge in one go.
    """
    # Sized off the elements it encloses, not off RW["x"] + RW["chord"].
    # The flap is placed behind a slot now, so the stack ends 517 mm aft of
    # the mainplane leading edge and 227 mm above it -- a plate cut to the
    # mainplane's chord left the flap trailing edge hanging 61 mm out of the
    # back of it and 43 mm over the top.
    els = spec.rear_elements()
    le_x, le_z = spec.chord_point(*els[0], 0.0)
    te_x, te_z = spec.chord_point(*els[-1], 1.0)
    x0 = le_x - 130.0
    x1 = te_x + 96.0
    zt = te_z + 62.0
    zb = le_z - 215.0
    # control points round the perimeter, then a spline through them
    ctrl = [(x0 + 44.0, zb + 18.0),          # lower leading corner
            (x0 + 2.0, zb + 150.0),          # swept leading edge
            (x0 + 18.0, zt - 96.0),
            (x0 + 96.0, zt - 8.0),           # top leading corner
            (x1 - 150.0, zt),
            (x1 - 96.0, zt - 74.0),          # the cut-away at the top rear
            (x1 - 8.0, zt - 132.0),
            (x1 + 4.0, zb + 176.0),          # trailing edge
            (x1 - 30.0, zb + 40.0),
            (x1 - 118.0, zb - 4.0),          # lower trailing corner
            (x0 + 168.0, zb - 10.0)]
    outline = shapes.panel_outline(ctrl, subdiv=4)

    span = max(1.0, x1 - x0)

    def bow(fx, fz):
        # flat at the leading edge, rolling outboard towards the trailing one
        return sgn * 46.0 * max(0.0, fx - 0.35) ** 2 / 0.42

    y = sgn * (RW["span"] / 2 - 6.0)
    parts = [shapes.shaped_panel(outline, y, RW["endplate_t"], bow=bow,
                                 rim_seg=6, rim=1.15)]
    # No louvre bank here. The plate carries louvres in exactly this place
    # already, as rear_louvre_l1..5 and r1..5 -- built separately so each slot
    # is its own object in the viewer. Two sets in the same 240 mm of plate is
    # one set of louvres drawn twice.
    # the footplate that turns the plate into a diffuser fence
    foot = shapes.panel_outline(
        [(x0 + 180.0, y - sgn * 6.0), (x1 - 40.0, y - sgn * 10.0),
         (x1 - 60.0, y - sgn * 96.0), (x0 + 250.0, y - sgn * 72.0)], subdiv=3)
    fv, ff = shapes.shaped_panel(foot, zb - 6.0, 8.0, rim_seg=4, axis="z")
    parts.append((fv, ff))
    # mounting bosses where the mainplane and flap pick up
    # one on the mainplane spar, one on the flap's hinge line -- the two
    # places the plate actually picks the wing up
    for xz in (spec.chord_point(*els[0], 0.25),
               spec.chord_point(*els[-1], 0.0)):
        bv, bf = shapes.bolt_boss(0.0, 0.0, 0.0, 17.0, 16.0, 12)
        parts.append(([(pz + xz[0], y - sgn * px, py + xz[1])
                       for (px, py, pz) in bv], bf))
    return mesh.join(*parts)
