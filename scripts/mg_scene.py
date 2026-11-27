"""Build native Blender geometry from the motion.json format in MOTION.md."""

import json
import math
import re
import sys
from pathlib import Path

import bpy


def number(value, name, minimum=None):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or (minimum is not None and value < minimum)
    ):
        raise ValueError(f"Invalid {name}: {value!r}")
    return value


def xy(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"Expected [x,y], got {value!r}")
    return tuple(number(n, "coordinate") for n in value)


def rgb(value, palette):
    color = palette.get(value, value) if isinstance(value, str) else None
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError(f"Expected an sRGB #RRGGBB or palette name, got {value!r}")
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels
    ) + (1,)


EASE = {"linear": "LINEAR", "smooth": "BEZIER", "hold": "CONSTANT"}


def insert(target, prop, value, frame, easing):
    setattr(target, prop, value)
    target.keyframe_insert(data_path=prop, frame=frame)
    # RNA insertion defaults to Bezier regardless of the UI preference. Set
    # the actual key on the owning object's (or node tree's) action slot.
    anim = target.id_data.animation_data
    bag = anim.action.layers[0].strips[0].channelbag(anim.action_slot)
    path = target.path_from_id(prop)
    for curve in bag.fcurves:
        if curve.data_path == path:
            for key in reversed(curve.keyframe_points):
                if abs(key.co.x - frame) < 0.001:
                    key.interpolation = EASE[easing]
                    if easing == "smooth":
                        key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
                    break
            curve.update()


def animate(keys, fields, start, length, fps):
    """fields maps JSON channels to (Blender target, RNA property, base, converter)."""
    if not isinstance(keys, list):
        raise TypeError("keys must be an array")
    used = set()
    previous = -1
    for key in keys:
        t = number(key.get("t"), "key time", 0)
        if t > length + 1e-8 or t <= previous:
            raise ValueError(f"Key times must increase within 0..{length:g}s: {t}")
        previous = t
        if key.get("ease", "smooth") not in EASE:
            raise ValueError(f"Unknown easing: {key['ease']!r}")
        channels = set(key) - {"t", "ease"}
        if not channels or not channels <= fields.keys():
            raise ValueError(f"Unknown or missing animation channel in {key!r}")
        used.update(channels)
    for channel, (target, prop, base, convert) in fields.items():
        value = convert(base)
        setattr(target, prop, value)
        if channel in used and not (keys[0]["t"] == 0 and channel in keys[0]):
            insert(target, prop, value, 1 + start * fps, "smooth")
    for key in keys:
        frame = 1 + (start + key["t"]) * fps
        for channel in key.keys() - {"t", "ease"}:
            target, prop, _, convert = fields[channel]
            insert(
                target, prop, convert(key[channel]), frame, key.get("ease", "smooth")
            )


def material(color):
    mat = bpy.data.materials.new("Ink")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    emission.inputs["Color"].default_value = color
    mat.diffuse_color = color
    return mat, emission.inputs["Color"]


