"""Sectionable hybrid machines, liquid-cooled inverter and split energy store.

Separate shells, windings, busbars and cells expose the architecture when
isolated. Power figures are design targets, not validated electromagnetic,
thermal or electrical safety ratings.
"""

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import gaspath

SM = spec.RES["small_revolve"]
import shapes
from parts import common

Y = spec.HYBRID
SEG = spec.RES["revolve"]
spec.PALETTE.setdefault("hv_orange", ((0.95, 0.19, 0.015), 0.0, 0.42))
spec.MATERIAL_MAP.update({
    "hv_": "hv_orange", "shield_hv": "braided",
    "mguk": "alu_forged", "mguk_rotor": "steel_nitrided",
    "mguk_stator": "steel_nitrided", "mguk_winding": "copper_wound",
    "mguh": "alu_forged", "mguh_rotor": "steel_nitrided",
    "mguh_stator": "steel_nitrided", "mguh_winding": "copper_wound",
    "inverter_busbar": "copper_wound", "inverter_cold": "alu_forged",
    "battery_busbar": "copper_wound", "battery_cooling": "alu_forged",
    "battery_cell": "alu_forged", "battery_service": "hv_orange",
})


def _shift(part, x=0.0, y=0.0, z=0.0):
    v, f = part
    return mesh.translate(v, x, y, z), f


def _tray(cx, cy, cz, sx, sy, sz, wall=3.0):
    return mesh.join(
        mesh.box(cx, cy, cz - sz / 2 + wall / 2, sx, sy, wall),
        *[mesh.box(cx + s * (sx - wall) / 2, cy, cz + wall / 2,
                   wall, sy, sz - wall) for s in (-1, 1)],
        *[mesh.box(cx, cy + s * (sy - wall) / 2, cz + wall / 2,
                   sx - 2 * wall, wall, sz - wall) for s in (-1, 1)])


def build():
    out = {}
    out.update(_mguk())
    out.update(_mguh())
    out.update(_electronics())
    out.update(_hv_loom())
    return out


