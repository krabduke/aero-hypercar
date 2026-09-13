"""Render the car. Run under `blender --background`.

    blender -b build/car.blend -P car/render.py -- <mode> [samples]

Modes: hero, top, cutaway, exploded, all
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "renders")

CORNERS = []


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def setup_render(samples=128, res=(1920, 1080)):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 6
    s.render.resolution_x, s.render.resolution_y = res
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    s.view_settings.exposure = -0.55
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "METAL"
        pr.get_devices()
        for d in pr.devices:
            d.use = True
        s.cycles.device = "GPU"
    except Exception as e:
        print("  (CPU render:", e, ")")


def setup_world(strength=0.55):
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    ramp.color_ramp.elements[0].color = (0.035, 0.040, 0.048, 1)
    ramp.color_ramp.elements[1].color = (0.240, 0.265, 0.300, 1)
    nt.links.new(tex.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Strength"].default_value = strength


def area(name, loc, rot, energy, size):
    d = bpy.data.lights.new(name, type="AREA")
    d.energy = energy
    d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = rot
    bpy.context.scene.collection.objects.link(o)
    return o


def setup_lights():
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    area("key",  (-2.2, -5.6, 4.6), (math.radians(48), 0, math.radians(-24)), 2300, 6.0)
    area("fill", ( 2.6,  5.0,-1.4), (math.radians(-62), 0, math.radians(152)), 760, 7.5)
    area("rim",  ( 6.0,  2.6, 3.0), (math.radians(62), 0, math.radians(118)), 1250, 3.5)
    area("bounce", (2.4, 0.0, -2.2), (math.radians(180), 0, 0), 420, 9.0)


def collect_corners():
    from mathutils import Vector as V
    xs, ys, zs = [], [], []
    for o in meshes():
        for c in o.bound_box:
            w = o.matrix_world @ V(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    cen = V(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2))
    size = V((max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)))
    CORNERS.clear()
    for sx in (-.5, .5):
        for sy in (-.5, .5):
            for sz in (-.5, .5):
                CORNERS.append(V((size.x*sx, size.y*sy, size.z*sz)))
    return cen


def fit_distance(cam, dirv, margin=1.06):
    """Smallest standoff that keeps every bounding-box corner in frame.

    Fitting the bounding sphere instead wastes most of the frame on something
    long and thin, which an aircraft very much is.
    """
    up = Vector((0, 0, 1))
    right = dirv.cross(up).normalized()
    camup = right.cross(dirv).normalized()
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    th = math.tan(cam.data.angle / 2.0)      # sensor-fit axis is horizontal
    tv = th / aspect
    d = 0.0
    for c in CORNERS:
        depth = c.dot(dirv)
        d = max(d, abs(c.dot(right)) / th - depth,
                   abs(c.dot(camup)) / tv - depth)
    return d * margin


def setup_camera(dirv, centre, lens=70.0, ortho=False):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    if ortho:
        cd.type = "ORTHO"
    ob = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    dirv = Vector(dirv).normalized()
    if ortho:
        span = max(max(abs(c.x), abs(c.y), abs(c.z)) for c in CORNERS) * 2.3
        cd.ortho_scale = span
        ob.location = centre - dirv * 2.0
    else:
        ob.location = centre - dirv * fit_distance(ob, dirv)
    ob.rotation_euler = dirv.to_track_quat("-Z", "Y").to_euler()
    return ob


def shoot(name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".png")
    bpy.context.scene.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print("  ->", p)


# Peel only the outer castings; the rotating assembly stays whole.
# Peel the bodywork only; the floor, wheels and internals stay whole.
SHELL = ("tub", "nose", "sidepod_", "engine_cover", "airbox")


def section(centre):
    """Peel the skin only, leaving the structure and systems whole -- the same
    reason the engine project sections its casings and not its rotor."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    cut = bpy.context.active_object
    cut.name = "__section"
    cut.scale = (7.0, 2.4, 3.0)
    cut.location = (centre.x, centre.y - 1.20, centre.z)
    cut.hide_render = True
    for o in meshes():
        if o is cut or not any(o.name.startswith(s) for s in SHELL):
            continue
        m = o.modifiers.new("sec", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "FLOAT"
        m.object = cut


def mode_hero(s):
    setup_render(s); setup_world(); setup_lights()
    c = collect_corners()
    setup_camera((0.46, 0.80, -0.38), c, lens=74)
    shoot("01_hero")


def mode_top(s):
    setup_render(s, res=(1600, 1200)); setup_world(0.75); setup_lights()
    c = collect_corners()
    setup_camera((0.0, 0.0, -1.0), c, ortho=True)
    shoot("02_plan")


def mode_cutaway(s):
    setup_render(s); setup_world(0.5); setup_lights()
    c = collect_corners()
    section(c)
    area("bay", (2.4, -3.6, 1.4), (math.radians(74), 0, 0), 2400, 5.0)
    setup_camera((0.36, 0.82, -0.44), c, lens=72)
    shoot("03_cutaway")


def mode_exploded(s):
    setup_render(s); setup_world(); setup_lights()
    moves = {
        "01 Bodywork": (0.0, 0.0, 0.85),
        "03 Wings": (0.0, 0.0, 0.42),
        "04 Wheels and Brakes": (0.0, 0.62, 0.0),
        "05 Suspension": (0.0, 0.30, 0.16),
        "06 Fan System": (0.75, 0.0, 0.20),
        "07 Power Unit": (0.0, 0.0, 0.34),
        "08 Cooling and Energy": (-0.55, 0.0, 0.30),
    }
    for cname, (dx, dy, dz) in moves.items():
        col = bpy.data.collections.get(cname)
        if not col:
            continue
        for o in col.objects:
            o.location.x += dx
            o.location.y += dy
            o.location.z += dz
    c = collect_corners()
    setup_camera((0.40, 0.78, -0.48), c, lens=58)
    shoot("04_exploded")


MODES = {"hero": mode_hero, "top": mode_top,
         "cutaway": mode_cutaway, "exploded": mode_exploded}

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["hero"]
    mode = argv[0]
    samples = int(argv[1]) if len(argv) > 1 else 128
    if mode == "all":
        for m in ("hero", "top", "cutaway", "exploded"):
            MODES[m](samples)
    else:
        MODES[mode](samples)
