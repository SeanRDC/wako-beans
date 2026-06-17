"""The Wako Beans bag: a 250 g flat-bottom pouch, built from numbers.

The bag is a loft of cross-sections. Low down it is a box full of beans; higher
up the front and back close on each other while the side gussets fold inward,
keeping each panel's paper length, until everything meets in the heat seal.
Wrinkles, the zipper ridge and a slight lean are added to the points before the
mesh is made, from a seed, so each coffee has its own bag and every build of it
is the same.

Sizes are metres. The front faces -Y.
"""
import math

import bpy
import numpy as np
from mathutils import Vector, noise

W, D, H = 0.130, 0.074, 0.250  # width, depth, height to the top of the seal
SEAL = 0.018                   # height of the crimped band
ZIP = H - SEAL - 0.022         # height of the zipper ridge
ROUND = 0.006                  # radius of the bottom edge
NF, NG = 80, 46                # points across a face, across a gusset
RINGS = 250
PERIM = 2 * (W + D)


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_linear(h):
    h = h.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ring(z, inset):
    """One cross-section at height z: (points, 2) going front, right gusset, back, left gusset."""
    body = H - SEAL
    zz = min(z / body, 1.0)
    close = float(smoothstep(0.40 * H, 0.915 * H, z)) ** 1.15   # 0 = full box, 1 = sealed flat
    belly = math.sin(math.pi * zz) ** 0.8
    b = (D / 2) * (1 + 0.05 * belly) * (1 - close) + 0.0013 * close
    a = W / 2 + 0.0012 * belly
    fold = math.sqrt(max((D / 2) ** 2 - min(b, D / 2) ** 2, 0.0))   # how far the gusset crease has gone in
    pillow = 0.0058 * belly * (1 - 0.35 * close)
    side = 0.0028 * belly * (1 - close)
    ridge = 0.0011 * math.exp(-((z - ZIP) / 0.0019) ** 2)

    pts = []
    for k in range(NF):                      # front, left to right
        x = -a + 2 * a * k / NF
        pts.append((x, -b - (pillow + ridge) * (1 - (x / a) ** 2) ** 0.7 - ridge * 0.4))
    for k in range(NG):                      # right gusset, front to back
        t = k / NG
        v = 1 - abs(2 * t - 1)
        pts.append((a - fold * v + side * math.sin(math.pi * t), -b + 2 * b * t))
    for k in range(NF):                      # back, right to left
        x = a - 2 * a * k / NF
        pts.append((x, b + (pillow + ridge) * (1 - (x / a) ** 2) ** 0.7 + ridge * 0.4))
    for k in range(NG):                      # left gusset, back to front
        t = k / NG
        v = 1 - abs(2 * t - 1)
        pts.append((-a + fold * v - side * math.sin(math.pi * t), b - 2 * b * t))
    ring = np.array(pts)

    # round the corners: more near the base, almost none at the creased top
    radius = 0.0105 * (1 - float(smoothstep(0.0, 0.5 * H, z))) + 0.0016
    sigma = radius * 0.55 / (PERIM / len(pts))
    if sigma > 0.35:
        half = int(math.ceil(sigma * 3))
        kernel = np.exp(-0.5 * (np.arange(-half, half + 1) / sigma) ** 2)
        kernel /= kernel.sum()
        padded = np.concatenate([ring[-half:], ring, ring[:half]])
        ring = np.stack([np.convolve(padded[:, i], kernel, mode="valid") for i in range(2)], axis=1)

    if inset > 0:  # the rounded bottom edge
        ring[:, 0] *= (a - inset) / a
        ring[:, 1] *= (b - inset) / b
    return ring


def bag_points(seed):
    """All the bag's points, (rings, columns, 3), wrinkled and leaning."""
    steps = 7
    zs, insets = [], []
    for i in range(steps):
        ang = (math.pi / 2) * i / steps
        zs.append(ROUND * (1 - math.cos(ang)))
        insets.append(ROUND * (1 - math.sin(ang)))
    for i in range(RINGS + 1):
        zs.append(ROUND + (H - ROUND) * i / RINGS)
        insets.append(0.0)

    P = np.zeros((len(zs), 2 * (NF + NG), 3))
    for i, (z, inset) in enumerate(zip(zs, insets)):
        P[i, :, :2] = _ring(z, inset)
        P[i, :, 2] = z

    rng = np.random.default_rng(seed)
    off = Vector(rng.uniform(-50, 50, 3))

    # outward normals from the grid itself
    dj = np.roll(P, -1, axis=1) - np.roll(P, 1, axis=1)
    di = np.gradient(P, axis=0)
    N = np.cross(dj, di)
    N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-12

    rows, cols = P.shape[:2]
    disp = np.zeros((rows, cols))
    for i in range(rows):
        z = zs[i]
        loose = 0.42 + 0.58 * float(smoothstep(0.30 * H, 0.72 * H, z))       # the empty top wrinkles most
        loose *= 1 - float(smoothstep(H - SEAL - 0.010, H - SEAL + 0.002, z))  # the seal is pressed flat
        loose *= float(smoothstep(0.0, 0.035, z))                              # and the base stands firm
        if loose < 1e-4:
            continue
        tuck = (1 - float(smoothstep(0.40 * H, 0.80 * H, z))) ** 2   # a folded-in gusset is held flat
        for j in range(cols):
            x, y, _ = P[i, j]
            p = Vector((x, y, z))
            dents = noise.fractal(p * 16.0 + off, 1.0, 2.0, 3)
            q = Vector((x * 30.0, y * 30.0, (z - 0.55 * abs(x)) * 15.0)) + off * 1.7   # creases run down and outward
            crease = (1.0 - abs(noise.noise(q))) ** 5
            q2 = Vector((x * 22.0 + 0.4 * z * 60.0, y * 22.0, z * 46.0)) - off
            fold = (1.0 - abs(noise.noise(q2))) ** 6
            d = loose * (0.0020 * dents - 0.0018 * crease - 0.0010 * fold)
            # near the seal the panels lie almost on each other: never push one through the next
            on_gusset = NF <= j < NF + NG or j >= 2 * NF + NG
            if on_gusset:
                d *= tuck
            disp[i, j] = max(d, -0.45 * abs(y))
    P += N * disp[:, :, None]

    # the seal is never dead straight, and the bag leans a little
    lean_y, lean_x, twist = rng.uniform(-1, 1, 3)
    t = (P[:, :, 2] / H)
    top = smoothstep(0.55, 1.0, t)
    P[:, :, 1] += 0.0016 * top * np.sin(P[:, :, 0] * 38.0 + off.x)
    P[:, :, 1] += 0.0070 * lean_y * t ** 2.2
    P[:, :, 0] += 0.0035 * lean_x * t ** 2.2
    ang = 0.035 * twist * t ** 2
    x, y = P[:, :, 0].copy(), P[:, :, 1].copy()
    P[:, :, 0] = x * np.cos(ang) - y * np.sin(ang)
    P[:, :, 1] = x * np.sin(ang) + y * np.cos(ang)
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
