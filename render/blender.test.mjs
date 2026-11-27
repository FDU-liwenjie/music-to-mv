import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  nativeFrameAt,
  findBlender,
  prepareBlenderFrames,
} from "./blender.mjs";

const cli = fileURLToPath(new URL("./cli.mjs", import.meta.url));
const starter = fileURLToPath(
  new URL("../scripts/new_project.py", import.meta.url),
);

test("fractional source fps, shot offsets and half-open source frames", () => {
  const shot = { start: 8.25, firstFrame: 11 };
  const rate = 24000 / 1001;
  assert.equal(nativeFrameAt(8.25, shot, rate), 11);
  assert.equal(nativeFrameAt(8.25 + 1001 / 24000, shot, rate), 12);
  assert.equal(nativeFrameAt(9.25, shot, rate), 34);
  assert.equal(nativeFrameAt(0, { start: 0 }, 24), 1);
});

test("a clip outside the native shot requires no Blender installation or file", async () => {
  const project = {
    style: "blender",
    scenes: [
      { start: 0, end: 0.5, blend: "missing.blend" },
      { start: 0.5, end: 1, style: "pixel" },
    ],
  };
  assert.equal(
    await prepareBlenderFrames(project, ".", {
      start: 0.5,
      fps: 10,
      count: 5,
      width: 64,
      height: 64,
    }),
    null,
  );
});

let binary;
try {
  binary = findBlender();
} catch (error) {
  if (process.env.BLENDER_BIN) throw error;
}

// An empty real scene with an animated world gives each native frame a distinct
// solid colour. It tests retiming, repeated plates, the song offset and lyrics
// without a binary fixture or slow geometry renders.
test(
  "native Blender to PNG and a mixed-style clipped MP4, using the public CLI",
  {
    skip: !binary && "Blender is not installed",
  },
  () => {
    const root = mkdtempSync(join(tmpdir(), "music-to-mv-test-"));
    const call = (name, args, options = {}) =>
      execFileSync(name, args, {
        cwd: root,
        stdio: ["ignore", "pipe", "pipe"],
        timeout: 120000,
        ...options,
      });
    try {
      writeFileSync(
        join(root, "build.py"),
        `import bpy, sys
scene = bpy.context.scene
for obj in list(bpy.data.objects):
    if obj != scene.camera:
        bpy.data.objects.remove(obj, do_unlink=True)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 1
scene.render.fps = 4
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get('Background')
bg.inputs['Strength'].default_value = 1
socket = bg.inputs[0]
for frame, color in [(5, (1,0,0,1)), (6,(0,1,0,1)), (7,(0,0,1,1))]:
    socket.default_value = color
    socket.keyframe_insert(data_path='default_value', frame=frame)
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
`,
      );
      call(binary, [
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python-exit-code",
        "1",
        "--python",
        "build.py",
        "--",
        join(root, "native.blend"),
      ]);
      call("ffmpeg", [
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "input.wav",
      ]);
      call("python3", [
        starter,
        "input.wav",
        "project",
        "--mode",
        "narrative",
        "--style",
        "blender",
        "--blend",
        "native.blend",
        "--first-frame",
        "5",
      ]);
      const json = join(root, "project", "project.json");
      const project = JSON.parse(readFileSync(json, "utf8"));
      assert.equal(project.scenes[0].firstFrame, 5);
      const native = { ...project.scenes[0], start: 0.5, end: 1 };
      project.style = "pixel";
      project.scenes = [
        { start: 0, end: 0.5 },
        { ...native, style: "blender" },
        { start: 1, end: 2 },
      ];
      project.lyrics = [{ start: 0.75, end: 0.875, text: "Sea" }];
      writeFileSync(json, JSON.stringify(project));
      const options = ["--width", "128", "--height", "72", "--fps", "8"];
      call(process.execPath, [
        cli,
        json,
        "still.png",
        "--start",
        "0.625",
        ...options,
      ]);
      const rawArgs = [
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
      ];
      const still = call("ffmpeg", ["-i", "still.png", ...rawArgs]);
      const upper = 3 * (128 * 12 + 60);
      assert.ok(
        still[upper] > 220 && still[upper + 1] < 35 && still[upper + 2] < 35,
        "source frame 5 is red: " + still.subarray(upper, upper + 3).join(","),
      );
      call(process.execPath, [
        cli,
        json,
        "clip.mp4",
        "--start",
        "0.625",
        "--duration",
        "0.5",
        ...options,
      ]);
      const raw = call("ffmpeg", [
        "-i",
        "clip.mp4",
        "-map",
        "0:v:0",
        ...rawArgs,
      ]);
      const frameSize = 128 * 72 * 3;
      assert.equal(raw.length, 4 * frameSize);
      assert.ok(
        raw[upper] > 200 && raw[upper + 1] < 40,
        "trim starts at native frame 5",
      );
      assert.ok(
        raw[frameSize + upper + 1] > 200 &&
          raw[2 * frameSize + upper + 1] > 200,
        "source frame 6 spans two output frames",
      );
      // Lower thirds differ on the same green native frame only while the lyric is active.
      const lowerGreen = (index) => {
        let sum = 0;
        for (
          let i = index * frameSize + 48 * 128 * 3 + 1;
          i < (index + 1) * frameSize;
          i += 3
        )
          sum += raw[i];
        return sum / (24 * 128);
      };
      assert.ok(
        lowerGreen(2) - lowerGreen(1) > 20,
        "the timed lyric and backing disappear at its exact end",
      );
      assert.ok(
        raw[3 * frameSize + upper + 1] < 200,
        "the final output frame belongs to the pixel shot",
      );
      const streams = JSON.parse(
        call("ffprobe", [
          "-v",
          "error",
          "-show_entries",
          "stream=codec_type,duration",
          "-of",
          "json",
          "clip.mp4",
        ]),
      ).streams;
      assert.ok(
        streams.some(
          (s) =>
            s.codec_type === "audio" &&
            Math.abs(Number(s.duration) - 0.5) < 0.002,
        ),
      );
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  },
);
