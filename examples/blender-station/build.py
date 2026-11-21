"""Build the editable rain station using Blender 4.5 LTS or newer.

blender -b -P build.py -- --output rain-station.blend
"""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coat import build_coat
from station import build_station
from train import build_train

FPS = 24
END = 388


def aim(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera_shot(collection, name, lens, poses, f_stop):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    data.lens = lens
    data.clip_end = 250
    data.dof.use_dof = True
    data.dof.aperture_fstop = f_stop
    data.dof.aperture_blades = 8
    for frame, location, look, focus in poses:
        obj.location = location
        aim(obj, look)
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        data.dof.focus_distance = focus
        data.dof.keyframe_insert(data_path="focus_distance", frame=frame)
    marker = bpy.context.scene.timeline_markers.new(name, frame=poses[0][0])
    marker.camera = obj
    return obj


def dusk_lighting(scene, train):
    world = scene.world.node_tree
    coords = world.nodes.new("ShaderNodeTexCoord")
    separate = world.nodes.new("ShaderNodeSeparateXYZ")
    altitude = world.nodes.new("ShaderNodeMath")
    altitude.operation = "ABSOLUTE"
    world.links.new(coords.outputs["Normal"], separate.inputs["Vector"])
    world.links.new(separate.outputs["Z"], altitude.inputs[0])
    sky = world.nodes.new("ShaderNodeValToRGB")
    ramp = sky.color_ramp
    ramp.elements[0].color = (0.32, 0.16, 0.15, 1)
    ramp.elements[1].color = (0.021, 0.035, 0.10, 1)
    for height, color in [
        (0.09, (0.24, 0.15, 0.23, 1)),
        (0.24, (0.055, 0.083, 0.19, 1)),
    ]:
        ramp.elements.new(height).color = color
    world.links.new(altitude.outputs[0], sky.inputs[0])
    output = next(node for node in world.nodes if node.type == "OUTPUT_WORLD")
    background = output.inputs["Surface"].links[0].from_node
    world.links.new(sky.outputs[0], background.inputs["Color"])
    background.inputs["Strength"].default_value = 0.8
    for light in bpy.data.lights:
        if "sky" in light.name or "bounce" in light.name:
            light.energy *= 0.46
        if "tungsten" in light.name:
            light.energy *= 2.45
            light.color = (1.0, 0.46, 0.20)

    for x in (-1.035, 1.035):
        light = bpy.data.lights.new("Headlamp • track spill", "SPOT")
        light.energy = 1450
        light.color = (1.0, 0.66, 0.33)
        light.shadow_soft_size = 0.10
        light.spot_size = math.radians(53)
        light.spot_blend = 0.80
        obj = bpy.data.objects.new("Headlamp • moving pool", light)
        scene.collection.objects.link(obj)
        obj.parent = train
        obj.location = (x, -0.32, 2.02)
        aim(obj, (x, -10.5, 0.10))
    # A tungsten practical just out of frame models the folds against the dark bench.
    light = bpy.data.lights.new("Bench • tungsten edge", "AREA")
    light.energy = 62
    light.color = (1, 0.43, 0.20)
    light.shape = "DISK"
    light.size = 1.8
    obj = bpy.data.objects.new("Bench • tungsten edge", light)
    scene.collection.objects.link(obj)
    obj.location = (4.74, -8.7, 3.28)
    aim(obj, (4.53, -7, 1.83))

    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.inputs["Threshold"].default_value = 1.8
    glare.inputs["Strength"].default_value = 0.21
    scene.node_tree.links.new(
        nodes.get("Render Layers").outputs["Image"], glare.inputs["Image"]
    )
    scene.node_tree.links.new(
        glare.outputs["Image"], nodes.get("Composite").inputs["Image"]
    )


def render_settings(scene):
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 8
        scene.cycles.use_denoising = True
    if scene.render.engine == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = 32
        scene.eevee.use_raytracing = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = END
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.12
    scene.render.film_transparent = False


def build(output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Rain Station"
    render_settings(scene)
    build_station()
    train = build_train()
    # Constant track speed on a horizontal section. The nose passes the lens
    # of the second camera; the remaining cars supply moving window light.
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    for frame, y in [(1, 15.5), (END, -30.5)]:
        train.location.y = y
        train.keyframe_insert(data_path="location", frame=frame)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
    build_coat(4.60, -7.0, 1.596)
    dusk_lighting(scene, train)
    cameras = bpy.data.collections.new("05 • Cameras")
    scene.collection.children.link(cameras)
    first = camera_shot(
        cameras,
        "01 • Across the rails",
        42,
        [
            (1, (-6.0, -10.0, 2.12), (1.2, 9.2, 1.76), 23),
            (112, (-5.55, -10.25, 2.08), (0.73, 5.25, 1.69), 14),
        ],
        6.3,
    )
    camera_shot(
        cameras,
        "02 • Headlight to carriage windows",
        31,
        [
            (113, (-3.85, -9.15, 1.1), (-0.18, 4.55, 1.68), 12),
            (190, (-3.75, -10.2, 1.35), (-0.27, -2.95, 1.82), 7.5),
            (273, (-3.42, -11.45, 1.75), (-0.03, -8.12, 2.17), 4.8),
        ],
        6.3,
    )
    camera_shot(
        cameras,
        "03 • The coat left behind",
        48,
        [
            (274, (4.16, -4.22, 2.67), (4.48, -7.02, 1.88), 6.3),
            (323, (3.92, -4.61, 2.53), (4.52, -7.01, 1.86), 2.59),
            (END, (3.67, -4.91, 2.46), (4.54, -7.03, 1.85), 2.34),
        ],
        2.8,
    )
    scene.camera = first
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
