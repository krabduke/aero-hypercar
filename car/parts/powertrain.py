"""Power unit, gearbox, radiators, battery and fuel cell.

The engine is the RX-8V from the sibling project, imported and positioned --
not re-modelled. It is mounted as a fully stressed member between the tub and
the gearbox, which is why the car can be this short.
"""

import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import spec
import mesh
import shapes
from parts import chassis, common

PT = spec.POWERTRAIN


# Every module name the engine and the car both define. If one of these is
# left resolved to the car's copy while the engine builds, the engine quietly
# comes out made of the car's primitives -- which is what happened to
# `shapes`: the two files are near-identical siblings, so it built and looked
# plausible for as long as they stayed in step, and broke the moment the
# engine grew a primitive the car did not have.
SHADOWED = ("spec", "mesh", "shapes", "airfoil")


T_REAR = spec.TUB["x_rear"]

def _load_engine():
    """Import the power-unit generators with powerunit/ ahead on the path, so
    their modules resolve their own `spec` rather than the car's."""
    saved = {k: v for k, v in sys.modules.items()
             if k in SHADOWED or k.startswith("parts")}
    for k in list(saved):
        del sys.modules[k]
    pu = os.path.join(HERE, "powerunit")
    sys.path.insert(0, pu)
    try:
        espec = importlib.import_module("spec")
        eshapes = importlib.import_module("shapes")
        if not os.path.abspath(eshapes.__file__).startswith(pu):
            raise RuntimeError(
                f"the engine is building with {eshapes.__file__}, not its own "
                "vendored primitives -- add the module to SHADOWED")
        # The engine is a 554k-vertex model on its own. Most of it is buried
        # inside the car and much of the rest is behind the engine cover, so
        # it is built at about two thirds resolution: enough that a cam lobe
        # is still a lobe in the cutaway, without doubling the download.
        espec.RES.update({"revolve": 56, "small_revolve": 20, "pipe": 14})
        # every module the engine's own assemble.py builds, in the same
        # order. Miss one and the car quietly carries a different engine from
        # the one in the engine project -- which is exactly what happened:
        # detail and plumbing were absent and the car was 111 parts behind.
        mods = [importlib.import_module(f"parts.{m}") for m in
                ("block", "bottomend", "heads", "plumbing", "induction",
                 "turbo", "hybrid", "drive", "detail", "ancillaries",
                 "harness")]
        built = {}
        for m in mods:
            built.update(m.build())
        return built, espec
    finally:
        sys.path.remove(pu)
        for k in list(sys.modules):
            if k in SHADOWED or k.startswith("parts"):
                del sys.modules[k]
        sys.modules.update(saved)