def _hv_loom():
    """The high-voltage cables, clipped to the engine.

    These used to be Manhattan routes: every waypoint changed exactly one
    coordinate, so every bend was a right angle, and `side` put them 24 mm
    outboard of the plenums -- the widest thing on the engine. The result was
    a bright orange rectangular cage standing off the castings, touching
    nothing, and it was the first thing you saw in any render.

    Real HV cable on a hybrid power unit runs in shielded conduit clipped
    along the block, takes swept bends because 600 V cable has a bend radius,
    and never stands proud of the widest casting. So: a corridor down the
    crankcase flank at y 150 -- outboard of the crankcase at 101, inboard of
    the engine mounts at 210, and below the plenums, which start at z 30 --
    and enough waypoints that `mesh.pipe`'s subdivision has something to
    round off.
    """
    ix, iy, iz = Y["inverter_pos"]
    iw, _, ih = Y["inverter"]
    bx, by, bz = Y["battery_pos"]
    bw, bd, bh = Y["battery"]
    # The corridor.
    #
    # Not down the block's side at head height: the heads fill y 47 to 215
    # from z 59 to 224, the cam covers and the plenums fill everything
    # outboard of them, and a cable crossing from the vee to the flank at
    # that height goes through a cylinder head. The one clear way down is the
    # inverter's own aft face at x 336, which is behind the bellhousing at
    # 318, and then forward under the sump at y 168 -- outboard of the sump
    # at 92 and the scavenge lines at 150, inboard of the oil cooler at 194.
    # ...and it is not the same on both sides. The dry-sump tank fills
    # y -240 to -116 from z -206 to -78 and the oil cooler sits outboard of
    # it, so the left-hand run has to go outboard of the tank while the right
    # has a clear corridor close in.
    #
    # The drop is alongside the bellhousing, not behind it. At x 336 the
    # runs crossed the bellhousing's back face, which is where the gearbox
    # bolts on: across the flywheel in every render of the engine, and
    # through the gearbox in the car.
    flank_l, flank_r = 252.0, 176.0
    drop_x = 280.0
    under = -196.0
    out = {}
    # Both connectors on the inverter's aft face, side by side. One was on
    # its front face, so the two cables from it -- to the pack and to the
    # MGU-K -- left forward and turned straight back over the unit to reach
    # the drop at its aft face: a hairpin loop standing above the engine.
    #
    # On its two side faces, over the drop on each side.
    iy_half = Y["inverter"][1] / 2
    ax = drop_x

    def plug(sgn):
        return (ax, iy + sgn * (iy_half + 10.0), iz + ih * 0.1)

    out["inverter_connectors"] = mesh.join(*[
        shapes.connector(*plug(sgn), 28.0, 22.0, 16.0, 8)
        for sgn in (-1.0, 1.0)])
    out["battery_terminals"] = mesh.join(*[
        shapes.connector(bx - sgn * bw * 0.3, by + sgn * bd * 0.38,
                         bz + bh / 2 + 7.0, 34.0, 20.0, 14.0, 2)
        for sgn in (1.0, -1.0)])

    # Inverter down the bellhousing's flank and under the sump to the pack.
    #
    # The sump's floor is at z -180 and the pack's lid at -218, the whole
    # length of the engine, and that gap is where these run -- tight to the
    # bell on the way down and between the pan and the pack on the way
    # along. They used to drop at y 176 and 252 and run forward at -196
    # outboard of everything: with the MGU-K lead they framed the engine in
    # orange, the widest and lowest things on it.
    gap = -199.0
    for sgn, tag in ((-1.0, "1"), (1.0, "2")):
        src = plug(sgn)
        term = (bx - sgn * bw * 0.3, by + sgn * bd * 0.38, bz + bh / 2 + 7.0)
        path = [src,
                (drop_x, sgn * 118.0, iz - ih * 0.40),
                (drop_x, sgn * 168.0, 40.0),
                (drop_x, sgn * 169.0, -40.0),
                (drop_x - 26.0, sgn * 146.0, -150.0),
                (term[0] + sgn * 60.0 + 30.0, sgn * 128.0, gap),
                (term[0] + 30.0, term[1], gap),
                term]
        out[f"hv_store_{tag}"] = mesh.pipe(
            mesh.smooth_path(path, 3), 5.0, SM, subdiv=2)

    # and forward under the sump to the MGU-K on the crank nose, coming in
    # to its connector from outboard, round the underside of the timing case
    motor = (Y["mguk_x"] - 4.0, -Y["mguk_r"], 0.0)
    src = plug(-1.0)
    path = [src,
            (drop_x - 4.0, -120.0, iz - ih * 0.55),
            (drop_x - 2.0, -178.0, 30.0),
            (drop_x - 4.0, -179.0, -50.0),
            (drop_x - 30.0, -120.0, -160.0),
            (spec.BLOCK["x_rear"] - 60.0, -60.0, gap),
            (spec.BLOCK["x_front"] + 40.0, -60.0, gap),
            (spec.FRONT["case_front"] - 10.0, -80.0, -172.0),
            (motor[0], -126.0, -70.0),
            (motor[0], -118.0, 0.0),
            motor]
    out["hv_motor_k"] = mesh.pipe(
        mesh.smooth_path(path, 3), 6.0, SM, subdiv=2)
    out["hv_motor_k_connector"] = shapes.connector(*motor, 24.0, 20.0, 18.0, 3)

    # And one to each MGU-H. The turbos' bearing housings are roofed over
    # completely -- the primaries arch over them on one side, the collector
    # and its heat blanket sit on top, the compressor inlet on the other --
    # so the lead cannot reach the machine itself. It lands on a bulkhead
    # connector on top of the collector's blanket, over the turbine, and the
    # link down to the stator runs inside the wrap.
    #
    # They used to be dropped in between the primaries from a loop 390 mm up
    # over the left bank: the front one through primary 1, the rear one
    # through primary 7, and both hairpinning back over the vee.
    #
    # From each connector the lead runs aft along the top of the engine,
    # outboard of the two compressor inlets, which stand up the middle of
    # the vee to z 391, and over the primaries, which peak at 365; then down
    # behind the rear turbine, outboard of the inverter, into its plug.
    src = plug(-1.0)
    D = gaspath.COLLECTOR_DRUM
    for index, x in enumerate(spec.TURBO["x"]):
        c = gaspath.collector_path(0 if x < 0 else 2)[0]
        top = c[2] + D["r"] + 4.0
        term = (c[0] + 9.0, c[1], top + 7.0)
        out[f"hv_motor_h_connector_{index}"] = shapes.connector(
            c[0], c[1], top + 7.0, 18.0, 16.0, 14.0, 3)
        lane = -90.0 - 8.0 * index         # two leads side by side
        path = [term, (term[0] + 18.0, -26.0, top + 8.0)]
        if x < 0:
            path += [(-104.0, lane, top + 6.0), (104.0, lane, top + 6.0)]
        path += [(214.0, lane - 4.0, top - 2.0),
                 (248.0, lane - 8.0, top - 28.0),
                 (274.0, lane - 12.0, top - 76.0),
                 (src[0] + 14.0, lane - 14.0, src[2] + 40.0),
                 (src[0] + 4.0, -116.0 + 2.0 * index, src[2] + 12.0 - 8.0 * index),
                 (src[0], src[1], src[2] + 4.0 - 8.0 * index)]
        out[f"hv_motor_h_{index}"] = mesh.pipe(
            mesh.smooth_path(path, 3), 4.0, SM, subdiv=2)
    return out


