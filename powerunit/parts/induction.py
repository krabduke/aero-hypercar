"""Twin airboxes, eight individual throttles and secondary port injection.

The direct injectors belong to heads.py; port injectors use distinct names
so assembly cannot silently replace the direct-injection meshes.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh

SM = spec.RES["small_revolve"]
import shapes
import gaspath
from parts import common

I = spec.INTAKE
SEG = spec.RES["revolve"]


PFI_NIPPLE = 22.0      # the port rails' front inlet nipple


def build():
    out = {}
    out.update(_plenum())
    out.update(_trumpets())
    out.update(_injection())
    return out


# Where the port rail sits, measured from the intake port: RAIL_OUT mm
# outboard of the bore axis and RAIL_UP mm further up it. That lands it at
# y 245, z 136 on the left bank -- the point in that pocket furthest from
# anything, found by measuring the distance from every candidate rail axis
# to every other part in the model rather than by eye. It clears its nearest
# neighbour, the blow-off valve, by 20 mm.
#
# The pocket it has to live in is small and it is bounded on all four sides.
# Below it are the runners, which reach z 116, and the two water unions
# standing out of the charge cooler's end tanks, which reach 115.6 at
# x +/- 152. Above and outboard is the cam cover, from z 147.7. Inboard is
# the intake camshaft -- y 179.7 to 208.5, from z 124.5 up -- and its lobes,
# which swing out to y 220. Outboard of 252 is wider than the car. Probed on
# a 4 mm grid at every 10 mm of x along the bank, what is left is roughly
# y 204 to 252 between z 116 and 122, opening out to y 220-252 above that.
RAIL_OUT = 27.0
RAIL_UP = 89.0

# How much of the run from the injector's tip to the rail is the injector
# itself; the rest is the union on top of it.
FEED_LEN = 10.0


def _injection():
    """Port injection: one injector into each runner, on its own low-pressure
    rail.

    `_pfi_`, because heads.py already has a direct injector in every chamber
    and both were called `injector_n`. Two systems is deliberate -- direct
    injection alone cannot keep a 350 bar chamber clean of intake-valve
    deposits, and port injection alone cannot cool the charge in the cylinder,
    so a high-output engine that has to idle and to pull 16,000 rpm carries
    both and crosses over between them with load. What was not deliberate was
    giving them the same names, which left assembly building two objects per
    injector and the high-pressure feeds pointing at the low-pressure rail.
    """
    out = {}
    rail_points = {0: [], 1: []}
    for n, pair, bank, x, a in spec.cylinders():
        port = gaspath.intake_port(bank, x)
        runner = gaspath.runner_path(bank, x)[-2]
        d, lat = common.bank_dir(bank), common.bank_lat(bank)
        # The nozzle is in the runner's crown half way along it, 10 mm above
        # the centreline. On the centreline the body leant out across the
        # trumpet flares and grazed them; the runner no longer arches up to
        # meet it the way the old hairpin did.
        tip = tuple((port[k] + runner[k]) / 2 + (10.0 if k == 2 else 0.0)
                    for k in range(3))
        # The rail, and then the injector aimed at it.
        #
        # The whole system used to run straight out along -lat from the tip:
        # injector 48 mm out, rail 68. Outboard of the port is where the
        # plenum, the intercooler and the trumpets are, so the rail sat at
        # y 223, z 49 -- inside the plenum, inside the intercooler and
        # through every runner on the bank. Sixty of the engine's hundred
        # and twenty remaining overlaps were this one mistake.
        #
        # Probed on a 5 mm grid at all four cylinder stations, the clear air
        # on this side of the engine is a band from z 116 to 144 between
        # y 200 and 250: above the runners and the intercooler, below the cam
        # cover, outboard of the head. That is also where a port rail goes on
        # a real engine -- along the flank of the head under the cam cover,
        # with the injectors leaning up into it out of the runners.
        rail = tuple(port[k] - lat[k] * RAIL_OUT + d[k] * RAIL_UP
                     for k in range(3))
        rail_points[bank].append(rail)
        reach = math.dist(tip, rail)
        u = mesh._normalise([rail[k] - tip[k] for k in range(3)])
        w = (0.0, u[2], -u[1])          # across the injector, in the y-z plane
        # the body fills the run bar the union, rather than being a fixed
        # 48 mm that happened to be longer than the gap it had to fit
        k_ax = (reach - FEED_LEN) / 48.0
        profile = [(0.0, 0.0), (0.0, 3.0), (12.0, 3.0),
                   (14.0, 7.0), (38.0, 7.0), (40.0, 9.0),
                   (46.0, 9.0), (48.0, 4.0), (48.0, 0.0)]
        profile = [(ax * k_ax, r) for (ax, r) in profile]
        verts, faces = mesh.revolve_closed(profile, SM)
        verts = [(tip[0] + py,
                  tip[1] + u[1] * px + w[1] * pz,
                  tip[2] + u[2] * px + w[2] * pz)
                 for px, py, pz in verts]
        if -(u[1] * w[2] - w[1] * u[2]) < 0.0:
            faces = [tuple(reversed(face)) for face in faces]
        out[f"pfi_injector_{n}"] = (verts, faces)
        # high up the body, where the connector actually is: at 28 of 48 it
        # was level with the runner's crown and buried in it
        plug_at = (reach - FEED_LEN) * 0.78
        # forward of the injector, not aft: the high-pressure fuel pump sits
        # on the right bank's cam drive from x -36 to 36, and cylinder 4's
        # connector at tip + 10 landed inside it, 214 vertices deep
        plug = (tip[0] - 10.0, tip[1] + u[1] * plug_at, tip[2] + u[2] * plug_at)
        # pins facing forward, away from the injector: they faced along +x,
        # into the injector's own body, and up is the head's cam carrier
        cv, cf = shapes.connector(*plug, 14.0, 12.0, 10.0, 2)
        cv = [(2.0 * plug[0] - px, py, pz) for (px, py, pz) in cv]
        cf = [tuple(reversed(f)) for f in cf]
        out[f"pfi_plug_{n}"] = (cv, cf)
        inlet = tuple(tip[k] + u[k] * (reach - FEED_LEN) for k in range(3))
        out[f"pfi_feed_{n}"] = mesh.pipe([inlet, rail], 3.5, SM)
    ends = []
    for bank, tag in ((0, "l"), (1, "r")):
        points = sorted(rail_points[bank])
        start = (points[0][0] - 18.0, *points[0][1:])
        end = (points[-1][0] + 18.0, *points[-1][1:])
        out[f"fuel_rail_pfi_{tag}"] = mesh.pipe([start, *points, end], 7.0, SM)
        ends.append(end)
        # 24 segments, not 6. At 6 this was a 32-vertex hexagonal stub, well
        # under the 120-vertex floor the geometry audit sets -- invisible
        # until the build was current enough for the audit to see it.
        # ...and the inlet union on the front end, with its nipple forward
        # for the feed hose: the rail's front end was an open tube.
        out[f"fuel_rail_pfi_union_{tag}"] = mesh.join(
            mesh.pipe([(end[0] - 6.0, *end[1:]), (end[0] + 6.0, *end[1:])],
                      10.0, 24),
            mesh.pipe([(start[0] + 6.0, *start[1:]),
                       (start[0] - 6.0, *start[1:])], 10.0, 24),
            mesh.pipe([(start[0] - 5.0, *start[1:]),
                       (start[0] - PFI_NIPPLE, *start[1:])], 5.0, 20))
    # Behind the block, not through it.
    #
    # This ran straight across the engine at the rails' own height, z 49,
    # which at y = 0 is inside the crankshaft's counterweight circle: a fuel
    # line through the crank, with block_bank_l and block_bank_r on the way.
    # `audit_intersect` allowed it, because ("fuel_rail_", "block_") and the
    # crank are both on its list of overlaps that are meant to be there.
    #
    # x 231.5 is aft of the block banks (222), the heads (218), the water
    # outlets, the intake camshafts' tails (228) and the direct-injection
    # crossover and supply line at 224, and forward of the bellhousing flange
    # (235) -- a 7 mm slot, which a 6 mm low-pressure line fits. It crosses at z 145, over the
    # direct-injection crossover at 132 and under the inverter at 153. It
    # used to dip to 110 on the way, down through the vee between the banks
    # and across the other crossover's riser, 11 mm into each.
    rear = spec.BLOCK["x_rear"] - 0.5
    over = 145.0
    out["fuel_rail_pfi_crossover"] = mesh.pipe(
        [ends[0], (rear, *ends[0][1:]), (rear, ends[0][1], over),
         (rear, ends[1][1], over), (rear, *ends[1][1:]), ends[1]], 3.0, SM,
        subdiv=3)
    return out


def _plenum():
    """A plenum outboard of each bank, feeding that bank's four ports.

    See the note in `spec.INTAKE`: the hot vee puts the intake ports on the
    outside of the heads, so this is where the air has to come from.
    """
    out = {}
    for bank, tag in ((0, "l"), (1, "r")):
        sgn = -1.0 if bank == 0 else 1.0
        y = sgn * I["plenum_y"]
        # A closed vessel with domed ends and a bolted end cap, not an
        # open-ended tube: as a tube it showed two black holes down the
        # front of the engine and held no pressure at all.
        L, R = I["plenum_len"] / 2, I["plenum_r"]
        v, f = mesh.revolve_closed(
            [(-L - 26.0, 0.0), (-L - 24.0, R * 0.34), (-L - 16.0, R * 0.72),
             (-L - 6.0, R * 0.94), (-L, R), (-L + 8.0, R * 1.04),
             (L - 8.0, R * 1.04), (L, R), (L + 6.0, R * 0.94),
             (L + 16.0, R * 0.72), (L + 24.0, R * 0.34), (L + 26.0, 0.0)],
            SEG)
        v = [(x, py + y, pz + I["plenum_z"]) for (x, py, pz) in v]
        out[f"plenum_{tag}"] = (v, f)
        # throttle body on the front face of each
        # body, mounting flange and the butterfly on its spindle
        tr = I["throttle_r"]
        # A stub on the plenum's OUTBOARD face at mid-length.
        #
        # Nowhere else will take it. The front of this engine is a gear
        # tower reaching 241 mm out to drive the cams; aft of the block the
        # car's bodywork has closed in to 252 mm; and the intake camshaft
        # sits directly above the plenum's crown. Outboard is the sidepod,
        # which is 456 mm of room at this height.
        tr = I["throttle_r"]
        h0 = I["plenum_r"] * 0.86
        tparts = [mesh.tube(h0, h0 + 56.0, tr - 7.0, tr, 32)]
        tparts.append(mesh.tube(h0 + 48.0, h0 + 56.0, tr, tr + 10.0, 32))
        tparts.append(mesh.tube(h0, h0 + 7.0, tr, tr + 10.0, 32))
        bv, bf = mesh.revolve_closed(
            [(-2.0, 0.0), (-2.0, tr - 8.0), (2.0, tr - 8.0), (2.0, 0.0)], 32)
        tparts.append(([(px + h0 + 27.0, py, pz) for (px, py, pz) in bv], bf))
        sv, sf = mesh.cylinder(-tr, tr, 4.0, 14)
        tparts.append(([(pz + h0 + 27.0, py, px) for (px, py, pz) in sv], sf))
        tv, tf = mesh.join(*tparts)
        # the lathe runs along its own +x; point it outboard, along y
        tv = [(pz, sgn * px + y, py + I["plenum_z"]) for (px, py, pz) in tv]
        out[f"throttle_{tag}"] = (tv, tf)
    return out


def _trumpets():
    """One velocity stack per cylinder, standing inside its bank's plenum and
    pointing at that cylinder's runner mouth."""
    parts = []
    for (n, pair, bank, x, a) in spec.cylinders():
        sgn = -1.0 if bank == 0 else 1.0
        prof = [(0.0, I["trumpet_r_in"]),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"]),
                (I["trumpet_len"], I["trumpet_r_out"]),
                (I["trumpet_len"], I["trumpet_r_out"] - 3.0),
                (I["trumpet_len"] * 0.62, I["trumpet_r_in"] - 3.0),
                (0.0, I["trumpet_r_in"] - 3.0)]
        tv, tf = mesh.revolve_closed(prof, 26)
        # the lathe runs along its own +x; the stack points inboard, from the
        # outboard wall of the plenum towards the runner mouth
        tv = [(pz + x,
               sgn * (I["plenum_y"] + I["plenum_r"] * 0.6 - px),
               py + I["plenum_z"])
              for (px, py, pz) in tv]
        parts.append((tv, tf))
    return {"trumpets": mesh.join(*parts)}