def build():
    out = {}
    built, espec = _load_engine()
    # the engine's +x is its crank axis; the car's +x is rearward, and the
    # engine sits with its flywheel toward the gearbox
    # The engine comes with a hybrid pack and an inverter of its own,
    # because as a standalone model it has to. This car has both already --
    # its own pack sits in the tub at x 2040 and its own power electronics
    # with it -- so the vendored copies are left out rather than carried
    # twice. They were also the lowest and the widest things on the engine,
    # which is why it would not fit between the floor and the sidepod.
    #
    # `hv_store` and `hv_motor` join the list. They are the power unit's own
    # high-voltage loom, and this car has its own -- but more than that, the
    # gearbox below is placed at the engine's rearmost vertex, and that
    # cable runs 51 mm past the bellhousing flange. With it installed the
    # gearbox was hung off the end of a wire instead of bolted to the bell,
    # and the two structural halves of the car stopped touching.
    #
    # The motor-generators stay: they are the engine's own machines, not
    # power electronics. The MGU-K is on the crank nose and carries the
    # crank sensor's bracket, and it is what starts the engine.
    # (and the port covers are the engine's shipping plugs: in the car the
    # airbox and the exhaust are on those flanges instead)
    CAR_PROVIDES = ("battery", "battery_modules", "battery_terminals",
                    "inverter", "inverter_connectors",
                    "hv_store", "hv_motor", "port_covers")
    # The castings the engine cuts -- its bores out of the block, its
    # chambers out of the heads -- are carried as parts of their own with
    # their cutters. Joined into the one "engine" mesh, a cutter would either
    # have gone in as solid geometry, rods filling every bore, or taken the
    # pistons out along with the metal round them.
    def place(verts):
        return [(x + PT["engine_x"], y, z + PT["engine_z"]) for (x, y, z) in verts]
    cut = {k[4:]: v for k, v in built.items() if k.startswith("cut:")}
    parts = []
    for name, (verts, faces) in built.items():
        if name.startswith("cut:") or name.startswith(CAR_PROVIDES):
            continue
        if name in cut:
            out[f"engine_{name}"] = (place(verts), faces)
            out[f"cut:engine_{name}"] = (place(cut[name][0]), cut[name][1])
            continue
        parts.append((place(verts), faces))
    out["engine"] = mesh.join(*parts)

    # The gearbox bolts to the back of the engine: it is a fully stressed
    # member, so the joint is the load path for the whole rear of the car.
    # Its station used to be a number in the spec that had drifted 34 mm
    # clear of the engine's rear face, leaving the two structural halves of
    # the car not touching.
    #
    # It bolts to the BELLHOUSING, which is the flange it is actually held
    # by, and not to whatever vertex of the engine happens to be furthest
    # aft. That was a high-voltage cable once, and then -- when the turbine
    # outlet moved back past the wheel where it belongs, and the tailpipe
    # behind it with it -- it was a tailpipe, which pushed the whole gearbox
    # 36 mm aft and 1.2 mm out through the car's own bodywork.
    bell_v, _bell_f = built["bellhousing"]
    x_rear = max(v[0] for v in bell_v) + PT["engine_x"]
    # The crash structure bolts to the back of the gearbox from the spec's
    # number; when the two disagreed it was hung 42 mm behind the casing.
    assert abs(x_rear - PT["gearbox_front_x"]) < 1.0, \
        f"gearbox_front_x is {PT['gearbox_front_x']}, the bellhousing is " \
        f"at {x_rear:.1f}"
    out["gearbox"] = _gearbox(x_rear)
    # A radiator drawn as a solid block is the laziest part on a car. These
    # are cores: tubes with fin packs between them, in a frame, with header
    # tanks at each end and the hoses that feed them.
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        x, y, z = PT["rad_x"], sgn * PT["rad_y"], PT["rad_z"]
        sx, sy, sz = PT["radiator"]
        # Baffles from the core's top and bottom edges to the pod's skin, so
        # the air in the pod goes through the core and not round it -- the
        # seal every ducted radiator has, and the only thing joining the
        # core to the duct it sits in.
        baffles = []
        for roof in (False, True):
            rings = []
            for i in range(9):
                bx = x - sx / 2 + sx * i / 8
                zs = chassis.sidepod_floor(bx, y, roof)
                zs += -0.5 if roof else 0.5
                ze = z + (sz / 2 - 2.0 if roof else -sz / 2 + 2.0)
                lo, hi = (ze, zs) if roof else (zs, ze)
                rings.append([(bx, y - 2.0, lo), (bx, y + 2.0, lo),
                              (bx, y + 2.0, hi), (bx, y - 2.0, hi)])
            baffles.append(common.loft(rings))
        out[f"radiator_{tag}"] = mesh.join(
            shapes.core(x, y, z, sx, sy, sz, n_tubes=16, n_fins=30),
            *baffles)
        tanks = []
        for dx in (-sx / 2 - 26.0, sx / 2 + 26.0):
            tanks.append(shapes.rounded_box(x + dx, y, z, 46.0,
                                            sy * 1.25, sz * 0.98, 18.0))
            # and a foot under each tank, down to the pod's floor: the core
            # was held in the pod by nothing but its own hoses
            z_tank = z - sz * 0.49
            z_floor = chassis.sidepod_floor(x + dx, y) + 0.5
            if z_tank - z_floor > 1.0:
                tanks.append(shapes.rounded_box(
                    x + dx, y, (z_tank + z_floor) / 2 + 2.0, 40.0, 70.0,
                    z_tank - z_floor + 4.0, 6.0))
        out[f"rad_tanks_{tag}"] = mesh.join(*tanks)
    out.update(_rad_hoses(espec))
    out.update(_lt_loop(espec))

    bx, by, bz = PT["battery_x"], 0.0, PT["battery_z"]
    sx, sy, sz = PT["battery"]
    out["battery"] = shapes.finned_case(bx, by, bz, sx, sy, sz,
                                        n_fins=12, fin_h=9.0, fin_t=4.0,
                                        r=14.0, side=-1.0)
    mods = []
    for i in range(5):
        f = (i + 0.5) / 5
        # 0.96 of the case's width, not 0.8: at 0.8 the modules stopped
        # 16 mm short of the wall and the pack was a box with a second box
        # rattling inside it.
        mods.append(shapes.rounded_box(bx - sx / 2 + sx * f, by, bz,
                                       sx / 6.2, sy * 0.96, sz * 0.7, 6.0))
    out["battery_modules"] = mesh.join(*mods)

    fx, fy, fz = PT["fuel_x"], 0.0, PT["fuel_z"]
    sx, sy, sz = PT["fuel"]
    out["fuel_cell"] = _bladder(fx, fy, fz, sx, sy, sz)
    # ...and the line carries on to the engine. It used to stop at x 2716
    # with the engine's front face at 2868, so the cell fed nothing.
    #
    # It feeds the engine's low-pressure side, the port-injection rail, whose
    # front end is on the right flank. Through the bulkhead the hose becomes
    # a 16 mm line that climbs the bulkhead's aft face -- forward of the
    # crank damper and the belt, which are the front of the engine -- and
    # crosses to the right over the top radiator hose, then runs aft outboard
    # of the timing case to the rail. It used to end in the middle of the
    # timing case, which is hollow.
    bh_aft = T_REAR + 11.0             # the engine bulkhead's aft eyelets
    ex, ez = PT["engine_x"], PT["engine_z"]
    rail = (ex - 161.5, 244.9, ez + 136.0)     # the rail's front end
    lane_x = bh_aft + 9.0
    z_run = ez + 134.0
    z_top = ez + 188.0                          # over the top hose
    out["fuel_fittings"] = mesh.join(
        mesh.pipe([(fx + sx * 0.3, 0.0, fz + sz * 0.5),
                   (fx + sx * 0.6, 0.0, fz + sz * 0.62),
                   # down through the engine bulkhead's aperture
                   (T_REAR - 50.0, 0.0, fz + sz * 0.25),
                   (bh_aft - 6.0, 0.0, z_run)], 24.0, 10),
        mesh.pipe([(bh_aft - 20.0, 0.0, z_run), (lane_x, 0.0, z_run),
                   (lane_x, 0.0, z_top), (lane_x, 252.0, z_top),
                   (rail[0] - 70.0, 252.0, z_top),
                   # the hose pushes on over the rail's 22 mm inlet nipple
                   (rail[0] - 44.0, rail[1], rail[2]),
                   (rail[0] - 10.0, rail[1], rail[2])], 8.0, 12,
                  bend=18.0),
        shapes.rounded_box(fx - sx * 0.3, 0.0, fz + sz * 0.5 + 18.0,
                           110.0, 110.0, 36.0, 12.0))
    return out


