// All coordinates are authored on a 960 × 540 stage. No network assets are loaded.
import { createCanvas, Path2D } from "@napi-rs/canvas";

export const WIDTH = 960,
  HEIGHT = 540;
export const styles = [
  "pixel",
  "riso",
  "watercolor",
  "papercut",
  "lowpoly",
  "typography",
  "cinematic",
  "blender",
];
export const settings = [
  "station",
  "street",
  "coast",
  "room",
  "bridge",
  "mountain",
  "stage",
];
export const actions = [
  "wait",
  "walk",
  "offer",
  "release",
  "return",
  "reach",
  "depart",
  "unfold",
];
export const motifs = [
  "letter",
  "boat",
  "flower",
  "train",
  "umbrella",
  "light",
  "clock",
  "leaf",
  "mountain",
];
export const emotions = [
  "calm",
  "romantic",
  "sad",
  "restless",
  "determined",
  "wild",
];
const inks = {
  blender: ["#172029", "#ede5d9", "#b98b70", "#718588", "#b8bac0"],
  cinematic: ["#172029", "#ede5d9", "#b98b70", "#718588", "#b8bac0"],
  pixel: ["#202c49", "#e8c38c", "#e07f61", "#819bb0", "#354861"],
  riso: ["#193f55", "#ffdfab", "#ef5642", "#55a7a0", "#d19874"],
  watercolor: ["#345467", "#f9eacb", "#cb735d", "#79aaa6", "#adacc3"],
  papercut: ["#233b49", "#f6dbad", "#e18362", "#71a79c", "#426b73"],
  lowpoly: ["#26364c", "#f6ddab", "#ef9869", "#89b4ad", "#757c99"],
  typography: ["#132c37", "#f7e7ba", "#eb553c", "#519d98", "#cfa56f"],
};
export function palette(style, override) {
  return inks[style].map((c, i) => override?.[i] ?? c);
}
export function generator(seed = 1) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
const alpha = (c, a) =>
  c +
  Math.round(a * 255)
    .toString(16)
    .padStart(2, "0");
