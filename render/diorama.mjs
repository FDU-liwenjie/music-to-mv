import * as THREE from "three";
import { poly } from "./art.mjs";

// Geometry, model transforms, lighting and camera are evaluated in 3D. Rasterize
// the small opaque triangle set in depth order to render on machines without WebGL.
export function diorama(c, shot, time, u, p, lyricMode) {
  const camera = new THREE.PerspectiveCamera(32, 960 / 540, 0.1, 90);
  camera.position.set(
    8 * Math.cos(0.78 + u * 0.23),
    5.7,
    8 * Math.sin(0.78 + u * 0.23),
  );
  camera.lookAt(0, 0.45, 0);
  camera.updateMatrixWorld();
  const group = new THREE.Group();
  const items = [];
  function mesh(geom, color, x, y, z, scale = [1, 1, 1], rotation = 0) {
    const node = new THREE.Mesh(geom);
    node.position.set(x, y, z);
    node.scale.set(...scale);
    node.rotation.y = rotation;
    group.add(node);
    items.push([node, color]);
    return node;
  }
  function box(x, y, z, w, h, d, color) {
    return mesh(new THREE.BoxGeometry(w, h, d), color, x, y, z);
  }
  function cone(x, y, z, r, h, n, color) {
    return mesh(new THREE.ConeGeometry(r, h, n), color, x, y, z);
  }
  const [ink, paper, accent, sea, shade] = p;
  mesh(
    new THREE.CylinderGeometry(3.12, 2.83, 0.3, 8),
    shade,
    0,
    -0.45,
    0,
    [1, 1, 0.8],
  );
  mesh(
    new THREE.CylinderGeometry(3.15, 3.13, 0.12, 8),
    sea,
    0,
    -0.25,
    0,
    [1, 1, 0.8],
  );
  if (["station", "street", "room"].includes(shot.setting)) {
    box(-1.1, 0.13, -0.21, 1.7, 0.7, 1.12, paper);
    const roof = cone(-1.1, 0.68, -0.21, 1.21, 0.58, 4, accent);
    roof.rotation.y = Math.PI / 4;
    for (let i = 0; i < 3; i++)
      box(-1.72 + i * 0.52, 0.15, 0.357, 0.23, 0.25, 0.025, ink);
    box(-0.65, 0.11, 0.36, 0.21, 0.51, 0.025, shade);
    for (let i = 0; i < 6; i++)
      box(-2 + i * 0.65, -0.12, 0.93, 0.14, 0.09, 0.52, paper);
    for (const z of [0.76, 1.09]) box(-0.1, -0.06, z, 4.3, 0.065, 0.05, ink);
  } else if (shot.setting === "stage") {
    box(0, -0.03, 0, 3.3, 0.36, 2, ink);
    for (const x of [-1.5, 1.5]) {
      box(x, 0.87, -0.8, 0.14, 1.8, 0.14, accent);
      box(x, 1.77, -0.8, 0.54, 0.18, 0.38, paper);
    }
  } else {
    cone(-1.12, 0.45, -0.62, 1.27, 1.55, 6, shade);
    cone(-1.12, 1.04, -0.62, 0.39, 0.42, 6, paper);
    cone(-1.94, 0.22, -0.51, 0.79, 0.9, 5, ink);
    for (let i = 0; i < 4; i++) {
      const x = -1.6 + i * 0.55,
        z = 0.2 + (i % 2) * 0.39;
      box(x, 0.05, z, 0.075, 0.43, 0.075, ink);
      cone(x, 0.4, z, 0.23, 0.79, 5, sea);
    }
    if (shot.setting === "bridge") {
      box(0.3, 0.07, 1.18, 2.8, 0.13, 0.5, accent);
      for (const x of [-0.9, 0.2, 1.4])
        box(x, -0.04, 1.18, 0.08, 0.55, 0.08, ink);
    }
  }
  const walk = ["walk", "return", "depart"].includes(shot.action);
  const ax = 0.64 + (walk ? (u - 0.5) * 1.2 : 0),
    az = 0.5;
  if (!lyricMode) {
    for (const [i, dx] of [-0.1, 0.1].entries()) {
      const leg = box(ax + dx, 0.12, az, 0.11, 0.57, 0.12, ink);
      leg.rotation.x = walk ? Math.sin(time * 5 + i * Math.PI) * 0.33 : 0;
    }
    cone(ax, 0.53, az, 0.31, 0.72, 5, accent);
    mesh(new THREE.IcosahedronGeometry(0.19, 0), paper, ax, 0.99, az);
    mesh(
      new THREE.IcosahedronGeometry(0.2, 0),
      ink,
      ax,
      1.07,
      az - 0.045,
      [1, 0.64, 1],
    );
  }
  // The 3D emblem uses the flat motif overlay for its detailed face in lyric mode.
  if (!lyricMode && shot.motif === "boat") {
    const boat = cone(ax + 0.57, 0.15, 0.78, 0.36, 0.16, 3, paper);
    boat.rotation.z = Math.PI;
  }
  if (!lyricMode && shot.motif === "light")
    mesh(new THREE.IcosahedronGeometry(0.13), paper, ax + 0.37, 0.9, az + 0.08);
  group.updateMatrixWorld(true);
  const faces = [];
  const a = new THREE.Vector3(),
    b = new THREE.Vector3(),
    d = new THREE.Vector3(),
    ab = new THREE.Vector3(),
    ac = new THREE.Vector3();
  const light = new THREE.Vector3(-0.24, 1, 0.61).normalize();
  for (const [node, color] of items) {
    const g = node.geometry,
      pos = g.getAttribute("position"),
      indices = g.index;
    const count = indices ? indices.count : pos.count;
    for (let i = 0; i < count; i += 3) {
      [a, b, d].forEach((v, k) =>
        v
          .fromBufferAttribute(pos, indices ? indices.getX(i + k) : i + k)
          .applyMatrix4(node.matrixWorld),
      );
      const normal = ab.subVectors(b, a).cross(ac.subVectors(d, a)).normalize();
      if (normal.dot(ac.subVectors(camera.position, a)) <= 0) continue;
      const shadeAmount = 0.73 + 0.27 * Math.max(0, normal.dot(light));
      const tint = new THREE.Color(color).multiplyScalar(shadeAmount);
      const projected = [a, b, d].map((v) => v.project(camera));
      faces.push({
        z: (a.z + b.z + d.z) / 3,
        points: projected.map((v) => [480 + v.x * 480, 265 - v.y * 270]),
        color: "#" + tint.getHexString(),
      });
    }
    g.dispose();
    node.material.dispose();
  }
  faces.sort((a, b) => b.z - a.z);
  for (const f of faces) {
    poly(c, f.points, f.color);
    c.strokeStyle = f.color;
    c.lineWidth = 0.65;
    c.stroke();
  }
}
