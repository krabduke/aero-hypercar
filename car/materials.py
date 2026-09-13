"""PBR materials for the car. Requires bpy."""

import os, sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec  # noqa: E402

PALETTE = spec.PALETTE


def build_all():
    out = {}
    for name, (rgb, metallic, rough) in PALETTE.items():
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        b = nt.nodes.get("Principled BSDF")
        if b is None:
            b = nt.nodes.new("ShaderNodeBsdfPrincipled")
            nt.links.new(b.outputs[0], nt.nodes["Material Output"].inputs[0])
        b.inputs["Base Color"].default_value = (*rgb, 1.0)
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Roughness"].default_value = rough
        if name in ("carbon_gloss",):
            # heat-tinted exhaust hardware glows faintly under load
            b.inputs["Coat Weight"].default_value = 0.55 if "Coat Weight" in b.inputs else 0.0
            if False:
                pass
        if name in ("alu_cast", "magnesium", "carbon_matte"):
            _cast_texture(nt, b, rough)
        out[name] = mat
    return out


def _cast_texture(nt, bsdf, base_rough):
    """Sand-cast surfaces are not smooth; break the roughness up so large
    castings do not read as machined billet."""
    coord = nt.nodes.new("ShaderNodeTexCoord"); coord.location = (-900, -180)
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 900.0
    tex.inputs["Detail"].default_value = 5.0
    tex.location = (-660, -180)
    nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = 0.35
    rng.inputs["From Max"].default_value = 0.65
    rng.inputs["To Min"].default_value = max(0.05, base_rough - 0.12)
    rng.inputs["To Max"].default_value = min(0.98, base_rough + 0.12)
    rng.location = (-430, -180)
    nt.links.new(tex.outputs["Fac"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], bsdf.inputs["Roughness"])
