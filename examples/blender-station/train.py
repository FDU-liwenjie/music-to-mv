"""Two-car electric train for Blender. Units are metres; the leading cab faces -Y."""

from math import cos, pi, sin

import bpy
from mathutils import Vector


CAR_LENGTH = 14.0
TRAIN_LENGTH = CAR_LENGTH * 2 + 0.48
BODY_HALF_WIDTH = 1.43


def _material(name, rgb, *, metal=0.0, rough=0.42, glow=0.0):
    mat = bpy.data.materials.new("Rail · " + name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if glow:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = glow
    return mat


def _materials():
    materials = {
        "cream": _material("butter enamel", (0.82, 0.62, 0.31), metal=0.25, rough=0.30),
        "light": _material("warm ivory", (0.91, 0.76, 0.47), metal=0.25, rough=0.26),
        "red": _material(
            "oxblood lacquer", (0.29, 0.014, 0.024), metal=0.34, rough=0.27
        ),
        "stripe": _material(
            "vermilion lining", (0.71, 0.106, 0.078), metal=0.28, rough=0.28
        ),
        "steel": _material(
            "brushed aluminum", (0.37, 0.43, 0.45), metal=0.72, rough=0.40
        ),
        "trim": _material(
            "bright metal edging", (0.56, 0.62, 0.63), metal=0.83, rough=0.23
        ),
        "roof": _material("weathered roof", (0.20, 0.24, 0.24), metal=0.53, rough=0.55),
        "rubber": _material("rubber seals", (0.018, 0.024, 0.027), rough=0.64),
        "under": _material(
            "undercarriage iron", (0.063, 0.077, 0.082), metal=0.55, rough=0.48
        ),
        "cabglass": _material(
            "petrol driver glass", (0.029, 0.080, 0.107), metal=0.46, rough=0.19
        ),
        "reflect": _material(
            "cab sky reflections", (0.11, 0.22, 0.245), metal=0.52, rough=0.29
        ),
        "warm": _material(
            "lit saloon wall", (0.80, 0.29, 0.078), rough=0.62, glow=0.85
        ),
        "ceiling": _material(
            "ceiling diffuser", (1.00, 0.67, 0.29), rough=0.30, glow=2.0
        ),
        "seat": _material("bottle-green moquette", (0.090, 0.135, 0.105), rough=0.86),
        "brass": _material(
            "brass fittings", (0.49, 0.29, 0.105), metal=0.68, rough=0.36
        ),
        "lamp": _material(
            "tungsten headlamp", (1.00, 0.73, 0.39), rough=0.20, glow=6.0
        ),
        "marker": _material(
            "red marker lens", (0.48, 0.013, 0.010), rough=0.22, glow=0.7
        ),
    }
    # World-size scratches run along each carriage. Only roughness varies,
    # keeping striping and distant highlights stable in a moving shot.
    steel_nodes = materials["steel"].node_tree
    texcoord = steel_nodes.nodes.new("ShaderNodeTexCoord")
    stretch = steel_nodes.nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (60.0, 0.55, 115.0)
    grain = steel_nodes.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 1.0
    grain.inputs["Detail"].default_value = 1.0
    roughness = steel_nodes.nodes.new("ShaderNodeValToRGB")
    roughness.color_ramp.elements[0].color = (0.31, 0.31, 0.31, 1)
    roughness.color_ramp.elements[1].color = (0.49, 0.49, 0.49, 1)
    steel_nodes.links.new(texcoord.outputs["Object"], stretch.inputs[0])
    steel_nodes.links.new(stretch.outputs[0], grain.inputs["Vector"])
    steel_nodes.links.new(grain.outputs["Fac"], roughness.inputs[0])
    steel_nodes.links.new(
        roughness.outputs["Color"],
        steel_nodes.nodes.get("Principled BSDF").inputs["Roughness"],
    )
    mat = _material("saloon glazing", (0.16, 0.27, 0.26), metal=0.35, rough=0.18)
    tree = mat.node_tree
    surface = tree.nodes.get("Principled BSDF")
    transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.11
    tree.links.new(transparent.outputs[0], mix.inputs[1])
    tree.links.new(surface.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], tree.nodes.get("Material Output").inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    materials["glazing"] = mat
    return materials


def _rounded_rect(u0, v0, u1, v1, radius):
    r = min(radius, (u1 - u0) / 2, (v1 - v0) / 2)
    if r <= 0:
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    points = []
    for u, v, start in [
        (u1 - r, v0 + r, -pi / 2),
        (u1 - r, v1 - r, 0),
        (u0 + r, v1 - r, pi / 2),
        (u0 + r, v0 + r, pi),
    ]:
        for index in range(5):
            angle = start + index * pi / 8
            points.append((u + r * cos(angle), v + r * sin(angle)))
    return points


class _Part:
    """Each mechanical assembly is one mesh, including its disconnected details."""

    def __init__(self, name, materials, facing_back=False):
        self.name = name
        self.materials = materials
        self.facing_back = facing_back
        self.vertices = []
        self.faces = []
        self.face_material = []
        self.smooth = []
        self.slots = []

    def vertex(self, p):
        x, y, z = p
        self.vertices.append(
            (-x, TRAIN_LENGTH - y, z) if self.facing_back else (x, y, z)
        )
        return len(self.vertices) - 1

    def face(self, indices, material, smooth=False):
        if material not in self.slots:
            self.slots.append(material)
        self.faces.append(indices)
        self.face_material.append(self.slots.index(material))
        self.smooth.append(smooth)

    def patch(self, points, material, smooth=False):
        self.face([self.vertex(p) for p in points], material, smooth)

    def band(self, rings, material, *, cap=True, smooth=False):
        loops = [[self.vertex(p) for p in ring] for ring in rings]
        if cap:
            self.face(loops[0][::-1], material)
            self.face(loops[-1], material)
        for a, b in zip(loops, loops[1:]):
            for i in range(len(a)):
                j = (i + 1) % len(a)
                self.face([a[i], a[j], b[j], b[i]], material, smooth)

    def box(self, x0, y0, z0, x1, y1, z1, material, bevel=0.0):
        b = min(bevel, (x1 - x0) * 0.22, (y1 - y0) * 0.22, (z1 - z0) * 0.22)
        rings = []
        profiles = [(z0, 0, 0), (z1, 0, 0)]
        if b > 0:
            profiles = [
                (z0, b * 0.48, b * 0.52),
                (z0 + b, 0, b),
                (z1 - b, 0, b),
                (z1, b * 0.48, b * 0.52),
            ]
        for z, inset, r in profiles:
            rings.append(
                [
                    (x, y, z)
                    for x, y in _rounded_rect(
                        x0 + inset, y0 + inset, x1 - inset, y1 - inset, r
                    )
                ]
            )
        self.band(rings, material)

    def rod(self, a, b, radius, material, sides=12):
        a, b = Vector(a), Vector(b)
        axis = (b - a).normalized()
        side = axis.cross(
            Vector((1, 0, 0)) if abs(axis.x) < 0.8 else Vector((0, 1, 0))
        ).normalized()
        other = axis.cross(side)
        rim = [
            radius * (side * cos(2 * pi * i / sides) + other * sin(2 * pi * i / sides))
            for i in range(sides)
        ]
        self.band([[p + q for q in rim] for p in (a, b)], material, smooth=True)

    def panel(self, side, depth, u0, z0, u1, z1, radius, material):
        """Rounded plate parallel to a car side, outward normal in ±X."""
        outline = [
            (side * depth, u, z) for u, z in _rounded_rect(u0, z0, u1, z1, radius)
        ]
        self.patch(outline if side > 0 else outline[::-1], material)

    def window_frame(self, side, depth, u0, z0, u1, z1, radius, border, material):
        outer = _rounded_rect(u0, z0, u1, z1, radius)
        inner = _rounded_rect(
            u0 + border,
            z0 + border,
            u1 - border,
            z1 - border,
            max(0.007, radius - border),
        )
        for i in range(len(outer)):
            j = (i + 1) % len(outer)
            face = [
                (side * depth, u, z)
                for u, z in (outer[i], outer[j], inner[j], inner[i])
            ]
            self.patch(face if side > 0 else face[::-1], material)

    def finish(self, parent):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        for key in self.slots:
            mesh.materials.append(self.materials[key])
        mesh.polygons.foreach_set("material_index", self.face_material)
        mesh.polygons.foreach_set("use_smooth", self.smooth)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = parent
        return obj


# At each height the front is crowned towards the outside and raked at the top.
_NOSE_RINGS = [
    (0.94, 1.08),
    (1.025, 1.31),
    (1.12, 1.395),
    (1.315, 1.425),
    (1.355, 1.43),
    (1.65, 1.43),
    (1.69, 1.43),
    (2.25, 1.43),
    (2.82, 1.43),
    (3.09, 1.385),
    (3.29, 1.28),
    (3.46, 1.03),
    (3.54, 0.62),
]


def _nose_y(x, z):
    return (
        0.012
        + 0.25 * (abs(x) / BODY_HALF_WIDTH) ** 3
        + 0.255 * (max(z - 2.25, 0) / 1.32) ** 1.5
        + 0.09 * (max(1.25 - z, 0) / 0.31) ** 1.4
    )


def _cab_skin(body):
    cols = 20

    def row(z, w):
        return [
            (w * (2 * i / cols - 1), _nose_y(w * (2 * i / cols - 1), z), z)
            for i in range(cols + 1)
        ]

    vert = []
    for z, w in _NOSE_RINGS:
        vert.append([body.vertex(p) for p in row(z, w)])
    for k, ((low, w0), (high, w1)) in enumerate(zip(_NOSE_RINGS, _NOSE_RINGS[1:])):
        material = (
            "under"
            if low < 1.02
            else "steel"
            if low < 1.12
            else "red"
            if low < 1.315
            else "stripe"
            if low < 1.355
            else "red"
            if low < 1.65
            else "stripe"
            if low < 1.69
            else "cream"
        )
        for col in range(cols):
            body.face(
                [
                    vert[k][col],
                    vert[k][col + 1],
                    vert[k + 1][col + 1],
                    vert[k + 1][col],
                ],
                material,
                True,
            )
        for side in (-1, 1):
            p = [
                (side * w0, _nose_y(side * w0, low), low),
                (side * w0, 1.52, low),
                (side * w1, 1.52, high),
                (side * w1, _nose_y(side * w1, high), high),
            ]
            body.patch(p if side > 0 else p[::-1], material)
    z, w = _NOSE_RINGS[-1]
    body.patch(
        [
            (-w, _nose_y(-w, z), z),
            (0, _nose_y(0, z), z),
            (w, _nose_y(w, z), z),
            (w, 1.52, z),
            (-w, 1.52, z),
        ],
        "roof",
    )


def _face_panel(part, points, offset, mat):
    # Conform rounded windows to the convex front. A triangle fan avoids the
    # irregular triangulation of a nonplanar n-gon during glTF or MP4 export.
    mid = tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))
    center = part.vertex((mid[0], _nose_y(*mid) - offset, mid[1]))
    rim = [part.vertex((x, _nose_y(x, z) - offset, z)) for x, z in points]
    for i in range(len(rim)):
        part.face([center, rim[i], rim[(i + 1) % len(rim)]], mat)


