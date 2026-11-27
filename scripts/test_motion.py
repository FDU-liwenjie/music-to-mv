"""Run with python3 -m unittest discover -s scripts; Blender 4.5 enables native tests."""

import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from build_mg import blender_binary, build
from mg_starter import starter_motion

ROOT = Path(__file__).resolve().parents[1]
try:
    BLENDER = blender_binary()
except ValueError:
    BLENDER = None


class MotionTests(unittest.TestCase):
    def test_phrase_timing(self):
        beats = [round(0.25 + i * 0.51, 3) for i in range(160)]
        for duration in [0.005, 1, 75.3]:
            attacks = [b for b in beats if b < duration]
            for mode in ["narrative", "lyric-visual"]:
                motion = starter_motion(duration, attacks, mode)
                cues = motion["cues"]
                self.assertEqual(cues[0]["start"], 0)
                self.assertEqual(cues[-1]["end"], duration)
                self.assertEqual(
                    [c["end"] for c in cues[:-1]], [c["start"] for c in cues[1:]]
                )
                if duration > 15:
                    self.assertTrue(all(c["start"] in attacks for c in cues[1:]))
                for cue in cues:
                    for obj in cue["objects"]:
                        ts = [k["t"] for k in obj.get("keys", [])]
                        self.assertEqual(ts, sorted(set(ts)))
                        self.assertTrue(
                            all(0 <= t <= cue["end"] - cue["start"] for t in ts)
                        )

    @unittest.skipUnless(BLENDER, "Blender is not installed")
    def test_native_default_rebuild_and_cue_cut(self):
        def run(argv):
            result = subprocess.run(
                list(map(str, argv)), capture_output=True, check=False
            )
            if result.returncode:
                self.fail((result.stdout + result.stderr).decode(errors="replace"))
            return result.stdout

        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            song = root / "song.wav"
            rate = 8000
            pulse = array(
                "h",
                (
                    round(16000 * math.sin(i * math.tau * 65 / rate))
                    if i % 4000 in range(1000, 1600)
                    else 0
                    for i in range(rate * 2)
                ),
            )
            if sys.byteorder != "little":
                pulse.byteswap()
            with wave.open(str(song), "wb") as wav:
                wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                wav.writeframes(pulse.tobytes())
            project = root / "project"
            run(
                [
                    sys.executable,
                    ROOT / "scripts/new_project.py",
                    song,
                    project,
                    "--mode",
                    "narrative",
                ]
            )
            descriptor = project / "project.json"
            motion_file = project / "motion.json"
            manifest = json.loads(descriptor.read_text())
            source = json.loads(motion_file.read_text())
            self.assertEqual(manifest["style"], "blender")
            self.assertGreaterEqual(len(source["beats"]), 3)
            self.assertEqual(source["beats"], manifest["beats"])
            blend = project / manifest["scenes"][0]["blend"]
            self.assertTrue(blend.is_file())
            custom = {
                "version": 1,
                "fps": 10,
                "duration": 2,
                "background": "#000000",
                "camera": {
                    "width": 16,
                    "keys": [
                        {"t": 0, "position": [0, 0], "ease": "linear"},
                        {"t": 1, "position": [2, 0]},
                    ],
                },
                "cues": [
                    {
                        "name": "Travel",
                        "start": 0,
                        "end": 1,
                        "objects": [
                            {"id": "Anchor", "shape": "group", "position": [-1, 0]},
                            {
                                "id": "Body",
                                "parent": "Anchor",
                                "shape": "disk",
                                "radius": 1,
                                "color": "#FF0000",
                                "keys": [
                                    {"t": 0, "position": [0, 0], "ease": "linear"},
                                    {"t": 1, "position": [4, 0]},
                                ],
                            },
                            {
                                "id": "Stroke",
                                "shape": "bezier",
                                "closed": True,
                                "points": [
                                    [-4, -2],
                                    {"co": [0, -2], "left": [-2, 0], "right": [2, 0]},
                                    [4, -2],
                                ],
                                "stroke": 0.1,
                                "keys": [
                                    {"t": 0, "reveal": 0, "ease": "hold"},
                                    {"t": 0.8, "reveal": 1},
                                ],
                            },
                        ],
                    },
                    {
                        "name": "Paper",
                        "start": 1,
                        "end": 2,
                        "background": "#00FF00",
                        "objects": [],
                    },
                ],
            }
            motion_file.write_text(json.dumps(custom))
            run(
                [
                    sys.executable,
                    ROOT / "scripts/build_mg.py",
                    motion_file,
                    "--output",
                    blend,
                ]
            )
            inspect = root / "inspect.py"
            inspect.write_text("""import bpy
s = bpy.context.scene
s.frame_set(6)
body = bpy.data.objects['Body']
stroke = bpy.data.objects['Stroke']
spline = stroke.data.splines[0]
assert not spline.use_cyclic_u and len(spline.bezier_points) == 4
assert (spline.bezier_points[0].co - spline.bezier_points[-1].co).length < .00001
assert body.parent.name == 'Anchor' and abs(body.location.x - 2) < .001
assert abs(s.camera.location.x - 1) < .001
assert not body.hide_render and stroke.data.bevel_factor_end == 0
s.frame_set(9)
assert stroke.data.bevel_factor_end == 1
s.frame_set(11)
assert body.hide_render
""")
            run(
                [
                    BLENDER,
                    "-b",
                    "--factory-startup",
                    "--disable-autoexec",
                    blend,
                    "--python-exit-code",
                    "1",
                    "--python",
                    inspect,
                ]
            )
            # Frame 6 shows the red disc centered at world x=1 with camera x=1.
            for t, expected in [(0.5, (255, 0, 0)), (1, (0, 255, 0))]:
                png = root / "frame.png"
                run(
                    [
                        "node",
                        ROOT / "render/cli.mjs",
                        descriptor,
                        png,
                        "--start",
                        t,
                        "--width",
                        128,
                        "--height",
                        72,
                    ]
                )
                pixels = run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-i",
                        png,
                        "-f",
                        "rawvideo",
                        "-pix_fmt",
                        "rgb24",
                        "-",
                    ]
                )
                center = 3 * (36 * 128 + 64)
                self.assertTrue(
                    all(
                        abs(a - b) < 10
                        for a, b in zip(pixels[center : center + 3], expected)
                    )
                )
            original = blend.read_bytes()
            custom["cues"][1]["start"] = 0.5
            motion_file.write_text(json.dumps(custom))
            with self.assertRaisesRegex(ValueError, "overlap"):
                build(motion_file, blend)
            self.assertEqual(blend.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
