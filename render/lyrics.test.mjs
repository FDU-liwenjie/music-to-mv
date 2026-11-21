// Regression: only the active timed lyric may change a rendered frame's text.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createCanvas } from "@napi-rs/canvas";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { prepareComposition } from "./composition.mjs";
import { styles } from "./art.mjs";

const backgrounds = fileURLToPath(
  new URL("../examples/rain-cinema/art/", import.meta.url),
);

function digest(canvas, region = null) {
  const pixels = region
    ? canvas.getContext("2d").getImageData(...region).data
    : canvas.data();
  return createHash("sha256").update(pixels).digest("hex");
}

for (const mode of ["narrative", "lyric-visual"]) {
  for (const style of styles) {
    test(`${mode} / ${style}: show only the active original line`, async () => {
      const shot = {
        start: 0,
        end: 4,
        setting: "room",
        motif: "letter",
        emotion: "calm",
        action: "wait",
      };
      if (style === "cinematic") shot.art = "track.jpg";
      const project = { mode, style, scenes: [shot], lyrics: [] };
      const withNotes = {
        ...project,
        title: "Private title",
        scenes: [
          {
            ...shot,
            meaning: "A private interpretation",
            caption: "A legacy caption",
            headline: "A legacy headline",
          },
        ],
      };
      const withLyrics = {
        ...withNotes,
        lyrics: [{ start: 1, end: 2, text: "月色入窗" }],
      };
      const [bare, notes, sung] = await Promise.all(
        [project, withNotes, withLyrics].map((p) =>
          prepareComposition(p, backgrounds, 320, 180),
        ),
      );
      const plate = style === "blender" ? createCanvas(320, 180) : undefined;
      for (const t of [0.75, 1.0, 1.75, 2.0, 2.5]) {
        const expected = digest(bare(t, plate)),
          annotated = digest(notes(t, plate)),
          current = digest(sung(t, plate));
        assert.equal(
          annotated,
          expected,
          "private notes must not affect pixels",
        );
        if (t >= 1 && t < 2) {
          assert.notEqual(current, expected, "the original line must appear");
          if (style === "typography") {
            assert.equal(
              digest(sung(t), [0, 150, 320, 30]),
              digest(bare(t), [0, 150, 320, 30]),
              "the typographic foreground must not get a duplicate bottom subtitle",
            );
          }
        } else {
          assert.equal(
            current,
            expected,
            "the lyric must disappear at its exact end",
          );
        }
      }
    });
  }
}
