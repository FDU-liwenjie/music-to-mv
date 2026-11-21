import assert from "node:assert/strict";
import test from "node:test";
import { createCanvas } from "@napi-rs/canvas";
import {
  cropForFrame,
  drawPhotograph,
  prepareMaskedLayers,
} from "./photography.mjs";

test("normalized crop respects zoom, source bounds and vertical output", () => {
  assert.deepEqual(
    cropForFrame(200, 100, 100, 100, { from: [1, 0.5, 1] }, 0),
    [100, 0, 100, 100],
  );
  assert.deepEqual(
    cropForFrame(200, 100, 50, 100, { from: [0, 1, 2] }, 0),
    [0, 50, 25, 50],
  );
  const move = { from: [0.25, 0.5, 1], to: [0.75, 0.5, 1], ease: "linear" };
  assert.deepEqual(
    cropForFrame(200, 100, 100, 100, move, 0.25),
    [25, 0, 100, 100],
  );
  assert.deepEqual(
    cropForFrame(200, 100, 100, 100, { ...move, ease: "hold" }, 1),
    [0, 0, 100, 100],
  );
});

test("camera plates remain static unless framing, a layer, or weather varies", () => {
  const plate = createCanvas(160, 80),
    p = plate.getContext("2d");
  p.fillStyle = "#2456b0";
  p.fillRect(0, 0, 80, 80);
  p.fillStyle = "#a53119";
  p.fillRect(80, 0, 80, 80);
  const overlay = createCanvas(160, 80),
    layer = overlay.getContext("2d");
  layer.fillStyle = "white";
  layer.fillRect(70, 30, 20, 20);
  const assets = new Map([
    ["plate", plate],
    ["layer", overlay],
  ]);
  const canvas = createCanvas(320, 320),
    c = canvas.getContext("2d");
  function frame(fields, u) {
    drawPhotograph(
      c,
      assets,
      { art: "plate", ...fields },
      u,
      u * 2,
      1,
      320,
      320,
    );
    return Buffer.from(canvas.data());
  }
  assert.ok(frame({}, 0).equals(frame({}, 1)));
  const move = {
    framing: { from: [0.25, 0.5, 1], to: [0.75, 0.5, 1], ease: "linear" },
  };
  assert.notDeepEqual(
    frame(move, 0).subarray(0, 4),
    frame(move, 1).subarray(0, 4),
  );
  const animated = {
    layers: [{ src: "layer", from: [0, 0, 1], to: [210, 0, 1] }],
  };
  assert.ok(!frame(animated, 0).equals(frame(animated, 1)));
  assert.ok(frame({ rain: 1 }, 0.32).equals(frame({ rain: 1 }, 0.32)));
  assert.ok(!frame({ rain: 1 }, 0.32).equals(frame({ rain: 1 }, 0.77)));
});

test("an alpha masked layer follows the plate's crop and can move independently", () => {
  const plate = createCanvas(200, 100),
    pc = plate.getContext("2d");
  pc.fillStyle = "black";
  pc.fillRect(0, 0, 200, 100);
  const train = createCanvas(200, 100),
    trainCtx = train.getContext("2d");
  trainCtx.fillStyle = "red";
  trainCtx.fillRect(0, 0, 200, 100);
  const mask = createCanvas(200, 100),
    m = mask.getContext("2d");
  m.fillStyle = "white";
  m.fillRect(65, 45, 10, 10);
  const layer = {
    src: "train",
    mask: "mask",
    space: "plate",
    from: [0, 0, 1],
    to: [15, 0, 1],
  };
  const second = { ...layer };
  const assets = new Map([
    ["plate", plate],
    ["train", train],
    ["mask", mask],
  ]);
  prepareMaskedLayers([layer, second], assets, new Map());
  assert.equal(assets.get(layer), assets.get(second));
  const frame = createCanvas(100, 100),
    ctx = frame.getContext("2d");
  const shot = {
    art: "plate",
    layers: [layer],
    framing: { from: [0.4, 0.5, 2] },
  };
  drawPhotograph(ctx, assets, shot, 0, 0, 0, 100, 100);
  const red = (x, y) => ctx.getImageData(x, y, 1, 1).data[0];
  assert.equal(red(30, 50), 255);
  assert.equal(red(60, 50), 0);
  drawPhotograph(ctx, assets, shot, 1, 1, 0, 100, 100);
  assert.equal(red(30, 50), 0);
  assert.equal(red(60, 50), 255);
});
