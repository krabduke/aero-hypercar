"""Flow-conditioning hardware and the small parts a real car carries.

Bargeboards, turning vanes, floor edge fences and edge wings, the beam wing,
brake ducts, mirrors, cameras, rain light and exhaust. None of these are
decoration: each one exists because of what the air does to the part behind it.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import common, wheels, chassis

BB = spec.BARGEBOARD
TV = spec.TURNING_VANE
FE = spec.FLOOR_EDGE
BW = spec.BEAM_WING
BD = spec.BRAKE_DUCT
D = spec.DETAIL


def build():
    out = {}
    out.update(_bargeboards())
    out.update(_turning_vanes())
    out.update(_floor_edge())
    out.update(_beam_wing())
    out.update(_details())
    out.update(_fan_fairings())
    return out


def _curved_vane(x0, x1, y0, y1, z0, z1, t, bow=0.0, n=10,
                 twist=0.0, serrate=0, serr_depth=0.0, top_cut=None,
                 lean=0.0):
    """A vane that curves in plan -- the whole point of a turning vane is that
    it is not flat, so it can turn the flow instead of just splitting it.

    This was a rectangular section swept along that curve: four points, sharp
    on both edges, the same height everywhere. It is a lifting surface, so it
    now has an aerofoil section, twist up its height, and a cut profile.
    """
    cam = []
    for i in range(9):
        f = i / 8
        cam.append((x0 + (x1 - x0) * f,
                    y0 + (y1 - y0) * f + bow * math.sin(math.pi * f)))
    chord = math.dist(cam[0], cam[-1]) or 1.0
    # `t` arrives in millimetres and turning_vane wants a fraction of chord.
    # There used to be a max(0.055, ...) floor under that conversion, which
    # is 5.5 percent of a chord that can be half a metre -- so every vane on
    # the car came out between four and six times the thickness the spec
    # declares for it, and the declared number was doing nothing. A vane is
    # a moulded carbon fence: it is as thick as it is, whatever its chord.
    return shapes.turning_vane(
        cam, z0, z1, t=t / chord, twist=twist, lean=lean,
        n_z=max(10, n), n_chord=40, top_cut=top_cut,
        serrate=serrate, serr_depth=serr_depth)


def _bargeboards():
    """Stacked bargeboards ahead of the sidepod. They pull the front tyre wake
    outboard so it does not get swallowed by the sidepod inlet or the floor."""
    parts = []
    for sgn in (-1.0, 1.0):
        for k in range(BB["elements"]):
            f = k / max(BB["elements"] - 1, 1)
            y = sgn * (BB["y"] - k * BB["gap"] * 0.55)
            x0 = BB["x0"] + k * 46.0
            x1 = BB["x1"] - k * 24.0
            z0 = BB["z0"] + k * 26.0
            z1 = BB["z1"] - k * 46.0
            # Each board leans and twists more than the one inboard of it:
            # they are a cascade, and a cascade that does not turn
            # progressively just stalls the last element. The feet are
            # serrated so the shear layer rolls up into a row of small
            # vortices instead of one big one that bursts over the floor.
            parts.append(_curved_vane(
                x0, x1, y, y + sgn * 62.0, z0, z1, BB["t"],
                bow=sgn * 34.0, twist=sgn * -(9.0 + 5.0 * k),
                lean=sgn * (10.0 + 7.0 * k), serrate=3 + k,
                serr_depth=14.0 - 2.0 * k,
                top_cut=lambda u, z1=z1: z1 - (z1 - z0) * 0.30 * u ** 1.6))
    # Each board is a separate element, trimmed on its own. Half the list is
    # the left side and half the right, in build order.
    half = len(parts) // 2
    return {f"bargeboard_{'lr'[i // half]}{i % half + 1}": m
            for i, m in enumerate(parts)}


def _turning_vanes():
    """Vanes under the nose, conditioning the flow that feeds the floor."""
    parts = []
    for sgn in (-1.0, 1.0):
        for k in range(TV["elements"]):
            y = sgn * (TV["y"] - k * 60.0)
            z1 = TV["z1"] - k * 48.0
            parts.append(_curved_vane(
                TV["x0"] + k * 60.0, TV["x1"], y, y + sgn * 40.0,
                TV["z0"], z1, TV["t"], bow=sgn * 22.0,
                twist=sgn * -(7.0 + 4.0 * k), lean=sgn * 8.0,
                top_cut=lambda u, z1=z1: z1 - (z1 - TV["z0"]) * 0.22 * u))
    half = len(parts) // 2
    return {f"turning_vane_{'lr'[i // half]}{i % half + 1}": m
            for i, m in enumerate(parts)}


def _floor_edge():
    """Floor edge fences and an edge wing. The fences stop the low pressure
    under the floor from pulling air in from outside and destroying the seal --
    which is the same job the skirts do further inboard."""
    out = {}
    fences = []
    from parts.floor import half_width
    for sgn in (-1.0, 1.0):
        for k in range(FE["fences"]):
            f = k / max(FE["fences"] - 1, 1)
            x0 = FE["x0"] + (FE["x1"] - FE["x0"]) * f * 0.82
            parts_x1 = x0 + 300.0
            # Outboard of the floor edge, hanging under the edge wing.
            #
            # These used to step INBOARD from the edge, 20 mm a fence, and
            # turn another 40 mm inboard along their length -- which put all
            # five of them inside the venturi tunnel, in the flow they were
            # meant to be conditioning, and the innermost one through a
            # diffuser strake. The floor's edge is at half_width; the tunnel
            # wall is 34 mm inboard of it; so the only place a fence can
            # stand is outboard of the edge, where the shear layer it works
            # on actually is.
            z1 = FE["edge_root_z"] - 4.0
            # follow the edge station by station: the floor waists in by
            # 130 mm over a fence's own length, and a straight fence set
            # from the narrow end starts inboard of the skirt
            # Each fence is rooted ON the edge and flares outboard along
            # its own length. Stepping the whole fence outboard by 12 mm a
            # time instead left the middle ones hanging in free air, bolted
            # to nothing.
            cam = []
            for i in range(9):
                f = i / 8.0
                cx = x0 + (parts_x1 - x0) * f
                cam.append((cx, sgn * (half_width(cx) + 4.0
                                       + (10.0 + k * 3.0) * f ** 1.5)))
            chord = math.dist(cam[0], cam[-1]) or 1.0
            fences.append(shapes.turning_vane(
                cam, z1 - FE["fence_h"], z1, t=FE["t"] / chord,
                twist=0.0, lean=sgn * 6.0, n_z=10, n_chord=40))
    # each fence is set individually on a real car, so each is its own object
    for i, m in enumerate(fences):
        out[f"floor_fence_{'lr'[i // (len(fences) // 2)]}{i % (len(fences) // 2) + 1}"] = m

    out["floor_edge_wings"] = _edge_wings(half_width)
    return out


def _beam_wing():
    """Beam wing below the rear wing. It works the diffuser exit and the rear
    wing together -- each makes the other more effective."""
    elems = []
    # spec.beam_elements() is the one placement: the mesh, aero/analyse.py and
    # the browser lattice each used to step the second element by a different
    # amount, and only one of them can have been drawing the car.
    for (x, z, chord, aoa) in spec.beam_elements():
        elems.append(common.wing_element(
            x, z, BW["span"], chord, aoa, thickness=0.09, camber=0.07,
            n_span=7, taper=0.92))
    return {"beam_wing": mesh.join(*elems)}


def _details():
    out = {}
    mirrors = []
    for sgn in (-1.0, 1.0):
        # the stalk roots on the cockpit side at y 244, not 282: the tub is
        # 256 mm of half width here, so the old root was 26 mm outboard of
        # the car and the mirrors were a detached pair floating beside it
        stalk = mesh.pipe([(D["mirror_x"] - 60.0, sgn * 244.0, D["mirror_z"] - 138.0),
                           (D["mirror_x"] - 10.0, sgn * 300.0, D["mirror_z"] - 30.0),
                           (D["mirror_x"], sgn * D["mirror_y"], D["mirror_z"])],
                          13.0, 10)
        mirrors.append(stalk)
        # The housing is a streamlined pod with the glass on its flat back
        # face, not a box: round-nosed, deepest a third of the way along,
        # cut off square behind where the mirror is.
        pv, pf = mesh.revolve_closed(
            [(66.0, 0.0), (64.0, 16.0), (52.0, 18.5), (30.0, 20.5),
             (14.0, 20.0), (4.0, 17.0), (0.0, 13.0), (0.0, 0.0)], 32)
        cx, cy, cz = (D["mirror_x"] - 9.0, sgn * (D["mirror_y"] + 16.5),
                      D["mirror_z"] + 8.0)
        # flip so the round nose leads and the flat glass face is aft
        mirrors.append(([(cx + 66.0 - px, cy + py * 0.80, cz + pz * 2.1)
                         for (px, py, pz) in pv], pf))
    out["mirrors"] = mesh.join(*mirrors)

    cams = []
    # The two on the nose are small streamlined pods standing on the skin,
    # set from the skin as meshed. They were boxes at a fixed height that
    # the nose had grown over, and only a dark sliver of each showed.
    for sgn in (-1.0, 1.0):
        best = min(range(20, 90), key=lambda a: abs(
            abs(chassis.skin_point(D["camera_x"], a)[1]) - 122.0))
        ang = best if sgn > 0 else 180 - best
        # laid along the skin, which climbs steeply here, its underside
        # on it
        p0 = chassis.skin_point(D["camera_x"] - 55.0, ang, 20.9)
        p1 = chassis.skin_point(D["camera_x"] + 55.0, ang, 20.9)
        pv, pf = mesh.revolve_closed(
            [(110.0, 0.0), (104.0, 14.0), (80.0, 19.0), (40.0, 20.0),
             (14.0, 17.0), (3.0, 11.0), (0.0, 0.0)], 28)
        d = tuple(p1[k] - p0[k] for k in range(3))
        cams.append((shapes.orient(pv, p0, d), pf))
        # and the foot it is bolted through the skin by
        top = chassis.skin_point(D["camera_x"], ang, 20.0)
        bot = chassis.skin_point(D["camera_x"], ang, -3.0)
        fv, ff = mesh.cylinder(0.0, math.dist(top, bot), 7.0, 14)
        cams.append((shapes.orient(fv, bot, tuple(top[k] - bot[k]
                                                   for k in range(3))), ff))
    # The T-camera sits on top of the roll hoop, where it looks down the
    # car. Just aft of the cockpit at z 820 it was 56 mm inside the airbox.
    RH = spec.ROLL_HOOP
    cv, cf = shapes.rounded_box(RH["x"], 0.0,
                                RH["top_z"] + RH["leg_r"] + 25.5,
                                150.0, 60.0, 52.0)
    cams.append((cv, cf))
    out["cameras"] = mesh.join(*cams)

    lv, lf = shapes.rounded_box(D["rainlight_x"], 0.0, D["rainlight_z"], 44.0, 96.0, 70.0)
    out["rainlight"] = (lv, lf)

    ex = []
    v, f = mesh.tube(D["exhaust_x"], D["exhaust_x"] + 130.0,
                     D["exhaust_r"] - 9.0, D["exhaust_r"], 26)
    ex.append(([(px, py, pz + D["exhaust_z"]) for (px, py, pz) in v], f))
    # No separate wastegate pipes. The engine's wastegates are integral
    # flaps that dump into the turbine outlet, so their gas leaves through
    # this tailpipe; the two screamer pipes that stood beside it were fed by
    # nothing and joined to nothing.
    # and the pipe that gets there from the engine. The tailpipe sat 848 mm
    # behind the engine with nothing between them, so the exhaust left from
    # nowhere. It runs over the gearbox, which tops out at z 536, and in
    # between the rear wing pylons, which is where a tailpipe exits.
    #
    # It starts ON the rear turbo's outlet flange, which faces outboard to
    # starboard at the back of the vee, and opens out from the flange's bore
    # to the tailpipe's. It used to start 60-120 mm away on the centreline
    # and join the turbo's elbow through its side.
    PT = spec.POWERTRAIN
    ex_x, ex_z = PT["engine_x"], PT["engine_z"]
    # (the flanges' centres, from the engine's turbo.py: 317.7 mm either
    # side of the engine's middle, 88 out and 281 up; they were placed 4 mm
    # off, beside the bores they are meant to be on)
    flange = (ex_x + 317.7, 88.0, ex_z + 281.0)
    ex.append(mesh.pipe(
        # then straight back in to the centreline, where the engine cover
        # is tall enough for it: outboard at y 128 the cover is down at z 585
        [flange, (flange[0] + 10.0, 104.0, flange[2] + 4.0),
         (3640.0, 64.0, 604.0), (3760.0, 10.0, 598.0),
         (4180.0, 0.0, 556.0), (D["exhaust_x"] + 10.0, 0.0, D["exhaust_z"])],
        [30.0, 34.0, 42.0, 52.0, 52.0, 52.0], 18, subdiv=3))
    # The front turbo's downpipe. Its outlet flange is at the front of the
    # vee facing forward and out to port, and it used to be connected to
    # nothing: the engine ends at its flanges and the car only ever plumbed
    # the rear one. From the flange it turns back on itself and runs aft
    # along the inside of the engine cover, over the port cam cover -- the
    # one clear lane down the engine, 60-100 mm between the cam cover's top
    # and the cover's skin -- then in behind the engine to join the tailpipe.
    f0 = (ex_x - 317.7, -88.0, ex_z + 281.0)
    ex.append(mesh.pipe(
        [f0, (f0[0] - 8.0, -112.0, f0[2] + 4.0),
         (f0[0] - 2.0, -150.0, f0[2] + 7.0),
         (f0[0] + 40.0, -176.0, 600.0), (3040.0, -180.0, 596.0),
         (3300.0, -164.0, 592.0), (3420.0, -148.0, 586.0),
         (3540.0, -128.0, 580.0),
         (3640.0, -84.0, 588.0), (3760.0, -18.0, 598.0)],
        [27.0, 28.0, 29.0, 30.0, 30.0, 30.0, 30.0, 32.0, 34.0, 36.0],
        18, subdiv=4))
    out["exhaust"] = mesh.join(*ex)

    # Engine cover cooling louvres, ON the cover.
    #
    # These were placed by hand at a fixed y and a falling z, which walked
    # them straight into the gearbox casing: the last two banks were 170 mm
    # inside it. A louvre is a slot cut in a surface, so it is set from the
    # surface -- like every other skin detail on the car.
    lv2 = []
    for ang in (66.0, 114.0):
        lv2.append(shapes.louvre_panel(
            chassis.skin_point, 3200.0, 3640.0, ang - 5.0, ang + 5.0,
            11, h=10.0, lean=24.0, t=3.0, m=8, base=1.3))
    out["cooling_louvres"] = mesh.join(*lv2)
    return out


def _fan_fairings():
    """The cowl round each fan: from the lip of the bellmouth back over the
    shroud and the nozzle to the exit, shaped so the air passing outside the
    fan follows it rather than breaking off a square step. Its bore is the
    shroud's and the nozzle's outside, which it is bonded over."""
    fan, ex = spec.FAN, spec.FAN_EXHAUST
    R = fan["duct_r"]
    profile = [(-76.0, R + 30.0), (-50.0, R + 40.0), (10.0, R + 42.0),
               (90.0, R + 34.0), (ex["exit_a"], ex["exit_r"] + 12.0),
               (ex["exit_a"], ex["exit_r"] + 6.0), (70.0, R + 8.0),
               (-54.0, R + 8.0), (-66.0, R + 16.0)]
    verts, faces = mesh.revolve_closed(profile, 64)
    out = {}
    for tag, sgn in (("l", -1.0), ("r", 1.0)):
        out[f"fan_fairing_{tag}"] = (
            [(fan["x"] + px, sgn * fan["y"] + py, fan["z"] + pz)
             for px, py, pz in verts], list(faces))
    return out


def _thicken(cam, t, n=26):
    """A closed aerofoil section built out from a camber line.

    Round at the nose, closing at the tail, thickness following the camber's
    own normal -- so a curled section stays the same thickness round the
    curl instead of pinching where it turns hardest.
    """
    dense = shapes._resample(cam, n)
    up, dn = [], []
    for i, (u, v) in enumerate(dense):
        p0 = dense[max(i - 1, 0)]
        p1 = dense[min(i + 1, n - 1)]
        tx, ty = p1[0] - p0[0], p1[1] - p0[1]
        m = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / m, tx / m
        f = i / (n - 1)
        h = t * 0.5 * math.sqrt(max(4.0 * f * (1.0 - f), 0.0)) ** 0.7
        h = max(h, t * 0.10)
        up.append((u + nx * h, v + ny * h))
        dn.append((u - nx * h, v - ny * h))
    return up + list(reversed(dn[1:-1]))


def _edge_wings(half_width, n_x=34):
    """The wing along the floor edge.

    This was a 900 mm span aerofoil laid ACROSS the car at x 3450 -- which
    put it straight through both venturi tunnels and over the centreline,
    where it would have blocked the floor it was meant to help. A floor edge
    wing runs along the edge, not across the car: it hangs off the outer lip
    for most of the floor's length and curls up outboard, so the shear layer
    coming off the edge rolls into one strong vortex that seals the floor
    instead of a sheet that wanders under it.
    """
    c, t = FE["edge_chord"], FE["edge_t"]
    cam = [(0.00, 0.00), (0.18, 0.07), (0.40, 0.20),
           (0.62, 0.40), (0.82, 0.62), (1.00, FE["edge_rise"])]
    sect = _thicken([(u * c, v * c) for (u, v) in cam], t)
    parts = []
    for sgn in (-1.0, 1.0):
        rings = []
        for i in range(n_x):
            f = i / (n_x - 1)
            x = FE["x0"] + (FE["x1"] - FE["x0"]) * f
            # fade the section in at both ends rather than stopping dead
            s = min(1.0, (min(f, 1.0 - f) / 0.12)) ** 0.6
            y0 = sgn * (half_width(x) + FE["edge_root_dy"])
            rings.append([(x, y0 + sgn * du * s,
                           FE["edge_root_z"] + dv * s)
                          for (du, dv) in sect])
        m = len(rings[0])
        verts = [v for r in rings for v in r]
        faces = []
        for i in range(n_x - 1):
            a, b = i * m, (i + 1) * m
            for k in range(m):
                k2 = (k + 1) % m
                faces.append((a + k, a + k2, b + k2, b + k))
        faces.append(tuple(range(m - 1, -1, -1)))
        base = (n_x - 1) * m
        faces.append(tuple(range(base, base + m)))
        parts.append((verts, faces))
    return mesh.join(*parts)
