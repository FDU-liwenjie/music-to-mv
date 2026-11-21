"""Original wet mountain railway platform. All lengths are metres; +Y goes down the track."""

import math
import random

import bpy
from mathutils import Vector


class _Geometry:
    """One mesh per finish keeps repeated sleepers, trusses and slats inexpensive."""

    def __init__(self):
        self.vertices = []
        self.faces = []

    def add(self, vertices, faces):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(start + i for i in face) for face in faces)

    def box(self, x0, x1, y0, y1, z0, z1):
        self.add(
            [
                (x0, y0, z0),
                (x1, y0, z0),
                (x1, y1, z0),
                (x0, y1, z0),
                (x0, y0, z1),
                (x1, y0, z1),
                (x1, y1, z1),
                (x0, y1, z1),
            ],
            [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
        )

    def beam(self, first, last, width, depth=None):
        """A rectangular beam with a horizontal cross-axis and a vertical cross-axis."""
        a, b = Vector(first), Vector(last)
        along = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(along.z) < 0.95 else Vector((0, 1, 0))
        across = along.cross(ref).normalized() * (width / 2)
        up = along.cross(across).normalized() * ((depth or width) / 2)
        ring = [-across - up, across - up, across + up, -across + up]
        self.add(
            [tuple(v + d) for v in (a, b) for d in ring],
            [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
        )

    def emit(self, name, mat, collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(mat)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        return obj


def _material(name, color, rough=0.52, metal=0.0, glow=0):
    mat = bpy.data.materials.new("Station / " + name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["Roughness"].default_value = rough
    if glow:
        bs.inputs["Emission Color"].default_value = (*color, 1)
        bs.inputs["Emission Strength"].default_value = glow
    return mat


def _weather(name, dark, light, scale, rough_range, bump_size, streak=(1, 1, 1)):
    mat = _material(name, light)
    nodes = mat.node_tree.nodes
    link = mat.node_tree.links.new
    bs = nodes.get("Principled BSDF")
    position = nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    axis = nodes.new("ShaderNodeVectorMath")
    axis.operation = "MULTIPLY"
    link(position, axis.inputs[0])
    axis.inputs[1].default_value = streak

    def noise(freq, detail):
        n = nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = freq
        n.inputs["Detail"].default_value = detail
        link(axis.outputs["Vector"], n.inputs["Vector"])
        return n.outputs["Fac"]

    wet = noise(scale, 3)
    tint = nodes.new("ShaderNodeValToRGB")
    tint.color_ramp.elements[0].position = 0.28
    tint.color_ramp.elements[0].color = (*dark, 1)
    tint.color_ramp.elements[1].position = 0.70
    tint.color_ramp.elements[1].color = (*light, 1)
    link(wet, tint.inputs["Fac"])
    link(tint.outputs["Color"], bs.inputs["Base Color"])
    roughness = nodes.new("ShaderNodeValToRGB")
    for stop, pos, value in zip(
        roughness.color_ramp.elements, (0.41, 0.59), rough_range
    ):
        stop.position = pos
        stop.color = (value, value, value, 1)
    link(wet, roughness.inputs["Fac"])
    link(roughness.outputs["Color"], bs.inputs["Roughness"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.27
    bump.inputs["Distance"].default_value = bump_size
    link(noise(scale * 32, 2), bump.inputs["Height"])
    link(bump.outputs["Normal"], bs.inputs["Normal"])
    bs.inputs["Coat Weight"].default_value = 0.20
    bs.inputs["Coat Roughness"].default_value = 0.15
    return mat


def _area(collection, name, xyz, target, rgb, energy, length, width):
    data = bpy.data.lights.new("Station / " + name, "AREA")
    data.energy = energy
    data.color = rgb
    data.shape = "RECTANGLE"
    data.size = length
    data.size_y = width
    obj = bpy.data.objects.new(data.name, data)
    collection.objects.link(obj)
    obj.location = xyz
    obj.rotation_euler = (
        (Vector(target) - Vector(xyz)).to_track_quat("-Z", "Y").to_euler()
    )
    return obj


def _horizon(batch, axis, distance, peaks, phase):
    # A distant ridgeline combines wide shoulders and smaller outcrops; beginning
    # and end extend outside the shot for both longitudinal and lateral views.
    verts = []
    for i in range(97):
        u = i * 3.5 - 145
        h = (
            peaks
            + 3.5 * math.sin(u * 0.035 + phase)
            + 1.5 * math.sin(u * 0.091 - phase * 0.7)
            + 0.8 * math.cos(u * 0.24 + phase)
        )
        top = (distance, u, h) if axis == "x" else (u, distance, h)
        base = (top[0], top[1], -3.0)
        verts.extend((base, top))
    batch.add(verts, [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(96)])


def _trees(batch, rng, x, y, h):
    # Conifer silhouettes with a lean and uneven branch tiers. Varying heights
    # and two shades avoid a regular triangular edge against the ridge.
    n = 9
    twist = rng.uniform(0, math.tau)
    radius = h * rng.uniform(0.12, 0.22)
    lean = rng.uniform(-0.065, 0.065) * h
    progress = [0.03, 0.14, 0.25, 0.36, 0.47, 0.57, 0.67, 0.76, 0.84]
    verts = []
    for k, z in enumerate(progress):
        phi = twist + k * 0.47
        # Drooping outer branch tips interleaved with the inset inner canopy.
        taper = (1 - z) ** 0.83
        for i in range(n):
            tip = i % 2 == k % 2
            reach = (0.99 if tip else 0.67) * radius * taper * rng.uniform(0.78, 1.16)
            az = phi + i * math.tau / n
            height = -0.4 + h * (z + rng.uniform(-0.047, 0.024) - (0.033 if tip else 0))
            verts.append(
                (x + lean * z + reach * math.cos(az), y + reach * math.sin(az), height)
            )
    last = len(verts)
    verts.append((x + lean, y, -0.4 + h))
    faces = []
    for k in range(len(progress) - 1):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            faces.extend(((a, b, b + n), (a, b + n, a + n)))
    faces.extend(
        ((len(progress) - 1) * n + i, (len(progress) - 1) * n + (i + 1) % n, last)
        for i in range(n)
    )
    batch.add(verts, faces)


def build_station():
    """Build once into the current scene and return the environment collection.

    Rails run on X = ±0.7175, top Z = 0. Platform coping X = 1.59 and
    walking surface Z = 1.09. The canopy front is cantilevered for cameras.
    """
    scene = bpy.context.scene
    name = "Station | rain platform"
    existing = scene.collection.children.get(name)
    if existing:
        return existing
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    rng = random.Random(2314)

    mats = {
        "ballast": _weather(
            "dark ballast",
            (0.016, 0.024, 0.029),
            (0.074, 0.083, 0.085),
            12,
            (0.46, 0.83),
            0.048,
        ),
        "platform": _weather(
            "rain on paving",
            (0.044, 0.060, 0.067),
            (0.137, 0.149, 0.146),
            0.95,
            (0.084, 0.53),
            0.009,
            (1.35, 0.67, 1),
        ),
        "coping": _weather(
            "pale granite coping",
            (0.105, 0.115, 0.118),
            (0.29, 0.28, 0.25),
            3.6,
            (0.18, 0.48),
            0.009,
        ),
        "concrete": _weather(
            "concrete base",
            (0.050, 0.067, 0.073),
            (0.14, 0.15, 0.142),
            2.1,
            (0.32, 0.78),
            0.015,
        ),
        "sleepers": _weather(
            "creosoted timber",
            (0.032, 0.024, 0.022),
            (0.102, 0.076, 0.055),
            2.7,
            (0.28, 0.63),
            0.015,
            (0.4, 3.8, 1),
        ),
        "steel": _material("rail body", (0.095, 0.073, 0.057), 0.35, 0.68),
        "railhead": _material("polished railhead", (0.37, 0.41, 0.43), 0.20, 0.88),
        "iron": _material("weathered canopy iron", (0.084, 0.131, 0.134), 0.37, 0.64),
        "roof": _material("roof and gutter", (0.037, 0.057, 0.062), 0.33, 0.65),
        "wood": _weather(
            "canopy wood grain",
            (0.105, 0.053, 0.026),
            (0.245, 0.143, 0.073),
            1.9,
            (0.36, 0.58),
            0.005,
            (2.5, 0.20, 1),
        ),
        "seam": _material("joint and frame", (0.028, 0.037, 0.039), 0.62, 0.1),
        "amber": _weather(
            "muted amber tactile tiles",
            (0.19, 0.115, 0.035),
            (0.43, 0.295, 0.105),
            3.9,
            (0.23, 0.6),
            0.006,
        ),
        "warm": _material("lamp diffuser", (1, 0.68, 0.34), 0.29, 0.0, 4.0),
        "marker": _material("trackside red lens", (0.8, 0.054, 0.018), 0.3, 0.0, 2.0),
        "forest1": _material("near wet fir", (0.023, 0.048, 0.051), 0.86),
        "forest2": _material("mid wet fir", (0.042, 0.068, 0.073), 0.88),
        "ridge1": _material("near ridge", (0.053, 0.087, 0.106), 0.95, glow=0.14),
        "ridge2": _material("mid ridge", (0.105, 0.155, 0.193), 0.96, glow=0.16),
        "ridge3": _material("far ridge", (0.157, 0.221, 0.259), 0.97, glow=0.19),
    }
    for key in ("forest1", "forest2"):
        leaf = mats[key].node_tree.nodes.get("Principled BSDF")
        leaf.inputs["Specular IOR Level"].default_value = 0.13
    batches = {k: _Geometry() for k in mats}
    b = batches
    # Track formation, sleepers and rails. Each rail has a flat polished crown.
    b["ballast"].box(-50, 1.59, -43, 116, -0.66, -0.37)
    b["concrete"].box(1.67, 8.08, -25, 75.2, -0.38, 1.025)
    b["platform"].box(1.93, 8.10, -25, 75.2, 1.02, 1.09)
    for k in range(84):
        y = -25 + 1.20 * k
        b["coping"].box(1.59, 1.94, y + 0.004, min(y + 1.195, 75.2), 0.93, 1.09)
    for i in range(202):
        y = -29 + i * 0.62
        b["sleepers"].box(-1.205, 1.205, y - 0.115, y + 0.115, -0.385, -0.151)
        for rail in (-0.7175, 0.7175):
            b["iron"].box(
                rail - 0.125, rail + 0.125, y - 0.103, y + 0.103, -0.153, -0.139
            )
    for x in (-0.7175, 0.7175):
        b["steel"].box(x - 0.069, x + 0.069, -39, 111, -0.148, -0.128)
        b["steel"].box(x - 0.012, x + 0.012, -39, 111, -0.130, -0.039)
        b["railhead"].box(x - 0.035, x + 0.035, -39, 111, -0.039, 0)
    # Edge warning surface, joints and slots; joints sit just above the surface.
    for i in range(201):
        y = -25 + 0.5 * i
        b["amber"].box(2.08, 2.38, y + 0.004, min(y + 0.495, 75.2), 1.09, 1.098)
    for j in range(3):
        x = 2.104 + j * 0.115
        b["amber"].box(x, x + 0.023, -25, 75.2, 1.098, 1.104)
    for k in range(26):
        y = -25 + 4 * k
        b["seam"].box(2.42, 8.05, y, y + 0.012, 1.09, 1.092)
    b["iron"].box(6.94, 7.026, -25, 75.2, 1.09, 1.095)
    for k in range(400):
        y = -25 + 0.25 * k
        b["seam"].box(6.948, 7.018, y, y + 0.023, 1.095, 1.098)
    # Timber soffit with a slight slope, steel edge flashing and cantilever brackets.
    y0, y1 = -17.8, 43.0

    def roof_z(x):
        return 4.32 + (x - 1.65) * 0.055

    for i in range(28):
        x = 1.65 + i * 0.206
        z = roof_z(x)
        b["wood"].box(x, x + 0.201, y0, y1, z, z + 0.073)
    b["roof"].box(1.60, 1.69, y0, y1, 4.29, 4.48)
    b["roof"].box(7.34, 7.48, y0, y1, 4.60, 4.83)
    for x in (2.04, 4.17, 6.73):
        z = roof_z(x)
        b["iron"].box(x - 0.045, x + 0.045, y0, y1, z - 0.115, z)
    for y in (-15, -7, 1, 9, 17, 25, 33, 41):
        # Rear columns are clear of the front sightline, and only carry the canopy.
        b["iron"].box(6.31, 6.49, y - 0.085, y + 0.085, 1.09, 4.61)
        b["iron"].box(6.21, 6.59, y - 0.17, y + 0.17, 1.09, 1.17)
        b["iron"].beam((1.69, y, 4.25), (7.35, y, 4.56), 0.125, 0.105)
        b["iron"].beam((6.40, y, 3.34), (3.65, y, 4.32), 0.092, 0.115)
        # Recessed diffuser, black gasket and two small suspension stems.
        b["iron"].box(3.08, 3.29, y - 0.95, y + 0.95, 4.05, 4.13)
        b["warm"].box(3.102, 3.268, y - 0.898, y + 0.898, 4.034, 4.068)
        for dy in (-0.67, 0.67):
            b["iron"].box(3.157, 3.181, y + dy - 0.018, y + dy + 0.018, 4.12, 4.38)
        _area(
            collection,
            f"canopy tungsten {y:+d}",
            (3.19, y, 4.017),
            (2.35, y, 1.02),
            (1.0, 0.65, 0.35),
            116,
            0.21,
            1.78,
        )

    # Two waiting rooms give the canopy a lived-in back wall. Window muntins
    # create a warm repeating rhythm behind the train and the final empty seat.
    mats["plaster"] = _weather(
        "waiting room render",
        (0.065, 0.073, 0.060),
        (0.18, 0.16, 0.12),
        3.1,
        (0.54, 0.80),
        0.008,
    )
    mats["frosted"] = _material(
        "frosted amber glass", (0.47, 0.21, 0.078), 0.43, glow=0.95
    )
    for key in ("plaster", "frosted"):
        b[key] = _Geometry()
    for lo, hi in [(-18.4, -8.25), (2.0, 20.8)]:
        b["plaster"].box(7.07, 10.8, lo, hi, 1.08, 4.0)
        b["roof"].box(6.84, 11.10, lo - 0.25, hi + 0.25, 3.98, 4.12)
        b["wood"].box(6.99, 7.07, lo, hi, 1.09, 1.72)
        for i in range(int((hi - lo) / 0.22)):
            cy = lo + i * 0.22
            b["wood"].box(6.976, 7.01, cy, cy + 0.018, 1.09, 1.73)
        for i in range(int((hi - lo) / 2.65)):
            cy = lo + 0.35 + i * 2.65
            b["wood"].box(6.965, 7.11, cy, cy + 1.92, 2.00, 3.44)
            b["frosted"].box(6.952, 6.961, cy + 0.08, cy + 1.84, 2.09, 3.36)
            for dz in (2.41, 3.07):
                b["seam"].box(6.937, 6.958, cy + 0.08, cy + 1.84, dz, dz + 0.025)
            for dy in (0.64, 1.28):
                b["seam"].box(6.936, 6.959, cy + dy, cy + dy + 0.032, 2.09, 3.36)
            b["wood"].box(6.88, 7.12, cy - 0.04, cy + 1.96, 1.946, 2.015)
    # The near bench looks toward the station's southern approach in the last shot.
    for k, (yy, h) in enumerate([(-55, 4), (-76, 8), (-100, 14)]):
        _horizon(b[["ridge1", "ridge2", "ridge3"][k]], "y", yy, h, 2.25 + k * 0.84)
    b["ballast"].box(-36, 45, -110, -42, -0.68, -0.39)
    # The near bench is also a wardrobe/story prop location. Top surface Z=1.594.
    # Both run along Y and the backrest is at increasing X, away from the train.
    for cx, y in ((4.60, -7.0), (5.24, 22.5)):
        for j in range(4):
            x = cx - 0.218 + j * 0.113
            b["wood"].box(x, x + 0.097, y - 1.29, y + 1.29, 1.53, 1.594)
        for z in (1.77, 1.91):
            b["wood"].box(cx + 0.22, cx + 0.275, y - 1.29, y + 1.29, z, z + 0.102)
        for dy in (-0.86, 0.86):
            b["iron"].box(
                cx - 0.19, cx - 0.12, y + dy - 0.046, y + dy + 0.046, 1.09, 1.53
            )
            b["iron"].box(
                cx + 0.18, cx + 0.25, y + dy - 0.046, y + dy + 0.046, 1.09, 2.02
            )
    # Trackside service pole, wire and lenses are useful scale cues when seen
    # past the approaching train. They never overlap the close platform camera.
    for y in (-2, 19, 40, 61, 82):
        b["iron"].beam((-5.4, y, -0.40), (-5.4, y, 5.7), 0.12)
        b["iron"].beam((-5.62, y, 5.40), (-4.36, y, 5.40), 0.073)
        for x in (-5.43, -4.55):
            for j in range(7):
                t1, t2 = j / 7, (j + 1) / 7
                z1, z2 = 5.49 - 0.84 * t1 * (1 - t1), 5.49 - 0.84 * t2 * (1 - t2)
                b["seam"].beam((x, y + t1 * 21, z1), (x, y + t2 * 21, z2), 0.022)
    b["iron"].box(-3.08, -2.98, 49, 49.1, -0.37, 2.87)
    b["seam"].box(-3.19, -2.86, 48.96, 49.13, 2.47, 3.10)
    b["marker"].box(-3.083, -2.97, 48.95, 48.963, 2.82, 2.93)

    # Separate distant terrain layers in two directions let the platform
    # terminate in a visible valley from both across-track and long-lens views.
    for n, (x, y, peaks) in enumerate(
        ((-25, 86, 6), (-58, 107, 12), (-96, 132, 20)), 1
    ):
        _horizon(b[f"ridge{n}"], "x", x, peaks, n * 1.78)
        _horizon(b[f"ridge{n}"], "y", y, peaks * 0.85, n * 2.51)
    for _ in range(230):
        x = rng.uniform(-27, -10)
        y = rng.uniform(-44, 92)
        _trees(b["forest2" if x < -19 else "forest1"], rng, x, y, rng.uniform(3.1, 9.5))
    for _ in range(75):
        x, y = rng.uniform(-19, 25), rng.uniform(71, 91)
        if abs(x) < 4:
            continue
        _trees(b["forest2"], rng, x, y, rng.uniform(3.3, 8.4))

    for key, geometry in batches.items():
        if geometry.faces:
            geometry.emit("Station / " + key, mats[key], collection)

    _area(
        collection,
        "blue hour sky",
        (-8, 5, 16),
        (1, 13, 1),
        (0.41, 0.60, 0.94),
        12200,
        24,
        41,
    )
    _area(
        collection,
        "far sky",
        (-5, 44, 17),
        (-1, 40, 1),
        (0.35, 0.55, 0.87),
        6200,
        20,
        35,
    )
    _area(
        collection,
        "cool platform bounce",
        (7, -5, 6),
        (0, 3, 1.5),
        (0.49, 0.66, 0.87),
        1350,
        12,
        13,
    )
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Station / blue hour")
    scene.world.use_nodes = True
    tree = scene.world.node_tree
    output = tree.nodes.get("World Output")
    if output is None:
        output = tree.nodes.new("ShaderNodeOutputWorld")
    sky = tree.nodes.new("ShaderNodeBackground")
    # Direction-space clouds keep the overcast sky and its reflection consistent
    # as the camera moves down the platform.
    direction = tree.nodes.new("ShaderNodeTexCoord").outputs["Normal"]
    stretch = tree.nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (1.5, 2.3, 8.0)
    tree.links.new(direction, stretch.inputs[0])
    cloud = tree.nodes.new("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value = 1.7
    cloud.inputs["Detail"].default_value = 3.5
    tree.links.new(stretch.outputs["Vector"], cloud.inputs["Vector"])
    tones = tree.nodes.new("ShaderNodeValToRGB")
    tones.color_ramp.elements[0].position = 0.14
    tones.color_ramp.elements[0].color = (0.093, 0.15, 0.25, 1)
    tones.color_ramp.elements[1].position = 0.83
    tones.color_ramp.elements[1].color = (0.25, 0.33, 0.41, 1)
    tree.links.new(cloud.outputs["Fac"], tones.inputs["Fac"])
    tree.links.new(tones.outputs["Color"], sky.inputs["Color"])
    sky.inputs["Strength"].default_value = 0.37
    tree.links.new(sky.outputs["Background"], output.inputs["Surface"])
    return collection
