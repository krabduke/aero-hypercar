"""Everything that bolts to the outside of the engine and makes it run.

Oil filter and cooler, thermostat, charge cooling and its pipework, the
mounts that actually carry the engine, the belt tensioner and idler, the
knock and cam sensors the control reads, and the port flanges and gaskets
between head and manifold.

None of this existed. The engine had a dry-sump tank, oil lines and a pump,
but nothing to filter or cool the oil; two turbochargers with no charge
cooler and no pipework between them and the plenum; mounting bosses with no
mounts on them; and an accessory belt running over pulleys with nothing
tensioning it.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
import gaspath
from parts import common

B = spec.BLOCK
T = spec.TURBO


def build():
    out = {}
    out.update(_oil_system())
    out.update(_cooling())
    out.update(_charge())
    out.update(_mounts())
    out.update(_belt())
    out.update(_sensors())
    out.update(_exhaust_joints())
    return out


def _lathe(profile, cx, cy, cz, axis="z", seg=24, flip=False):
    """Revolve an (along, radius) profile and stand it on a given axis.

    `flip` points the "along" direction the other way. A part on the left bank
    has to grow outboard just as its twin does on the right, and a profile
    that always runs +y grows outboard on one side and inboard on the other --
    which is how the knock sensors and engine mounts came out 34 mm from
    mirroring each other. Done as a rotation rather than by negating a
    coordinate, so the winding stays right way out.
    """
    v, f = mesh.revolve_closed(list(profile), seg)
    if flip:
        v = mesh.rot_z(v, math.pi)
    if axis == "z":
        v = [(pz, py, px) for (px, py, pz) in v]
    elif axis == "y":
        v = [(pz, px, py) for (px, py, pz) in v]
    return ([(px + cx, py + cy, pz + cz) for (px, py, pz) in v], f)


# --------------------------------------------------------------------------

def _oil_system():
    """Spin-on filter on its pedestal, and the stacked-plate cooler beside it.

    A dry sump with no filter is a pump circulating its own debris.
    """
    out = {}
    # The pedestal's inboard face is 1 mm into the crankcase wall, which is
    # 0.86 of the block's half width. Placed off the full half width it stood
    # 10.5 mm off the wall, on the gallery it is meant to feed, bolted to
    # nothing.
    y = -(B["half_width"] * 0.86 + 39.0)
    # below the fuel rail, which runs this flank at z 31..69
    zc = -70.0
    x = 26.0        # aft of the engine mount at x -95
    parts = []
    # the pedestal casting on the block, with the two galleries through it
    parts.append(shapes.rounded_box(x, y + 18.0, zc, 108.0, 44.0, 86.0, 8.0))
    for dx in (-30.0, 30.0):
        parts.append(_lathe(
            [(0.0, 0.0), (26.0, 0.0), (26.0, 15.0), (0.0, 15.0)],
            x + dx, y + 8.0, zc, axis="y", seg=14))
    # The canister: rolled seam, fluted body, sealing face -- pointing OUT.
    # `_lathe` runs the profile up +y, so written from 0 to +140 the filter
    # screwed itself inboard: 140 mm of canister through the block wall,
    # across the crankcase and into the crankshaft, with the cooling fins
    # left outside on their own.
    #
    # 82 mm long, not 140: the cooler stands outboard of it, and the
    # canister's end lands on the cooler's inboard face -- the oil goes
    # straight from one into the other. At 140 the canister ran 52 mm on
    # through the cooler's plate pack.
    L = 82.7
    parts.append(_lathe(
        [(-L, 0.0), (-L, 46.0), (-L + 8.0, 54.0), (-24.0, 54.0),
         (-18.0, 58.0), (-8.0, 58.0), (0.0, 52.0), (0.0, 0.0)],
        x, y - 6.0, zc, axis="y", seg=28))
    for k in range(16):
        a = 2 * math.pi * k / 16
        fv, ff = mesh.cylinder(0.0, L - 36.0, 3.4, 6)
        fv = [(56.0 * math.cos(a) + pz, -px, 56.0 * math.sin(a) + py)
              for (px, py, pz) in fv]
        parts.append(([(px + x, py + y - 26.0, pz + zc)
                       for (px, py, pz) in fv], ff))
    out["oil_filter"] = mesh.join(*parts)

    # the cooler: a real plate pack, not a brick
    # Outboard of the battery, which fills the floor of the engine bay
    # under the sump. At 58 mm off the block the cooler was inside it.
    cx, cy, cz = -10.0, -(B["half_width"] + 140.0), -74.0
    parts = [shapes.core(cx, cy, cz, 190.0, 58.0, 76.0, n_plates=14)]
    # the inlet union at the forward end; the outlet is the face the filter
    # stands on
    for dx in (-84.0,):
        parts.append(_lathe(
            [(0.0, 0.0), (30.0, 0.0), (30.0, 17.0), (22.0, 17.0),
             (22.0, 13.0), (0.0, 13.0)],
            # from 2 mm into the core's face, not 5 mm off it
            cx + dx, cy + 27.0, cz, axis="y", seg=14))
    # the bracket tying its forward end back towards the block, forward of
    # the filter
    parts.append(shapes.rounded_box(cx - 62.0, cy + 42.0, cz + 22.0,
                                    66.0, 34.0, 14.0, 4.0))
    out["oil_cooler"] = mesh.join(*parts)
    return out


def _cooling():
    """Thermostat and its housing, on the timing case's front face.

    The heads' water comes forward through the case and out of the boss in
    its vee, which is where the housing bolts on. The housing carries two
    radiator outlet stubs, one each side, because the vehicle has a
    radiator in each sidepod and the front of this engine is too full for a
    hose to cross it: its bulkhead is 9 mm ahead of the damper. The bypass
    back to the pump runs inside the timing case's casting, as it does on
    most race engines; it used to be an external hose looping down the
    right-hand side of the case, which left the housing only one outlet.

    It used to stand behind the case on the block's front face, 104 mm
    across in a gap between the two banks' gear trains that is 30 mm wide at
    that height -- and the train had to be left not meshing to make room.
    """
    out = {}
    C = spec.COOLANT
    x0 = C["stat_x"]
    x1 = spec.FRONT["case_front"]
    zc = C["stat_z"]
    parts = []
    parts.append(_lathe(
        [(0.0, 0.0), (0.0, 30.0), (4.0, 34.0), (x1 - x0 - 6.0, 34.0),
         (x1 - x0 - 6.0, 42.0), (x1 - x0, 42.0), (x1 - x0, 0.0)],
        x0, 0.0, zc, axis="x", seg=28))
    xm = x0 + spec.STAT_STUB_X
    # the two radiator hose stubs, with their beads, under the axis
    zs = zc - spec.STAT_STUB_DROP
    for flip in (True, False):
        parts.append(_lathe(
            [(0.0, 0.0), (0.0, 14.0), (47.0, 14.0), (51.0, 17.0),
             (55.0, 17.0), (59.0, 14.0), (65.0, 14.0), (65.0, 0.0)],
            xm, -15.0 if flip else 15.0, zs, axis="y", seg=18, flip=flip))
    # four bolts through the flange into the case, clear of the two ports
    # and the header tank on top
    for k in range(4):
        a = 2 * math.pi * (k + 0.5) / 4
        bv, bf = mesh.cylinder(x1 - 10.0, x1 - 4.0, 4.5, 8)
        bv = [(px, 38.0 * math.cos(a) + py, 38.0 * math.sin(a) + pz + zc)
              for (px, py, pz) in bv]
        parts.append((bv, bf))
    out["thermostat"] = mesh.join(*parts)
    return out


# how far out of the plenum's axis the charge coolers' water stubs reach
LT_STUB = 84.0


def lt_stubs(bank):
    """(inlet, outlet) hose-stub ends of a bank's charge cooler, and the
    direction each points: the vehicle's low-temperature loop connects
    here."""
    I = spec.INTAKE
    s_ = -1.0 if bank == 0 else 1.0
    L = I["plenum_len"] / 2 - 34.0
    y = s_ * (I["plenum_y"] + LT_STUB)
    # each end tank runs 28 mm aft from its station; the union is mid-tank
    return (((-L + 14.0, y, I["plenum_z"]), (0.0, s_, 0.0)),
            ((L + 14.0, y, I["plenum_z"]), (0.0, s_, 0.0)))


def _charge():
    """Water-to-air charge coolers, and the pipe from each turbo to them.

    The cooler cores live INSIDE the plenums, which is what a hot vee does
    and the only thing that fits here: the vee is full of turbochargers and
    exhaust, the cam covers reach y 252, and anything outboard of those is
    wider than the car this engine goes in. It also makes the charge run
    what it should be -- compressor outlet, up over the cam cover, straight
    down into the throttle -- instead of a three-metre loop out to a cooler
    on the roof and back, which is what was here: two open-ended trunks
    arcing over and around the engine and touching nothing at the far end.
    """
    from parts import induction
    out = {}
    runs = []
    I = spec.INTAKE
    for bank, tag in ((0, "l"), (1, "r")):
        s_ = -1.0 if bank == 0 else 1.0
        cy = s_ * I["plenum_y"]
        cz = I["plenum_z"]
        # the core, sitting in the plenum's own bore, with an end tank at
        # each end carrying the water unions
        parts = [shapes.core(0.0, cy, cz, I["plenum_len"] - 96.0,
                             I["plenum_r"] * 1.05, I["plenum_r"] * 1.05,
                             n_plates=16)]
        for dx in (-(I["plenum_len"] / 2 - 34.0), I["plenum_len"] / 2 - 34.0):
            parts.append(_lathe(
                [(0.0, 0.0), (0.0, I["plenum_r"] * 0.72),
                 (8.0, I["plenum_r"] * 0.80), (22.0, I["plenum_r"] * 0.80),
                 (28.0, I["plenum_r"] * 0.72), (28.0, 0.0)],
                dx, cy, cz, axis="x", seg=20))
            # The water union out of each end tank, through the plenum's
            # outboard wall to a beaded hose stub: the front one is the
            # charge cooler's inlet, the aft one its outlet. They used to
            # stand 22 mm up out of the plenum's crown and end there, with
            # nothing on them -- a water-to-air cooler with no water. The
            # low-temperature loop (pump, core, hoses) is the vehicle's, as
            # the main radiator is; these stubs are where it connects, and
            # outboard is where the car's sidepod and its cores are.
            parts.append(_lathe(
                [(20.0, 0.0), (20.0, 9.0), (I["plenum_r"] * 1.04 - 2.0, 9.0),
                 (I["plenum_r"] * 1.04 - 2.0, 15.0), (I["plenum_r"] * 1.04 + 6.0, 15.0),
                 (I["plenum_r"] * 1.04 + 6.0, 10.0), (LT_STUB - 14.0, 10.0),
                 (LT_STUB - 11.0, 12.5), (LT_STUB - 7.0, 12.5),
                 (LT_STUB - 4.0, 10.0), (LT_STUB, 10.0), (LT_STUB, 0.0)],
                dx + 14.0, cy, cz, axis="y", seg=16, flip=(bank == 0)))
        out[f"intercooler_{tag}"] = mesh.join(*parts)

        # compressor outlet -> over the cam cover -> that bank's throttle.
        # The start is the mouth of the volute gaspath declares, not a guess
        # 96 mm out to the side of the turbo: the pipe used to leave the
        # housing from a point that was not on it.
        tx = T["x"][bank]
        mouth = gaspath.compressor_outlet(0 if bank == 0 else 2)
        thr_y = s_ * (I["plenum_y"] + I["plenum_r"] * 0.86 + 54.0)
        # and in on the throttle's own axis, so the pipe meets its mouth
        # instead of stopping in the air in front of the engine
        # Out along the scroll's own tangent first, so the pipe leaves the
        # volute the way the air does and clears the bearing housing beside
        # it; then fore or aft to the station where this bank's primaries
        # have already turned inboard; then straight out and down.
        #
        # The path is monotone in y from there. It used to double back in x
        # halfway along, and a swept tube through a reversal folds in on
        # itself -- the mesh bulged far enough to reach parts a hundred
        # millimetres away.
        # and it stays low while it crosses the plane the primaries climb
        # in: this bank's two pipes go up at y = +-85, and the charge pipe
        # leaves the volute at y = +-62, so the only way past them is under
        # them -- they are 70 mm higher by the time they get there.
        # ...and it crosses at the station where this bank's primaries have
        # already climbed, which is BETWEEN two cylinders and not over one.
        # Offset the other way, as it used to be relative to a turbo at 118,
        # it now lands on number one's tube just out of the port, where the
        # primary is still low and there is nothing to pass under.
        out_x = mouth[0] + (3.0 if bank == 0 else -3.0)
        path = [mouth,
                # y 82, not 64: this is a 60 mm pipe, so at 64 its inboard
                # wall is at y 34 and the MGU-H is a 64 mm rotor on the shaft
                # reaching to y 32. The pipe was brushing the motor.
                (out_x, s_ * 82.0, T["z"] - 14.0),
                (out_x, s_ * 132.0, T["z"] + 8.0),
                (out_x, s_ * 250.0, T["z"] + 12.0),
                (out_x, s_ * 322.0, 176.0),
                (out_x * 0.4, s_ * 350.0, 104.0),
                (0.0, s_ * 352.0, cz),
                # butted onto the throttle's inlet spigot, which is this
                # pipe's size, inside a coupler
                induction.throttle_mouth(bank)]
        r = 30.0
        pipe_parts = [mesh.pipe(path, r, segments=18, subdiv=3)]
        # the silicone coupler over the joint, with a clamp each side of it
        jm = path[-1]
        cpl = [(jm[0], jm[1] - s_ * 16.0, jm[2]), (jm[0], jm[1] + s_ * 16.0, jm[2])]
        pipe_parts.append(mesh.pipe(cpl, induction.CHARGE_SPIGOT + 4.0,
                                    segments=20, bend=0.0))
        for dy in (-9.0, 9.0):
            pipe_parts.append(mesh.pipe(
                [(jm[0], jm[1] + dy - 3.0, jm[2]), (jm[0], jm[1] + dy + 3.0, jm[2])],
                induction.CHARGE_SPIGOT + 6.0, segments=20, bend=0.0))
        # a coupling bead at the turbo end, which is where a clamp lands
        for pt, nxt in ((path[0], path[1]),):
            m = math.dist(pt, nxt) or 1.0
            step = tuple((nxt[k] - pt[k]) / m * 14.0 for k in range(3))
            pipe_parts.append(mesh.pipe(
                [tuple(pt[k] - step[k] * 0.2 for k in range(3)),
                 tuple(pt[k] + step[k] for k in range(3))],
                r + 3.5, segments=20))
        runs.extend(pipe_parts)

    # The turbochargers are at x = -118 and +118 -- fore and aft on the vee,
    # not left and right -- so the pipework between them and the coolers is
    # one assembly. Naming it _l/_r would claim a mirror symmetry it does not
    # have, and the structure audit would rightly call that a failure.
    out["charge_pipes"] = mesh.join(*runs)

    # Recirculating blow-off valve, standing on the left charge pipe where it
    # crosses out over the cam cover. It used to be at x = +120 in the middle
    # of the vee, which is neither on that pipe nor on any other -- it was a
    # valve bolted to the air.
    parts = []
    # y -280: at -272 its body was 4 mm into the cam cover's ribs
    bx, by, bz = -120.4, -280.0, 228.0
    # hanging under the pipe, not standing on top of it: the exhaust runs
    # over the cam cover directly above this
    parts.append(_lathe(
        [(0.0, 0.0), (0.0, 30.0), (-10.0, 34.0), (-52.0, 34.0),
         (-58.0, 30.0), (-58.0, 22.0), (-70.0, 22.0), (-70.0, 0.0)],
        bx, by, bz, axis="z", seg=20))
    # its vent, straight down out of the bottom of the valve. It used to
    # leave the side facing the engine and ran 40 mm into the cam cover.
    parts.append(_lathe(
        [(0.0, 0.0), (0.0, 13.0), (26.0, 13.0), (26.0, 0.0)],
        bx, by, bz - 66.0, axis="z", seg=14, flip=True))
    out["blowoff"] = mesh.join(*parts)
    return out


def _mounts():
    """The mounts the engine actually hangs on.

    There were bosses on the block and nothing bolted to them.
    """
    out = {}
    for bank, tag in ((0, "l"), (1, "r")):
        s = -1.0 if bank == 0 else 1.0
        parts = []
        # on the face of the block's mount boss (spec.MOUNTS)
        M = spec.MOUNTS
        y = s * (M["boss_face"] - 1.0)
        for x in M["x"]:
            # the bracket: a machined foot with a rubber bush in its eye
            # z 30 put the bracket up the side of the head; the mount bolts
            # to the block, which is below it
            # Between the dry-sump pump below (its top is at z = 3) and the
            # head above (its bottom is at 46). The bracket was at z -18..78
            # and so was in both.
            # below the fuel rail, which runs the length of the block's
            # outboard flank at z 26..64
            parts.append(shapes.rounded_box(x, y + s * 15.0, M["z"],
                                            72.0, 30.0, 38.0, 6.0))
            fl = s < 0
            # the bush's eye is let 2 mm into the foot; at +62 it stood 2 mm
            # off it, a rubber bush held on by nothing
            parts.append(_lathe(
                [(0.0, 0.0), (0.0, 22.0), (24.0, 22.0), (24.0, 0.0)],
                x, y + s * 28.0, M["z"], axis="y", seg=22, flip=fl))
            parts.append(_lathe(
                [(1.0, 0.0), (23.0, 0.0), (23.0, 13.0), (1.0, 13.0)],
                x, y + s * 28.0, M["z"], axis="y", seg=18, flip=fl))
            # Two bolts through the foot into the block. They were at z 12,
            # above the foot and 17 mm off the block, fastening nothing.
            for dx in (-24.0, 24.0):
                parts.append(_lathe(
                    [(0.0, 0.0), (0.0, 9.0), (6.0, 9.0), (6.0, 5.0),
                     (44.0, 5.0), (44.0, 0.0)],
                    x + dx, y + s * 36.0, M["z"], axis="y", seg=12,
                    flip=not fl))
        out[f"engine_mount_{tag}"] = mesh.join(*parts)
    return out


def _belt():
    """Tensioner and idler on the accessory belt run.

    Both hang off the timing case's front plate, where its legs run up to
    the cam gears, on the belt's plane in spec.FRONT. The idler is a pulley
    on a stand-off post. The tensioner is a sprung arm: a pivot post on the
    case, an arm swinging out from it, and the pulley on the arm's end
    pressing the belt tight.
    """
    from parts.plumbing import pulley
    out = {}
    F = spec.FRONT
    bx = F["belt_x"]
    x_post = bx + F["pulley_w"] / 2.0            # behind the pulley
    x_case = F["case_front"]

    y, z, r = F["idler"]
    pv, pf = pulley(bx, r)
    post = mesh.cylinder(x_post - 0.5, x_case, 14.0, 20)
    boss = mesh.cylinder(x_case - 6.0, x_case, 22.0, 24)
    out["belt_idler"] = mesh.join(
        *[([(px, py + y, pz + z) for (px, py, pz) in v], f)
          for (v, f) in ((pv, pf), post, boss)])

    y, z, r = F["tensioner"]
    # the pivot is inboard and above the pulley, on the leg
    qy, qz = y - 30.0, z + 30.0
    pv, pf = pulley(bx, r)
    parts = [([(px, py + y, pz + z) for (px, py, pz) in pv], pf)]
    # pulley axle back to the arm
    av, af = mesh.cylinder(x_post - 0.5, x_post + 8.0, 9.0, 16)
    parts.append(([(px, py + y, pz + z) for (px, py, pz) in av], af))
    # the arm, pulley to pivot
    L = math.hypot(qy - y, qz - z)
    ang = math.atan2(qz - z, qy - y)
    armv, armf = shapes.rounded_box(x_post + 7.0, L / 2.0, 0.0,
                                    10.0, L + 30.0, 26.0, 6.0)
    armv = mesh.rot_x(armv, ang)
    parts.append(([(px, py + y, pz + z) for (px, py, pz) in armv], armf))
    # the pivot post and its spring housing, on the case
    for (x0, x1, rr) in ((x_post + 11.5, x_case, 15.0),
                         (x_post + 16.0, x_case - 10.0, 24.0)):
        cv, cf = mesh.cylinder(x0, x1, rr, 22)
        parts.append(([(px, py + qy, pz + qz) for (px, py, pz) in cv], cf))
    out["belt_tensioner"] = mesh.join(*parts)
    return out


def _sensors():
    """Knock and cam position sensors: what the control actually listens to."""
    out = {}
    for bank, tag in ((0, "l"), (1, "r")):
        s = -1.0 if bank == 0 else 1.0
        parts = []
        for x in (-102.0, 0.0, 102.0):
            y = s * (B["half_width"] - 2.0)
            parts.append(_lathe(
                [(0.0, 0.0), (0.0, 15.0), (16.0, 15.0), (16.0, 22.0),
                 (22.0, 22.0), (22.0, 11.0), (34.0, 11.0), (34.0, 0.0)],
                x, y, 12.0, axis="y", seg=14, flip=s < 0))
            parts.append(shapes.connector(x, y + s * 40.0, 12.0,
                                          20.0, 15.0, 12.0, pins=2))
        out[f"knock_sensor_{tag}"] = mesh.join(*parts)

        parts = []
        for j, cz in enumerate((0.0, 1.0)):
            a = spec.bank_angle_rad(bank)
            h = spec.DECK_HEIGHT + spec.HEAD["height"] * 0.62
            off = spec.HEAD["cam_centres"] / 2 * (1 if j else -1)
            y = s * (B["bank_half_width"] + 46.0 + off * 0.3)
            z = h + abs(off) * 0.5 * (1 if j else -1)
            parts.append(_lathe(
                [(0.0, 0.0), (0.0, 13.0), (14.0, 13.0), (14.0, 19.0),
                 (20.0, 19.0), (20.0, 10.0), (30.0, 10.0), (30.0, 0.0)],
                spec.HEAD["x_rear"] - 6.0, y, z, axis="x", seg=14))
            # pins facing outboard: aft of it, 12 mm off, is the inverter's
            # own connector block, and there is no room for a plug between
            cx, cy = spec.HEAD["x_rear"] + 26.0, y
            cv, cf = shapes.connector(cx, cy, z, 18.0, 14.0, 11.0, pins=3)
            cv = [(cx - s * (py - cy), cy + s * (px - cx), pz) for (px, py, pz) in cv]
            parts.append((cv, cf))
        out[f"cam_sensor_{tag}"] = mesh.join(*parts)
    return out


def _exhaust_joints():
    """Port flanges and gaskets between head and manifold.

    The primaries were growing straight out of the head casting.

    Placed with common.bank_point, whose lateral axis runs across the bore and
    is positive inboard -- which on this engine is the exhaust side, because
    the turbochargers sit in the vee. The first attempt mixed a world y taken
    from the bank normal with a world z taken from the deck height, which is
    not a frame at all: the flanges came out 100 per cent inside the heads.
    """
    out = {}
    H = spec.HEAD
    for bank, tag in ((0, "l"), (1, "r")):
        # 0.30, not 0.45: at 0.45 the flange ran into the fuel rail above it
        along = spec.DECK_HEIGHT + H["height"] * 0.16
        lat_face = H["half_width"] + 15.0       # between the fuel rail above and
                                        # the turbochargers in the vee
        flanges, gaskets = [], []
        for i in range(spec.N_CYL // 2):
            x = spec.cylinder_x(i, bank)
            c = common.bank_point(x, along, lat_face + 9.0, bank)
            n = common.bank_lat(bank)
            d = common.bank_dir(bank)
            # the flange plate, its two bolt bosses and the port through it
            fv, ff = shapes.rounded_box(0.0, 0.0, 0.0, 62.0, 18.0, 74.0, 5.0)
            fv = [(px + c[0],
                   c[1] + n[1] * py + d[1] * pz,
                   c[2] + n[2] * py + d[2] * pz) for (px, py, pz) in fv]
            flanges.append((fv, ff))
            for dz in (-26.0, 26.0):
                b = common.bank_point(x, along + dz, lat_face + 9.0, bank)
                bv, bf = mesh.cylinder(0.0, 20.0, 10.0, 10)
                bv = [(px + b[0], b[1] + n[1] * py + d[1] * pz,
                       b[2] + n[2] * py + d[2] * pz) for (px, py, pz) in bv]
                flanges.append((bv, bf))
            # the gasket, in the joint face itself
            g = common.bank_point(x, along, lat_face, bank)
            gv, gf = mesh.revolve_closed(
                [(0.0, 22.0), (2.4, 22.0), (2.4, 30.0), (0.0, 30.0)], 20)
            gv = [(py + g[0] if False else g[0] + pz,
                   g[1] + n[1] * px + d[1] * py,
                   g[2] + n[2] * px + d[2] * py) for (px, py, pz) in gv]
            gaskets.append((gv, gf))
        out[f"exhaust_flange_{tag}"] = mesh.join(*flanges)
        out[f"exhaust_gasket_{tag}"] = mesh.join(*gaskets)
    return out