const rgb = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
export function mix(a, b, t) {
  const A = rgb(a),
    B = rgb(b);
  return (
    "#" +
    A.map((v, i) =>
      Math.round(v + (B[i] - v) * t)
        .toString(16)
        .padStart(2, "0"),
    ).join("")
  );
}
export function poly(c, points, color) {
  c.fillStyle = color;
  c.beginPath();
  for (let i = 0; i < points.length; i++) {
    const [x, y] = points[i];
    if (i) c.lineTo(x, y);
    else c.moveTo(x, y);
  }
  c.closePath();
  c.fill();
}
function rect(c, x, y, w, h, color) {
  c.fillStyle = color;
  c.fillRect(x, y, w, h);
}
export function oval(c, x, y, rx, ry, color) {
  c.fillStyle = color;
  c.beginPath();
  c.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  c.fill();
}
function stroke(c, points, color, width = 2) {
  c.strokeStyle = color;
  c.lineWidth = width;
  c.lineJoin = "round";
  c.lineCap = "round";
  c.beginPath();
  points.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
  c.stroke();
}
function svg(c, d, fill) {
  c.fillStyle = fill;
  c.fill(new Path2D(d));
}
function wash(c, x, y, rx, ry, col, rng) {
  for (let j = 0; j < 7; j++) {
    const points = [];
    for (let i = 0; i < 40; i++) {
      const a = (i * Math.PI) / 20;
      const jitter = 0.87 + 0.18 * rng();
      points.push([
        x + rx * jitter * Math.cos(a) + j - 3,
        y + ry * jitter * Math.sin(a),
      ]);
    }
    poly(c, points, alpha(col, 0.045));
  }
}
function mountain(c, x, y, w, h, col, snow) {
  poly(
    c,
    [
      [x, y],
      [x + w * 0.24, y - h * 0.42],
      [x + w * 0.43, y - h * 0.91],
      [x + w * 0.51, y - h],
      [x + w * 0.66, y - h * 0.63],
      [x + w * 0.8, y - h * 0.41],
      [x + w, y],
    ],
    col,
  );
  if (snow)
    poly(
      c,
      [
        [x + w * 0.34, y - h * 0.68],
        [x + w * 0.43, y - h * 0.91],
        [x + w * 0.51, y - h],
        [x + w * 0.6, y - h * 0.79],
        [x + w * 0.67, y - h * 0.62],
        [x + w * 0.54, y - h * 0.72],
        [x + w * 0.51, y - h * 0.67],
        [x + w * 0.45, y - h * 0.8],
      ],
      snow,
    );
}
function pine(c, x, y, s, p) {
  rect(c, x - s * 0.04, y - s * 0.32, s * 0.08, s * 0.32, p[0]);
  for (let i = 0; i < 3; i++)
    poly(
      c,
      [
        [x, y - s * (1 - i * 0.18)],
        [x + s * (0.2 + i * 0.04), y - s * (0.62 - i * 0.19)],
        [x - s * (0.2 + i * 0.04), y - s * (0.62 - i * 0.19)],
      ],
      p[4],
    );
}
function station(c, p) {
  const [ink, paper, accent, sea, shade] = p;
  // Roof, timber structure and the warm rectangles of the ticket hall.
  rect(c, 25, 223, 391, 130, shade);
  poly(
    c,
    [
      [0, 226],
      [67, 178],
      [368, 178],
      [443, 222],
      [442, 231],
      [-8, 237],
    ],
    ink,
  );
  poly(
    c,
    [
      [56, 187],
      [69, 179],
      [367, 179],
      [380, 187],
    ],
    paper,
  );
  for (let x = 44; x < 390; x += 65) {
    rect(c, x, 247, 49, 67, ink);
    rect(c, x + 4, 251, 41, 38, paper);
    rect(c, x + 24, 250, 2, 42, shade);
    rect(c, x + 3, 270, 43, 2, shade);
    rect(c, x + 5, 296, 39, 11, mix(shade, ink, 0.3));
  }
  for (let x = 32; x < 422; x += 91) rect(c, x, 227, 8, 117, ink);
  rect(c, 12, 336, 416, 14, ink);
  rect(c, 710, 210, 10, 141, ink);
  rect(c, 878, 207, 10, 142, ink);
  rect(c, 696, 207, 202, 49, ink);
  rect(c, 701, 210, 192, 39, paper);
  oval(c, 730, 229, 11, 11, accent);
  stroke(
    c,
    [
      [757, 225],
      [867, 225],
    ],
    shade,
    3,
  );
  stroke(
    c,
    [
      [757, 234],
      [828, 234],
    ],
    shade,
    2,
  );
  for (let i = 0; i < 2; i++) rect(c, 0, 389 + i * 31, 960, 5, ink);
  for (let x = -60; x < 980; x += 41)
    poly(
      c,
      [
        [x, 399],
        [x + 13, 399],
        [x + 37, 429],
        [x + 23, 429],
      ],
      shade,
    );
}
function house(c, x, y, w, h, p, variant) {
  const [ink, paper, accent, sea, shade] = p;
  rect(c, x, y - h, w, h, variant ? shade : ink);
  rect(c, x - 3, y - h - 4, w + 6, 7, variant ? ink : shade);
  let rows = Math.floor(h / 23);
  for (let r = 0; r < rows; r++) {
    for (let k = 0; k < Math.floor(w / 17); k++) {
      if ((r * 3 + k + variant) % 5 !== 1)
        rect(
          c,
          x + 7 + k * 16,
          y - h + 10 + r * 22,
          8,
          10,
          (r + k) % 4 === 0 ? accent : paper,
        );
    }
  }
}
function street(c, p, rng) {
  for (let x = -8; x < 970; ) {
    let w = 35 + 44 * rng(),
      h = 42 + 75 * rng();
    house(c, x, 313, w, h, p, 1);
    x += w + 8;
  }
  for (const [x, w, h] of [
    [-55, 165, 170],
    [70, 106, 107],
    [780, 147, 131],
    [907, 113, 183],
  ])
    house(c, x, 351, w, h, p, 0);
  for (const x of [184, 740]) {
    rect(c, x, 234, 5, 119, p[0]);
    stroke(
      c,
      [
        [x + 2, 240],
        [x + 12, 226],
        [x + 31, 226],
      ],
      p[0],
      4,
    );
    oval(c, x + 30, 229, 10, 4, p[1]);
  }
  stroke(
    c,
    [
      [-10, 133],
      [267, 175],
      [557, 168],
      [970, 117],
    ],
    p[0],
    1.5,
  );
}
function coast(c, p, rng) {
  const [ink, paper, accent, sea, shade] = p;
  rect(c, 0, 293, 960, 135, sea);
  for (let j = 0; j < 92; j++) {
    let x = rng() * 960,
      y = 300 + rng() * 106;
    rect(c, x, y, 5 + rng() * 55, 1.1, alpha(paper, 0.55));
  }
  poly(
    c,
    [
      [583, 318],
      [725, 284],
      [784, 289],
      [854, 270],
      [960, 269],
      [960, 318],
    ],
    shade,
  );
  poly(
    c,
    [
      [762, 288],
      [769, 212],
      [783, 212],
      [791, 284],
    ],
    paper,
  );
  poly(
    c,
    [
      [764, 253],
      [766, 237],
      [786, 237],
      [787, 253],
    ],
    accent,
  );
  rect(c, 767, 204, 18, 9, ink);
  poly(
    c,
    [
      [762, 205],
      [777, 194],
      [790, 205],
    ],
    accent,
  );
  rect(c, 774, 270, 5, 11, ink);
}
function bridge(c, p) {
  rect(c, -10, 331, 980, 18, p[0]);
  for (const x of [144, 784]) {
    poly(
      c,
      [
        [x - 7, 333],
        [x - 4, 204],
        [x + 3, 199],
        [x + 9, 333],
      ],
      p[0],
    );
  }
  let pts = [];
  for (let i = 0; i <= 40; i++) {
    const x = i * 24;
    const y = 202 + 90 * Math.sin((Math.PI * (x - 144)) / 640);
    pts.push([x, y]);
    if (i % 2 === 0)
      stroke(
        c,
        [
          [x, y],
          [x, 333],
        ],
        p[4],
        2,
      );
  }
  stroke(c, pts, p[0], 4);
  rect(c, 0, 351, 960, 65, p[3]);
}
function room(c, p) {
  const [ink, paper, accent, sea, shade] = p;
  rect(c, 0, 0, 960, 362, mix(shade, ink, 0.25));
  rect(c, 111, 76, 335, 206, ink);
  rect(c, 121, 85, 314, 188, paper);
  mountain(c, 114, 270, 317, 108, sea, null);
  rect(c, 113, 174, 332, 8, ink);
  rect(c, 269, 80, 8, 200, ink);
  poly(
    c,
    [
      [98, 65],
      [180, 65],
      [160, 178],
      [127, 212],
      [137, 292],
      [96, 292],
    ],
    accent,
  );
  poly(
    c,
    [
      [375, 65],
      [457, 65],
      [451, 293],
      [409, 293],
      [421, 209],
      [393, 175],
    ],
    accent,
  );
  rect(c, 595, 245, 209, 10, ink);
  rect(c, 615, 252, 8, 92, ink);
  rect(c, 783, 250, 8, 94, ink);
  stroke(
    c,
    [
      [803, 242],
      [803, 196],
      [777, 163],
    ],
    paper,
    4,
  );
  poly(
    c,
    [
      [753, 168],
      [783, 152],
      [798, 174],
      [752, 186],
    ],
    accent,
  );
  rect(c, 631, 231, 36, 13, paper);
}
function stage(c, p, rng) {
  for (const x of [166, 654]) {
    poly(
      c,
      [
        [x, 5],
        [x + 52, 5],
        [x + 192, 340],
        [x - 75, 340],
      ],
      alpha(p[1], 0.2),
    );
    rect(c, x - 21, 0, 94, 13, p[0]);
  }
  for (let i = 0; i < 25; i++)
    oval(c, rng() * 960, 100 + rng() * 230, 1.5, 1.5, alpha(p[1], 0.62));
  for (let i = 0; i < 11; i++)
    stroke(
      c,
      [
        [i * 98 - 60, 408],
        [400 + i * 19, 307],
      ],
      p[4],
      2,
    );
}
function plants(c, p, rng) {
  for (const edge of [0, 1])
    for (let i = 0; i < 10; i++) {
      let x = edge * 960 + (edge ? -1 : 1) * rng() * 114,
        y = 434 + rng() * 56,
        h = 34 + rng() * 79;
      stroke(
        c,
        [
          [x, y],
          [x + 9, y - h * 0.5],
          [x + 7, y - h],
        ],
        p[0],
        2,
      );
      for (let k = 0; k < 3; k++) {
        let u = y - h * k * 0.24;
        poly(
          c,
          [
            [x + 3, u - 2],
            [x - 12, u - 20],
            [x - 14, u - 31],
            [x + 3, u - 15],
          ],
          p[0],
        );
        poly(
          c,
          [
            [x + 8, u - 9],
            [x + 26, u - 30],
            [x + 27, u - 38],
            [x + 8, u - 21],
          ],
          p[0],
        );
      }
    }
}
export function makeBackdrop(s, style, p, seed) {
  const canvas = createCanvas(
      style === "pixel" ? 320 : 960,
      style === "pixel" ? 180 : 540,
    ),
    c = canvas.getContext("2d");
  const [ink, paper, accent, sea, shade] = p;
  const rng = generator(seed + 71);
  c.scale(canvas.width / WIDTH, canvas.height / HEIGHT);
  let g = c.createLinearGradient(0, 0, 0, 540);
  let top =
    style === "riso" ? mix(paper, accent, 0.26) : mix(shade, accent, 0.26);
  g.addColorStop(0, top);
  g.addColorStop(0.6, paper);
  g.addColorStop(1, mix(shade, sea, 0.5));
  rect(c, 0, 0, 960, 540, g);
  if (style === "pixel")
    for (let j = 0; j < 12; j++)
      rect(c, 0, j * 23, 960, 23, mix(top, paper, j / 13));
  oval(c, 689, 116, 52, 52, style === "riso" ? accent : paper);
  if (style === "watercolor") {
    for (let j = 0; j < 55; j++)
      wash(
        c,
        rng() * 1040 - 40,
        rng() * 230,
        30 + rng() * 95,
        8 + rng() * 28,
        j % 2 ? accent : sea,
        rng,
      );
  }
  for (let k = 0; k < 4; k++) {
    let y = 279 + k * 10,
      x = -400 + k * 239;
    mountain(
      c,
      x,
      y,
      780 - k * 66,
      79 + rng() * 107,
      mix(paper, shade, 0.32 + k * 0.12),
      k % 2 === 0 ? mix(paper, "#ffffff", 0.55) : null,
    );
  }
  if (s.setting === "mountain" || s.setting === "station")
    mountain(c, 285, 295, 558, 231, shade, paper);
  poly(
    c,
    [
      [-20, 310],
      [83, 285],
      [177, 294],
      [281, 271],
      [427, 299],
      [618, 274],
      [750, 297],
      [870, 272],
      [978, 286],
      [980, 411],
      [-18, 411],
    ],
    mix(shade, sea, 0.46),
  );
  rect(c, 0, 351, 960, 189, mix(ink, shade, 0.73));
  if (s.setting === "coast") coast(c, p, rng);
  else if (s.setting === "room") room(c, p);
  else if (s.setting === "street") street(c, p, rng);
  else if (s.setting === "station") station(c, p);
  else if (s.setting === "bridge") bridge(c, p);
  else if (s.setting === "stage") stage(c, p, rng);
  else
    for (let i = 0; i < 34; i++)
      pine(c, rng() * 960, 317 + rng() * 46, 20 + rng() * 69, p);
  if (!["room", "stage", "station"].includes(s.setting)) plants(c, p, rng);
  if (style === "riso") {
    for (let y = 1; y < 540; y += 6)
      for (let x = (y % 2) * 3; x < 960; x += 6) {
        if ((x - 670) ** 2 + (y - 115) ** 2 < 67 ** 2 || y > 360)
          oval(c, x, y, 0.75, 0.75, alpha(ink, 0.31));
      }
  }
  if (style === "papercut") {
    for (let k = 0; k < 4; k++) {
      let y = 430 + k * 18;
      let pts = [
        [0, 560],
        [0, y],
      ];
      for (let x = 0; x <= 980; x += 28)
        pts.push([x, y + Math.sin(x * 0.009 + k) * 13 + rng() * 3]);
      pts.push([980, 560]);
      c.save();
      c.shadowBlur = 12;
      c.shadowColor = alpha(ink, 0.4);
      c.shadowOffsetY = -2;
      poly(c, pts, mix(shade, ink, 0.18 + k * 0.18));
      c.restore();
    }
  }
  if (style !== "pixel") {
    for (let j = 0; j < 12500; j++) {
      const x = rng() * 960,
        y = rng() * 540;
      rect(
        c,
        x,
        y,
        0.55 + rng() * 1.25,
        0.7,
        alpha(j % 2 === 0 ? paper : ink, 0.09),
      );
    }
  }
  return canvas;
}

