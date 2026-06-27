"""Coffee beans for the Wako Beans site: the four species, and a bed of roasted beans.

    blender -b --factory-startup -P assets/3d/beans.py -- --job species
    blender -b --factory-startup -P assets/3d/beans.py -- --job bed

Each species has its own bean. Arabica is an oval with an S-shaped crease,
robusta is rounder with a straight one, liberica is the largest and lopsided,
with a hooked tip, and excelsa is a small teardrop.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as studio  # noqa: E402
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


def place(mesh, material, location, rotation):
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = Euler(rotation)
    if not mesh.materials:
        mesh.materials.append(material)
    return obj


def scatter(kind, rng, count, spread, material, variants=4, gap=1.12):
    """Beans lying on the floor, none overlapping: most crease-down, a few showing it."""
    length, width, thick = SPECIES[kind][:3]
    meshes = [bean_mesh(f"{kind} {i}", kind, seed=i + 1) for i in range(variants)]
    placed = []
    tries = 0
    while len(placed) < count and tries < 4000:
        tries += 1
        p = rng.uniform(-1, 1, 2) * spread
        if any(np.hypot(*(p - q)) < length * MM * gap * 0.82 for q in placed):
            continue
        placed.append(p)
        up = rng.random() < 0.45
        tilt = rng.uniform(-0.12, 0.12)
        rot = (tilt, math.pi if up else 0.0, rng.uniform(0, 2 * math.pi))
        z = (thick * 0.38 / 2 if not up else thick / 2) * MM
        place(meshes[len(placed) % variants], material, (p[0], p[1], z), rot)
    return placed


def job_species(out, samples, scale):
    """Each species alone: a loose handful seen from above and a little to the front."""
    only = studio.arg("--only")
    for kind in SPECIES:
        if only and kind not in only.split(","):
            continue
        scene = studio.setup(samples)
        rng = np.random.default_rng(hash(kind) % 1000 + 7)
        rng = np.random.default_rng({"arabica": 3, "robusta": 5, "excelsa": 8, "liberica": 13}[kind])
        scatter(kind, rng, 15, (0.024, 0.031), bean_material(kind))
        target = (0.0, 0.0, 0.002)
        studio.light("Key", (-0.20, -0.16, 0.30), target, 1.5, 0.22)
        studio.light("Fill", (0.25, -0.10, 0.12), target, 0.22, 0.30)
        studio.light("Rim", (0.10, 0.26, 0.16), target, 1.0, 0.14)
        cam = studio.camera((0.0, -0.115, 0.245), target, 110.0)
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector(target)).length
        cam.data.dof.aperture_fstop = 11.0
        studio.render(scene, os.path.join(out, "species", f"{kind}.png"), (960, 1200), scale)


def job_bed(out, samples, scale):
    """A bed of all four species mixed, close, for full-bleed backgrounds."""
    scene = studio.setup(samples)
    scene.render.film_transparent = False
    world = scene.world.node_tree.nodes.get("Background")
    world.inputs["Color"].default_value = (0.02, 0.012, 0.008, 1.0)
    for obj in list(bpy.data.objects):
        if obj.name == "Shadow catcher":
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.active_object
    mat = bpy.data.materials.new("Tray")
    mat.use_nodes = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.012, 0.008, 0.006, 1.0)
    floor.data.materials.append(mat)

    rng = np.random.default_rng(21)
    kinds = list(SPECIES)
    meshes = {k: [bean_mesh(f"{k} bed {i}", k, seed=10 + i) for i in range(3)] for k in kinds}
    mats = {k: bean_material(k) for k in kinds}
    half_x, half_y = 0.105, 0.062
    # three layers on a staggered grid, each a little looser and more tumbled than the one below
    for layer, (pitch, lift, lean) in enumerate(((0.0084, 0.0022, 0.3), (0.0096, 0.0060, 0.7), (0.0112, 0.0096, 1.0))):
        ny = int(2 * half_y / (pitch * 0.86)) + 2
        nx = int(2 * half_x / pitch) + 2
        for iy in range(ny):
            for ix in range(nx):
                if layer == 2 and rng.random() < 0.25:
                    continue
                x = -half_x + (ix + 0.5 * (iy % 2)) * pitch + rng.uniform(-1, 1) * pitch * 0.22
                y = -half_y + iy * pitch * 0.86 + rng.uniform(-1, 1) * pitch * 0.22
                kind = kinds[int(rng.integers(0, 4))]
                up = rng.random() < 0.5
                rot = (rng.uniform(-1, 1) * lean * 0.5, (math.pi if up else 0.0) + rng.uniform(-1, 1) * lean * 0.6, rng.uniform(0, 2 * math.pi))
                place(meshes[kind][int(rng.integers(0, 3))], mats[kind], (x, y, lift + rng.uniform(0, 0.0012)), rot)

    target = (0.0, 0.0, 0.006)
    studio.light("Key", (-0.22, -0.10, 0.30), target, 3.4, 0.20)
    studio.light("Rim", (0.24, 0.20, 0.12), target, 1.6, 0.10)
    studio.light("Fill", (0.10, -0.30, 0.20), target, 0.4, 0.4)
    cam = studio.camera((0.0, -0.085, 0.36), target, 80.0, vertical=False)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (Vector(cam.location) - Vector(target)).length
    cam.data.dof.aperture_fstop = 5.6
    studio.render(scene, os.path.join(out, "bed.png"), (1920, 1080), scale)


if __name__ == "__main__":
    out_dir = os.path.abspath(studio.arg("--out", os.path.join(HERE, "out", "renders")))
    job = studio.arg("--job", "species")
    n = int(studio.arg("--samples", "64"))
    k = float(studio.arg("--scale", "1.0"))
    {"species": job_species, "bed": job_bed}[job](out_dir, n, k)