def _rad_hoses(espec):
    """The main radiators' hoses, onto the engine's own cooling stubs.

    The engine has an outlet stub each side of its thermostat and a return
    stub on the tee at its water pump's inlet, on the right. Each radiator
    is fed from the stub on its own side; both return through a Y beside
    the pump. The left radiator's return is the one hose that has to cross
    the car, and it crosses in the bay between the fuel cell and the engine
    bulkhead, over the battery -- the front of the engine is 9 mm from the
    bulkhead, and nothing crosses there.

    These used to land on nothing: all four ended at the engine's mid-length,
    95 mm either side of the crank, in the middle of its cylinder banks,
    where the engine has no port of any kind. They were 60 to 74 mm moulded
    hoses; the stubs are 28 mm, and so, now, are the hoses' bores.
    """
    out = {}
    r = 18.0
    P, yj, ret = rad_hose_paths(espec)
    # the two feeds as one part and the returns as another: the two sides
    # are not mirror images -- each feed takes the one way out past the
    # front of the engine that its side has, and both returns meet in one Y
    groups = {"hot": [P["l"][0], P["r"][0]],
              "return": P["l"][1:] + P["r"][1:]}
    for tag, paths in groups.items():
        hoses = []
        for path in paths:
            hoses.append(mesh.pipe(path, r, 24, subdiv=3))
            for (pt, nxt) in ((path[0], path[1]), (path[-1], path[-2])):
                if pt == yj:
                    continue
                d = tuple(nxt[k] - pt[k] for k in range(3))
                cv, cf = mesh.revolve_closed(
                    [(4.0, r + 0.5), (16.0, r + 0.5), (16.0, r + 3.5),
                     (4.0, r + 3.5)], 24)
                hoses.append((shapes.orient(cv, pt, d), cf))
        if tag == "return":
            # the Y, a moulded junction the two returns and the pump hose
            # push onto
            hoses.append(shapes.rounded_box(*yj, 50.0, 50.0, 50.0, 22.0))
        out[f"rad_hoses_{tag}"] = mesh.join(*hoses)
    return out


