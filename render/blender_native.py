"""Trusted background entry point. Run only through render/blender.mjs."""

import json
import math
from pathlib import Path
import sys

import bpy


def render():
    job_path = Path(sys.argv[sys.argv.index("--") + 1])
    job = json.loads(job_path.read_text(encoding="utf8"))
    directory = job_path.parent
    scene = bpy.context.scene
    if scene.camera is None and not any(
        marker.camera for marker in scene.timeline_markers
    ):
        raise ValueError("The active Blender scene needs a render camera.")
    settings = scene.render
    rate = settings.fps / settings.fps_base
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("The native Blender frame rate must be positive.")
    settings.resolution_x = job["width"]
    settings.resolution_y = job["height"]
    settings.resolution_percentage = 100
    settings.pixel_aspect_x = settings.pixel_aspect_y = 1
    settings.use_border = False
    settings.use_multiview = False
    settings.use_sequencer = False
    settings.use_stamp = False
    for obj in bpy.data.objects:
        if obj.type == "FONT":
            obj.hide_render = True
    settings.image_settings.file_format = "PNG"
    settings.image_settings.color_mode = "RGBA"
    settings.image_settings.color_depth = "8"

    # Preserve the artist's compositing but keep auxiliary File Output nodes
    # from writing to unrelated paths saved in the source file.
    trees = list(bpy.data.node_groups)
    for item in bpy.data.scenes:
        tree = getattr(item, "compositing_node_group", None) or getattr(
            item, "node_tree", None
        )
        if tree:
            trees.append(tree)
    for tree in trees:
        for node in tree.nodes:
            if node.bl_idname == "CompositorNodeOutputFile":
                node.mute = True
                if hasattr(node, "base_path"):
                    node.base_path = str(directory)
    native = None
    for index in range(job["first"], job["stop"]):
        t = job["start"] + index / job["fps"]
        frame = job["firstFrame"] + math.floor(
            max(0, t - job["shotStart"]) * rate + 1e-7
        )
        if frame == native:
            continue
        native = frame
        scene.frame_set(frame)
        settings.filepath = str(directory / f"{frame}.png")
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result or not Path(settings.filepath).is_file():
            raise RuntimeError(f"Blender did not produce native frame {frame}.")
    (directory / "fps.txt").write_text(str(rate), encoding="ascii")


render()
