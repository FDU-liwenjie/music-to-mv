"""Model the unclaimed red windbreaker lying over the platform bench."""

import math
import bpy
from mathutils import Vector


def fabric(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    tree = mat.node_tree
    shader = tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 245
    bump = tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.007
    tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def surface(name, points, faces, material, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    for face in mesh.polygons:
        face.use_smooth = True
    sub = obj.modifiers.new("Soft woven folds", "SUBSURF")
    sub.levels = 2
    solid = obj.modifiers.new("Lined cloth", "SOLIDIFY")
    solid.thickness = 0.005
    return obj


def piping(name, points, radius, mat, collection):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, pos in zip(spline.bezier_points, points):
        point.co = pos
        point.handle_left_type = point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(mat)


def build_coat(x, y, seat_z):
    collection = bpy.data.collections.new("04 • Red windbreaker")
    bpy.context.scene.collection.children.link(collection)
    wool = fabric("Windbreaker • vermilion twill", (0.28, 0.010, 0.008), 0.48)
    lining = fabric("Windbreaker • oxblood lining", (0.074, 0.007, 0.011), 0.67)
    zip_mat = fabric("Windbreaker • worn bronze zip", (0.26, 0.14, 0.055), 0.34)
    # The coat hooks over the back rail, pools on the slats, and drops over the front lip.
    rows = [
        (0.33, 0.23, 0.27),
        (0.27, 0.41, 0.31),
        (0.19, 0.49, 0.25),
        (0.12, 0.47, 0.30),
        (0.075, 0.39, 0.31),
        (0.05, 0.29, 0.30),
        (0.01, 0.17, 0.28),
        (-0.02, 0.095, 0.28),
        (-0.075, 0.065, 0.28),
        (-0.19, 0.067, 0.27),
        (-0.26, 0.047, 0.266),
        (-0.295, -0.055, 0.26),
        (-0.31, -0.16, 0.245),
    ]

    def cloth_point(row, cross):
        dx, height, half_width = row
        fold = 0.022 * math.sin(11 * cross + height * 9) + 0.012 * math.cos(
            17 * cross - 11 * height
        )
        return (
            x + dx + fold * 0.55,
            y + half_width * cross + 0.04 * (1 - height),
            seat_z + height + fold + 0.018 * cross,
        )

    n = 21
    points = [cloth_point(row, j * 2 / (n - 1) - 1) for row in rows for j in range(n)]
    faces = [
        (i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j)
        for i in range(len(rows) - 1)
        for j in range(n - 1)
    ]
    surface("Coat • folded body", points, faces, wool, collection)

    for side in (-1, 1):
        arm = [
            (0.13, 0.24, 0.41, 0.106),
            (0.105, 0.32, 0.34, 0.092),
            (0.04, 0.37, 0.24, 0.082),
            (-0.045, 0.40, 0.12, 0.077),
            (-0.13, 0.38, 0.081, 0.067),
            (-0.20, 0.32, 0.083, 0.060),
        ]
        if side == 1:
            arm[3:] = [
                (0.01, 0.46, 0.14, 0.08),
                (-0.01, 0.53, 0.075, 0.073),
                (-0.065, 0.58, 0.077, 0.059),
            ]
        verts = []
        for i, (ax, ay, h, r) in enumerate(arm):
            for j in range(12):
                angle = j * math.tau / 12
                crinkle = 1 + 0.07 * math.cos(angle * 3 + i)
                verts.append(
                    (
                        x + ax + r * math.cos(angle) * crinkle,
                        y + side * ay,
                        seat_z + h + r * 0.63 * math.sin(angle) * crinkle,
                    )
                )
        rings = [
            (
                i * 12 + j,
                i * 12 + (j + 1) % 12,
                (i + 1) * 12 + (j + 1) % 12,
                (i + 1) * 12 + j,
            )
            for i in range(len(arm) - 1)
            for j in range(12)
        ]
        surface("Coat • sleeve " + str(side), verts, rings, wool, collection)
        last = verts[-12:]
        piping("Coat • stitched cuff", last + [last[0]], 0.005, lining, collection)
        collar = [
            (x + 0.10, y, seat_z + 0.446),
            (x + 0.06, y + side * 0.105, seat_z + 0.40),
            (x + 0.13, y + side * 0.185, seat_z + 0.49),
            (x + 0.22, y + side * 0.14, seat_z + 0.53),
            (x + 0.23, y + side * 0.04, seat_z + 0.52),
        ]
        surface(
            "Coat • turned collar",
            collar,
            [(0, 1, 2), (0, 2, 4), (2, 3, 4)],
            lining,
            collection,
        )
    for side in [-1, 1]:
        pocket = [
            Vector(cloth_point(rows[i], side * c)) + Vector((-0.012, 0, 0.014))
            for i, c in [(6, 0.71), (7, 0.64), (8, 0.55), (9, 0.49)]
        ]
        piping("Coat • welt pocket seam", pocket, 0.006, lining, collection)
    zipper = [
        Vector(cloth_point(row, -0.15)) + Vector((-0.007, 0, 0.01)) for row in rows[3:]
    ]
    piping("Coat • zipper", zipper, 0.0035, zip_mat, collection)
    piping(
        "Coat • folded hem",
        [cloth_point(rows[-1], i / 5) for i in range(-5, 6)],
        0.005,
        lining,
        collection,
    )