def _mguk():
    """Crankshaft motor-generator packaging envelope."""
    # bored to the nose it is keyed to: at nose_r + 4 it was a ring hanging
    # round the shaft that drives it
    v, f = mesh.tube(Y["mguk_x"] - Y["mguk_len"] / 2, Y["mguk_x"] + Y["mguk_len"] / 2,
                     spec.CRANK["nose_r"], Y["mguk_r"], SEG)
    fins = []
    for k in range(28):
        a = 2 * math.pi * k / 28
        fv, ff = shapes.rounded_box(Y["mguk_x"], Y["mguk_r"] + 5.0, 0.0,
                                    Y["mguk_len"] * 0.86, 11.0, 3.0, 1.2)
        fins.append((mesh.rot_x(fv, a), ff))
    return {"mguk": mesh.join((v, f), *fins)}


def _mguh():
    """Turbo-shaft motor-generator packaging envelopes."""
    parts = []
    for x in spec.TURBO["x"]:
        # bored to the shaft, not to 2.5 times it. An MGU-H rotor is pressed
        # onto the turbo shaft -- that is the whole machine. At a 22.5 mm bore
        # on a 9 mm shaft it was a sleeve hanging in the bearing housing with
        # a 13 mm annulus between it and the thing it is supposed to drive.
        v, f = mesh.tube(x - Y["mguh_len"] / 2, x + Y["mguh_len"] / 2,
                         spec.TURBO["shaft_r"], Y["mguh_r"], SM)
        v = [(px, py, pz + spec.TURBO["z"]) for (px, py, pz) in v]
        parts.append((v, f))
    return {"mguh": mesh.join(*parts)}


