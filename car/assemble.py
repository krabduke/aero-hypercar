"""Build the car in Blender. Run under `blender --background`."""

import csv
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import spec              # noqa: E402
import mesh as meshlib   # noqa: E402
import materials         # noqa: E402
from parts import (chassis, floor, wings, wheels,        # noqa: E402
                   suspension, fans, powertrain, aerodetail,
                   detail, systems, hardware)

MM = 0.001

MODULES = [
    ("chassis", chassis), ("floor", floor), ("wings", wings),
    ("wheels", wheels), ("suspension", suspension), ("fans", fans),
    ("powertrain", powertrain), ("aero detail", aerodetail),
    ("body detail", detail), ("systems", systems),
    ("hardware", hardware),
]

COLLECTIONS = ["01 Bodywork", "02 Floor and Diffuser", "03 Wings",
               "04 Wheels and Brakes", "05 Suspension", "06 Fan System",
               "07 Power Unit", "08 Cooling and Energy", "09 Aero Detail",
               "10 Cockpit", "11 Structure and Service"]


def collection_for(name):
    n = name.lower()
    if n.startswith(("engine", "gearbox")):
        return "07 Power Unit"
    if n.startswith(("radiator", "rad_", "battery", "fuel", "accumulator")):
        return "08 Cooling and Energy"
    if n.startswith("fan"):
        return "06 Fan System"
    if n.startswith(("wishbone", "pushrod", "trackrod", "rocker",
                     "driveshaft", "damper", "torsion", "heave", "antiroll",
                     "steering_", "spring")):
        return "05 Suspension"
    if n.startswith(("tyre", "wheel", "rim", "disc", "caliper",
                     "upright", "hub_", "brake_pad", "tether")):
        return "04 Wheels and Brakes"
    if n.startswith(("bargeboard", "turning_vane", "floor_fence",
                     "brake_duct", "mirror", "camera", "rainlight",
                     "exhaust", "cooling_louvre", "gills",
                     "nose_cape", "nose_pylon", "bargeboard", "turning_vane",
                     "bduct_", "exit_louvres", "aero_rake", "rear_light")):
        return "09 Aero Detail"
    if n.startswith(("helmet", "driver", "seat", "steering", "headrest",
                     "harness", "dash", "extinguisher", "drink_bottle",
                     "pedal_box")):
        return "10 Cockpit"
    if n.startswith(("crash_", "side_impact", "jack_", "tow_", "airbox",
                     "bulkhead_", "side_intrusion", "gun_socket",
                     "starter_socket", "fuel_coupling", "tyre_sensors",
                     "brake_lines", "master_cylinders", "wiring_loom",
                     "control_boxes", "roll_hoop")):
        return "11 Structure and Service"
    if n.startswith("drs_"):
        return "03 Wings"
    if "wing" in n or "endplate" in n or "pylon" in n or "louvre" in n \
       or "gurney" in n or "cascade" in n or "y250" in n:
        return "03 Wings"
    if n.startswith(("floor", "tunnel")):
        return "02 Floor and Diffuser"
    return "01 Bodywork"


def material_for(name):
    n = name.lower()
    best, best_len = spec.DEFAULT_MATERIAL, -1
    for key, mat in spec.MATERIAL_MAP.items():
        if key in n and len(key) > best_len:
            best, best_len = mat, len(key)
    return best


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.length_unit = "MILLIMETERS"


