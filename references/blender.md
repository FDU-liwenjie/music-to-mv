# Making motion graphics in Blender

The music project has two timelines. `motion.json` describes what moves, when it moves and how it looks. Building the score creates editable geometry and keyframes in Blender. `project.json` places the rendered picture, the original audio and the reviewed lyric cues on the song timeline.

## Work on one phrase

1. Listen to a short section and mark the start of the vocal, the strongest musical accent and the following rest. Give each a time in seconds from the start of the recording.
2. Pick a gesture the viewer can follow. To show two rhythms slipping apart, draw two hands on one dial. Start them at the same angle, hold through the pickup, then move one hand ahead. A stationary outer ring gives the viewer a reference for the separation.
3. In the motion score, set the cue boundaries on the song timeline. Give each shape a readable object ID. Put the moving hand and its details under a shared pivot. Set animation keys in seconds from the beginning of the cue. A straight angular sweep reads as steady time. A held pose followed by a jump reads as a missed beat.
4. Build the scene, open it in Blender and scrub across the change. The Outliner exposes the shapes and groups. Use the Graph Editor to inspect the motion. Save any hand-edited version under a separate filename before rebuilding from the score.

From the repository root, these commands rebuild an example into a separate Blender file and render a frame from the example project. The audio generator creates the original practice recording used by the published projects.

```sh
python3 examples/night-train/make_audio.py
python3 scripts/build_mg.py examples/mg-out-of-time/motion.json --output outputs/out-of-time-study.blend
node render/cli.mjs examples/mg-out-of-time/project.json outputs/out-of-time.png --start 3 --width 960 --height 540
```

The still command uses the `blend` path recorded in the example's `project.json`. To preview an edit to the separate study file, use Blender's camera view or point a copy of the project at the edited file. The score reference lists the supported primitives, animation channels and coordinate system. [Motion score reference](../scripts/MOTION.md)

## Check the motion against the recording

Inspect the frame before the action, the strongest pose and the first frame of the next cue. Make sure the shape reads at the intended display size. Check which silhouette is visible when objects overlap, and whether a foreground object completely hides the action. Play the same range with the recording to judge the cut. A held shot can give a vocal entrance room even when the beat detector finds several accents.

The same CLI renders a PNG at a song time or an MP4 over an interval. For example, this exports four seconds with the recording from the lyric-visual project.

```sh
node render/cli.mjs examples/mg-out-of-time/project.json outputs/out-of-time-detail.mp4 --start 1 --duration 4 --width 960 --height 540 --fps 24
```

## Bring an existing Blender scene

A project can also use a hand-built Blender file with modeled sets, lighting and camera animation. Place a render camera, set the native frame rate, and bind cameras to timeline markers for cuts. Pack external textures where possible, and keep remaining linked assets at portable relative paths. Install Blender 4.5 LTS on your PATH or set `BLENDER_BIN` to the executable. On macOS the tools also look in the system and user Applications folders.

```sh
python3 scripts/new_project.py "/path/to/song.wav" "/path/to/my-mv" --mode narrative --style blender --blend "/path/to/shot.blend"
```

The project can set `style` to `blender` for the whole song or for an individual shot. Each such shot has a `blend` path relative to the project. `firstFrame` defaults to 1. For example, these four seconds of song begin on frame 97 of the Blender file.

```json
{"start": 8, "end": 12, "style": "blender", "blend": "assets/shot-01.blend", "firstFrame": 97}
```

Playback follows the native scene frame rate. Changing the export frame rate preserves the speed of its animation. The initial shot covers the recording. If the modeled action is shorter, cut to another shot when that action ends. Surface lettering is part of the model, so review sign textures and geometry before rendering a wordless sequence.

## Revisit the modeled studies

*Last Train After the Rain* follows a train across a wet platform and ends on a red coat left on a bench. Open its camera view to inspect how the track-level camera, moving train, reflected lamps and final close-up share the same three-dimensional set. *Out of Time* uses two pocket watches with different hand speeds. These projects include the native Blender files and their Python modeling sources. [Station study](../examples/blender-station/) · [Watch study](../examples/blender-clocks/)

To regenerate the first study from its Python models, run the following from the repository root.

```sh
blender --background --factory-startup --python-exit-code 1 --python examples/blender-station/build.py -- --output outputs/custom-station.blend
```

For installation and command-line options, see the Blender documentation. [Download Blender](https://www.blender.org/download/) · [Background rendering](https://docs.blender.org/manual/en/4.5/advanced/command_line/render.html)
