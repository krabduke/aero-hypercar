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

PT = spec.POWERTRAIN


# Every module name the engine and the car both define. If one of these is
# left resolved to the car's copy while the engine builds, the engine quietly
# comes out made of the car's primitives -- which is what happened to
# `shapes`: the two files are near-identical siblings, so it built and looked
# plausible for as long as they stayed in step, and broke the moment the
# engine grew a primitive the car did not have.
SHADOWED = ("spec", "mesh", "shapes", "airfoil")


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
                 "turbo", "hybrid", "drive", "detail")]
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
    parts = []
    for name, (verts, faces) in built.items():
        parts.append(([(x + PT["engine_x"], y, z + PT["engine_z"])
                       for (x, y, z) in verts], faces))
    out["engine"] = mesh.join(*parts)

    # The gearbox bolts to the back of the engine: it is a fully stressed
    # member, so the joint is the load path for the whole rear of the car.
    # Its station used to be a number in the spec that had drifted 34 mm
    # clear of the engine's rear face, leaving the two structural halves of
    # the car not touching.
    x_rear = max(v[0] for v in out["engine"][0])
    out["gearbox"] = _gearbox(x_rear)
    # A radiator drawn as a solid block is the laziest part on a car. These
    # are cores: tubes with fin packs between them, in a frame, with header
    # tanks top and bottom and the hoses that feed them.
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        x, y, z = PT["rad_x"], sgn * PT["rad_y"], PT["rad_z"]
        sx, sy, sz = PT["radiator"]
        out[f"radiator_{tag}"] = shapes.core(x, y, z, sx, sy, sz,
                                             n_tubes=16, n_fins=30)
        tanks = []
        for dz in (-sz / 2 - 26.0, sz / 2 + 26.0):
            tanks.append(shapes.rounded_box(x, y, z + dz, sx * 0.98,
                                            sy * 1.25, 46.0, 18.0))
        out[f"rad_tanks_{tag}"] = mesh.join(*tanks)
        hoses = []
        for dz, xe in ((-sz / 2 - 26.0, -1.0), (sz / 2 + 26.0, 1.0)):
            path = [(x + sx * 0.42 * xe, y, z + dz),
                    (x + sx * 0.58 * xe, y * 0.82, z + dz * 0.86),
                    (x + sx * 0.70 * xe, y * 0.62, z + dz * 0.7),
                    ((x + sx * 0.70 * xe + PT["engine_x"]) / 2, y * 0.44,
                     (z + dz * 0.7 + PT["engine_z"] + dz * 0.5) / 2),
                    (PT["engine_x"], y * 0.28, PT["engine_z"] + dz * 0.5)]
            # a moulded hose swells where it is unsupported and necks down
            # into each stub
            hoses.append(mesh.pipe(
                path, [30.0, 35.0, 37.0, 35.0, 30.0], 24, subdiv=4))
            # and it is held on by a clamp at each end, which is the part
            # that actually fails
            for (pt, nxt) in ((path[0], path[1]), (path[-1], path[-2])):
                d = tuple(nxt[k] - pt[k] for k in range(3))
                cv, cf = mesh.revolve_closed(
                    [(14.0, 31.0), (30.0, 31.0), (30.0, 37.0),
                     (14.0, 37.0)], 24)
                hoses.append((shapes.orient(cv, pt, d), cf))
        out[f"rad_hoses_{tag}"] = mesh.join(*hoses)

    bx, by, bz = PT["battery_x"], 0.0, PT["battery_z"]
    sx, sy, sz = PT["battery"]
    out["battery"] = shapes.finned_case(bx, by, bz, sx, sy, sz,
                                        n_fins=12, fin_h=9.0, fin_t=4.0,
                                        r=14.0, side=-1.0)
    mods = []
    for i in range(5):
        f = (i + 0.5) / 5
        mods.append(shapes.rounded_box(bx - sx / 2 + sx * f, by, bz,
                                       sx / 6.2, sy * 0.8, sz * 0.7, 6.0))
    out["battery_modules"] = mesh.join(*mods)

    # a fuel cell is a bladder in a shaped bay, not a cuboid
    fx, fy, fz = PT["fuel_x"], 0.0, 330.0
    sx, sy, sz = PT["fuel"]
    out["fuel_cell"] = shapes.rounded_box(fx, fy, fz, sx, sy, sz,
                                          r=60.0, seg=6, draft=3.0)
    out["fuel_fittings"] = mesh.join(
        mesh.pipe([(fx + sx * 0.3, 0.0, fz + sz * 0.5),
                   (fx + sx * 0.6, 0.0, fz + sz * 0.62)], 24.0, 10),
        shapes.rounded_box(fx - sx * 0.3, 0.0, fz + sz * 0.5 + 18.0,
                           110.0, 110.0, 36.0, 12.0))
    return out


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
