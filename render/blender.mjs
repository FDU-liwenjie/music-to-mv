// Blender supplies one native plate at a time to the same compositor as 2D shots.
import { spawn } from "node:child_process";
import { once } from "node:events";
import {
  accessSync,
  constants,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { homedir, tmpdir } from "node:os";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadImage } from "@napi-rs/canvas";

const adapter = fileURLToPath(new URL("./blender_native.py", import.meta.url));
const frameTolerance = 1e-8;

export function findBlender() {
  const program = process.platform === "win32" ? "blender.exe" : "blender";
  const app = "Applications/Blender.app/Contents/MacOS/Blender";
  const candidates = process.env.BLENDER_BIN
    ? [resolve(process.env.BLENDER_BIN)]
    : [
        ...(process.env.PATH || "")
          .split(delimiter)
          .filter(Boolean)
          .map((dir) => join(dir, program)),
        ...(process.platform === "darwin"
          ? [join(homedir(), app), "/" + app]
          : []),
      ];
  for (const path of candidates) {
    try {
      accessSync(path, constants.X_OK);
      if (statSync(path).isFile()) return path;
    } catch (error) {
      if (!["ENOENT", "ENOTDIR", "EACCES"].includes(error.code)) throw error;
    }
  }
  throw Error(
    "Install Blender or set BLENDER_BIN to its executable" +
      (process.env.BLENDER_BIN ? ": " + process.env.BLENDER_BIN : ""),
  );
}

export function nativeFrameAt(time, shot, rate) {
  return (
    (shot.firstFrame ?? 1) +
    Math.floor(Math.max(0, time - shot.start) * rate + 1e-7)
  );
}

function selectShots(project, start, fps, count) {
  const shots = [];
  for (const [index, shot] of project.scenes.entries()) {
    if ((shot.style || project.style) !== "blender") continue;
    // Match half-open scene lookup in composition.mjs, including fractional cuts.
    const first = Math.max(
      0,
      Math.ceil((shot.start - start - frameTolerance) * fps),
    );
    const stop = Math.min(
      count,
      Math.ceil((shot.end - start - frameTolerance) * fps),
    );
    if (first < stop) shots.push({ index, shot, first, stop });
  }
  return shots;
}

export async function prepareBlenderFrames(
  project,
  base,
  { start, fps, count, width, height },
) {
  const shots = selectShots(project, start, fps, count);
  if (!shots.length) return null;

  const binary = findBlender();
  const temp = mkdtempSync(join(tmpdir(), "music-to-mv-blender-"));
  let child;
  function close() {
    child?.kill();
    rmSync(temp, { recursive: true, force: true });
    process.off("exit", close);
    process.off("SIGINT", interrupt);
    process.off("SIGTERM", terminate);
  }
  const interrupt = () => process.exit(130);
  const terminate = () => process.exit(143);
  process.once("exit", close);
  process.once("SIGINT", interrupt);
  process.once("SIGTERM", terminate);

  try {
    for (const record of shots) {
      const { shot, first, stop, index } = record;
      const blend = resolve(base, shot.blend);
      if (!existsSync(blend) || !statSync(blend).isFile())
        throw Error("Blender scene not found: " + blend);
      const directory = join(temp, String(index));
      mkdirSync(directory);
      const job = join(directory, "job.json");
      writeFileSync(
        job,
        JSON.stringify({
          start,
          fps,
          width,
          height,
          first,
          stop,
          shotStart: shot.start,
          firstFrame: shot.firstFrame ?? 1,
        }),
      );
      child = spawn(
        binary,
        [
          "--background",
          "--factory-startup",
          "--disable-autoexec",
          blend,
          "--python-exit-code",
          "1",
          "--python",
          adapter,
          "--",
          job,
        ],
        {
          stdio: ["ignore", "pipe", "pipe"],
          cwd: directory,
          windowsHide: true,
        },
      );
      let log = "";
      function keepTail(chunk) {
        log = (log + chunk.toString()).slice(-5000);
      }
      child.stdout.on("data", keepTail);
      child.stderr.on("data", keepTail);
      console.error(
        "Blender · " + shot.blend + " (" + (stop - first) + " output frames)",
      );
      const [code, signal] = await once(child, "close");
      child = null;
      if (code !== 0)
        throw Error("Blender failed: " + (log.trim() || signal || code));
      const rate = Number(readFileSync(join(directory, "fps.txt"), "utf8"));
      if (!Number.isFinite(rate) || rate <= 0)
        throw Error("Invalid frame rate in " + blend);
      Object.assign(record, { directory, rate });
    }

    let path,
      plate,
      cursor = 0;
    return {
      async frame(i) {
        // The CLI consumes frames in song order. Hold only the current plate.
        while (cursor < shots.length && shots[cursor].stop <= i) cursor++;
        const record = shots[cursor];
        if (!record || i < record.first) {
          path = null;
          plate = null;
          return null;
        }
        const n = nativeFrameAt(start + i / fps, record.shot, record.rate);
        const next = join(record.directory, String(n) + ".png");
        if (path !== next) {
          plate = await loadImage(readFileSync(next));
          path = next;
        }
        return plate;
      },
      close,
    };
  } catch (error) {
    close();
    throw error;
  }
}