def _electronics():
    """Finned inverter, split energy-store and ECU packaging with connectors."""
    out = {}
    ix, iy, iz = Y["inverter_pos"]
    sx, sy, sz = Y["inverter"]
    out["inverter"] = shapes.finned_case(ix, iy, iz, sx, sy, sz,
                                         n_fins=11, fin_h=7.0, fin_t=3.4,
                                         r=7.0, axis="x")
    out["inverter_connectors"] = mesh.join(
        shapes.connector(ix - sx * 0.5 - 12.0, iy, iz + sz * 0.1, 28.0, 22.0, 16.0, 8),
        shapes.connector(ix + sx * 0.5 + 12.0, iy, iz + sz * 0.1, 28.0, 22.0, 16.0, 8))

    bx, by, bz = Y["battery_pos"]
    sx, sy, sz = Y["battery"]
    # Two flat lobes straddling the sump keel, not one slab hung underneath
    # it. Underneath, the pack was either inside the oil pan or -- once it had
    # been dropped clear of it -- 106 mm below the floor of the engine bay
    # when this engine is installed in the car. Beside the keel it clears the
    # sump and stays inside the bay, which is also where a real energy store
    # goes: low and flat, either side of the centreline.
    # Each lobe's inboard face is set from the pan's own half-width, so the
    # clearance holds if the pan is ever reshaped -- rather than from a
    # fraction that happened to look right once.
    lobe_y = sy * 0.28
    inner = spec.ANCILLARY["sump_w"] / 2 + 10.0
    lobe_c = inner + lobe_y / 2
    out["battery"] = mesh.join(*[
        shapes.finned_case(bx, by + sgn * lobe_c, bz,
                           sx, lobe_y, sz, n_fins=14, fin_h=5.0, fin_t=3.0,
                           r=8.0, axis="x", side=-1.0)
        for sgn in (-1.0, 1.0)])
    # the modules inside it, visible when the case is hidden
    mods = []
    for i in range(6):
        f = (i + 0.5) / 6
        for sgn in (-1.0, 1.0):
            mods.append(shapes.rounded_box(
                bx - sx / 2 + sx * f, by + sgn * lobe_c, bz,
                sx / 7.6, lobe_y * 0.78, sz * 0.72, 4.0))
    # a through-bolt strap: without it the modules float inside a case they
    # never touch. The strap crosses both lobes and pierces their walls, so
    # the pack is one structurally honest object.
    mods.append(shapes.rounded_box(
        bx, by, bz, sx * 0.42, lobe_c * 2 + lobe_y, sz * 0.30, 3.0))
    out["battery_modules"] = mesh.join(*mods)
    out["battery_terminals"] = mesh.join(
        # outboard of the bedplate, which fills the middle of this face
        shapes.connector(bx - sx * 0.3, by + sy * 0.38, bz + sz * 0.5 + 7.0,
                         34.0, 20.0, 14.0, 2),
        shapes.connector(bx + sx * 0.3, by - sy * 0.38, bz + sz * 0.5 + 7.0,
                         34.0, 20.0, 14.0, 2))

    a = spec.ANCILLARY
    sx, sy, sz = a["ecu"]
    # On top of the right bank's plenum. At y 132 it was inside the cam
    # cover, the camshaft and four of the lobes.
    # Low on the block's right flank, below the plenum and outboard of
    # the engine mounts. On top of the plenum it was inside the cam cover;
    # directly under it, it was in the intake runners.
    # Inboard to 150 from 206, and forward, so it lands on the right engine
    # mount. At 206 it was bolted to nothing: the ECU and its connector were
    # a two-part island 66 mm off the side of the engine, which no audit here
    # could see because not touching was what all of them were looking for.
    # On the rear right engine mount, at x 150, z -50. The mounts are two
    # brackets per bank and nothing else, so a box centred on x 0 had no
    # bracket anywhere near it whatever height it sat at. At (0, 206, -80)
    # the ECU and its connector were a two-part island beside the engine,
    # bolted to nothing: the ECU and its connector were a two-part island beside
    # the engine, which no audit here could see because not touching was
    # what every one of them was looking for.
    # y 196 and x 124, not 206 and 130. The hypercar that carries this engine
    # closes its bodywork 2 mm inside the box's aft outboard corner, so the
    # ECU stood 2.3 mm proud of the car -- a part that fits the engine on its
    # own and not the thing the engine goes in.
    # x 0, not 124. The right engine mount's bracket spans x 114 to 186 at
    # this height and the box is 168 long, so at 124 it straddled the
    # bracket -- 138 of its vertices inside it. Forward of the bracket it
    # bolts to its front face instead of sitting inside it, which is also
    # what the joint audit means by engine management being bolted to the
    # engine: at x 0 it was clear of the bracket and 30 mm from anything.
    # And forward to x 24.5 when the mounts moved to x -95: its front face on
    # the aft face of the right mount's foot, bolted to it.
    ex, ey, ez = -59.5 + sx / 2, 196.0, -50.0
    out["ecu"] = shapes.finned_case(ex, ey, ez, sx, sy, sz,
                                    n_fins=9, fin_h=5.0, fin_t=2.6, r=5.0)
    # the loom plugs into the aft face; the front face is on the bracket
    out["ecu_connector"] = shapes.connector(ex + sx * 0.5 + 10.0, ey, ez,
                                            22.0, sy * 0.6, sz * 0.5, 10)
    return out