// Motifs are drawn as vector paths. The same motif can travel through several shots.
export function motif(c, kind, x, y, size, angle, p) {
  const [ink, paper, accent, sea, shade] = p;
  c.save();
  c.translate(x, y);
  c.rotate(angle);
  c.scale(size / 100, size / 100);
  c.lineJoin = "round";
  switch (kind) {
    case "flower":
      stroke(
        c,
        [
          [-14, 40],
          [0, 8],
          [13, -19],
        ],
        ink,
        5,
      );
      svg(c, "M-6 25 Q-29 23 -27 6 Q-12 5 -6 25", sea);
      for (let i = 0; i < 6; i++) {
        let a = (i * Math.PI) / 3;
        oval(c, 12 + Math.cos(a) * 12, -19 + Math.sin(a) * 12, 10, 10, accent);
      }
      oval(c, 12, -19, 8, 8, paper);
      break;
    case "boat":
      poly(
        c,
        [
          [-51, 6],
          [2, -8],
          [44, -19],
          [26, 20],
          [-24, 25],
        ],
        paper,
      );
      poly(
        c,
        [
          [-51, 6],
          [-2, 10],
          [44, -19],
          [10, 18],
          [-24, 25],
        ],
        accent,
      );
      poly(
        c,
        [
          [-32, 3],
          [-1, -25],
          [8, 2],
          [-2, 10],
        ],
        sea,
      );
      stroke(
        c,
        [
          [-51, 6],
          [-2, 10],
          [44, -19],
        ],
        ink,
        2,
      );
      break;
    case "train":
      rect(c, -49, -27, 95, 44, accent);
      rect(c, -50, 8, 98, 12, ink);
      for (let i = 0; i < 5; i++) rect(c, -43 + i * 18, -19, 13, 17, paper);
      for (let i of [-31, 28]) oval(c, i, 21, 7, 7, ink);
      break;
    case "umbrella":
      stroke(
        c,
        [
          [0, -29],
          [0, 31],
          [-4, 38],
          [-13, 36],
          [-15, 29],
        ],
        ink,
        4,
      );
      svg(
        c,
        "M-46 2 Q-27 -34 1 -38 Q32 -29 46 4 Q30 -7 20 5 Q7 -6 -2 4 Q-15 -7 -25 3 Q-36 -9 -46 2",
        accent,
      );
      stroke(
        c,
        [
          [0, -36],
          [-12, -20],
          [-23, 0],
        ],
        paper,
        1.5,
      );
      break;
    case "clock":
      oval(c, 0, 0, 32, 34, ink);
      oval(c, 0, 0, 28, 30, paper);
      for (let k = 0; k < 12; k++) {
        const a = (k * Math.PI) / 6;
        stroke(
          c,
          [
            [Math.sin(a) * 23, Math.cos(a) * 25],
            [Math.sin(a) * 25, Math.cos(a) * 28],
          ],
          shade,
          2,
        );
      }
      stroke(
        c,
        [
          [0, -19],
          [0, 0],
          [15, 9],
        ],
        accent,
        4,
      );
      break;
    case "leaf":
      svg(c, "M-34 22 C-34 -7 -4 -35 39 -31 C30 -6 24 24 -12 28 Z", accent);
      stroke(
        c,
        [
          [-40, 33],
          [28, -22],
        ],
        ink,
        2.8,
      );
      break;
    case "mountain":
      mountain(c, -52, 29, 104, 76, sea, paper);
      break;
    case "light":
      oval(c, 0, -3, 25, 29, paper);
      rect(c, -11, 20, 22, 13, ink);
      stroke(
        c,
        [
          [-10, 0],
          [0, 14],
          [10, 0],
        ],
        accent,
        2,
      );
      for (let k = 0; k < 8; k++) {
        const a = (k * Math.PI) / 4;
        stroke(
          c,
          [
            [Math.cos(a) * 35, Math.sin(a) * 35],
            [Math.cos(a) * 43, Math.sin(a) * 43],
          ],
          paper,
          2,
        );
      }
      break;
    default:
      poly(
        c,
        [
          [-42, -22],
          [38, -25],
          [44, 24],
          [-39, 28],
        ],
        paper,
      );
      stroke(
        c,
        [
          [-42, -22],
          [0, 6],
          [38, -25],
        ],
        ink,
        2.7,
      );
      stroke(
        c,
        [
          [-38, 25],
          [-13, 3],
        ],
        shade,
        1.2,
      );
      rect(c, 22, -16, 11, 12, accent);
      break;
  }
  c.restore();
}