def rad_hose_paths(espec):
    """({"l": [path, ...], "r": [...]}, the return Y, the return stub):
    every main-radiator hose's centreline, stub end last where it has one."""
    ex, ez = PT["engine_x"], PT["engine_z"]

    def eng(p):
        return (p[0] + ex, p[1], p[2] + ez)

    C = espec.COOLANT
    drop = espec.STAT_STUB_DROP
    stat = {s: eng((C["stat_x"] + espec.STAT_STUB_X, s * 80.0,
                    C["stat_z"] - drop)) for s in (-1.0, 1.0)}
    ret = eng((C["pump_x"] + 52.0, C["pump_y"] + 75.0, C["pump_z"]))
    x, z = PT["rad_x"], PT["rad_z"]
    sx, sy, sz = PT["radiator"]
    x_t = x + sx / 2 + 26.0                  # the aft tank, which is divided
    z_in, z_out = z + sz * 0.30, z - sz * 0.30
    y_r = PT["rad_y"]
    yj = (ret[0] - 82.0, ret[1] + 40.0, ret[2] + 4.0)    # the return Y
    P = {}
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        st = stat[sgn]
        paths = []
        # this side's radiator, in at the top of its aft tank <- the stub
        # The front of the engine is a belt, its idler and tensioner, the
        # HP fuel pump and the breather hose, all within 60 mm of the
        # bulkhead, and these are the ways out found clear of all of it by
        # tools/route_solve: on the left over the breather's descent and in
        # front of it, on the right down under the HP pump and out along
        # its underside, then forward past the bulkhead's edge into the pod.
        if sgn < 0:
            mid = [(2910.0, -192.0, 444.0), (st[0] - 2.0, -174.0, st[2])]
        else:
            mid = [(2652.0, 480.0, 396.0), (st[0] - 2.0, 204.0, 396.0),
                   (st[0] - 2.0, 162.0, 396.0)]
        paths.append([(x_t, sgn * y_r, z_in), (x_t + 43.0, sgn * y_r, z_in)]
                     + mid
                     + [(st[0], sgn * 130.0, st[2]),
                        (st[0], st[1] - sgn * 18.0, st[2])])
        # out at the bottom, back to the Y
        if sgn > 0:
            paths.append([(x_t, y_r, z_out), (x_t + 78.0, y_r - 10.0, z_out - 2.0),
                          yj])
            # and the one hose from the Y onto the pump's return stub
            paths.append([yj, (ret[0] - 12.0, yj[1] + 2.0, ret[2] + 2.0),
                          (ret[0], ret[1] + 28.0, ret[2]),
                          (ret[0], ret[1] - 18.0, ret[2])])
        else:
            paths.append([(x_t, -y_r, z_out), (x_t + 78.0, -y_r + 10.0, z_out + 6.0),
                          (2745.0, 0.0, 300.0), (2790.0, 250.0, 276.0),
                          (2870.0, 326.0, 252.0), yj])
        P[tag] = paths
    return P, yj, ret