def _cab_fittings(part):
    for s in (-1, 1):
        sign = lambda contour: [
            (s * x, z) for x, z in (contour if s > 0 else contour[::-1])
        ]
        for edge, offset, material in [
            (0, 0.023, "rubber"),
            (0.042, 0.032, "trim"),
            (0.061, 0.045, "cabglass"),
        ]:
            rect = _rounded_rect(
                0.09 + edge, 2.29 + edge, 1.21 - edge, 3.08 - edge, 0.105 - edge * 0.5
            )
            # Pinch the top outside corners and draw the centre pillar upright.
            points = [
                (
                    x - 0.080 * ((z - 2.29) / 0.79) * (x / 1.21),
                    z + 0.055 * (1 - x / 1.21),
                )
                for x, z in rect
            ]
            _face_panel(part, sign(points), offset, material)
        _face_panel(
            part,
            sign([(0.82, 2.40), (0.94, 2.40), (0.59, 2.98), (0.49, 2.98)]),
            0.070,
            "reflect",
        )

        def wiper(p, q, r, mat):
            point = lambda v: (s * v[0], _nose_y(s * v[0], v[1]) - 0.092, v[1])
            part.rod(point(p), point(q), r, mat, 10)

        wiper((0.25, 2.30), (0.69, 2.68), 0.023, "rubber")
        wiper((0.49, 2.52), (0.88, 2.78), 0.018, "under")
        wiper((0.24, 2.30), (0.29, 2.34), 0.037, "brass")
        for x, z, r, material in [
            (1.035, 2.02, 0.205, "lamp"),
            (1.205, 1.52, 0.086, "marker"),
        ]:
            x *= s
            y = _nose_y(x, z)
            part.rod((x, y + 0.035, z), (x, y - 0.040, z), r, "rubber", 32)
            part.rod((x, y - 0.038, z), (x, y - 0.069, z), r * 0.88, "trim", 32)
            part.rod((x, y - 0.067, z), (x, y - 0.083, z), r * 0.74, material, 32)
            if material == "lamp":
                for dz in (-0.045, 0, 0.045):
                    part.rod(
                        (x - 0.105, y - 0.084, z + dz),
                        (x + 0.105, y - 0.084, z + dz),
                        0.0035,
                        "light",
                        8,
                    )
        # Front footsteps, access handrail and lower air hose.
        part.rod((s * 1.26, -0.01, 1.18), (s * 0.86, -0.095, 1.18), 0.028, "trim")
        part.rod((s * 1.30, -0.016, 1.30), (s * 1.30, -0.016, 1.58), 0.020, "trim")
        part.rod((s * 0.53, -0.018, 0.96), (s * 0.63, -0.125, 0.75), 0.043, "rubber")
        part.rod((s * 0.63, -0.125, 0.75), (s * 0.48, -0.20, 0.69), 0.040, "rubber")
    # Small louver, no route text, mimic lights or insignia.
    _face_panel(part, _rounded_rect(-0.40, 3.18, 0.40, 3.34, 0.04), 0.025, "rubber")
    for i in range(5):
        z = 3.202 + i * 0.027
        part.rod(
            (-0.32, _nose_y(-0.32, z) - 0.039, z),
            (0.32, _nose_y(0.32, z) - 0.039, z),
            0.0065,
            "roof",
            8,
        )
    _face_panel(part, _rounded_rect(-0.48, 1.85, 0.48, 2.01, 0.055), 0.016, "red")
    for z in (1.886, 1.943):
        part.rod((-0.40, -0.021, z), (0.40, -0.021, z), 0.009, "trim", 10)
    # A folded-steel shank and two-piece knuckle protrude just ahead of the pilot.
    part.box(-0.15, -0.23, 0.69, 0.15, 0.28, 0.86, "under", 0.045)
    part.box(-0.17, -0.33, 0.68, 0.05, -0.20, 0.87, "under", 0.033)
    part.box(0.015, -0.32, 0.69, 0.14, -0.245, 0.825, "roof", 0.025)


