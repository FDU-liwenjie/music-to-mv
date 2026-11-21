import { createCanvas, GlobalFonts, loadImage } from "@napi-rs/canvas";
import { resolve, extname } from "node:path";
import { readFileSync } from "node:fs";
import {
  actor,
  makeBackdrop,
  motif,
  palette,
  mix,
  oval,
  poly,
  styles,
  emotions,
} from "./art.mjs";
import { diorama } from "./diorama.mjs";

const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(v, hi));
const ease = (u) => u * u * (3 - 2 * u);
const fontNames = [
  "Noto Sans CJK SC",
  "PingFang SC",
  "Hiragino Sans GB",
  "Microsoft YaHei",
  "Source Han Sans CN",
  "Noto Sans SC",
  "Arial Unicode MS",
  "DejaVu Sans",
  "sans-serif",
];
function fontFamily() {
  const installed = JSON.parse(GlobalFonts.getFamilies().toString()).map(
    (f) => f.family,
  );
  return [
    ...(process.env.MV_FONT ? ["MV Custom"] : []),
    ...fontNames.filter((f) => installed.includes(f) || f === "sans-serif"),
  ]
    .map((n) => `"${n}"`)
    .join(",");
}
function arrangedLines(ctx, text, maxWidth) {
  const lines = [];
  let chunk = "";
  for (const letter of [...text]) {
    if (
      letter === "\n" ||
      (chunk && ctx.measureText(chunk + letter).width > maxWidth)
    ) {
      lines.push(chunk.trim());
      chunk = "";
    }
    if (letter !== "\n") chunk += letter;
  }
  if (chunk.trim()) lines.push(chunk.trim());
  return lines;
}
function label(
  ctx,
  text,
  x,
  y,
  maxWidth,
  size,
  font,
  color,
  align = "center",
  outline = false,
) {
  if (!text) return;
  ctx.save();
  ctx.textAlign = align;
  ctx.textBaseline = "middle";
  let lines = [];
  while (size >= 11) {
    ctx.font = `600 ${size}px ${font}`;
    lines = arrangedLines(ctx, text, maxWidth);
    if (lines.length <= 3) break;
    size -= 1;
  }
  const lh = size * 1.25;
  for (let i = 0; i < lines.length; i++) {
    const ly = y + (i - (lines.length - 1) / 2) * lh;
    if (outline) {
      ctx.lineJoin = "round";
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#111923c7";
      ctx.strokeText(lines[i], x, ly);
    }
    ctx.fillStyle = color;
    ctx.fillText(lines[i], x, ly);
  }
  ctx.restore();
  return lines.length * lh;
}
// The visual material can stay constant while an individual scene changes mood.
function scenePalette(style, override, emotion) {
  const colors = palette(style, override);
  if (override) return colors;
  const tints = {
    sad: ["#6785a1", 0.22],
    calm: ["#91afaa", 0.1],
    romantic: ["#f19298", 0.18],
    restless: ["#c395bc", 0.14],
    determined: ["#f4aa61", 0.13],
    wild: ["#dd4687", 0.24],
  };
  const tint = tints[emotion];
  if (!tint) return colors;
  return colors.map((color, index) =>
    mix(color, tint[0], tint[1] * (index === 0 ? 0.4 : 1)),
  );
}
function motion(action, u, t, intensity) {
  const s = ease(clamp(u));
  const walk = ["walk", "return", "depart"].includes(action);
  let x = 476;
  if (action === "walk") x = 350 + 184 * s;
  if (action === "return") x = 585 - 154 * s;
  if (action === "depart") x = 455 + 195 * s;
  const gesture =
    action === "offer" || action === "reach"
      ? Math.sin(Math.PI * s)
      : action === "release" || action === "unfold"
        ? Math.min(1, s * 2)
        : 0.1;
  let mx = x + 29,
    my = 293,
    angle = -0.11;
  if (action === "release") {
    mx += s * 207;
    my -= 61 * Math.sin(s * Math.PI) + s * 10;
    angle += s * 0.47;
  }
  if (action === "offer" || action === "reach") {
    mx += gesture * 39;
    my -= gesture * 13;
  }
  if (action === "unfold") {
    my -= s * 23;
    angle += s * 0.24;
  }
  return {
    x,
    walk: walk ? 0.6 + 0.4 * intensity : 0,
    gesture,
    mx,
    my,
    angle,
    phase: t * (3.6 + intensity),
  };
}
function pulseAt(beats, t) {
  let l = 0,
    r = beats.length;
  while (l < r) {
    let m = (l + r) >> 1;
    if (beats[m] <= t) l = m + 1;
    else r = m;
  }
  return l ? Math.exp(-Math.max(0, t - beats[l - 1]) * 9) : 0;
}
function camera(ctx, id, u, intensity) {
  let z = 1,
    dx = 0;
  switch (id) {
    case "still":
      return;
    case "pan-left":
      dx = 20 * (0.5 - u);
      z = 1.055;
      break;
    case "pan-right":
      dx = 20 * (u - 0.5);
      z = 1.055;
      break;
    default:
      z = 1 + (0.025 + 0.04 * intensity) * ease(u);
  }
  ctx.translate(480 + dx, 270);
  ctx.scale(z, z);
  ctx.translate(-480, -270);
}
function plate(c, shot, t, u, p, state, pulse) {
  const [ink, paper, accent, sea] = p;
  const kind = shot.motif || "letter";
  const traveling = shot.action === "release" || shot.action === "depart";
  const x = 454 + (traveling ? u * 111 : 0),
    y = 235 - 12 * Math.sin(u * Math.PI);
  const size = 146 + 9 * pulse;
  c.save();
  c.globalAlpha = 0.88;
  poly(
    c,
    [
      [x - 123, y - 78],
      [x + 95, y - 93],
      [x + 112, y + 64],
      [x - 109, y + 82],
    ],
    ink,
  );
  c.restore();
  for (let j = 0; j < 4; j++) {
    c.save();
    c.globalAlpha = 0.12 + 0.04 * j;
    motif(
      c,
      kind,
      x - 41 + j * 10,
      y + 8 - j * 2,
      size * 0.87,
      state.angle - 0.1,
      p,
    );
    c.restore();
  }
  motif(c, kind, x + 1, y, size, state.angle, p);
  if (shot.action === "unfold")
    motif(c, "leaf", x + 66 * u, y - 48 * u, 52 * u, 0.24 * u, p);
}
function poster(c, shot, t, u, p, state, pulse, font, lyricMode) {
  const [ink, paper, accent, sea] = p;
  c.fillStyle = paper;
  c.fillRect(0, 0, 960, 540);
  poly(
    c,
    [
      [-80, 144],
      [207, -36],
      [421, -36],
      [-43, 330],
    ],
    accent,
  );
  poly(
    c,
    [
      [553, 540],
      [960, 276],
      [960, 540],
    ],
    sea,
  );
  const cx = lyricMode ? 390 : 679,
    cy = 224;
  oval(c, cx, cy, 122 + 4 * pulse, 122 + 4 * pulse, ink);
  for (let j = 0; j < 7; j++) {
    c.strokeStyle = mix(ink, paper, 0.37);
    c.lineWidth = 1.1;
    c.beginPath();
    c.arc(cx, cy, 69 + j * 6, 0.1, Math.PI * 1.94);
    c.stroke();
  }
  motif(c, shot.motif, cx, cy, 136 + 5 * pulse, -0.13 + u * 0.13, p);
  if (!lyricMode)
    actor(
      c,
      state.x - 200,
      363,
      1.9,
      state.walk,
      state.gesture,
      state.phase,
      p,
    );
  const headline = shot.headline || shot.meaning || shot.caption || "";
  if (headline)
    label(
      c,
      headline,
      lyricMode ? 689 : 251,
      lyricMode ? 233 : 130,
      324,
      headline.length > 12 ? 35 : 51,
      font,
      ink,
    );
}
async function loadArt(path) {
  if (
    ![".png", ".svg", ".jpg", ".jpeg", ".webp"].includes(
      extname(path).toLowerCase(),
    )
  )
    throw Error(`Unsupported artwork: ${path}`);
  return loadImage(readFileSync(path));
}
export async function prepareComposition(project, base, width, height) {
  if (
    process.env.MV_FONT &&
    !GlobalFonts.registerFromPath(process.env.MV_FONT, "MV Custom")
  )
    throw Error("MV_FONT could not be loaded");
  const font = fontFamily(),
    target = createCanvas(width, height),
    tc = target.getContext("2d");
  const assets = new Map();
  for (const shot of project.scenes) {
    for (const source of [
      shot.art,
      ...(shot.layers || []).map((l) => l.src),
    ].filter(Boolean)) {
      if (!assets.has(source))
        assets.set(source, await loadArt(resolve(base, source)));
    }
  }
  let lastScene = -1,
    backdrop,
    stageCanvas,
    stage;
  function art(c, source, mode, dx = 0, dy = 0, scale = 1) {
    const img = assets.get(source);
    const factor =
      (mode === "cover" ? Math.max : Math.min)(
        960 / img.width,
        540 / img.height,
      ) * scale;
    const w = img.width * factor,
      h = img.height * factor;
    c.drawImage(img, (960 - w) / 2 + dx, (540 - h) / 2 + dy, w, h);
  }
  function draw(t) {
    const idx = project.scenes.findIndex(
      (s) => t >= s.start - 1e-8 && t < s.end - 1e-8,
    );
    if (idx < 0) throw Error(`No scene covers ${t.toFixed(3)}s`);
    const shot = project.scenes[idx];
    const style = shot.style || project.style;
    const p = scenePalette(
      style,
      shot.palette || project.palette,
      shot.emotion,
    );
    const u = clamp((t - shot.start) / (shot.end - shot.start));
    const intensities = {
      calm: 0.15,
      sad: 0.24,
      romantic: 0.4,
      restless: 0.74,
      determined: 0.64,
      wild: 0.95,
    };
    const intensity = clamp(
      shot.intensity ?? intensities[shot.emotion] ?? 0.45,
    );
    const state = motion(shot.action, u, t, intensity);
    if (lastScene !== idx) {
      lastScene = idx;
      backdrop = makeBackdrop(shot, style, p, 83 + idx * 919);
      const sw =
        style === "pixel" && !shot.art && !shot.layers?.length
          ? 320
          : Math.max(960, Math.min(width, 1920));
      stageCanvas = createCanvas(sw, Math.round((sw * 9) / 16));
      stage = stageCanvas.getContext("2d");
    }
    const c = stage;
    const pulse = pulseAt(project.beats || [], t);
    const lyricMode = project.mode === "lyric-visual";
    c.save();
    c.scale(stageCanvas.width / 960, stageCanvas.height / 540);
    c.fillStyle = p[0];
    c.fillRect(0, 0, 960, 540);
    c.save();
    camera(c, shot.camera || "push", u, intensity);
    const backgroundArt = shot.art && shot.artMode !== "foreground";
    if (backgroundArt) {
      art(c, shot.art, "cover");
    } else if (style === "typography") {
      poster(c, shot, t, u, p, state, pulse, font, lyricMode);
    } else if (style === "lowpoly") {
      const g = c.createLinearGradient(0, 0, 0, 540);
      g.addColorStop(0, mix(p[1], p[4], 0.46));
      g.addColorStop(1, p[1]);
      c.fillStyle = g;
      c.fillRect(0, 0, 960, 540);
      oval(c, 695, 96, 47, 47, p[1]);
      diorama(c, shot, t, u, p, lyricMode);
      if (lyricMode)
        motif(
          c,
          shot.motif,
          515 + 12 * u,
          224,
          108 + 7 * pulse,
          state.angle,
          p,
        );
      else if (!["boat", "light"].includes(shot.motif))
        motif(c, shot.motif, 504, 243, 32, state.angle, p);
    } else {
      c.drawImage(backdrop, 0, 0, 960, 540);
      if (lyricMode) plate(c, shot, t, u, p, state, pulse);
      else {
        if (shot.action === "offer")
          actor(c, 575, 368, 1.05, 0, 0.48, t, p, -1);
        actor(
          c,
          state.x,
          374,
          1.57,
          state.walk,
          state.gesture,
          state.phase,
          p,
          shot.action === "return" ? -1 : 1,
        );
        motif(
          c,
          shot.motif,
          state.mx,
          state.my,
          48 + state.gesture * 8 + pulse * 2,
          state.angle,
          p,
        );
      }
    }
    if (shot.art && shot.artMode === "foreground")
      art(
        c,
        shot.art,
        "contain",
        (state.x - 476) * 0.65,
        -state.gesture * 9,
        1 + 0.04 * ease(u),
      );
    for (const layer of shot.layers || []) {
      const a = layer.from || [0, 0, 1],
        b = layer.to || a,
        s = ease(u);
      c.save();
      if (layer.rotation) {
        const [px, py] = layer.pivot || [480, 270];
        c.translate(px, py);
        c.rotate(
          ((layer.rotation[0] + (layer.rotation[1] - layer.rotation[0]) * s) *
            Math.PI) /
            180,
        );
        c.translate(-px, -py);
      }
      art(
        c,
        layer.src,
        "contain",
        a[0] + s * (b[0] - a[0]),
        a[1] + s * (b[1] - a[1]),
        a[2] + s * (b[2] - a[2]),
      );
      c.restore();
    }
    c.restore();
    c.restore();
    tc.save();
    tc.imageSmoothingEnabled = style !== "pixel";
    tc.fillStyle = p[0];
    tc.fillRect(0, 0, width, height);
    const cover = Math.max(
      width / stageCanvas.width,
      height / stageCanvas.height,
    );
    tc.drawImage(
      stageCanvas,
      (width - stageCanvas.width * cover) / 2,
      (height - stageCanvas.height * cover) / 2,
      stageCanvas.width * cover,
      stageCanvas.height * cover,
    );
    tc.restore();
    // Overlay captions after compositing so the camera never crops them.
    const currentLyric = (project.lyrics || []).find(
      (line) => t >= line.start && t < line.end,
    );
    const meaning = lyricMode ? shot.meaning || "" : "";
    const caption = currentLyric?.text ?? shot.caption ?? "";
    if (meaning || caption) {
      const unit = Math.min(width / 960, height / 540),
        totalHeight = height / unit,
        wide = width / unit;
      tc.save();
      tc.scale(unit, unit);
      const maxWidth = wide * 0.88;
      const lyricSize = 26,
        meaningSize = caption ? 18 : 26;
      const blockHeight = (text, size) => {
        tc.font = `600 ${size}px ${font}`;
        return text
          ? arrangedLines(tc, text, maxWidth).length * size * 1.25
          : 0;
      };
      const lyricH = blockHeight(caption, lyricSize),
        meaningH = blockHeight(meaning, meaningSize);
      const bottom = totalHeight - 30,
        gap = lyricH && meaningH ? 10 : 0;
      const top = Math.max(0, bottom - lyricH - gap - meaningH - 52);
      const grad = tc.createLinearGradient(0, top, 0, totalHeight);
      grad.addColorStop(0, "#14202d00");
      grad.addColorStop(1, "#14202dee");
      tc.fillStyle = grad;
      tc.fillRect(0, top, wide, totalHeight - top);
      if (meaning)
        label(
          tc,
          meaning,
          wide / 2,
          bottom - lyricH - gap - meaningH / 2,
          maxWidth,
          meaningSize,
          font,
          "#ffedca",
          "center",
          true,
        );
      if (caption)
        label(
          tc,
          caption,
          wide / 2,
          bottom - lyricH / 2,
          maxWidth,
          lyricSize,
          font,
          "#fbf8f0",
          "center",
          true,
        );
      tc.restore();
    }
    return target;
  }
  return draw;
}