def _lt_loop(espec):
    """The charge coolers' low-temperature loop, one per side.

    The engine's charge coolers are water-to-air, in its plenums, and each
    ends in two hose stubs on the plenum's outboard face -- the engine
    leaves its cooling loops to the vehicle, as it does the main one. This is
    that loop: a small core in the sidepod behind the main radiator, where
    the pod's air has already been through the main core but is still far
    colder than charge air; an electric pump on its outlet; and the two
    hoses in to the stubs. The core's aft tank is divided, in at the top
    and out at the bottom, so both hoses leave the same end and neither has
    to cross the other.
    """
    out = {}
    I = espec.INTAKE
    ex, ez = PT["engine_x"], PT["engine_z"]
    L = I["plenum_len"] / 2 - 34.0 + 14.0
    y_stub = I["plenum_y"] + 84.0            # the stubs' ends
    zs = ez + I["plenum_z"]
    cx, cy, cz = PT["lt_x"], PT["lt_y"], PT["lt_z"]
    sx, sy, sz = PT["lt_core"]
    xt = cx + sx / 2 + 20.0                 # the aft tank's centre
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        y = sgn * cy
        parts = [shapes.core(cx, y, cz, sx, sy, sz, n_tubes=10, n_fins=18)]
        for xc in (cx - sx / 2 - 20.0, xt):
            parts.append(shapes.rounded_box(xc, y, cz, 40.0, sy * 1.25,
                                            sz * 0.98, 12.0))
            # a foot under each tank, down to the pod's floor
            z_tank = cz - sz * 0.49
            z_floor = chassis.sidepod_floor(xc, y) + 0.5
            if z_tank - z_floor > 1.0:
                parts.append(shapes.rounded_box(
                    xc, y, (z_tank + z_floor) / 2 + 2.0, 34.0, 50.0,
                    z_tank - z_floor + 4.0, 5.0))
        out[f"rad_lt_{tag}"] = mesh.join(*parts)

        # the pump, on the tank's lower port, its axis inboard: volute
        # against the tank, motor inboard of it, the outlet tangential and
        # aft, and the motor's connector on its end
        y_face = sgn * (cy - sy * 0.625)        # the tank's inboard face
        zp = cz - sz * 0.27
        pump = [
            _lathe_y([(0.0, 0.0), (0.0, 16.0), (12.0, 16.0), (12.0, 0.0)],
                     xt, y_face + sgn * 2.0, zp, -sgn),         # port spigot
            _lathe_y([(0.0, 0.0), (0.0, 36.0), (4.0, 38.0), (26.0, 38.0),
                      (30.0, 34.0), (30.0, 0.0)],
                     xt, y_face - sgn * 10.0, zp, -sgn),        # volute
            _lathe_y([(0.0, 0.0), (0.0, 28.0), (70.0, 28.0), (74.0, 24.0),
                      (74.0, 0.0)],
                     xt, y_face - sgn * 40.0, zp, -sgn),        # motor
            shapes.rounded_box(xt, y_face - sgn * 118.0, zp, 24.0, 16.0,
                               20.0, 3.0),                      # connector
        ]
        out_pt = (xt + 38.0, y_face - sgn * 25.0, zp - 22.0)
        pump.append(mesh.pipe([(xt + 20.0, out_pt[1], out_pt[2]),
                               (out_pt[0] + 14.0, out_pt[1], out_pt[2])],
                              11.0, 16))                        # outlet
        # and a bracket from the motor down to the pod's floor
        z_floor = chassis.sidepod_floor(xt, y_face - sgn * 75.0) + 0.5
        pump.append(shapes.rounded_box(xt, y_face - sgn * 75.0,
                                       (zp - 27.0 + z_floor) / 2, 30.0, 20.0,
                                       zp - 27.0 - z_floor + 4.0, 3.0))
        out[f"rad_lt_pump_{tag}"] = mesh.join(*pump)

        hoses = []
        r_h = LT_HOSE_R
        for path in lt_hose_paths(espec)[tag]:
            hoses.append(mesh.pipe(path, r_h, 18, subdiv=3))
            for (pt, nxt) in ((path[0], path[1]), (path[-1], path[-2])):
                d = tuple(nxt[k] - pt[k] for k in range(3))
                cv, cf = mesh.revolve_closed(
                    [(6.0, r_h + 0.5), (18.0, r_h + 0.5), (18.0, r_h + 3.5),
                     (6.0, r_h + 3.5)], 20)
                hoses.append((shapes.orient(cv, pt, d), cf))
        out[f"rad_lt_hoses_{tag}"] = mesh.join(*hoses)

        # and its power: a lead from the motor's connector, in through the
        # pod's wall and the tub's (the path tools/route_solve found clear),
        # to a plug on the pack's aft face -- the pack's low-voltage side
        bx1 = PT["battery_x"] + PT["battery"][0] / 2
        plug = (bx1 + 4.0, sgn * 100.0, PT["battery_z"] + 10.0)
        lead = [(xt, y_face - sgn * 124.0, zp),
                (xt, y_face - sgn * 170.0, zp - 12.0),
                (xt - 4.0, sgn * 130.0, PT["battery_z"] + 40.0),
                (plug[0] + 8.0, plug[1], plug[2] + 6.0),
                (plug[0] + 2.0, plug[1], plug[2])]
        out[f"lt_pump_lead_{tag}"] = mesh.join(
            mesh.pipe(lead, 4.0, 12, bend=20.0),
            shapes.rounded_box(*plug, 14.0, 22.0, 18.0, 3.0))
    return out