_SIDE_BAYS = [
    (1.52, 2.18, "cab"),
    (2.32, 3.57, "door"),
    (3.76, 4.75, "window"),
    (4.89, 5.88, "window"),
    (6.02, 7.01, "window"),
    (7.19, 8.44, "door"),
    (8.62, 9.61, "window"),
    (9.75, 10.74, "window"),
    (10.88, 11.87, "window"),
    (12.06, 13.31, "door"),
]


def _car_sides(shell, detail, interior):
    w = BODY_HALF_WIDTH

    def side_box(part, s, x0, y0, z0, x1, y1, z1, mat, bevel=0):
        left, right = sorted((s * x0, s * x1))
        part.box(left, y0, z0, right, y1, z1, mat, bevel)

    for s in (-1, 1):

        def sheet(y0, z0, y1, z1, mat, depth=w):
            shell.panel(s, depth, y0, z0, y1, z1, 0, mat)

        sheet(1.519, 1.04, CAR_LENGTH, 1.30, "steel")
        sheet(1.519, 1.30, CAR_LENGTH, 1.36, "stripe")
        sheet(1.519, 1.36, CAR_LENGTH, 1.65, "red")
        sheet(1.519, 1.65, CAR_LENGTH, 1.70, "stripe")
        sheet(1.519, 1.70, CAR_LENGTH, 1.91, "steel")
        sheet(1.519, 2.87, CAR_LENGTH, 3.18, "steel")
        sheet(1.519, 3.13, CAR_LENGTH, 3.19, "red", w + 0.002)
        last = 1.52
        for start, end, kind in _SIDE_BAYS:
            if start > last:
                sheet(last, 1.91, start, 2.87, "steel")
            if kind == "door":
                for sign, (lo, hi) in enumerate(
                    [(start, (start + end) / 2), ((start + end) / 2, end)]
                ):
                    # Full-height door leaves wrap the continuing waist stripes.
                    detail.panel(s, w + 0.012, lo, 1.085, hi, 3.055, 0.026, "rubber")
                    detail.panel(
                        s, w + 0.016, lo + 0.012, 1.10, hi - 0.012, 3.04, 0.023, "steel"
                    )
                    detail.panel(
                        s, w + 0.022, lo + 0.018, 1.36, hi - 0.018, 1.65, 0, "red"
                    )
                    detail.panel(
                        s, w + 0.023, lo + 0.018, 1.653, hi - 0.018, 1.70, 0, "stripe"
                    )
                    detail.panel(
                        s,
                        w + 0.020,
                        lo + 0.082,
                        2.04,
                        hi - 0.082,
                        2.80,
                        0.066,
                        "rubber",
                    )
                    detail.panel(
                        s, w + 0.026, lo + 0.11, 2.075, hi - 0.11, 2.77, 0.047, "warm"
                    )
                    detail.panel(
                        s, w + 0.029, lo + 0.11, 2.67, hi - 0.11, 2.74, 0.012, "ceiling"
                    )
                    handle = hi - 0.038 if sign == 0 else lo + 0.038
                    detail.rod(
                        (s * (w + 0.037), handle, 1.80),
                        (s * (w + 0.037), handle, 2.00),
                        0.010,
                        "trim",
                        8,
                    )
                side_box(
                    detail,
                    s,
                    w - 0.06,
                    start + 0.03,
                    1.013,
                    w + 0.074,
                    end - 0.03,
                    1.049,
                    "trim",
                    0.012,
                )
            else:
                # The frame is a true hole. Seats, poles and amber walls sit
                # physically behind a lightly reflecting pane.
                detail.window_frame(
                    s, w + 0.013, start, 1.91, end, 2.87, 0.095, 0.047, "rubber"
                )
                detail.window_frame(
                    s,
                    w + 0.021,
                    start + 0.037,
                    1.947,
                    end - 0.037,
                    2.833,
                    0.064,
                    0.015,
                    "trim",
                )
                detail.panel(
                    s,
                    w + 0.010,
                    start + 0.046,
                    1.957,
                    end - 0.046,
                    2.824,
                    0.055,
                    "glazing",
                )
                detail.rod(
                    (s * (w + 0.030), start + 0.047, 2.64),
                    (s * (w + 0.030), end - 0.047, 2.64),
                    0.013,
                    "trim",
                    8,
                )
                middle = (start + end) / 2
                if kind == "cab":
                    side_box(
                        interior, s, 0.72, start, 1.4, 0.76, end, 2.89, "cabglass", 0.02
                    )
                else:
                    side_box(
                        interior,
                        s,
                        0.45,
                        start - 0.10,
                        1.56,
                        0.51,
                        end + 0.10,
                        2.95,
                        "warm",
                        0.016,
                    )
                    side_box(
                        interior,
                        s,
                        0.95,
                        start - 0.04,
                        2.765,
                        1.055,
                        end + 0.04,
                        2.804,
                        "ceiling",
                        0.01,
                    )
                    side_box(
                        interior,
                        s,
                        0.83,
                        middle - 0.37,
                        1.68,
                        1.12,
                        middle + 0.36,
                        1.80,
                        "seat",
                        0.045,
                    )
                    side_box(
                        interior,
                        s,
                        0.83,
                        middle + 0.10,
                        1.77,
                        1.12,
                        middle + 0.21,
                        2.21,
                        "seat",
                        0.047,
                    )
                    side_box(
                        interior,
                        s,
                        0.86,
                        middle + 0.12,
                        2.16,
                        1.13,
                        middle + 0.225,
                        2.29,
                        "rubber",
                        0.035,
                    )
                    interior.rod(
                        (s * 1.11, start + 0.22, 1.70),
                        (s * 1.11, start + 0.22, 2.81),
                        0.014,
                        "brass",
                        8,
                    )
            last = end
        sheet(last, 1.91, CAR_LENGTH, 2.87, "steel")
        for z in (1.123, 1.184, 1.245, 1.743, 1.802):
            for a, b in [(1.53, 2.25), (3.64, 7.12), (8.50, 11.99), (13.36, 13.96)]:
                detail.rod(
                    (s * (w + 0.006), a, z), (s * (w + 0.006), b, z), 0.012, "trim", 8
                )
        detail.rod((s * 1.405, 1.53, 3.225), (s * 1.405, 13.98, 3.225), 0.026, "trim")
    shell.box(-1.375, 1.49, 0.994, 1.375, CAR_LENGTH, 1.09, "under", 0.045)
    shell.box(-1.403, 13.916, 1.05, 1.403, CAR_LENGTH, 3.225, "steel", 0.043)


