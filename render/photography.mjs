import { createCanvas } from "@napi-rs/canvas";

// Frame a still in the output aspect ratio. A center point is relative to the full
// source photograph; zoom = 1 is the largest in-bounds crop that fills the frame.
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const mix = (a, b, u) => a + (b - a) * u;
const smooth = (u) => u * u * (3 - 2 * u);
const centered = [0.5, 0.5, 1];

export function cropForFrame(iw, ih, width, height, framing, progress) {
  const a = framing?.from ?? centered;
  const b = framing?.to ?? a;
  const t = clamp(progress, 0, 1);
  const ease = framing?.ease ?? "smooth";
  const u = ease === "hold" ? 0 : ease === "linear" ? t : smooth(t);
  const zoom = a[2] * (b[2] / a[2]) ** u;
  const scale = Math.max(width / iw, height / ih) * zoom;
  const w = Math.min(iw, width / scale);
  const h = Math.min(ih, height / scale);
  const x = clamp(mix(a[0], b[0], u) * iw - w / 2, 0, iw - w);
  const y = clamp(mix(a[1], b[1], u) * ih - h / 2, 0, ih - h);
  return [x, y, w, h];
}

// Composite alpha masks at the source resolution once during preparation.
// Source pixels in transparent SVG/PNG areas are removed, regardless of RGB.
export function prepareMaskedLayers(layers, assets, cache) {
  for (const layer of layers ?? []) {
    if (!layer.mask) continue;
    const key = JSON.stringify([layer.src, layer.mask]);
    if (!cache.has(key)) {
      const image = assets.get(layer.src);
      const mask = assets.get(layer.mask);
      const out = createCanvas(image.width, image.height);
      const ctx = out.getContext("2d");
      ctx.drawImage(image, 0, 0);
      ctx.globalCompositeOperation = "destination-in";
      const scale = Math.max(
        image.width / mask.width,
        image.height / mask.height,
      );
      const mw = mask.width * scale,
        mh = mask.height * scale;
      ctx.drawImage(
        mask,
        (image.width - mw) / 2,
        (image.height - mh) / 2,
        mw,
        mh,
      );
      cache.set(key, out);
    }
    assets.set(layer, cache.get(key));
  }
}

function drawLayer(ctx, layer, image, s, width, height, onPlate) {
  const from = layer.from ?? [0, 0, 1];
  const to = layer.to ?? from;
  const unit = onPlate ? 1 : Math.min(width / 960, height / 540);
  const fit = Math.min(width / image.width, height / image.height);
  const scale = fit * mix(from[2], to[2], s);
  const w = image.width * scale,
    h = image.height * scale;
  if (layer.rotation) {
    let x = width / 2,
      y = height / 2;
    if (layer.pivot) {
      x = onPlate ? layer.pivot[0] : x + (layer.pivot[0] - 480) * unit;
      y = onPlate ? layer.pivot[1] : y + (layer.pivot[1] - 270) * unit;
    }
    ctx.translate(x, y);
    ctx.rotate((mix(layer.rotation[0], layer.rotation[1], s) * Math.PI) / 180);
    ctx.translate(-x, -y);
  }
  ctx.drawImage(
    image,
    (width - w) / 2 + mix(from[0], to[0], s) * unit,
    (height - h) / 2 + mix(from[1], to[1], s) * unit,
    w,
    h,
  );
}

// Default layer positions use 960 × 540 centered screen units. In plate
// space, anchors and offsets are in source pixels and use the camera crop.
export function drawImageLayers(
  ctx,
  layers,
  assets,
  u,
  width = 960,
  height = 540,
  plate = null,
) {
  const fraction = clamp(u, 0, 1);
  for (const layer of layers ?? []) {
    let s = smooth(fraction);
    if (layer.ease === "linear") s = fraction;
    if (layer.ease === "perspective") {
      // Constant world-space speed along the optical axis. The projected
      // scale is inversely proportional to the distance from the camera.
      const near = layer.from?.[2] ?? 1;
      const far = layer.to?.[2] ?? near;
      s = (fraction * near) / mix(far, near, fraction);
    }
    const image = assets.get(layer) ?? assets.get(layer.src);
    const onPlate = layer.space === "plate" && plate;
    ctx.save();
    if (onPlate) {
      const [cx, cy, cw, ch] = plate.crop;
      ctx.scale(width / cw, height / ch);
      ctx.translate(-cx, -cy);
    }
    drawLayer(
      ctx,
      layer,
      image,
      s,
      onPlate ? plate.width : width,
      onPlate ? plate.height : height,
      onPlate,
    );
    ctx.restore();
  }
}

const frac = (n) => n - Math.floor(n);
function noise(seed) {
  const n = Math.imul(seed ^ (seed >>> 16), 0x45d9f3b);
  return ((n ^ (n >>> 16)) >>> 0) / 0x100000000;
}

function drawRain(ctx, width, height, time, strength, shotIndex) {
  const unit = Math.min(width / 960, height / 540);
  const count = Math.ceil(
    (170 * strength * (width * height)) / (960 * 540 * unit * unit),
  );
  const pad = 20 * unit;
  const w = width + 2 * pad;
  const h = height + 2 * pad;
  ctx.save();
  ctx.lineCap = "round";
  for (let i = 0; i < count; i++) {
    const seed = (i + 1) * 7919 + (shotIndex + 1) * 104729;
    const depth = noise(seed + 97);
    const speed = (125 + 235 * depth) * unit;
    const x = frac(noise(seed) - (time * speed * 0.17) / w) * w - pad;
    const y = frac(noise(seed + 337) + (time * speed) / h) * h - pad;
    const len = (3.5 + 10 * depth) * unit;
    ctx.strokeStyle =
      "rgba(218,228,236," +
      (0.07 + depth * 0.14) * (0.5 + strength * 0.5) +
      ")";
    ctx.lineWidth = (0.45 + 0.6 * depth) * unit;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - len * 0.17, y + len);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawPhotograph(
  ctx,
  assets,
  shot,
  u,
  seconds,
  shotIndex,
  width,
  height,
) {
  const img = assets.get(shot.art);
  if (!img)
    throw new Error(
      "A cinematic scene needs its own JPG or PNG photograph in scene.art",
    );
  const crop = cropForFrame(
    img.width,
    img.height,
    width,
    height,
    shot.framing,
    u,
  );
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, ...crop, 0, 0, width, height);
  drawImageLayers(ctx, shot.layers, assets, u, width, height, {
    crop,
    width: img.width,
    height: img.height,
  });
  if (shot.rain) drawRain(ctx, width, height, seconds, shot.rain, shotIndex);
  ctx.restore();
}
