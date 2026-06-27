"""Renders for the Wako Beans site.

    blender -b --factory-startup -P assets/3d/render.py -- --job hero
    blender -b --factory-startup -P assets/3d/render.py -- --job spin --only atok
    blender -b --factory-startup -P assets/3d/render.py -- --job row
    blender -b --factory-startup -P assets/3d/render.py -- --job test --only atok

Options: --only a,b   --samples 96   --scale 1.0 (of each job's own size)   --out <folder>

Cycles on a transparent film with a shadow-catcher floor, so every picture
keeps only the object and its contact shadow and can sit on any of the site's
colour fields. Colours go through the Standard view transform so the print on
the bags stays close to the site's own hex values.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wako_bag  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
LABELS = os.path.join(HERE, "out", "labels")
with open(os.path.join(ROOT, "src", "content", "coffees.json"), encoding="utf8") as fh:
    COFFEES = json.load(fh)
SEEDS = {"atok": 11, "apo": 23, "kulaman": 37, "amadeo": 41, "lipa": 59}


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def setup(samples):
    clear()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.max_bounces = 6
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.film_transparent = True
    scene.render.threads_mode = "AUTO"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    settings = scene.render.image_settings
    settings.file_format = "PNG"
    settings.color_mode = "RGBA"
    settings.compression = 60

    world = scene.world or bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.85, 0.85, 0.85, 1.0)
    background.inputs["Strength"].default_value = 0.20

    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.active_object
    floor.name = "Shadow catcher"
    floor.is_shadow_catcher = True
    return scene


def aim(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def light(name, location, target, power, size, size_y=None):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "RECTANGLE" if size_y else "SQUARE"
    data.size = size
    if size_y:
        data.size_y = size_y
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def studio(target, scale=1.0):
    """A tall soft key from the front left, a low fill, and a rim from behind to lift the edges."""
    s = scale
    light("Key", (-0.62 * s, -0.78 * s, 0.52 * s), target, 9.0 * s * s, 0.55 * s, 0.85 * s)
    light("Fill", (0.80 * s, -0.55 * s, 0.20 * s), target, 1.6 * s * s, 0.9 * s)
    light("Rim", (0.45 * s, 0.75 * s, 0.50 * s), target, 7.5 * s * s, 0.35 * s, 0.7 * s)
    light("Top", (0.0, -0.05 * s, 0.85 * s), target, 2.4 * s * s, 0.6 * s)


def camera(location, target, lens, vertical=True):
    data = bpy.data.cameras.new("Camera")
    data.lens = lens
    data.sensor_fit = "VERTICAL" if vertical else "HORIZONTAL"
    data.sensor_height = 36.0
    data.sensor_width = 36.0
    data.clip_start = 0.01
    obj = bpy.data.objects.new("Camera", data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    bpy.context.scene.camera = obj
    return obj


def render(scene, path, size, scale):
    scene.render.resolution_x = int(size[0] * scale)
    scene.render.resolution_y = int(size[1] * scale)
    scene.render.resolution_percentage = 100
    if os.path.exists(path) and "--force" not in sys.argv:
        print(f"KEPT {path}", flush=True)
        return
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"RENDERED {path}", flush=True)


def wanted():
    only = arg("--only")
    names = only.split(",") if only else [c["slug"] for c in COFFEES]
    return [c for c in COFFEES if c["slug"] in names]


def bag_camera():
    return camera((0.0, -1.02, 0.235), (0.0, 0.0, 0.123), 110.0)


def job_hero(out, samples, scale):
    """One portrait of each bag, turned a little so the gusset shows."""
    for coffee in wanted():
        scene = setup(samples)
        carrier = wako_bag.build_bag(coffee["slug"], coffee["colors"], LABELS, SEEDS[coffee["slug"]])
        carrier.rotation_euler.z = math.radians(-24)
        studio((0.0, 0.0, 0.125))
        bag_camera()
        render(scene, os.path.join(out, "hero", f"{coffee['slug']}.png"), (1000, 1500), scale)


def job_spin(out, samples, scale):
    """A full turn of each bag in equal steps, for the product page's drag-to-turn."""
    frames = int(arg("--frames", "24"))
    start = int(arg("--from", "0"))
    for coffee in wanted():
        scene = setup(samples)
        carrier = wako_bag.build_bag(coffee["slug"], coffee["colors"], LABELS, SEEDS[coffee["slug"]])
        studio((0.0, 0.0, 0.125))
        bag_camera()
        for f in range(start, frames):
            carrier.rotation_euler.z = math.radians(-24) - 2 * math.pi * f / frames  # frame 0 is the portrait's pose
            render(scene, os.path.join(out, "spin", coffee["slug"], f"{f:02d}.png"), (480, 720), scale)


def job_row(out, samples, scale):
    """All five in a line, highest farm first, so the altitude columns step down."""
    scene = setup(samples)
    gap = 0.172
    for i, coffee in enumerate(COFFEES):
        carrier = wako_bag.build_bag(coffee["slug"], coffee["colors"], LABELS, SEEDS[coffee["slug"]])
        carrier.location.x = (i - 2) * gap
        carrier.rotation_euler.z = math.radians((-7, 5, -3, 6, -5)[i])
    studio((0.0, 0.0, 0.125), scale=1.9)
    camera((0.0, -2.35, 0.30), (0.0, 0.0, 0.118), 110.0, vertical=False)
    render(scene, os.path.join(out, "row.png"), (2000, 900), scale)


def job_test(out, samples, scale):
    """Quick looks while shaping the bag: front three-quarter, side and back."""
    coffee = wanted()[0]
    scene = setup(samples)
    carrier = wako_bag.build_bag(coffee["slug"], coffee["colors"], LABELS, SEEDS[coffee["slug"]])
    studio((0.0, 0.0, 0.125))
    bag_camera()
    for name, deg in (("front", -24),):
        carrier.rotation_euler.z = math.radians(deg)
        render(scene, os.path.join(out, "test", f"{coffee['slug']}-{name}.png"), (600, 900), scale)


if __name__ == "__main__":
    out_dir = os.path.abspath(arg("--out", os.path.join(HERE, "out", "renders")))
    job = arg("--job", "test")
    n = int(arg("--samples", "96"))
    k = float(arg("--scale", "1.0"))
    {"hero": job_hero, "spin": job_spin, "row": job_row, "test": job_test}[job](out_dir, n, k)