def _roof(part):
    arch = [
        (-1.43, 3.178),
        (-1.39, 3.245),
        (-1.30, 3.321),
        (-1.14, 3.398),
        (-0.90, 3.471),
        (-0.63, 3.519),
        (0, 3.548),
        (0.63, 3.519),
        (0.90, 3.471),
        (1.14, 3.398),
        (1.30, 3.321),
        (1.39, 3.245),
        (1.43, 3.178),
    ]
    for (x0, z0), (x1, z1) in zip(arch, arch[1:]):
        part.patch(
            [
                (x0, 1.49, z0),
                (x1, 1.49, z1),
                (x1, CAR_LENGTH, z1),
                (x0, CAR_LENGTH, z0),
            ],
            "roof",
            True,
        )
    for mid in (4.36, 10.25):
        part.box(-0.87, mid - 1.04, 3.49, 0.87, mid + 1.04, 3.68, "rubber", 0.050)
        part.box(-0.83, mid - 0.99, 3.60, 0.83, mid + 0.99, 3.86, "roof", 0.090)
        for hub in (mid - 0.55, mid + 0.48):
            part.rod((0, hub, 3.853), (0, hub, 3.871), 0.32, "under", 28)
            for i in range(8):
                a = i * pi / 4
                part.rod(
                    (0.08 * cos(a), hub + 0.08 * sin(a), 3.88),
                    (0.28 * cos(a + 0.24), hub + 0.28 * sin(a + 0.24), 3.88),
                    0.020,
                    "roof",
                    8,
                )
            part.rod((0, hub, 3.877), (0, hub, 3.90), 0.071, "trim", 16)
        for side in (-1, 1):
            for j in range(10):
                part.box(
                    side * 0.825 - 0.009,
                    mid - 0.78 + j * 0.16,
                    3.665,
                    side * 0.825 + 0.009,
                    mid - 0.725 + j * 0.16,
                    3.79,
                    "under",
                )
    # Roof cable, ceramic posts, a low, folded diamond pantograph.
    for x in (-0.43, 0.43):
        for y in (6.74, 8.31):
            part.rod((x, y, 3.50), (x, y, 3.685), 0.062, "brass", 12)
            for z in (3.565, 3.62):
                part.rod((x, y, z), (x, y, z + 0.024), 0.083, "light", 12)
        part.rod((x, 6.74, 3.69), (x, 8.31, 3.69), 0.030, "under")
        part.rod((x, 6.84, 3.71), (x, 7.79, 3.94), 0.026, "under")
        part.rod((x, 7.79, 3.94), (x, 7.19, 4.00), 0.020, "brass")
    part.rod((-0.81, 7.19, 4.01), (0.81, 7.19, 4.01), 0.027, "under")
    part.rod((-0.66, 7.12, 4.03), (0.66, 7.12, 4.03), 0.014, "brass")
    part.rod((0.77, 0.94, 3.41), (0.77, 1.19, 3.77), 0.016, "under", 8)