LT_HOSE_R = 13.5


def lt_hose_paths(espec):
    """{"l": [path, ...], "r": [...]}: each side's two charge-cooler hoses,
    the engine's stub end last."""
    I = espec.INTAKE
    ex, ez = PT["engine_x"], PT["engine_z"]
    L0 = I["plenum_len"] / 2 - 34.0
    xf, xa = ex - L0 + 14.0, ex + L0 + 14.0     # the stubs, mid-tank
    y_stub = I["plenum_y"] + 84.0
    zs = ez + I["plenum_z"]
    cx, cy, cz = PT["lt_x"], PT["lt_y"], PT["lt_z"]
    sx, sy, sz = PT["lt_core"]
    xt = cx + sx / 2 + 20.0
    out = {}
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        y_face = sgn * (cy - sy * 0.625)
        zp = cz - sz * 0.27
        out_pt = (xt + 38.0, y_face - sgn * 25.0, zp - 22.0)
        # pump outlet -> the charge cooler's inlet, the plenum's front stub
        p_in = [(out_pt[0] + 6.0, out_pt[1], out_pt[2]),
                (out_pt[0] + 60.0, out_pt[1], out_pt[2]),
                (xf - 20.0, sgn * (y_stub + 60.0), zs - 30.0),
                (xf, sgn * (y_stub + 40.0), zs),
                (xf, sgn * (y_stub - 18.0), zs)]
        # the core's upper port -> the charge cooler's outlet, the aft stub
        p_out = [(xt, y_face + sgn * 6.0, cz + sz * 0.27),
                 (xt, sgn * (cy - 50.0), cz + sz * 0.27),
                 (xt + 120.0, sgn * (cy - 60.0), cz + sz * 0.27),
                 (xa - 120.0, sgn * (y_stub + 90.0), zs + 30.0),
                 (xa, sgn * (y_stub + 44.0), zs),
                 (xa, sgn * (y_stub - 18.0), zs)]
        out[tag] = [p_in, p_out]
    return out


def _lathe_y(profile, x, y, z, sgn):
    """Revolve an (along, radius) profile about a line parallel to y
    through (x, y, z), growing toward sgn * y."""
    v, f = mesh.revolve_closed(list(profile), 24)
    return shapes.orient(v, (x, y, z), (0.0, sgn, 0.0)), f


