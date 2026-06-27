"""Coffee beans for the Wako Beans site: one model for each of the four species.

Each species has its own bean. Arabica is an oval with an S-shaped crease,
robusta is rounder with a straight one, liberica is the largest and lopsided,
with a hooked tip, and excelsa is a small teardrop.
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wako_bag import hex_linear  # noqa: E402

MM = 0.001
SPECIES = {
    #            length width thick  taper  hook  s-curve  roast colour
    "arabica":  (10.8,  7.4,  4.3,  0.00,  0.0,  0.9,  "#684026"),
    "robusta":  (8.6,   7.3,  4.9,  0.00,  0.0,  0.12, "#5a3620"),
    "excelsa":  (10.0,  6.4,  4.2,  0.34,  0.25, 0.45, "#4a2c1a"),
    "liberica": (14.2,  8.8,  5.2,  0.26,  0.9,  0.6,  "#33201a"),
}


def bean_mesh(name, kind, seed=0):
    length, width, thick, taper, hook, scurve, _ = SPECIES[kind]
    rng = np.random.default_rng(seed)
    nu, nv = 72, 48
    verts, groove = [], []
    for i in range(nv + 1):
        phi = math.pi * i / nv                     # along the bean, tip to tip
        yn = -math.cos(phi)                        # -1..1
        for j in range(nu):
            th = 2 * math.pi * j / nu
            r = math.sin(phi) ** 0.82              # blunter ends than an ellipsoid
            x = math.cos(th) * r
            z = math.sin(th) * r
            # one end narrows; liberica's also bends to the side
            w = 1.0 - taper * (0.5 + 0.5 * yn) ** 1.4
            x *= w
            bend = hook * 0.10 * (0.5 + 0.5 * yn) ** 2.2
            # the flat face (z < 0) is much shallower than the dome
            z = z * (1.0 if z > 0 else 0.38)
            # the crease: a groove along the flat face that wanders in an S
            g = 0.0
            if z <= 0.02:
                centre = 0.16 * scurve * math.sin(yn * math.pi * 0.95)
                d = (x - centre) / 0.105
                fade = max(0.0, 1.0 - abs(yn) ** 6)
                g = math.exp(-d * d) * fade
                lips = math.exp(-((abs(x - centre) - 0.20) / 0.12) ** 2) * fade
                z = z + 0.50 * g - 0.10 * lips
            px = (x * width / 2 + bend * width) * MM
            py = yn * length / 2 * MM
            pz = z * thick / 2 * MM
            verts.append((px, py, pz))
            groove.append(g)
    faces = []
    for i in range(nv):
        for j in range(nu):
            j2 = (j + 1) % nu
            faces.append((i * nu + j, i * nu + j2, (i + 1) * nu + j2, (i + 1) * nu + j))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    attr = mesh.color_attributes.new("groove", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", np.repeat(np.array(groove, dtype=np.float32), 4) * np.tile([1, 1, 1, 0], len(groove)) + np.tile([0, 0, 0, 1], len(groove)))
    mesh.update()
    # a little lopsidedness so no two meshes are the same
    k = rng.uniform(-0.05, 0.05, 3)
    for v in mesh.vertices:
        v.co.x += k[0] * v.co.y
        v.co.z += k[1] * abs(v.co.y) * 0.4
    return mesh


def bean_material(kind, colour=None):
    mat = bpy.data.materials.new(f"Bean {kind}")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    base = hex_linear(colour or SPECIES[kind][6])
    dark = sum(base) / 3 < 0.03

    info = nodes.new("ShaderNodeObjectInfo")
    coords = nodes.new("ShaderNodeTexCoord")
    mottle = nodes.new("ShaderNodeTexNoise")
    mottle.inputs["Scale"].default_value = 260.0
    mottle.inputs["Detail"].default_value = 4.0
    links.new(coords.outputs["Object"], mottle.inputs["Vector"])

    # every bean a slightly different roast, mottled, with pale chaff left in the crease
    vary = nodes.new("ShaderNodeMapRange")
    vary.inputs["To Min"].default_value = 0.72
    vary.inputs["To Max"].default_value = 1.30
    links.new(info.outputs["Random"], vary.inputs["Value"])
    tone = nodes.new("ShaderNodeMapRange")
    tone.inputs["From Min"].default_value = 0.3
    tone.inputs["From Max"].default_value = 0.7
    tone.inputs["To Min"].default_value = 0.78
    tone.inputs["To Max"].default_value = 1.18
    links.new(mottle.outputs["Fac"], tone.inputs["Value"])
    mul = nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    links.new(vary.outputs["Result"], mul.inputs[0])
    links.new(tone.outputs["Result"], mul.inputs[1])
    shade = nodes.new("ShaderNodeMixRGB")
    shade.blend_type = "MULTIPLY"
    shade.inputs["Fac"].default_value = 1.0
    shade.inputs["Color1"].default_value = (*base, 1.0)
    links.new(mul.outputs["Value"], shade.inputs["Color2"])

    groove = nodes.new("ShaderNodeAttribute")
    groove.attribute_name = "groove"
    chaff = nodes.new("ShaderNodeMixRGB")
    chaff.inputs["Color2"].default_value = (*hex_linear("#c9a36b"), 1.0)
    amount = nodes.new("ShaderNodeMath")
    amount.operation = "MULTIPLY"
    amount.inputs[1].default_value = 0.20 if dark else 0.55
    links.new(groove.outputs["Fac"], amount.inputs[0])
    links.new(amount.outputs["Value"], chaff.inputs["Fac"])
    links.new(shade.outputs["Color"], chaff.inputs["Color1"])
    links.new(chaff.outputs["Color"], bsdf.inputs["Base Color"])

    bsdf.inputs["Roughness"].default_value = 0.36 if dark else 0.55
    bsdf.inputs["Specular IOR Level"].default_value = 0.5
    if dark:  # a dark roast sweats oil
        bsdf.inputs["Coat Weight"].default_value = 0.35
        bsdf.inputs["Coat Roughness"].default_value = 0.18

    skin = nodes.new("ShaderNodeTexNoise")
    skin.inputs["Scale"].default_value = 900.0
    skin.inputs["Detail"].default_value = 3.0
    links.new(coords.outputs["Object"], skin.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0003
    links.new(skin.outputs["Fac"], bump.inputs["Height"])
    wrinkle = nodes.new("ShaderNodeTexNoise")
    wrinkle.inputs["Scale"].default_value = 180.0
    wrinkle.inputs["Detail"].default_value = 5.0
    wrinkle.inputs["Distortion"].default_value = 2.0
    links.new(coords.outputs["Object"], wrinkle.inputs["Vector"])
    bump2 = nodes.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.30
    bump2.inputs["Distance"].default_value = 0.0006
    links.new(wrinkle.outputs["Fac"], bump2.inputs["Height"])
    links.new(bump.outputs["Normal"], bump2.inputs["Normal"])
    links.new(bump2.outputs["Normal"], bsdf.inputs["Normal"])
    return mat