def _underframe(part):
    part.box(-0.89, 0.62, 0.78, 0.89, 13.76, 1.02, "under", 0.08)
    for y in (4.72, 6.51, 8.62):
        part.box(-0.91, y - 0.58, 0.43, 0.91, y + 0.58, 0.82, "under", 0.066)
        for x in (-0.93, 0.93):
            for dz in (0, 0.075, 0.15):
                part.box(
                    x - 0.014,
                    y - 0.42,
                    0.53 + dz,
                    x + 0.014,
                    y + 0.42,
                    0.56 + dz,
                    "roof",
                )
    for center in (2.04, 11.84):
        for y in (center - 0.78, center + 0.78):
            part.rod((-0.91, y, 0.363), (0.91, y, 0.363), 0.104, "under", 14)
            for s in (-1, 1):
                # Tread meets the rail at z=0; flange is inboard of the railhead.
                part.rod(
                    (s * 0.690, y, 0.363), (s * 0.785, y, 0.363), 0.363, "under", 36
                )
                part.rod(
                    (s * 0.678, y, 0.363), (s * 0.709, y, 0.363), 0.383, "roof", 36
                )
                part.rod(
                    (s * 0.790, y, 0.363), (s * 0.843, y, 0.363), 0.240, "roof", 24
                )
                part.rod(
                    (s * 0.838, y, 0.363), (s * 0.908, y, 0.363), 0.109, "under", 16
                )
        for s in (-1, 1):
            part.box(
                min(s * 0.88, s * 1.01),
                center - 0.96,
                0.48,
                max(s * 0.88, s * 1.01),
                center + 0.96,
                0.655,
                "under",
                0.055,
            )
            for y in (center - 0.49, center + 0.49):
                for z in (0.544, 0.59, 0.636, 0.682):
                    part.rod(
                        (s * 0.947, y, z), (s * 0.947, y, z + 0.021), 0.094, "roof", 12
                    )