def _bladder(cx, cy, cz, sx, sy, sz, n_z=18, n_a=44):
    """The fuel cell: a rubber bladder that takes the shape of its bay.

    The comment here used to say "a fuel cell is a bladder in a shaped bay,
    not a cuboid" above a rounded box. It is not a cuboid: it is moulded to
    the tub, so it is widest where the tub is widest and its shoulders pull
    in under the engine cover, the bottom rolls into a sump the pickup can
    empty, and the top carries the filler and the vent. Fuel sloshing in a
    box is also why a real one is full of baffle foam -- that part is not
    modelled, because none of it can be seen.
    """
    # (height fraction, half-x scale, half-y scale, section exponent)
    table = [(0.00, 0.70, 0.58, 2.6), (0.10, 0.88, 0.86, 3.4),
             (0.32, 0.99, 1.00, 4.2), (0.64, 1.00, 1.00, 4.2),
             (0.86, 0.95, 0.90, 3.4), (1.00, 0.76, 0.66, 2.4)]

    def lerp(t):
        for i in range(len(table) - 1):
            a, b = table[i], table[i + 1]
            if t <= b[0] or i == len(table) - 2:
                f = (t - a[0]) / ((b[0] - a[0]) or 1.0)
                f = max(0.0, min(1.0, f))
                return tuple(a[k] + (b[k] - a[k]) * f for k in range(1, 4))
        return table[-1][1:]

    rings = []
    for k in range(n_z):
        t = k / (n_z - 1)
        hx, hy, n = lerp(t)
        z = cz - sz / 2 + sz * t
        ring = []
        for j in range(n_a):
            a = 2.0 * math.pi * j / n_a
            ca, sa = math.cos(a), math.sin(a)
            p = 2.0 / n
            ring.append((cx + sx / 2 * hx * math.copysign(abs(ca) ** p, ca),
                         cy + sy / 2 * hy * math.copysign(abs(sa) ** p, sa),
                         z))
        rings.append(ring)
    verts = [v for r in rings for v in r]
    faces = []
    for k in range(n_z - 1):
        a0, b0 = k * n_a, (k + 1) * n_a
        for j in range(n_a):
            j2 = (j + 1) % n_a
            faces.append((a0 + j, a0 + j2, b0 + j2, b0 + j))
    faces.append(tuple(range(n_a - 1, -1, -1)))
    base = (n_z - 1) * n_a
    faces.append(tuple(range(base, base + n_a)))
    parts = [(verts, faces)]

    # the collector: a small pot at the bottom that stays full under
    # cornering, so the pickup never sees air. It is mostly inside the
    # bladder, and its foot is what the cell stands on the battery by; 66 mm
    # of it hung below, into the pack.
    pv, pf = mesh.revolve_closed(
        [(0.0, 0.0), (0.0, 92.0), (12.0, 92.0), (20.0, 74.0), (20.0, 0.0)], 26)
    parts.append(([(py + cx + sx * 0.10, pz + cy, -px + cz - sz / 2 + 8.0)
                   for (px, py, pz) in pv], pf))
    # filler neck and the dry-break coupling on top of it
    nv, nf = mesh.revolve_closed(
        [(0.0, 0.0), (0.0, 54.0), (46.0, 54.0), (46.0, 62.0), (58.0, 62.0),
         (58.0, 44.0), (52.0, 40.0), (6.0, 40.0), (6.0, 0.0)], 24)
    parts.append(([(py + cx - sx * 0.26, pz + cy + sy * 0.20,
                    px + cz + sz / 2 - 10.0) for (px, py, pz) in nv], nf))
    # the roll-over vent valve, which is the other hole in the top
    vv, vf = mesh.revolve_closed(
        [(0.0, 0.0), (0.0, 26.0), (18.0, 26.0), (24.0, 20.0), (24.0, 9.0),
         (44.0, 9.0), (44.0, 0.0)], 18)
    # forward of the control boxes on the cell's lid, not under one
    parts.append(([(py + cx + sx * 0.42, pz + cy - sy * 0.24,
                    px + cz + sz / 2 - 6.0) for (px, py, pz) in vv], vf))
    return mesh.join(*parts)


