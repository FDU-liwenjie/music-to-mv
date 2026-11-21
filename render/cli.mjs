#!/usr/bin/env node
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import {
  readFileSync,
  existsSync,
  mkdirSync,
  renameSync,
  rmSync,
  statSync,
} from "node:fs";
import { dirname, resolve, basename, extname } from "node:path";
import { randomUUID } from "node:crypto";
import { prepareComposition } from "./composition.mjs";
import { actions, emotions, motifs, settings, styles } from "./art.mjs";

const usage = `Usage: node render/cli.mjs PROJECT.json OUTPUT.mp4 [--start seconds] [--duration seconds] [--width 1280] [--height 720] [--fps 30]
Use OUTPUT.png to inspect the frame at --start. Time is relative to the start of the source recording, including when rendering a clip.`;
function check(ok, message) {
  if (!ok) throw new Error(message);
}
function within(value, lo, hi) {
  return Number.isFinite(value) && value >= lo && value <= hi;
}
function list(value, choices, field) {
  check(
    choices.includes(value),
    `${field} must be one of ${choices.join(", ")}`,
  );
}
function checkPalette(p) {
  if (p !== undefined)
    check(
      Array.isArray(p) &&
        p.length >= 3 &&
        p.length <= 5 &&
        p.every((s) => /^#[\da-f]{6}$/i.test(s)),
      "palette requires 3–5 hex colors, e.g. #badcaf",
    );
}
function validateProject(p) {
  check(p && typeof p === "object", "Expected a project object");
  check(
    typeof p.audio === "string" && p.audio.length,
    "Provide audio as a path relative to PROJECT.json",
  );
  list(p.mode, ["narrative", "lyric-visual"], "mode");
  list(p.style, styles, "style");
  checkPalette(p.palette);
  check(Array.isArray(p.scenes) && p.scenes.length, "Add at least one scene");
  for (const [i, s] of p.scenes.entries()) {
    check(
      s &&
        within(s.start, 0, Infinity) &&
        Number.isFinite(s.end) &&
        s.end > s.start,
      `Invalid start/end in scene ${i + 1}`,
    );
    if (i > 0)
      check(
        s.start >= p.scenes[i - 1].end - 1e-7,
        `Scene ${i + 1} overlaps an earlier scene`,
      );
    if (s.style) list(s.style, styles, "scene.style");
    checkPalette(s.palette);
    for (const [key, choices] of Object.entries({
      setting: settings,
      action: actions,
      motif: motifs,
      emotion: emotions,
      camera: ["still", "push", "pan-left", "pan-right"],
      artMode: ["foreground", "background"],
    }))
      if (s[key] != null) list(s[key], choices, `scene ${i + 1}.${key}`);
    for (const key of ["caption", "meaning", "headline", "art"])
      if (s[key] != null)
        check(typeof s[key] === "string", `scene.${key} must be text`);
    if (s.intensity != null)
      check(
        within(s.intensity, 0, 1),
        "scene.intensity must be between 0 and 1",
      );
    if (s.layers != null) {
      check(Array.isArray(s.layers), "scene.layers must be an array");
      for (const layer of s.layers) {
        check(
          layer && typeof layer.src === "string",
          "Each layer needs an image src",
        );
        for (const key of ["pivot", "rotation"])
          if (layer[key] != null) {
            const pair = layer[key];
            check(
              Array.isArray(pair) &&
                pair.length === 2 &&
                pair.every(Number.isFinite),
              `layer.${key} expects two numbers`,
            );
          }
        for (const key of ["from", "to"])
          if (layer[key] != null) {
            const a = layer[key];
            check(
              Array.isArray(a) &&
                a.length === 3 &&
                a.every(Number.isFinite) &&
                a[2] > 0,
              `layer.${key} expects [x, y, positiveScale]`,
            );
          }
      }
    }
  }
  const lyrics = p.lyrics ?? [];
  check(Array.isArray(lyrics), "lyrics must be a timed array");
  for (const [i, l] of lyrics.entries()) {
    check(
      l &&
        within(l.start, 0, Infinity) &&
        Number.isFinite(l.end) &&
        l.end > l.start &&
        typeof l.text === "string",
      `Invalid timed lyric ${i + 1}`,
    );
  }
  const beats = p.beats ?? [];
  check(
    Array.isArray(beats) &&
      beats.every(
        (b, i) => within(b, 0, Infinity) && (!i || b >= beats[i - 1]),
      ),
    "beats must contain chronological seconds",
  );
}
function toolResult(name, args) {
  const out = spawnSync(name, args, { encoding: "utf8" });
  if (out.error)
    throw Error(`Install ${name} and add it to PATH (${out.error.message})`);
  check(out.status === 0, out.stderr?.trim() || `${name} failed`);
  return out.stdout;
}
async function run(argv) {
  if (argv.includes("--help") || argv.includes("-h")) {
    console.log(usage);
    return;
  }
  check(argv.length >= 2, usage);
  const [src, dest, ...args] = argv;
  const flags = {};
  for (let i = 0; i < args.length; i += 2) {
    let k = args[i];
    check(
      ["--start", "--duration", "--fps", "--width", "--height"].includes(k) &&
        i + 1 < args.length &&
        !Object.hasOwn(flags, k),
      "Invalid or duplicate option: " + k,
    );
    flags[k] = Number(args[i + 1]);
    check(Number.isFinite(flags[k]), `Invalid number after ${k}`);
  }
  const input = resolve(src),
    output = resolve(dest),
    type = extname(output).toLowerCase(),
    p = JSON.parse(readFileSync(input, "utf8"));
  validateProject(p);
  check([".png", ".mp4"].includes(type), "Use an .mp4 or .png output filename");
  const audio = resolve(dirname(input), p.audio);
  check(audio !== output && input !== output, "Use a separate output file");
  check(
    existsSync(audio) && statSync(audio).isFile(),
    `Audio not found: ${audio}`,
  );
  const media = JSON.parse(
    toolResult("ffprobe", [
      "-v",
      "error",
      "-show_entries",
      "stream=codec_type,duration:format=duration",
      "-of",
      "json",
      audio,
    ]),
  );
  const stream = media.streams?.find((s) => s.codec_type === "audio");
  check(stream, "Input has no audio stream");
  const audioEnd = Number(stream.duration) || Number(media.format?.duration);
  check(within(audioEnd, Number.EPSILON, Infinity), "Audio length unavailable");
  const start = flags["--start"] ?? p.scenes[0].start,
    duration =
      flags["--duration"] ?? Math.min(audioEnd, p.scenes.at(-1).end) - start;
  check(
    start >= 0 && start < audioEnd,
    `--start must be inside ${audioEnd.toFixed(3)}s of audio`,
  );
  check(
    duration > 0 && start + duration <= audioEnd + 0.000001,
    "Requested duration exceeds audio",
  );
  const end = type === ".png" ? start + 0.0000001 : start + duration;
  let covered = start;
  for (const s of p.scenes) {
    if (s.end <= covered) continue;
    if (s.start > covered + 0.000001) break;
    covered = s.end;
    if (covered >= end - 0.000001) break;
  }
  check(
    covered >= end - 0.000001,
    "Scenes do not cover the requested interval",
  );
  const fps = flags["--fps"] ?? 30,
    width = flags["--width"] ?? 1280,
    height = flags["--height"] ?? 720;
  check(
    Number.isInteger(fps) && within(fps, 1, 120),
    "fps must be an integer from 1 to 120",
  );
  for (const dim of [width, height])
    check(
      Number.isInteger(dim) && within(dim, 16, 4096) && dim % 2 === 0,
      "Dimensions must be even integers from 16 to 4096",
    );
  const draw = await prepareComposition(p, dirname(input), width, height);
  mkdirSync(dirname(output), { recursive: true });
  const temp = resolve(
    dirname(output),
    `.${basename(output)}.${randomUUID()}${type}`,
  );
  try {
    if (type === ".png") {
      draw(start).savePng(temp);
      renameSync(temp, output);
      console.log(output);
      return;
    }
    toolResult("ffmpeg", ["-version"]);
    const frames = Math.max(1, Math.ceil(duration * fps - 1e-7));
    const enc = spawn(
      "ffmpeg",
      [
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgba",
        "-video_size",
        `${width}x${height}`,
        "-framerate",
        String(fps),
        "-i",
        "pipe:0",
        "-ss",
        String(start),
        "-t",
        String(duration),
        "-i",
        audio,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-map_metadata",
        "-1",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        temp,
      ],
      { stdio: ["pipe", "ignore", "pipe"] },
    );
    let diagnostic = "",
      pipeError = null;
    enc.stderr.on("data", (d) => {
      diagnostic = (diagnostic + d.toString()).slice(-1600);
    });
    enc.stdin.on("error", (e) => {
      pipeError = e;
    });
    const closed = once(enc, "close");
    try {
      for (let i = 0; i < frames; i++) {
        if (pipeError) throw pipeError;
        const pixels = draw(start + i / fps).data();
        if (!enc.stdin.write(pixels)) await once(enc.stdin, "drain");
        if (i > 0 && i % (fps * 15) === 0)
          console.error(`${Math.round((i / frames) * 100)}%`);
      }
      enc.stdin.end();
      const [code] = await closed;
      check(code === 0, `FFmpeg: ${diagnostic || `exit ${code}`}`);
    } catch (error) {
      enc.stdin.destroy();
      enc.kill();
      await closed.catch(() => {});
      throw new Error(diagnostic.trim() || error.message);
    }
    renameSync(temp, output);
    console.log(`${output} (${frames} frames)`);
  } finally {
    rmSync(temp, { force: true });
  }
}
run(process.argv.slice(2)).catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