def _connection(part):
    y0 = CAR_LENGTH
    for i in range(6):
        a = y0 + 0.026 + i * 0.073
        part.box(-1.01, a, 1.08, 1.01, a + 0.055, 3.06, "rubber", 0.038)
        for s in (-1, 1):
            part.rod(
                (s * 0.994, a + 0.025, 1.14),
                (s * 0.994, a + 0.025, 3.00),
                0.014,
                "roof",
                8,
            )
    part.box(-0.68, y0, 0.99, 0.68, TRAIN_LENGTH - CAR_LENGTH, 1.095, "steel", 0.017)
    part.rod((0, y0, 0.72), (0, y0 + 0.48, 0.72), 0.11, "under")


def build_train():
    """Return a movable Empty at the front track center, facing world -Y."""
    root = bpy.data.objects.new("Train · butter and oxblood suburban EMU", None)
    bpy.context.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.55
    root["length_m"] = TRAIN_LENGTH
    root["track_gauge_m"] = 1.435
    mats = _materials()
    for which in (0, 1):

        def assembly(label):
            return _Part(f"Car {which + 1} · {label}", mats, facing_back=bool(which))

        shell, detail, cab = (
            assembly("enamel and body"),
            assembly("side frames"),
            assembly("cab fittings"),
        )
        interior, roof, running = (
            assembly("saloon"),
            assembly("roof equipment"),
            assembly("running gear"),
        )
        _cab_skin(shell)
        _cab_fittings(cab)
        _car_sides(shell, detail, interior)
        _roof(roof)
        _underframe(running)
        for part in (shell, detail, cab, interior, roof, running):
            part.finish(root)
    bridge = _Part("Inter-car concertina gangway", mats)
    _connection(bridge)
    bridge.finish(root)
    return root