def curve_data(spec):
    shape = spec["shape"]
    data = bpy.data.curves.new(spec["id"], "CURVE")
    data.dimensions = "3D"
    filled = spec.get("filled", False)
    closed = spec.get("closed", False)
    if shape == "bezier":
        points = spec["points"]
        if len(points) < (3 if filled else 2):
            raise ValueError("A Bezier needs two anchors, or three for a fill")
        spline = data.splines.new("BEZIER")
        spline.bezier_points.add(len(points) - 1)
        for anchor, point in zip(spline.bezier_points, points):
            if isinstance(point, dict):
                anchor.co = (*xy(point["co"]), 0)
                for side in ("left", "right"):
                    handle = "handle_" + side
                    if side in point:
                        setattr(anchor, handle + "_type", "FREE")
                        setattr(anchor, handle, (*xy(point[side]), 0))
                    else:
                        setattr(anchor, handle + "_type", "AUTO")
            else:
                anchor.co = (*xy(point), 0)
                anchor.handle_left_type = anchor.handle_right_type = "AUTO"
        spline.use_cyclic_u = bool(closed or filled)
        needs_reveal = "reveal" in spec or any(
            "reveal" in k for k in spec.get("keys", [])
        )
        if closed and not filled and needs_reveal:
            # Blender ignores bevel_factor_end on cyclic splines. Open the
            # spline at its seam and duplicate that anchor with both tangents.
            handles = [
                (p.co.copy(), p.handle_left.copy(), p.handle_right.copy())
                for p in spline.bezier_points
            ]
            spline.use_cyclic_u = False
            spline.bezier_points.add(1)
            for p, (co, left, right) in zip(
                spline.bezier_points, [*handles, handles[0]]
            ):
                p.handle_left_type = p.handle_right_type = "FREE"
                p.co, p.handle_left, p.handle_right = co, left, right
        data.resolution_u = 20
    else:
        if filled:
            raise ValueError(
                "Use a polygon or a filled closed Bezier for filled geometry"
            )
        if shape == "polyline":
            points = [xy(p) for p in spec["points"]]
            if closed and points:
                points.append(points[0])
        else:
            radius = number(spec.get("radius", 1), "radius", 0.00001)
            a = number(spec.get("startAngle", 0), "startAngle")
            b = (
                a + 360
                if shape == "ring"
                else number(spec.get("endAngle", 90), "endAngle")
            )
            steps = max(2, min(2048, math.ceil(abs(b - a) / 3)))
            angles = (math.radians(a + (b - a) * i / steps) for i in range(steps + 1))
            points = [(radius * math.cos(v), radius * math.sin(v)) for v in angles]
        if len(points) < 2:
            raise ValueError("A polyline needs at least two points")
        spline = data.splines.new("POLY")
        spline.points.add(len(points) - 1)
        for anchor, (x, y) in zip(spline.points, points):
            anchor.co = (x, y, 0, 1)
    if filled:
        data.dimensions = "2D"
        data.fill_mode = "BOTH"
    else:
        data.bevel_depth = number(spec.get("stroke", 0.08), "stroke", 0.00001) / 2
        data.bevel_resolution = 2
        data.use_fill_caps = True
        data.bevel_factor_mapping_end = "SPLINE"
    return data


def geometry(spec):
    shape = spec["shape"]
    if shape == "group":
        return None
    if shape in {"ring", "arc", "polyline", "bezier"}:
        return curve_data(spec)
    if shape == "rect":
        w, h = xy(spec.get("size", [1, 1]))
        if min(w, h) <= 0:
            raise ValueError("Rectangle dimensions must be positive")
        points = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    elif shape == "disk":
        r = number(spec.get("radius", 1), "radius", 0.00001)
        points = [
            (r * math.cos(i * math.tau / 128), r * math.sin(i * math.tau / 128))
            for i in range(128)
        ]
    elif shape == "polygon":
        points = [xy(v) for v in spec["points"]]
        if len(points) < 3:
            raise ValueError("A polygon needs at least three points")
    else:
        raise ValueError(f"Unknown shape {shape!r}")
    mesh = bpy.data.meshes.new(spec["id"])
    mesh.from_pydata([(x, y, 0) for x, y in points], [], [list(range(len(points)))])
    mesh.update()
    return mesh


def visibility(obj, start, end, fps):
    for prop in ("hide_render", "hide_viewport"):
        if start > 0:
            insert(obj, prop, True, 1, "hold")
        insert(obj, prop, False, 1 + start * fps, "hold")
        insert(obj, prop, True, 1 + end * fps, "hold")


def make_cue(cue, palette, fps, materials):
    collection = bpy.data.collections.new(cue["name"])
    bpy.context.scene.collection.children.link(collection)
    objects = {}
    parents = {}
    for i, spec in enumerate(cue["objects"]):
        name = spec.get("id")
        if not isinstance(name, str) or not name or name in objects:
            raise ValueError(
                f"{cue['name']}: expected a unique object id, got {name!r}"
            )
        try:
            data = geometry(spec)
            obj = bpy.data.objects.new(name, data)
            collection.objects.link(obj)
            objects[name] = obj
            if spec.get("parent") is not None:
                parents[name] = spec["parent"]
            z = number(spec.get("z", i * 0.003), "z")
            keys = spec.get("keys", [])
            # Flatten the bevel in depth so thick strokes respect the layer order.
            depth = 0.001 if obj.type == "CURVE" else 1
            fields = {
                "position": (
                    obj,
                    "location",
                    spec.get("position", [0, 0]),
                    lambda p, plane=z: (*xy(p), plane),
                ),
                "scale": (
                    obj,
                    "scale",
                    spec.get("scale", [1, 1]),
                    lambda s, thickness=depth: (*xy(s), thickness),
                ),
                "rotation": (
                    obj,
                    "rotation_euler",
                    spec.get("rotation", 0),
                    lambda a: (0, 0, math.radians(number(a, "rotation"))),
                ),
            }
            if data:
                ink = rgb(spec.get("color", "#FFFFFF"), palette)
                has_color_keys = any("color" in key for key in keys)
                if has_color_keys:
                    mat, socket = material(ink)
                    fields["color"] = (
                        socket,
                        "default_value",
                        spec.get("color", "#FFFFFF"),
                        lambda c: rgb(c, palette),
                    )
                else:
                    if ink not in materials:
                        materials[ink] = material(ink)[0]
                    mat = materials[ink]
                data.materials.append(mat)
            if obj.type == "CURVE" and not spec.get("filled"):
                fields["reveal"] = (
                    data,
                    "bevel_factor_end",
                    spec.get("reveal", 1),
                    reveal,
                )
            elif "reveal" in spec:
                raise ValueError("reveal requires a stroked path")
            animate(keys, fields, cue["start"], cue["end"] - cue["start"], fps)
            visibility(obj, cue["start"], cue["end"], fps)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"{cue['name']} / {name}: {exc}") from exc
    for child, parent in parents.items():
        visited = {child}
        ancestor = parent
        while ancestor is not None:
            if ancestor in visited or ancestor not in objects:
                raise ValueError(f"{cue['name']}: invalid parent chain for {child!r}")
            visited.add(ancestor)
            ancestor = parents.get(ancestor)
        objects[child].parent = objects[parent]


