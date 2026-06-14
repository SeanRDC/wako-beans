"""The Wako Beans bag: a 250 g flat-bottom pouch, built from numbers.

The bag is a loft of cross-sections. Low down it is a box full of beans; higher
up the front and back close on each other while the side gussets fold inward,
keeping each panel's paper length, until everything meets in the heat seal.

Sizes are metres. The front faces -Y.
"""
import math

import bpy
import numpy as np

W, D, H = 0.130, 0.074, 0.250  # width, depth, height to the top of the seal
SEAL = 0.018                   # height of the crimped band
NF, NG = 80, 46                # points across a face, across a gusset
RINGS = 250


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ring(z):
    """One cross-section at height z: (points, 2) going front, right gusset, back, left gusset."""
    body = H - SEAL
    zz = min(z / body, 1.0)
    close = float(smoothstep(0.40 * H, 0.915 * H, z)) ** 1.15   # 0 = full box, 1 = sealed flat
    belly = math.sin(math.pi * zz) ** 0.8
    b = (D / 2) * (1 + 0.05 * belly) * (1 - close) + 0.0013 * close
    a = W / 2 + 0.0012 * belly
    fold = math.sqrt(max((D / 2) ** 2 - min(b, D / 2) ** 2, 0.0))   # how far the gusset crease has gone in
    side = 0.0028 * belly * (1 - close)

    pts = []
    for k in range(NF):                      # front, left to right
        x = -a + 2 * a * k / NF
        pts.append((x, -b))
    for k in range(NG):                      # right gusset, front to back
        t = k / NG
        v = 1 - abs(2 * t - 1)
        pts.append((a - fold * v + side * math.sin(math.pi * t), -b + 2 * b * t))
    for k in range(NF):                      # back, right to left
        x = a - 2 * a * k / NF
        pts.append((x, b))
    for k in range(NG):                      # left gusset, back to front
        t = k / NG
        v = 1 - abs(2 * t - 1)
        pts.append((-a + fold * v - side * math.sin(math.pi * t), b - 2 * b * t))
    return np.array(pts)


def bag_points(seed):
    """All the bag's points, (rings, columns, 3)."""
    zs = [H * i / RINGS for i in range(RINGS + 1)]
    P = np.zeros((len(zs), 2 * (NF + NG), 3))
    for i, z in enumerate(zs):
        P[i, :, :2] = _ring(z)
        P[i, :, 2] = z
    return P


def grey_material(name):
    """A plain grey stand-in while the shape is worked out."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.6
    return mat


def build_bag(slug, colours, labels_dir, seed):
    """Make one bag standing on z = 0. Returns the empty that carries it."""
    P = bag_points(seed)
    rows, cols = P.shape[:2]

    verts = P.reshape(-1, 3).tolist()
    faces = []
    for i in range(rows - 1):
        for j in range(cols):
            j2 = (j + 1) % cols
            faces.append((i * cols + j, i * cols + j2, (i + 1) * cols + j2, (i + 1) * cols + j))
    bottom = tuple(range(cols - 1, -1, -1))
    top = tuple((rows - 1) * cols + j for j in range(cols))
    faces.append(bottom)
    faces.append(top)

    mesh = bpy.data.meshes.new(f"Bag {slug}")
    mesh.from_pydata(verts, [], faces)
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()

    obj = bpy.data.objects.new(f"Bag {slug}", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(grey_material(f"Paper {slug}"))

    carrier = bpy.data.objects.new(f"Carrier {slug}", None)
    bpy.context.collection.objects.link(carrier)
    obj.parent = carrier
    return carrier
