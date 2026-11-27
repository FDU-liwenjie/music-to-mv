# Authoring motion graphics in Blender

From the repository root, start a project with a local recording. The default uses Blender 4.5 LTS, Python 3, FFmpeg and ffprobe. Set `BLENDER_BIN` if Blender is outside your PATH or the usual macOS Applications folders.

```sh
python3 scripts/new_project.py song.wav my-mv --mode lyric-visual
node render/cli.mjs my-mv/project.json my-mv/preview.png --start 1
```

The new folder contains a copy of the recording, `project.json`, `motion.json` and `scene.blend`. The motion file starts with an editable geometric study sized to the recording. Its phrase cuts and gesture turns use measured low-frequency attacks where available. Replace those gestures with the subjects, actions and timing chosen for your song. The two available modes are `narrative` and `lyric-visual`. Existing explicit styles, including `--style blender --blend packed.blend`, still work.

Edit `motion.json` and rebuild the Blender file the renderer reads. Each successful build replaces the named output. To keep changes made by hand in Blender, save that version under another name and point the shot's `blend` field to it.

```sh
python3 scripts/build_mg.py my-mv/motion.json --output my-mv/scene.blend
node render/cli.mjs my-mv/project.json my-mv/preview.mp4 --start 1 --duration 3
```

## Minimal motion file

This four-second cue traces an orbit while a disc moves to its rim. It can also be used as the beginning of a longer motion project.

```json
{
  "version": 1,
  "fps": 24,
  "duration": 4,
  "palette": { "paper": "#102A38", "chalk": "#F4E5C7", "signal": "#FC704F" },
  "background": "paper",
  "camera": { "position": [0, 0], "width": 16 },
  "cues": [
    {
      "name": "Orbit",
      "start": 0,
      "end": 4,
      "objects": [
        {
          "id": "Route",
          "shape": "arc",
          "radius": 2,
          "stroke": 0.08,
          "startAngle": -90,
          "endAngle": 180,
          "color": "chalk",
          "keys": [
            { "t": 0, "reveal": 0, "ease": "linear" },
            { "t": 3, "reveal": 1 }
          ]
        },
        {
          "id": "Signal",
          "shape": "disk",
          "radius": 0.35,
          "color": "signal",
          "keys": [
            { "t": 0, "position": [-5, 0], "ease": "smooth" },
            { "t": 3, "position": [-2, 0] }
          ]
        }
      ]
    }
  ]
}
```

## Coordinates and timing

| Field | Meaning |
| --- | --- |
| `version`, `fps`, `duration` | Use format version 1, a native integer frame rate of 1–120 (default 24), and a positive duration in seconds. Native frame 1 is time zero. |
| `palette`, `background` | Palette names map to sRGB `#RRGGBB` values. All colors accept either a name or a hex value. The world provides the background and a cue can override it for its interval. |
| `camera` | An orthographic camera. `position:[x,y]` is its center, `width` is its horizontal span and `rotation` is rotation in degrees. At width 16 and 16:9, the default bounds are x = −8…8, y = −4.5…4.5. Positive x points right, positive y up. |
| `cues` | Chronological, non-overlapping intervals. Objects appear at the first sampled native frame at or after `start` and disappear at `end`. Name each cue to make it a collection and a timeline marker in Blender. Gaps show the project background. |
| `beats` | Optional reference array of attack times in song seconds. The starter also writes these to `project.json`. Position a key at `beat - cue.start` to align it to that attack. Changing the beat list alone does not move authored keys. |
| Object `keys` | `t` is elapsed seconds from **cue start**. Keys must have increasing times within the cue. A key can specify any combination of `position`, `scale`, `rotation`, `color` and stroke `reveal`. Channels animate independently. |
| Camera `keys` | `t` is elapsed seconds from **song start**. Animate `position`, `width` or `rotation`. |
| `ease` | Applies from that key to the next key on each channel it sets. `smooth` uses native Bézier interpolation, `linear` moves at constant rate and `hold` steps at the next key. A channel keeps its final keyed value. |

## Native geometry

Each cue object needs a unique `id` and a `shape`. The shape's local origin is its pivot. Transform it with `position:[x,y]`, `scale:[sx,sy]`, and counterclockwise `rotation` in degrees. A larger `z` is closer to the camera. The default depth increases by 0.003 units per object within each cue. A `parent` uses another object's id in the same cue. Parent transforms apply to the child's local coordinates and depth. Place shared pivots in a `group`.

| Shape | Geometry |
| --- | --- |
| `disk` | Filled circle, `radius` in scene units (default 1). |
| `rect` | Centered rectangle, `size:[width,height]` in positive scene units (default [1,1]). |
| `polygon` | Filled boundary with three or more ordered `points:[[x,y],…]`. Use a simple, non-self-intersecting perimeter. |
| `ring` | Circular stroke with `radius` and optional `startAngle` in degrees. |
| `arc` | Circular stroke from `startAngle` to `endAngle` in degrees. Angle zero points along positive x. Angles can decrease for clockwise motion. |
| `polyline` | Straight segments through two or more ordered `points`. Set `closed:true` to return to the first point. |
| `bezier` | Smooth native curve through `points`. A point can be an auto-handled `[x,y]` or `{"co":[x,y],"left":[x,y],"right":[x,y]}` with absolute handles in object-local units. Use `closed:true` for a loop or `filled:true` for a solid silhouette. |
| `group` | Native Empty for parenting and animating a group of objects around a common origin. |

Strokes take `stroke` as their **full width** in scene units (default 0.08). Set or animate `reveal` from 0 to 1 to draw along a stroke in point order. Use a second object for a separate fill and outline. Colors and geometry compile to native mesh, curve and material data. The camera, object transforms, colors and reveals use editable Blender keyframes. Add timed lyrics in `project.json` after the wording and timing have been reviewed. Song lyrics are composited at render time.