def reveal(v):
    if number(v, "reveal", 0) > 1:
        raise ValueError("reveal must be between 0 and 1")
    return v


def build(source, output):
    doc = json.loads(source.read_text(encoding="utf-8-sig"))
    if doc.get("version") != 1:
        raise ValueError("Expected motion format version 1")
    duration = number(doc["duration"], "duration", 1e-10)
    fps = doc.get("fps", 24)
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError("fps must be an integer from 1 to 120")
    palette = doc.get("palette", {})
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 0
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.frame_end = max(1, math.ceil(duration * fps))
    scene.world = bpy.data.worlds.new("Paper")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    bg_node.inputs["Strength"].default_value = 1
    bgcolor = bg_node.inputs["Color"]
    background = rgb(doc.get("background", "#101820"), palette)
    insert(bgcolor, "default_value", background, 1, "hold")
    camera_data = bpy.data.cameras.new("Orthographic")
    camera_data.type = "ORTHO"
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.clip_end = 1000
    cam = bpy.data.objects.new("Motion camera", camera_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    camera = doc.get("camera", {})
    animate(
        camera.get("keys", []),
        {
            "position": (
                cam,
                "location",
                camera.get("position", [0, 0]),
                lambda p: (*xy(p), 400),
            ),
            "width": (
                camera_data,
                "ortho_scale",
                camera.get("width", 16),
                lambda w: number(w, "camera width", 0.001),
            ),
            "rotation": (
                cam,
                "rotation_euler",
                camera.get("rotation", 0),
                lambda a: (0, 0, math.radians(number(a, "rotation"))),
            ),
        },
        0,
        duration,
        fps,
    )
    cues = doc.get("cues")
    if not isinstance(cues, list) or not cues:
        raise ValueError("Provide at least one cue")
    last = 0
    materials = {}
    for i, cue in enumerate(cues):
        start = number(cue.get("start"), "cue start", 0)
        end = number(cue.get("end"), "cue end", 0)
        if start < last - 1e-8 or end <= start or end > duration + 1e-8:
            raise ValueError(
                f"Cue {i + 1} overlaps another cue or extends outside the song"
            )
        last = end
        if not isinstance(cue.get("objects"), list):
            raise TypeError(f"Cue {i + 1} needs an objects array")
        cue.setdefault("name", f"Cue {i + 1}")
        scene.timeline_markers.new(cue["name"], frame=1 + round(start * fps))
        insert(
            bgcolor,
            "default_value",
            rgb(cue.get("background", doc.get("background", "#101820")), palette),
            1 + start * fps,
            "hold",
        )
        insert(bgcolor, "default_value", background, 1 + end * fps, "hold")
        make_cue(cue, palette, fps, materials)
    scene.frame_set(1)
    # Open ready to inspect the composition and its actual material colours.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.shading.color_type = "MATERIAL"
            for space in area.spaces:
                if space.type == "FILE_BROWSER" and space.params is not None:
                    # This RNA field is a fixed-size C buffer. Overwrite the
                    # old bytes before shortening it to the relative path.
                    space.params.directory = b"/" * 768
                    space.params.directory = b"//"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)


if __name__ == "__main__":
    source, output = sys.argv[sys.argv.index("--") + 1 :]
    build(Path(source), Path(output))
