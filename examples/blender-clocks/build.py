"""Build an editable macro shot of two pocket watches for Blender 4.5 LTS.

blender -b -P build.py -- --output clocks.blend
"""

import argparse
from math import cos, pi, radians, sin
from pathlib import Path
import sys

import bpy
from mathutils import Vector

TAU = 2 * pi
FPS = 24
FRAMES = 168


def material(name, color, metal=0, rough=0.42):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Metallic"].default_value = metal
    node.inputs["Roughness"].default_value = rough
    return mat


def grain(mat, frequency, stretch, colors, bump=0.0):
    """Directional grain in local object coordinates, no texture dependencies."""
    tree = mat.node_tree
    make, link = tree.nodes.new, tree.links.new
    tex = make("ShaderNodeTexCoord")
    scale = make("ShaderNodeVectorMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = stretch
    noise = make("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = frequency
    noise.inputs["Detail"].default_value = 2.5
    noise.inputs["Roughness"].default_value = 0.64
    ramp = make("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*colors[0], 1)
    ramp.color_ramp.elements[1].color = (*colors[1], 1)
    surface = tree.nodes.get("Principled BSDF")
    link(tex.outputs["Object"], scale.inputs[0])
    link(scale.outputs["Vector"], noise.inputs["Vector"])
    link(noise.outputs["Fac"], ramp.inputs[0])
    link(ramp.outputs["Color"], surface.inputs["Base Color"])
    if bump:
        relief = make("ShaderNodeBump")
        relief.inputs["Strength"].default_value = 0.18
        relief.inputs["Distance"].default_value = bump
        link(noise.outputs["Fac"], relief.inputs["Height"])
        link(relief.outputs["Normal"], surface.inputs["Normal"])


def crystal():
    mat = material("07 · sapphire crystal", (0.32, 0.59, 0.63), 0.18, 0.09)
    mat.surface_render_method = "BLENDED"
    mat.use_transparency_overlap = False
    tree = mat.node_tree
    make, link = tree.nodes.new, tree.links.new
    clear = make("ShaderNodeBsdfTransparent")
    glossy = make("ShaderNodeBsdfGlossy")
    glossy.inputs["Color"].default_value = (0.81, 0.95, 1.0, 1)
    glossy.inputs["Roughness"].default_value = 0.065
    facing = make("ShaderNodeFresnel")
    facing.inputs["IOR"].default_value = 1.48
    strength = make("ShaderNodeMath")
    strength.operation = "MULTIPLY_ADD"
    strength.inputs[1].default_value = 0.24
    strength.inputs[2].default_value = 0.010
    mix = make("ShaderNodeMixShader")
    link(facing.outputs[0], strength.inputs[0])
    link(strength.outputs[0], mix.inputs[0])
    link(clear.outputs[0], mix.inputs[1])
    link(glossy.outputs[0], mix.inputs[2])
    link(mix.outputs[0], tree.nodes.get("Material Output").inputs["Surface"])
    return mat


def mesh_obj(
    name, verts, faces, materials, assignments=None, smooth=False, parent=None
):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for m in materials:
        mesh.materials.append(m)
    if assignments:
        mesh.polygons.foreach_set("material_index", assignments)
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(faces))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    return obj


def lathe(name, profile, materials, parent=None, sides=120):
    """Close a radial cross section; each row describes radius, z and next finish."""
    vertices = [
        (r * cos(TAU * i / sides), r * sin(TAU * i / sides), z)
        for r, z, _ in profile
        for i in range(sides)
    ]
    faces = []
    slots = []
    for j, row in enumerate(profile):
        next_row = (j + 1) % len(profile)
        for i in range(sides):
            k = (i + 1) % sides
            faces.append(
                (
                    j * sides + i,
                    j * sides + k,
                    next_row * sides + k,
                    next_row * sides + i,
                )
            )
            slots.append(row[2])
    obj = mesh_obj(name, vertices, faces, materials, slots, parent=parent)
    # Keep broad flat annuli flat, while curved bezel and glass profiles share
    # smooth normals. Otherwise flat dial faces inherit a dark outer-edge halo.
    smooth = []
    for j, (_, z, _) in enumerate(profile):
        flat = abs(z - profile[(j + 1) % len(profile)][1]) < 1.0e-6
        smooth.extend([not flat] * sides)
    obj.data.polygons.foreach_set("use_smooth", smooth)
    return obj


def geometric(name, verts, faces, mat, parent=None):
    return mesh_obj(name, verts, faces, [mat], parent=parent)


def prism(name, outline, lower, upper, mat, parent=None):
    n = len(outline)
    vertices = [(x, y, z) for z in (lower, upper) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    return geometric(name, vertices, faces, mat, parent)


def curve(name, paths, radius, mat, parent=None):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 2
    data.resolution_u = 4
    for path, closed in paths:
        spline = data.splines.new("POLY")
        spline.points.add(len(path) - 1)
        for p, coord in zip(spline.points, path):
            p.co = (*coord, 1)
        spline.use_cyclic_u = closed
    data.materials.append(mat)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    return obj


def empty(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = 0.13
    return obj


def radial_rect(vertices, faces, angle, inner, outer, w0, w1, z0, z1):
    off = len(vertices)
    for z in (z0, z1):
        for radius, width in ((inner, -w0), (outer, -w1), (outer, w1), (inner, w0)):
            vertices.append(
                (
                    radius * sin(angle) + width * cos(angle),
                    radius * cos(angle) - width * sin(angle),
                    z,
                )
            )
    a, b, c, d, e, f, g, h = range(off, off + 8)
    faces.extend(
        [
            (a, b, c, d),
            (h, g, f, e),
            (a, e, f, b),
            (b, f, g, c),
            (c, g, h, d),
            (d, h, e, a),
        ]
    )


def machinings(prefix, parent, metal, dark, light):
    ticks = []
    tf = []
    buttons = []
    bf = []
    luminous = []
    lf = []
    for i in range(60):
        a = TAU * i / 60
        if i % 5:
            radial_rect(ticks, tf, a, 0.768, 0.813, 0.005, 0.006, 0.299, 0.304)
        else:
            radial_rect(buttons, bf, a, 0.685, 0.805, 0.021, 0.027, 0.297, 0.323)
            radial_rect(luminous, lf, a, 0.712, 0.779, 0.009, 0.012, 0.324, 0.329)
    geometric(prefix + " · minute track", ticks, tf, dark, parent)
    geometric(prefix + " · twelve applied indices", buttons, bf, metal, parent)
    geometric(prefix + " · enamel index inlays", luminous, lf, light, parent)
    ribs = []
    rf = []
    for i in range(128):
        radial_rect(ribs, rf, TAU * i / 128, 0.977, 0.998, 0.009, 0.005, 0.085, 0.148)
    geometric(prefix + " · milled case edge", ribs, rf, metal, parent)


def small_dial(prefix, parent, colors):
    """A recessed, engine-turned small-seconds register without numerals."""
    root = empty(prefix + " · small seconds")
    root.parent = parent
    root.location = (0.0, -0.398, 0.296)
    lathe(
        prefix + " · register moulding",
        [
            (0.008, 0, 0),
            (0.214, 0, 1),
            (0.220, 0.010, 0),
            (0.220, 0.022, 0),
            (0.211, 0.027, 1),
            (0.197, 0.010, 0),
            (0.008, 0.011, 0),
        ],
        colors[:2],
        root,
        72,
    )
    lathe(
        prefix + " · concentric engraving",
        [(0.001, 0.012, 0), (0.195, 0.012, 0), (0.195, 0.015, 0), (0.001, 0.015, 0)],
        [colors[2]],
        root,
        64,
    )
    circles = []
    for i in range(8):
        r = 0.045 + 0.015 * i
        circles.append(
            (
                [
                    (r * cos(TAU * k / 64), r * sin(TAU * k / 64), 0.017)
                    for k in range(64)
                ],
                True,
            )
        )
    curve(prefix + " · record grooves", circles, 0.0015, colors[1], root)
    v = []
    f = []
    for i in range(24):
        radial_rect(
            v,
            f,
            TAU * i / 24,
            0.151 if i % 6 else 0.136,
            0.174,
            0.0035,
            0.0035,
            0.018,
            0.022,
        )
    geometric(prefix + " · register marks", v, f, colors[1], root)
    arm = prism(
        prefix + " · register needle",
        [(-0.011, -0.04), (0.011, -0.04), (0.005, 0.149), (-0.005, 0.149)],
        0.024,
        0.031,
        colors[3],
        root,
    )
    arm.rotation_euler.z = -0.48
    arm.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
    arm.rotation_euler.z = -1.7
    arm.keyframe_insert(data_path="rotation_euler", index=2, frame=FRAMES)
    lathe(
        prefix + " · register pin",
        [(0.002, 0.023, 0), (0.024, 0.023, 0), (0.024, 0.035, 0), (0.014, 0.043, 0)],
        [colors[3]],
        root,
        36,
    )


def hand(prefix, length, halfwidth, height, angle, edge, inlay, parent):
    body = prism(
        prefix,
        [
            (0, -0.12),
            (-halfwidth * 0.60, -0.078),
            (-halfwidth, 0.13),
            (-halfwidth * 0.55, length * 0.65),
            (0, length),
            (halfwidth * 0.55, length * 0.65),
            (halfwidth, 0.13),
            (halfwidth * 0.60, -0.078),
        ],
        height,
        height + 0.018,
        edge,
        parent,
    )
    # Two polished facets catch different lights as the camera slides.
    geometric(
        prefix + " · bevel facet",
        [
            (0, -0.054, height + 0.029),
            (-halfwidth * 0.76, 0.145, height + 0.019),
            (0, length * 0.912, height + 0.019),
            (0, 0.14, height + 0.035),
        ],
        [(0, 1, 2, 3)],
        inlay,
        body,
    )
    body.rotation_euler.z = -radians(angle)
    return body


def second_hand(prefix, parent, metal, pearl, colors):
    stem = prism(
        prefix + " · sweep seconds",
        [
            (-0.015, -0.25),
            (0.015, -0.25),
            (0.012, 0.58),
            (0.006, 0.77),
            (-0.006, 0.77),
            (-0.012, 0.58),
        ],
        0.362,
        0.372,
        metal,
        parent,
    )
    counter = lathe(
        prefix + " · hollow counterweight",
        [(0.040, 0.370, 0), (0.061, 0.370, 0), (0.061, 0.382, 0), (0.040, 0.382, 0)],
        [metal],
        stem,
        40,
    )
    counter.location.y = -0.215
    for frame, angle in colors:
        stem.rotation_euler.z = -radians(angle)
        stem.keyframe_insert(data_path="rotation_euler", index=2, frame=frame)
    lathe(
        prefix + " · pivot and jewel",
        [
            (0.002, 0.349, 0),
            (0.069, 0.350, 0),
            (0.076, 0.368, 0),
            (0.066, 0.39, 1),
            (0.040, 0.398, 1),
            (0.002, 0.398, 1),
        ],
        [metal, pearl],
        parent,
        48,
    )


def bow_crown(prefix, parent, metal, trim):
    # Stem points outward in the plane of the face.
    crown = lathe(
        prefix + " · turned winding crown",
        [
            (0.002, 0, 0),
            (0.090, 0, 0),
            (0.090, 0.075, 1),
            (0.131, 0.094, 0),
            (0.145, 0.133, 0),
            (0.137, 0.204, 1),
            (0.098, 0.232, 0),
            (0.002, 0.232, 0),
        ],
        [metal, trim],
        parent,
        64,
    )
    crown.rotation_euler.x = -pi / 2
    crown.location = (0, 0.958, 0.182)
    grooves = []
    for i in range(40):
        a = i * TAU / 40
        grooves.append(
            (
                [
                    (0.144 * cos(a), 1.091, 0.182 + 0.144 * sin(a)),
                    (0.136 * cos(a), 1.162, 0.182 + 0.136 * sin(a)),
                ],
                False,
            )
        )
    curve(prefix + " · crown knurl", grooves, 0.0048, trim, parent)
    bow = [
        (0.245 * cos(TAU * i / 84), 1.23 + 0.215 * sin(TAU * i / 84), 0.165)
        for i in range(84)
    ]
    curve(prefix + " · pendant bow", [(bow, True)], 0.042, metal, parent)


def watch(prefix, where, yaw, palette, glass, seconds):
    case, trim, dial, ink, lume, second, facet = palette
    root = empty(prefix)
    root.location = where
    root.rotation_euler.z = radians(yaw)
    lathe(
        prefix + " · turned case",
        [
            (0.002, 0.02, 0),
            (0.87, 0.02, 0),
            (0.95, 0.042, 0),
            (0.986, 0.082, 1),
            (0.989, 0.146, 0),
            (0.978, 0.165, 1),
            (0.993, 0.180, 0),
            (1.004, 0.203, 0),
            (1.003, 0.224, 1),
            (0.989, 0.241, 0),
            (0.976, 0.259, 1),
            (0.981, 0.279, 0),
            (0.966, 0.303, 0),
            (0.937, 0.326, 1),
            (0.910, 0.341, 1),
            (0.889, 0.346, 1),
            (0.878, 0.313, 0),
            (0.880, 0.290, 0),
            (0.002, 0.284, 0),
        ],
        [case, trim],
        root,
    )
    lathe(
        prefix + " · stepped chapter ring",
        [
            (0.816, 0.289, 0),
            (0.884, 0.288, 0),
            (0.900, 0.319, 1),
            (0.885, 0.327, 0),
            (0.832, 0.303, 0),
            (0.814, 0.300, 0),
        ],
        [case, trim],
        root,
    )
    lathe(
        prefix + " · face",
        [(0.001, 0.259, 0), (0.875, 0.259, 0), (0.874, 0.296, 0), (0.001, 0.296, 0)],
        [dial],
        root,
    )
    machinings(prefix, root, case, ink, lume)
    bow_crown(prefix, root, case, trim)
    small_dial(prefix, root, [case, ink, dial, second])
    hand(prefix + " · hour", 0.487, 0.047, 0.319, 298, case, facet, root)
    hand(prefix + " · minute", 0.667, 0.036, 0.339, 50, case, facet, root)
    second_hand(prefix, root, second, trim, seconds)
    # Closed double-surfaced domed crystal. The outside remains above the jewel.
    dome = [
        (0.002, 0.428, 0),
        (0.30, 0.423, 0),
        (0.58, 0.413, 0),
        (0.76, 0.399, 0),
        (0.85, 0.383, 0),
        (0.881, 0.363, 0),
        (0.888, 0.341, 0),
        (0.883, 0.325, 0),
        (0.867, 0.336, 0),
        (0.842, 0.354, 0),
        (0.751, 0.377, 0),
        (0.575, 0.393, 0),
        (0.29, 0.404, 0),
        (0.002, 0.408, 0),
    ]
    lathe(prefix + " · solid domed crystal", dome[::-1], [glass], root)
    return root


def rounded_pad(name, x0, y0, x1, y1, r, z0, z1, mat):
    rim = []
    for x, y, a in [
        (x1 - r, y0 + r, -pi / 2),
        (x1 - r, y1 - r, 0),
        (x0 + r, y1 - r, pi / 2),
        (x0 + r, y0 + r, pi),
    ]:
        for j in range(9):
            angle = a + j * pi / 16
            rim.append((x + r * cos(angle), y + r * sin(angle)))
    solid = prism(name, rim, z0, z1, mat)
    mod = solid.modifiers.new("Rolled edge", "BEVEL")
    mod.width = 0.026
    mod.segments = 3
    return solid


def chain(name, start, end, bend, metal):
    start, end = Vector(start), Vector(end)
    coords = []
    for i in range(23):
        t = i / 22
        center = start.lerp(end, t) + Vector(
            (0, bend * sin(pi * t), 0.012 * sin(2 * pi * t))
        )
        tangent = (end - start + Vector((0, pi * bend * cos(pi * t), 0))).normalized()
        side = Vector((-tangent.y, tangent.x, 0))
        lift = 0.78 if i % 2 else 0.24
        rim = []
        for j in range(24):
            a = TAU * j / 24
            v = (
                center
                + tangent * (0.107 * cos(a))
                + side * (0.043 * sin(a) * cos(lift))
            )
            v.z += 0.047 * sin(a) * sin(lift)
            rim.append(v)
        coords.append((rim, True))
    curve(name, coords, 0.012, metal)


def light(name, pos, target, power, color, size, size_y):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size_y
    data.energy = power
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (
        (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    )


def camera(scene):
    data = bpy.data.cameras.new("Macro optics")
    obj = bpy.data.objects.new("Camera · slow arc between watches", data)
    bpy.context.collection.objects.link(obj)
    data.lens = 53
    data.dof.use_dof = True
    data.dof.aperture_fstop = 3.5
    data.dof.aperture_blades = 8
    rig = [
        (1, (-0.54, -5.55, 5.83), (-0.08, 0.01, 0.22), (-0.95, 0.05, 0.31)),
        (76, (0.12, -5.39, 5.75), (0.02, 0.04, 0.20), (-0.40, 0.08, 0.33)),
        (FRAMES, (0.73, -5.16, 5.68), (0.11, 0.09, 0.23), (1.04, 0.19, 0.33)),
    ]
    for frame, pos, target, focus in rig:
        obj.location = pos
        obj.rotation_euler = (
            (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        data.dof.focus_distance = (Vector(focus) - obj.location).length
        data.dof.keyframe_insert(data_path="focus_distance", frame=frame)
    scene.camera = obj


def build(output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Two Escapements"
    scene.render.engine = (
        "CYCLES" if bpy.app.version < (4, 2, 0) else "BLENDER_EEVEE_NEXT"
    )
    if scene.render.engine == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = 8
        scene.eevee.use_raytracing = False
    else:
        scene.cycles.samples = 8
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -0.15
    world = bpy.data.worlds.new("Softbox room")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.21, 0.25, 0.27, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.40
    scene.world = world
    steel = material("01 · palladium brushed steel", (0.47, 0.56, 0.58), 0.86, 0.29)
    grain(steel, 1, (35, 2, 60), [(0.35, 0.40, 0.42), (0.57, 0.62, 0.64)])
    polish = material("02 · polished nickel", (0.73, 0.81, 0.84), 0.91, 0.17)
    brass = material("03 · aged bronze case", (0.58, 0.31, 0.099), 0.8, 0.27)
    grain(brass, 1, (45, 2, 55), [(0.43, 0.22, 0.071), (0.72, 0.42, 0.142)])
    edge = material("04 · polished gold rim", (0.85, 0.53, 0.243), 0.87, 0.18)
    ceramic = material("05 · porcelain ivory", (0.85, 0.78, 0.59), 0.13, 0.32)
    teal = material("06 · smoked petrol dial", (0.018, 0.092, 0.091), 0.39, 0.35)
    grain(teal, 1, (120, 3, 1), [(0.012, 0.046, 0.049), (0.030, 0.104, 0.112)])
    glass = crystal()
    navy = material("08 · blued steel", (0.029, 0.111, 0.22), 0.77, 0.21)
    # The darker blue line carries its own saturated reflection through a light dial.
    blue = material("09 · heat blued sweep", (0.015, 0.085, 0.255), 0.63, 0.22)
    amber = material("10 · amber lacquer sweep", (0.94, 0.29, 0.027), 0.48, 0.22)
    jet = material("11 · engraved charcoal", (0.032, 0.051, 0.059), 0.29, 0.37)
    ivory = material("12 · aged lume", (0.87, 0.76, 0.49), 0.16, 0.40)
    pale = material("13 · pale silver edge", (0.80, 0.82, 0.72), 0.72, 0.25)
    wood = material("14 · walnut workbench", (0.16, 0.057, 0.024), 0.08, 0.37)
    grain(wood, 1, (1.65, 14, 6), [(0.047, 0.014, 0.007), (0.32, 0.126, 0.045)], 0.018)
    suede = material("15 · moss leather", (0.090, 0.121, 0.085), 0, 0.66)
    grain(suede, 80, (1, 1, 1), [(0.039, 0.059, 0.044), (0.100, 0.132, 0.084)], 0.016)
    yarn = material("16 · flax stitching", (0.39, 0.315, 0.173), 0.02, 0.75)
    rounded_pad("Walnut table", -14, -12, 14, 14, 0.16, -0.60, -0.16, wood)
    pad = rounded_pad(
        "Leather travel tray", -3.64, -1.58, 3.46, 1.68, 0.24, -0.15, 0, suede
    )
    pad.rotation_euler.z = radians(-9)
    stitches = []
    for y in (-1.445, 1.549):
        for i in range(92):
            x = -3.30 + 0.07 * i
            stitches.append(([(x, y, 0.0035), (x + 0.033, y, 0.0035)], False))
    seam = curve("Flax saddle stitches", stitches, 0.0055, yarn)
    seam.rotation_euler.z = pad.rotation_euler.z
    watch(
        "Palladium · left",
        (-1.043, 0.037, 0.010),
        8,
        [steel, polish, ceramic, jet, jet, blue, navy],
        glass,
        [(1, -16), (49, -3), (74, 2), (99, -5), (140, -14), (FRAMES, -15)],
    )
    watch(
        "Bronze · right",
        (1.11, 0.17, 0.010),
        8,
        [brass, edge, teal, ivory, ivory, amber, pale],
        glass,
        [(1, -16), (49, -3), (74, 4), (107, 47), (142, 98), (FRAMES, 132)],
    )
    chain(
        "Silver chain curling out of frame",
        (-1.23, 1.45, 0.114),
        (-3.69, 1.21, 0.058),
        0.30,
        polish,
    )
    chain(
        "Bronze chain beside crown",
        (0.92, 1.57, 0.115),
        (3.42, 1.60, 0.058),
        0.24,
        brass,
    )
    light(
        "High north softbox",
        (-2.9, 2.3, 5.25),
        (0, 0.25, 0),
        420,
        (1, 0.84, 0.62),
        4.4,
        1.1,
    )
    light(
        "Long cool strip",
        (-3.7, -2.4, 2.7),
        (-0.3, 0.1, 0.2),
        180,
        (0.66, 0.80, 1.0),
        3.0,
        0.62,
    )
    light(
        "Bronze edge strip",
        (3.9, 1.10, 3.4),
        (0.8, 0.2, 0.2),
        350,
        (1, 0.68, 0.37),
        3.3,
        0.72,
    )
    light(
        "Overhead silk", (0.1, -1.3, 5.3), (0, 0.2, 0), 155, (0.85, 0.92, 1), 4.2, 3.9
    )
    camera(scene)
    scene.frame_set(1)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.context.preferences.filepaths.save_version = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reopen file browsers relative to this project on the next artist's machine.
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == "FILE_BROWSER" and space.params is not None:
                    space.params.directory = b"//"
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    build(args.output)
