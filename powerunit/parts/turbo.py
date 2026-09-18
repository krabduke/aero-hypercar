"""Twin turbochargers in the vee, their wastegates and the tailpipes.

Hot vee: the exhaust ports face inward into the vee and the turbos sit between
the banks. It makes the shortest possible path from port to turbine, which is
what the transient response depends on, and it keeps the outside of the engine
cold so the car's bodywork can be tight around it.

A turbocharger was two discs on a tube here -- `_housing` lathed a rectangle
into a cylinder and called it a volute, twice, with a plain cylinder stuck on
the side for a wastegate, all merged into one object named `turbos`. A
turbocharger is the one part of this engine whose shape IS its function: the
turbine passage tightens as it goes so the gas keeps its velocity round to the
cutwater, the compressor passage opens as it goes because more flow joins it
every degree, and both of those are visible from across a room. Drawn as
cylinders they are decoration.

So both housings are built on the spirals gaspath.py declares -- the same
spirals the flow animation runs down -- and the rest of the turbocharger is
here too: the bearing housing between them with its oil feed and drain, the
V-band clamps that hold the three pieces together, an external wastegate with
its actuator and dump pipe, and the inlet each compressor breathes through.
Without that last one the engine had no air source at all.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes

SM = spec.RES["small_revolve"]
import gaspath
from parts import common

T = spec.TURBO
E = spec.EXHAUST
SEG = spec.RES["revolve"]

# Numbered, not sided: these two are fore and aft of each other on the
# engine's centreline, so _l / _r would claim a mirror in y that does not
# exist -- and the structure audit checks exactly that claim. They pair
# with collector_1 and collector_2, which were already numbered.
SIDES = ((0, "1"), (2, "2"))          # bank_pair used to select the turbo


def build():
    out = {}
    out.update(_housings())
    out.update(_centres())
    out.update(_wastegates())
    out.update(_oil())
    out.update(_inlets())
    # `_manifolds` built a second complete set of exhaust primaries --
    # eight more pipes from the same eight ports to the same two turbines,
    # on a different route, by a module that had never heard of the first
    # set. The surviving set is `primary_1..8` in plumbing.py, which is per
    # cylinder, carries its own flange, and is drawn on the centreline
    # `gaspath.primary_path` declares, so the viewer's flow animation runs
    # down the pipe that is actually there.
    out.update(_tailpipes())
    return out


# --------------------------------------------------------------------------
# the volutes
# --------------------------------------------------------------------------

def _scroll(points, radii, sect=16, wall=None, zc=0.0):
    """Loft a circular section of varying radius along a spiral.

    The section lies in the plane containing the shaft axis and the local
    radius, which is what makes a scroll a scroll rather than a bent tube:
    it is a passage wrapped round a wheel, so its section stands up out of
    the plane of the spiral.

    `zc` is the height of that shaft axis. It is not optional in practice:
    the radius has to be measured from the axis the spiral is drawn about,
    and these spirals are drawn about z = T["z"] = 255. Measured from z = 0
    instead, every section stood within 12 degrees of vertical all the way
    round -- so the section never rotated with the spiral, and round the
    bottom of the volute it leaned inwards, into the wheel the volute is
    wrapped round. Station 6 of the turbine wanted (+0.50, -0.87), down and
    outboard, and got (+0.13, +0.99), which is very nearly straight up.
    """
    rings = []
    for (p, r) in zip(points, radii):
        x, y, z = p
        m = math.hypot(y, z - zc) or 1.0
        uy, uz = y / m, (z - zc) / m     # outward radial direction
        ring = []
        for i in range(sect):
            a = 2 * math.pi * i / sect
            ca, sa = math.cos(a), math.sin(a)
            rr = r if wall is None else r + wall
            ring.append((x + rr * ca, y + rr * sa * uy, z + rr * sa * uz))
        rings.append(ring)
    return rings


def _loft_open(rings):
    """Join a stack of rings, capped at both ends."""
    n = len(rings[0])
    verts = [v for r in rings for v in r]
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for s in range(n):
            s2 = (s + 1) % n
            faces.append((a + s, a + s2, b + s2, b + s))
    faces.append(tuple(range(n - 1, -1, -1)))
    base = (len(rings) - 1) * n
    faces.append(tuple(range(base, base + n)))
    return verts, faces


def _housings():
    """Turbine and compressor volutes, each on its declared spiral."""
    out = {}
    for pair, tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)

        # ---- turbine: the passage tightens all the way to the cutwater ----
        sc = gaspath.turbine_scroll(pair)
        pts = [p for (p, _r) in sc]
        rad = [r for (_p, r) in sc]
        parts = [_loft_open(_scroll(pts, rad, 18, zc=T["z"]))]
        # the exhaust-side face closes the scroll onto the wheel: a disc
        # standing inboard of it, bored for the outlet
        # the back plate faces the bearing housing, the snout faces out
        parts.append(_backplate(pts[0][0] + ib * 2.0, _footprint(sc),
                                T["shaft_r"] * 3.4, ib * 9.0))
        # The shroud: the wall that runs over the blade tips, from the
        # volute's tongue to the exducer face, and then in to the outlet.
        #
        # Without it the housing was a spiral tube and a disc with a wheel
        # spinning in open air between them, which is why the blades were
        # visible from outside and why the outlet, bored at 34 against a
        # 39.7 mm tip, could be bolted straight through them. `EXPECTED`
        # carried ("turbine_housing", "turbine_wheel") to keep the audit
        # quiet about it -- a permission standing in for the one surface
        # that makes a turbine housing a housing.
        depth = gaspath.turbine_wheel_depth()
        sh = T["turb_r"] * T["turb_wheel_frac"] + T["wheel_tip_clear"]
        x0 = pts[0][0]
        prof = [(x0, sh), (x0 - ib * depth, sh),
                (x0 - ib * (depth + 12.0), 34.0),
                (x0 - ib * (depth + 12.0), 40.0),
                (x0 - ib * depth, sh + 6.0), (x0, sh + 6.0)]
        if ib < 0:
            prof = list(reversed(prof))
        sv, sf = mesh.revolve_closed(prof, SEG // 2)
        parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in sv], sf))
        # the outlet snout, axial, which is where a radial turbine
        # discharges -- starting where the blades stop, not inside them
        parts.append(_snout(x0 - ib * (depth + 12.0), -ib, 34.0, 30.0, 26.0))
        # inlet flange, standing off the first section of the spiral
        parts.append(_flange_at(pts[0], (pts[0][0], pts[0][1] * 1.7,
                                         pts[0][2] * 1.0 + 26.0),
                                rad[0], 8.0, 11.0))
        out[f"turbine_housing_{tag}"] = mesh.join(*parts)

        # ---- compressor: the passage opens as more flow joins it ----------
        cs = gaspath.compressor_scroll(pair)
        pts = [p for (p, _r) in cs]
        rad = [r for (_p, r) in cs]
        parts = [_loft_open(_scroll(pts, rad, 18, zc=T["z"]))]
        parts.append(_backplate(pts[0][0] - ib * 2.0, _footprint(cs),
                                T["shaft_r"] * 3.2, -ib * 8.0))
        # and the shroud over this wheel too, eye to exducer. Without it the
        # inlet duct and the charge pipe both ran through the blades, and
        # EXPECTED carried a permission for each.
        depth_c = T["comp_r"] * T["comp_wheel_frac"] * T["wheel_depth_frac"]
        shc = T["comp_r"] * T["comp_wheel_frac"] + T["wheel_tip_clear"]
        x0c = pts[0][0]
        prof = [(x0c, shc), (x0c + ib * depth_c, shc),
                (x0c + ib * depth_c, shc + 6.0), (x0c, shc + 6.0)]
        if ib > 0:
            prof = list(reversed(prof))
        cv, cf = mesh.revolve_closed(prof, SEG // 2)
        parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in cv], cf))
        # The eye: a bellmouth on the axis, which is the only way in.
        #
        # At the eye PLANE, pointing away from the wheel. The volute wraps the
        # exducer, and the eye is a wheel's length inboard of it -- the snout
        # was starting 10 mm inboard of the volute and running 37 mm further,
        # which is straight down the middle of the wheel. And its bore has to
        # be the inducer's shroud line: at r 30 against a wheel whose tip is
        # at 38.3 the inlet duct's own wall was inside the blades.
        r_eye = T["comp_r"] * T["comp_wheel_frac"] + T["wheel_tip_clear"]
        eye = pts[0][0] + ib * (T["comp_wheel_len"] + 2.0)
        parts.append(_snout(eye, ib, r_eye, r_eye + 4.0, r_eye))
        # and the outlet the charge pipe bolts to
        last = pts[-1]
        parts.append(_flange_at(last,
                                (last[0], last[1] * 1.6, last[2]),
                                rad[-1], 7.0, 10.0))
        out[f"compressor_housing_{tag}"] = mesh.join(*parts)
    return out


def _footprint(scroll):
    """How far out the volute actually reaches, from the shaft axis.

    The backplate is the face the volute closes onto, so it has to be at
    least as big as the volute. Both plates were sized off the housing
    constant instead -- 0.98 of turb_r and of comp_r -- and both volutes
    stood proud of their own backplate, the turbine by 21 mm and the
    compressor by 16. Measuring the spiral cannot disagree with the spiral.
    """
    return max(math.hypot(y, z - T["z"]) + r for ((_x, y, z), r) in scroll)


def _backplate(x, r_out, r_bore, t):
    """The flat face a volute closes onto, bored for the wheel."""
    v, f = mesh.revolve_closed(
        [(x, r_bore), (x + t, r_bore), (x + t, r_out), (x, r_out)], SEG // 2)
    return [(px, py, pz + T["z"]) for (px, py, pz) in v], f


def _snout(x, dirn, r_in, r_out, r_lip):
    """The axial stub on a housing face: turbine outlet, compressor eye."""
    L = 30.0
    prof = [(x, r_in), (x + dirn * L * 0.45, r_in * 0.96),
            (x + dirn * L, r_out), (x + dirn * (L + 7.0), r_out),
            (x + dirn * (L + 7.0), r_lip), (x + dirn * L, r_lip),
            (x + dirn * L * 0.45, r_in * 0.96 - 4.0), (x, r_in - 4.0)]
    if dirn < 0:
        prof = list(reversed(prof))
    v, f = mesh.revolve_closed(prof, SEG // 2)
    return [(px, py, pz + T["z"]) for (px, py, pz) in v], f


def _duct_frame(at, towards):
    """(origin, axis, and two perpendiculars) for something on a duct end."""
    d = [towards[k] - at[k] for k in range(3)]
    m = math.dist(at, towards) or 1.0
    d = [c / m for c in d]
    up = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (0.0, 1.0, 0.0)
    n1 = mesh._normalise(mesh._cross(d, up))
    n2 = mesh._cross(d, n1)

    def place(verts):
        return [(at[0] + d[0] * px + n1[0] * py + n2[0] * pz,
                 at[1] + d[1] * px + n1[1] * py + n2[1] * pz,
                 at[2] + d[2] * px + n1[2] * py + n2[2] * pz)
                for (px, py, pz) in verts]

    return place


def _flange_at(at, towards, r, thick, pad):
    """A bolted flange standing normal to the duct it terminates."""
    place = _duct_frame(at, towards)
    v, f = mesh.revolve_ring(
        [(0.0, r), (0.0, r + pad), (thick, r + pad), (thick, r)], SM)
    return (place(v), f)


# --------------------------------------------------------------------------
# what holds the two halves together
# --------------------------------------------------------------------------

def _centres():
    """The bearing housing: the part that makes a turbocharger one machine.

    It carries the shaft on two journal bearings and a thrust face, takes oil
    in at the top under gallery pressure and drains it out of the bottom under
    gravity -- which is why a turbo has to sit above the sump line -- and is
    water-jacketed so it does not coke the oil when the engine is shut down
    hot. Every one of those shows on the outside as a boss.
    """
    out = {}
    for pair, tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)
        hw = T["housing_w"] * 0.6
        r = T["shaft_r"]
        parts = []
        # the housing itself: waisted in the middle, flanged at both ends
        prof = [(tx - hw + 4.0, r * 1.25), (tx - hw + 4.0, r * 3.6),
                (tx - hw + 12.0, r * 3.2), (tx - 6.0, r * 2.5),
                (tx + 6.0, r * 2.5), (tx + hw - 12.0, r * 3.2),
                (tx + hw - 4.0, r * 3.6), (tx + hw - 4.0, r * 1.25)]
        # 28 segments, not 48: this is a 55 mm casting between two
        # housings, and it was carrying 14,000 vertices of its own
        v, f = mesh.revolve_ring(prof, SM)
        parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in v], f))
        # oil in at the top, out at the bottom, water across the middle
        # Oil in at the side, out of the bottom. The feed boss is normally on
        # top; here the exhaust collector passes directly over the bearing
        # housing on its way to the turbine, so a line coming down onto a top
        # boss would come down through it.
        fv, ff = mesh.revolve_ring(
            [(0.0, 4.0), (0.0, 9.0), (26.0, 9.0), (26.0, 12.0),
             (32.0, 12.0), (32.0, 4.0)], SM)
        # straight down, beside the drain. There is nowhere else: above the
        # bearing housing is the collector, on the bank side the compressor's
        # own outlet and the charge pipe leaving it, on top the wastegate
        # canister -- and out to either side the exhaust flange strips run
        # the length of the vee from y = 16 to y = 77.
        parts.append(([(pz + tx - 13.0, py, -px + T["z"] - r * 2.4)
                       for (px, py, pz) in fv], ff))
        dv, df = mesh.revolve_ring(
            [(0.0, 8.0), (0.0, 13.0), (20.0, 13.0), (20.0, 17.5),
             (26.0, 17.5), (26.0, 8.0)], SM)
        parts.append(([(pz + tx + 13.0, py, -px + T["z"] - r * 2.4)
                       for (px, py, pz) in dv], df))
        # and the water jacket unions, one each side
        for s2 in (-1.0, 1.0):
            wv, wf = mesh.revolve_ring(
                [(0.0, 4.0), (0.0, 7.5), (13.0, 7.5), (13.0, 4.0)], SM)
            parts.append(([(pz + tx + s2 * 18.0, s2 * px * 0.0 + py,
                            s2 * 0.0 + px + T["z"] + r * 2.2)
                           for (px, py, pz) in wv], wf))
        # the V-band clamps, one at each joint
        for x in (tx - hw + 2.0, tx + hw - 2.0):
            cv, cf = mesh.ring_torus(x, r * 3.9, 3.6, 18, 8)
            parts.append(([(px, py, pz + T["z"]) for (px, py, pz) in cv], cf))
        out[f"turbo_centre_{tag}"] = mesh.join(*parts)
    return out


# --------------------------------------------------------------------------
# boost control
# --------------------------------------------------------------------------

def _wastegates():
    """Boost control, and the reason the engine can be told not to make any.

    Internal, not external. This vee has no room for a pair of 40 mm gates
    and their dump pipes: every place one will fit is already carrying a
    primary climbing out of a head, a collector, or a tailpipe. An internal
    gate is a flap in the turbine housing that lets gas past the wheel
    straight into the outlet, opened by a rod off a diaphragm canister
    mounted on the cold side -- which is where the boost reference it is
    listening to comes from.

    So what is modelled is what you can see of one: the canister, its bracket,
    the rod, and the crank arm on the turbine housing the rod pulls.
    """
    out = {}
    for pair, tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)
        # the canister sits on the compressor housing, out of the exhaust's way
        cx = tx + ib * T["housing_w"] * 0.6
        # Above the MGU-H, which is a 64 mm rotor on the shaft reaching to
        # z + 32. At z + 26 the canister's lower cap and its bracket were
        # inside it.
        # Above the MGU-H, which is a 64 mm rotor on the shaft reaching to
        # z + 32, and below the primary that climbs past at z 333.
        # In the 35 mm of clear air between the compressor wheel, whose tip
        # reaches z 293, and the primary that climbs past at z 333.
        cy, cz = -sgn * 44.0, T["z"] + 42.0
        parts = []
        # 27 mm tall, not 31. There are 40 mm between the compressor wheel's
        # tip at z 293 and the primary that climbs past at 328, and a can that
        # fills all but nine of them has nowhere to sit.
        for (z0, z1, rr) in ((0.0, 4.0, 26.0), (4.0, 22.0, 30.0),
                             (22.0, 27.0, 26.0)):
            v, f = mesh.revolve_open(
                [(z0, 0.0), (z0, rr), (z1, rr), (z1, 0.0)],
                SM, cap_start=True, cap_end=True)
            parts.append(([(pz + cx, py + cy, px + cz)
                           for (px, py, pz) in v], f))
        # The reference nipple, out of the SIDE of the cap.
        #
        # There is 40 mm between the compressor wheel's tip at z 293 and the
        # primary climbing past at 333, and the canister is 31 of it. A nipple
        # standing 13 mm off the top of it does not fit in the 9 that are
        # left; out of the side it does, and that is where the boost line
        # would come off anyway.
        nv, nf = mesh.revolve_open(
            [(0.0, 0.0), (0.0, 3.2), (13.0, 3.2), (13.0, 0.0)],
            14, cap_start=True, cap_end=True)
        parts.append(([(pz + cx, -sgn * px + cy - sgn * 26.0, py + cz + 20.0)
                       for (px, py, pz) in nv], nf))
        # the bracket that holds it off the housing
        parts.append(shapes.rounded_box(cx, cy * 0.72, cz + 4.0,
                                        10.0, abs(cy) * 0.56, 18.0, r=2.0))
        # the rod down to the crank arm on the turbine housing, and the arm
        arm = (tx - ib * (T["housing_w"] * 0.6 + 4.0), -sgn * 30.0,
               T["z"] + 38.0)
        parts.append(mesh.pipe([(cx, cy, cz - 2.0),
                                (cx - ib * 20.0, cy * 0.92, cz - 10.0),
                                arm], 3.0, 12, subdiv=3))
        av, af = mesh.revolve_closed(
            [(0.0, 0.0), (7.0, 0.0), (7.0, 9.0), (0.0, 9.0)], 14)
        parts.append(([(pz + arm[0], py + arm[1], px + arm[2])
                       for (px, py, pz) in av], af))
        out[f"wastegate_{tag}"] = mesh.join(*parts)
    return out


def _oil():
    """Feed into the top of the bearing housing, drain out of the bottom.

    Short lines, both of them inside the vee, because that is where the
    fittings are: a hot-vee block carries its turbo oil unions on the vee
    faces, a few inches under the turbocharger. They were routed round the
    outside of the engine before, which took the feed line through both
    cylinder heads, a fuel rail, a valve spring and the top compression ring
    of number two piston.

    The drain is the fatter of the two and leaves the bottom, because oil
    comes out of a turbocharger under nothing but gravity.
    """
    out = {}
    for pair, tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)
        r = T["shaft_r"]
        top = (tx - 13.0, 0.0, T["z"] - r * 2.4 - 32.0)
        bot = (tx + 13.0, 0.0, T["z"] - r * 2.4 - 26.0)
        # straight up the station the bearing housing is on: the gap between
        # the two volutes is eight millimetres wide and it is the only
        # vertical corridor there is
        # Both straight down the vee's own centreline: the exhaust flange
        # strips run the length of the vee from y = 16 to y = 77 on each
        # side, so the 32 mm between them is the only gap there is.
        # ... and down to z 122, which is in the block's vee face. They
        # stopped at 150, which is 122 mm of clear air above the union they
        # are described as screwing into: both lines, on both turbos, ended
        # in space with a boss on the end of them.
        vee = spec.BLOCK["vee_face_z"]
        feed = [(tx - 13.0, 0.0, vee), top]
        drain = [bot, (tx + 13.0, 0.0, vee)]
        parts = [mesh.pipe(feed, 5.0, spec.RES["pipe"], subdiv=4),
                 mesh.pipe(drain, 9.0, spec.RES["pipe"], subdiv=4)]
        # the union at each end that screws into the block
        for (at, rr) in ((feed[0], 7.0), (drain[-1], 11.0)):
            bv, bf = mesh.revolve_closed(
                [(0.0, 0.0), (9.0, 0.0), (9.0, rr * 1.5), (5.0, rr * 1.7),
                 (0.0, rr * 1.5)], 14)
            parts.append(([(pz + at[0], py + at[1], px + at[2])
                           for (px, py, pz) in bv], bf))
        out[f"turbo_oil_{tag}"] = mesh.join(*parts)
    return out


def _bored_duct(path, r_out, wall, seg, subdiv):
    """A duct with a hole down it, as one watertight surface.

    Two swept tubes, the inner one turned inside out, stitched to each other
    at both ends. They share a path and a segment count, so their rings
    correspond one for one and the two end rings close into an annulus -- the
    part is a single closed surface with a bore, not two shells that happen to
    touch.

    Joining two capped pipes would have been easier and is what was here: the
    cap on the open end was a flat disc 60 mm across sitting in the middle of
    the flange, and it read in every render as a blank white circle stuck on
    the front of the engine rather than as the mouth of an intake.
    """
    ov, of = mesh.pipe(path, r_out, seg, caps=False, subdiv=subdiv)
    iv, if_ = mesh.pipe(path, [r - wall for r in r_out], seg,
                        caps=False, subdiv=subdiv)
    n = len(ov)
    ns = mesh._T(seg)
    rings = n // ns
    verts = list(ov) + list(iv)
    # the inner wall faces into the bore, so its winding is reversed
    faces = [tuple(f) for f in of]
    faces += [tuple(i + n for i in reversed(f)) for f in if_]
    for base, first in (((rings - 1) * ns, False), (0, True)):
        for k in range(ns):
            a0, a1 = base + k, base + (k + 1) % ns
            b0, b1 = a0 + n, a1 + n
            faces.append((a0, b0, b1, a1) if first else (a0, a1, b1, b0))
    return verts, faces


def _inlets():
    """What each compressor breathes through.

    There was nothing here: the compressors drew from a sealed vee. The engine
    ends at a flange -- the car supplies the airbox behind it -- so this is the
    bellmouth, a short trunk turning up out of the vee, and the flange the
    car's ducting bolts to.
    """
    out = {}
    for pair, tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)
        eye = gaspath.compressor_path(pair)[0]
        # up and out to its own side. The two eyes face each other across the
        # middle of the vee 41 mm apart, so a duct that carried straight on
        # would run into the other one.
        # near enough vertical: the two banks' primaries climb the vee at
        # y = +-85, so a duct that leans out at all lands in one of them
        # This duct overhangs the wheel's inducer, and it is not a local
        # fault. The compressor eyes face each other across the middle of
        # the vee 29 mm apart, so each duct has to turn upward within a
        # couple of centimetres of its own eye plane -- which puts its first
        # ring at about 70 degrees to the shaft, reaching out over blades
        # whose tips are 2.2 mm away. Measured: fifteen of its 9824 vertices
        # end up inside the wheel.
        #
        # Three ways out were tried and all of them cost more than they
        # bought. Moving the duct outboard of the wheel moves it towards the
        # other turbo's duct and the two collide instead (40%). Sizing the
        # bore to the eye it bolts to, which is the right thing on its own
        # terms, makes both ducts big enough to thread through each other
        # over their whole height (204 vertices, the full run from z 243 to
        # 380). Belling only the mouth halves the wheel overlap and still
        # leaves the ducts touching at 42%.
        #
        # What is actually wrong is the clocking: two compressors breathing
        # from the same 29 mm of vee. That is a layout decision in
        # `turbo_side`, not a fix to this function, so this stays as it is
        # and the permission below says what it is covering.
        path = [(eye[0] - ib * 8.0, 0.0, T["z"]),
                (eye[0] + ib * 2.0, sgn * 8.0, T["z"] + 30.0),
                (eye[0] - ib * 2.0, sgn * 22.0, T["z"] + 72.0),
                (eye[0] - ib * 8.0, sgn * 30.0, T["z"] + 106.0)]
        # A duct with a bore, not a capped rod.
        #
        # mesh.pipe caps both ends, so this finished in a flat disc 60 mm
        # across sitting in the middle of the flange -- a blank white circle
        # in every render, reading as a sticker rather than the mouth of an
        # intake. Two walls with a bore between them, closed by a ring at the
        # compressor end and by the flange at the other, so the part is still
        # watertight and you can see down it.
        wall = 4.0
        r_out = [26.0, 27.0, 29.0, 30.0]
        parts = [_bored_duct(path, r_out, wall, spec.RES["pipe"], 5)]
        r_in = [r - wall for r in r_out]
        end = (path[-1][0] + (path[-1][0] - path[-2][0]),
               path[-1][1] + (path[-1][1] - path[-2][1]),
               path[-1][2] + (path[-1][2] - path[-2][2]))
        parts.append(_flange_at(path[-1], end, r_in[-1], 8.0,
                                r_out[-1] - r_in[-1] + 11.0))
        # the radius round the mouth, and the bolts the car's ducting picks up
        place = _duct_frame(path[-1], end)
        tv, tf = mesh.ring_torus(0.0, r_in[-1] + 2.2, 2.2, SM, 10)
        # _duct_frame maps (axial, y, z) onto the duct, and everything the
        # lathe makes already has its axis along x -- so the offset goes on
        # px. Putting it on pz stood the ring on edge, as a blade across the
        # mouth of the pipe.
        parts.append((place([(px + 8.0, py, pz) for (px, py, pz) in tv]), tf))
        n_bolt = 8
        for k in range(n_bolt):
            a = 2.0 * math.pi * k / n_bolt
            rb = r_out[-1] + 5.5
            bv, bf = mesh.cylinder(0.0, 5.0, 4.2, 12)
            parts.append((place([(px + 8.0, py + rb * math.cos(a),
                                  pz + rb * math.sin(a))
                                 for (px, py, pz) in bv]), bf))
        out[f"compressor_inlet_{tag}"] = mesh.join(*parts)
    return out


def _tailpipes():
    """The elbow off each turbine, out to the flange the car's exhaust bolts to.

    This is where the engine ends. It used to carry a full exhaust system --
    two pipes running the length of the engine to a common exit behind the
    gearbox -- and there is nowhere for them to run: outboard of the vee is
    cam cover from y = 145 to 245, inboard of that the eight primaries climb
    out of the heads at y = 90, above them the collectors and the heat
    shields, and the charge pipes cross the whole of it on their way to the
    plenums. Every route tried went through one of those, and the last one
    also went through the car's engine-cover louvres.

    A radial turbine discharges along its own axis, so each one gets the
    elbow that turns that discharge outboard and up over the cam cover, and a
    V-band flange on the end. What happens after that is the car's problem,
    which is correct:
    this engine goes in a car that already builds its own exhaust exit.
    """
    parts = []
    for pair, _tag in SIDES:
        _, tx, sgn, ib = gaspath.turbo_side(pair)
        out_pt = gaspath.turbine_path(pair)[-1]
        d = -ib                         # away from the middle of the engine
        # out and very slightly up: the crankcase breathers stand to z = 247
        # under the front of it and the cam sensor to 248 under the back
        path = [out_pt,
                (out_pt[0] + d * 26.0, sgn * 26.0, T["z"] + 8.0),
                (out_pt[0] + d * 46.0, sgn * 62.0, T["z"] + 18.0),
                (out_pt[0] + d * 58.0, sgn * 88.0, T["z"] + 26.0)]
        # bored, not capped: this is the end of the exhaust and you have to be
        # able to see down it
        wall = 3.0
        r_out = E["collector_r"]
        parts.append(_bored_duct(path, [r_out] * len(path), wall,
                                 spec.RES["pipe"], 5))
        end = (path[-1][0] + (path[-1][0] - path[-2][0]),
               path[-1][1] + (path[-1][1] - path[-2][1]),
               path[-1][2] + (path[-1][2] - path[-2][2]))
        # No V-band clamp round the outside of this one. There is 45 mm to the
        # cam sensor under the back of the bank and a band big enough to go
        # over the flange lands on it; the flange is the feature anyway.
        parts.append(_flange_at(path[-1], end, r_out - wall, 9.0, 13.0 + wall))
    return {"tailpipes": mesh.join(*parts)}