def _gearbox(x_front=None):
    """The gearbox casing, which is a structural member and not a cylinder.

    It bolts to the back of the engine and carries the entire rear
    suspension, the rear wing pylons and the crash structure, so it is a
    ribbed casting with a bolt flange at the front, pickups moulded into its
    flanks, a diff bulge across the middle, output bearing housings either
    side and the selector barrel housing on top. A plain tube was carrying
    all of that on nothing.
    """
    gx = PT["gearbox_x"] if x_front is None else x_front
    L = PT["gearbox_len"]
    R = PT["gearbox_r"]
    z = PT["gearbox_z"]
    parts = []
    # main case: a waisted body, deep at the diff and drawn in at the tail
    rings = []
    for (f, sy, sz_, dz) in ((0.00, 1.00, 1.00, 0.0), (0.06, 1.02, 1.02, 0.0),
                             (0.22, 0.92, 0.96, -6.0), (0.44, 0.86, 1.04, -4.0),
                             (0.62, 0.90, 1.06, 0.0), (0.80, 0.76, 0.88, 6.0),
                             (0.94, 0.58, 0.70, 12.0), (1.00, 0.52, 0.62, 14.0)):
        ring = []
        for i in range(40):
            a = 2 * math.pi * i / 40
            ca, sa = math.cos(a), math.sin(a)
            e = 2.0 / 2.7                       # squared off, like a casting
            ring.append((gx + L * f,
                         R * sy * math.copysign(abs(ca) ** e, ca),
                         z + dz + R * sz_ * math.copysign(abs(sa) ** e, sa)))
        rings.append(ring)
    parts.append(shapes._loft_closed(rings))
    # bolt flange onto the back of the engine
    fv, ff = mesh.flange(gx, R * 0.62, R * 1.18, 16.0, 14, bolt_r=7.0)
    parts.append(([(px, py, pz + z) for (px, py, pz) in fv], ff))
    # ribs down the flanks
    for i in range(7):
        f = 0.12 + 0.11 * i
        for sgn in (-1.0, 1.0):
            parts.append(shapes.rounded_box(
                gx + L * f, sgn * R * 0.84, z + 10.0, 16.0, 30.0,
                R * 1.20, 5.0, seg=5))
    # output bearing housings, where the driveshafts leave
    for sgn in (-1.0, 1.0):
        ov, of = mesh.revolve_closed(
            [(0.0, 0.0), (54.0, 0.0), (54.0, 44.0), (46.0, 54.0),
             (16.0, 62.0), (0.0, 68.0)], 30)
        parts.append(([(px + gx + L * 0.40, sgn * pz + sgn * R * 0.78,
                        py + z - 14.0) for (px, py, pz) in ov], of))
    # suspension pickups on the case: two per side, plus the wing pylon feet
    # Inside the bodywork: the wishbones reach them through slots in the
    # cover, which is how it is done. Standing them proud put the upper pair
    # 32 mm through the engine cover.
    for sgn in (-1.0, 1.0):
        for (f, dz) in ((0.30, 85.0), (0.66, 85.0),
                        (0.34, -70.0), (0.70, -70.0)):
            parts.append(shapes.rounded_box(
                gx + L * f, sgn * R * 0.62, z + dz, 60.0, 44.0, 46.0,
                8.0, seg=5))
    # Selector barrel housing along the upper flank. On top of the case it
    # stood 37 mm through the engine cover, which tapers hard over the
    # gearbox -- a real one is offset for exactly that reason.
    parts.append(shapes.rounded_box(gx + L * 0.42, -R * 0.46, z + R * 0.52,
                                    L * 0.52, 82.0, 70.0, 16.0, seg=6))
    # and the actuator that drives it
    parts.append(mesh.revolve_closed(
        [(gx + L * 0.10, 0.0), (gx + L * 0.26, 0.0), (gx + L * 0.26, 24.0),
         (gx + L * 0.12, 28.0), (gx + L * 0.10, 22.0)], 24))
    v, f = parts[-1]
    parts[-1] = ([(px, py - R * 0.46, pz + z + R * 0.52)
                  for (px, py, pz) in v], f)
    # oil pump and cooler union on the flank
    parts.append(mesh.revolve_closed(
        [(gx + L * 0.20, 0.0), (gx + L * 0.20 + 60.0, 0.0),
         (gx + L * 0.20 + 60.0, 38.0), (gx + L * 0.20, 44.0)], 24))
    v, f = parts[-1]
    parts[-1] = ([(px, py - R * 0.92, pz + z - 40.0)
                  for (px, py, pz) in v], f)
    return mesh.join(*parts)