def make_object(name, verts, faces, coll, pivot=None):
    """Build one object. `pivot` (in mm) becomes the object's origin.

    Geometry is authored in world millimetres, so without this every object's
    origin is the world origin -- which means a fan "spins" by swinging round
    the middle of the car and a control surface hinges about the nose. Moving
    the mesh data onto the pivot and putting the pivot in the object transform
    exports a glTF node that rotates in place, for any consumer, not just our
    viewer.
    """
    px, py, pz = (pivot or (0.0, 0.0, 0.0))
    me = bpy.data.meshes.new(name)
    me.from_pydata([((x - px) * MM, (y - py) * MM, (z - pz) * MM)
                    for (x, y, z) in verts],
                   [], [list(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = (px * MM, py * MM, pz * MM)
    coll.objects.link(ob)
    return ob


def apply_cutters(obj, cv, cf):
    cutter = make_object(obj.name + "__cut", cv, cf, bpy.context.scene.collection)
    # an exact boolean reads inside from outside off the normals, and a
    # cutter is joined from pieces authored in whatever winding they came in
    recalc_normals(cutter)
    m = obj.modifiers.new("cut", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.use_self = True           # a cutter is often several solids joined
    m.object = cutter
    bpy.context.view_layer.objects.active = obj
    ok = True
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
    except RuntimeError as e:
        print(f"    ! boolean failed on {obj.name}: {e}")
        obj.modifiers.remove(m)
        ok = False
    bpy.data.objects.remove(cutter, do_unlink=True)
    return ok


def array_rotational(obj, count, axis_x, axis_z):
    """Rotate copies about the engine's own axis, which is offset from the
    aircraft datum -- so shift to the axis, replicate, and shift back."""
    verts = [(v.co.x - axis_x, v.co.y, v.co.z - axis_z) for v in obj.data.vertices]
    faces = [tuple(p.vertices) for p in obj.data.polygons]
    nv, nf = meshlib.replicate(verts, faces, count)
    nv = [(x + axis_x, y, z + axis_z) for (x, y, z) in nv]
    me = bpy.data.meshes.new(obj.name + "_arr")
    me.from_pydata(nv, [], [list(f) for f in nf])
    me.validate(verbose=False)
    me.update()
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


def recalc_normals(obj):
    """Make normals point outward. Every part here is a closed manifold, so
    Blender can resolve winding reliably -- far more robust than trying to get
    the face order right by hand for each panel orientation and deflection."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


def shade(obj, angle_deg=34.0):
    """Smooth, with sharp edges marked from face angles. The operator form of
    this fails silently in background mode, so do it directly."""
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    limit = math.cos(math.radians(angle_deg))
    normals = [tuple(p.normal) for p in me.polygons]
    by_edge = {}
    for pi, poly in enumerate(me.polygons):
        for ek in poly.edge_keys:
            by_edge.setdefault(ek, []).append(pi)
    edges = {e.key: e for e in me.edges}
    n = 0
    for ek, fs in by_edge.items():
        e = edges.get(ek)
        if e is None:
            continue
        if len(fs) != 2:
            e.use_edge_sharp = True
            n += 1
            continue
        a, b = normals[fs[0]], normals[fs[1]]
        if sum(p * q for p, q in zip(a, b)) < limit:
            e.use_edge_sharp = True
            n += 1
    return n


def main():
    t0 = time.time()
    clear_scene()
    mats = materials.build_all()
    cols = {}
    for c in COLLECTIONS:
        col = bpy.data.collections.new(c)
        bpy.context.scene.collection.children.link(col)
        cols[c] = col

    rows, n_sharp = [], 0
    # "cut:<part>" entries are solids to take out of a part -- the engine's
    # bores and chambers out of its block and heads. They are pooled across
    # every module first so a cutter reaches its part wherever that is built.
    # `apply_cutters` was here and nothing called it: a cutter handed back by
    # a module would have been built as an object called "cut:...".
    built_all, cutters = [], {}
    for modname, module in MODULES:
        built = module.build()
        for key, geom in built.items():
            if key.startswith("cut:"):
                cutters.setdefault(key[4:], []).append(geom)
        built_all.append((modname, module, built))
    n_cut = n_cut_ok = 0
    for modname, module, built in built_all:
        t1 = time.time()
        objects = {k: v for k, v in built.items() if not k.startswith("cut:")}
        piv = module.pivots() if hasattr(module, "pivots") else {}

        for name, (v, f) in sorted(objects.items()):
            cname = collection_for(name)
            spec_p = piv.get(name)
            ob = make_object(name, v, f, cols[cname],
                             pivot=spec_p[0] if spec_p else None)
            # outward before cutting, not only after: the boolean takes the
            # part's inside from its normals too
            if name in cutters and name != "engine":
                recalc_normals(ob)
            for cv, cf in cutters.get(name, ()):
                n_cut += 1
                n_cut_ok += bool(apply_cutters(ob, cv, cf))
            if name != "engine":
                recalc_normals(ob)
            mname = material_for(name)
            ob.data.materials.append(mats[mname])
            n_sharp += shade(ob)
            # World-space bounds. Read them through matrix_world and you get
            # whatever Blender last evaluated -- which, for an object whose
            # origin was moved after it was linked, is the state before the
            # move. Every pivoted part then reports local coordinates and the
            # dimension checks measure the wrong aeroplane. The transform here
            # is a pure translation, so applying it directly is both exact and
            # free.
            lx, ly, lz = ob.location
            bb = meshlib.bbox([(x.co.x + lx, x.co.y + ly, x.co.z + lz)
                               for x in ob.data.vertices])
            ax = spec_p[1] if spec_p else ("", "", "")
            rows.append({
                "name": name, "collection": cname, "material": mname,
                "pivot_x_mm": round(spec_p[0][0], 1) if spec_p else "",
                "pivot_y_mm": round(spec_p[0][1], 1) if spec_p else "",
                "pivot_z_mm": round(spec_p[0][2], 1) if spec_p else "",
                "axis_x": ax[0], "axis_y": ax[1], "axis_z": ax[2],
                "spin": spec_p[2] if spec_p and len(spec_p) > 2 else "",
                "role": spec_p[3] if spec_p and len(spec_p) > 3 else "",
                "verts": len(ob.data.vertices), "faces": len(ob.data.polygons),
                "x_min_mm": round(bb[0] / MM, 1), "x_max_mm": round(bb[3] / MM, 1),
                "y_min_mm": round(bb[1] / MM, 1), "y_max_mm": round(bb[4] / MM, 1),
                "z_min_mm": round(bb[2] / MM, 1), "z_max_mm": round(bb[5] / MM, 1),
            })
        print(f"  [{modname}] {len(objects)} objects in {time.time()-t1:.1f}s")

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    p = os.path.join(ROOT, "build", "parts.csv")
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tv = sum(r["verts"] for r in rows)
    tf = sum(r["faces"] for r in rows)
    print(f"\n{len(rows)} objects | {tv:,} verts | {tf:,} faces")
    print(f"sharp edges: {n_sharp:,}  cuts {n_cut_ok}/{n_cut}")
    if n_cut_ok < n_cut:
        raise SystemExit(f"{n_cut - n_cut_ok} cuts failed")
    print(f"parts.csv -> {p}")
    blend = os.path.join(ROOT, "build", "car.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print(f"blend     -> {blend}")
    print(f"total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    # Blender exits 0 even when a background script raises, so a build that
    # dropped a whole module -- every mount, the belt drive, the charge
    # pipework -- printed a traceback into the log and then reported
    # success. `make verify` then ran against a model with those parts
    # missing and passed, because the gates only see what is there. Fail
    # loudly instead: print the traceback and hand back a non-zero status
    # that make will stop on.
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