export function actor(c, x, y, scale, walk, gesture, phase, p, look = 1) {
  const [ink, paper, accent, sea] = p;
  c.save();
  c.translate(x, y);
  c.scale(look * scale, scale);
  const stride = Math.sin(phase) * walk * 13;
  oval(c, 0, 0, 22, 3, alpha(ink, 0.25));
  stroke(
    c,
    [
      [-7, -33],
      [-8 + stride * 0.3, -19],
      [-11 + stride, -4],
    ],
    ink,
    7,
  );
  stroke(
    c,
    [
      [6, -34],
      [6 - stride * 0.4, -17],
      [10 - stride, -3],
    ],
    ink,
    7,
  );
  stroke(
    c,
    [
      [-11 + stride, -3],
      [-5 + stride, -2],
    ],
    paper,
    3,
  );
  stroke(
    c,
    [
      [10 - stride, -3],
      [16 - stride, -2],
    ],
    ink,
    4,
  );
  svg(
    c,
    "M-11 -72 Q0 -78 11 -69 L14 -41 L20 -31 Q6 -25 -18 -32 L-14 -56 Z",
    accent,
  );
  stroke(
    c,
    [
      [-8, -65],
      [-15, -47],
      [-11, -38],
    ],
    mix(ink, accent, 0.5),
    6,
  );
  const elbow = [14 + gesture * 2, -53 - gesture * 5],
    hand = [15 + gesture * 14, -42 - gesture * 20];
  stroke(c, [[9, -66], elbow, hand], accent, 7);
  oval(c, hand[0], hand[1], 3.5, 3.5, paper);
  svg(c, "M-2 -69 L-1 -78 L8 -80 L7 -70 Z", paper);
  oval(c, 1, -84, 11, 12, paper);
  svg(
    c,
    "M-12 -82 Q-15 -102 1 -101 Q13 -100 14 -90 L4 -91 L1 -87 L-3 -86 L-7 -76 Z",
    ink,
  );
  poly(
    c,
    [
      [-12, -74],
      [5, -73],
      [13, -70],
      [4, -66],
      [-10, -68],
    ],
    sea,
  );
  poly(
    c,
    [
      [-8, -70],
      [-19, -63],
      [-20, -55],
      [-12, -57],
    ],
    sea,
  );
  c.restore();
}
