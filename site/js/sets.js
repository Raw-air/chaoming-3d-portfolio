// 場景建構：暴風圈、機艙（五個艙間）、天空漁港、雕刻暗室、藝廊。全部用程式生成，不需要額外的模型檔。
import * as THREE from 'three';
import { DECK, PORT, CHAMBER, WORKS } from './scenes.js';

const R = Math.random;
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

/* ---------------------------------------------------------------- 工具：畫布貼圖、批次方塊 */
function canvasTex(w, h, draw, repeat) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}
const panelDraw = (g, w, h) => {
  g.fillStyle = '#7d828b'; g.fillRect(0, 0, w, h);
  const n = 4, cell = w / n;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const v = (132 + R() * 56) | 0;
    g.fillStyle = `rgb(${v},${v + 3},${v + 9})`; g.fillRect(i * cell + 2, j * cell + 2, cell - 4, cell - 4);
    g.strokeStyle = 'rgba(0,0,0,.22)'; g.lineWidth = 2; g.strokeRect(i * cell + 12, j * cell + 12, cell - 24, cell - 24);
    g.fillStyle = 'rgba(0,0,0,.5)';
    for (const [bx, by] of [[9, 9], [cell - 9, 9], [9, cell - 9], [cell - 9, cell - 9]]) { g.beginPath(); g.arc(i * cell + bx, j * cell + by, 3, 0, 7); g.fill(); }
  }
  g.strokeStyle = 'rgba(0,0,0,.75)'; g.lineWidth = 4;
  for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * cell, 0); g.lineTo(i * cell, h); g.moveTo(0, i * cell); g.lineTo(w, i * cell); g.stroke(); }
  for (let k = 0; k < 90; k++) {
    g.strokeStyle = `rgba(255,255,255,${0.03 + R() * 0.07})`; g.lineWidth = 1; g.beginPath();
    const x = R() * w, y = R() * h; g.moveTo(x, y); g.lineTo(x + (R() - 0.5) * 70, y + (R() - 0.5) * 14); g.stroke();
  }
  for (let k = 0; k < 26; k++) { const x = R() * w, y = R() * h, r = 20 + R() * 60, gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, 'rgba(0,0,0,.16)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); }
};
const blobTex = () => canvasTex(128, 128, (g) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); });
const cloudTex = () => canvasTex(256, 256, (g) => {
  for (let k = 0; k < 46; k++) { const a = R() * 6.28, d = R() * 70, x = 128 + Math.cos(a) * d, y = 128 + Math.sin(a) * d * 0.62, r = 26 + R() * 46, gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(255,255,255,${0.1 + R() * 0.14})`); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); }
});
const textTex = (w, h, lines, opt = {}) => canvasTex(w, h, (g) => {
  if (opt.bg) { g.fillStyle = opt.bg; g.fillRect(0, 0, w, h); }
  if (opt.frame) { g.strokeStyle = opt.frame; g.lineWidth = 8; g.strokeRect(10, 10, w - 20, h - 20); }
  g.textAlign = 'center'; g.textBaseline = 'middle';
  lines.forEach(([txt, size, color, y, font]) => {
    g.font = `${font || 800} ${size}px Unbounded, "Noto Sans TC", sans-serif`;
    if (opt.neon) { g.shadowColor = color; g.shadowBlur = size * 0.5; g.fillStyle = color; g.fillText(txt, w / 2, y); g.fillText(txt, w / 2, y); g.shadowBlur = 0; g.fillStyle = '#fff'; g.globalAlpha = 0.75; g.fillText(txt, w / 2, y); g.globalAlpha = 1; }
    else { g.fillStyle = color; g.fillText(txt, w / 2, y); }
  });
  if (opt.scan) { g.fillStyle = 'rgba(0,0,0,.28)'; for (let y = 0; y < h; y += 4) g.fillRect(0, y, w, 2); }
});

function makeKit(group, detail) {
  const boxes = [], glows = [], cyls = [];
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), S = new THREE.Vector3(), P = new THREE.Vector3(), C = new THREE.Color();
  const inst = (geo, mat, list) => {
    if (!list.length) return;
    const im = new THREE.InstancedMesh(geo, mat, list.length);
    list.forEach((it, i) => {
      P.set(it[0], it[1], it[2]); E.set(it[8] || 0, it[7] || 0, it[9] || 0); Q.setFromEuler(E); S.set(it[3], it[4], it[5]);
      im.setMatrixAt(i, M.compose(P, Q, S)); C.set(it[6]); if (it[10]) C.multiplyScalar(it[10]); im.setColorAt(i, C);
    });
    im.frustumCulled = false; group.add(im);
  };
  return {
    box(x, y, z, sx, sy, sz, color = 0x3a3f47, ry = 0, rx = 0, rz = 0) { boxes.push([x, y, z, sx, sy, sz, color, ry, rx, rz]); },
    glow(x, y, z, sx, sy, sz, color, k = 1.6, ry = 0) { glows.push([x, y, z, sx, sy, sz, color, ry, 0, 0, k]); },
    cyl(x, y, z, r, h, color = 0x3a3f47, rx = 0, rz = 0) { cyls.push([x, y, z, r * 2, h, r * 2, color, 0, rx, rz]); },
    build(rough = 0.62, metal = 0.45) {
      inst(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ map: detail, roughness: rough, metalness: metal }), boxes);
      inst(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial(), glows);
      inst(new THREE.CylinderGeometry(0.5, 0.5, 1, 20), new THREE.MeshStandardMaterial({ roughness: rough, metalness: metal }), cyls);
    },
  };
}
const plane = (w, h, tex, o = {}) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, transparent: !!o.alpha, depthWrite: !o.alpha, blending: o.add ? THREE.AdditiveBlending : THREE.NormalBlending, side: o.double ? THREE.DoubleSide : THREE.FrontSide }));
  if (o.k) m.material.color.setScalar(o.k);
  if (o.color) m.material.color.set(o.color).multiplyScalar(o.k || 1);
  return m;
};
const coneMat = (color, amp) => new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
  uniforms: { uColor: { value: new THREE.Color(color) }, uAmp: { value: amp } },
  vertexShader: `varying vec2 vUv; varying float vF; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position,1.0); vec3 n = normalize(normalMatrix * normal); vF = abs(dot(n, normalize(-mv.xyz))); gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `varying vec2 vUv; varying float vF; uniform vec3 uColor; uniform float uAmp; void main(){ float a = pow(clamp(vUv.y, 0.0, 1.0), 1.6) * uAmp * pow(clamp(vF, 0.0, 1.0), 1.7); gl_FragColor = vec4(uColor * a, 1.0); }`,
});
const NOISE = `
  float h2(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float n2(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h2(i), h2(i + vec2(1,0)), f.x), mix(h2(i + vec2(0,1)), h2(i + vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++){ s += a * n2(p); p = p * 2.03 + 7.1; a *= 0.5; } return s; }`;

/* ---------------------------------------------------------------- 天空 */
function buildSky() {
  const U = {
    uTop: { value: new THREE.Color() }, uHor: { value: new THREE.Color() }, uCloud: { value: new THREE.Color() }, uSunCol: { value: new THREE.Color() },
    uSun: { value: new THREE.Vector3(0, 1, 0) }, uAmt: { value: 1 }, uSunAmt: { value: 0 }, uPhase: { value: 0 }, uFlash: { value: 0 },
  };
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false, uniforms: U,
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      varying vec3 vDir; uniform vec3 uTop, uHor, uCloud, uSunCol, uSun; uniform float uAmt, uSunAmt, uPhase, uFlash;
      ${NOISE}
      void main(){
        vec3 d = normalize(vDir);
        vec3 col = mix(uHor, uTop, pow(clamp(abs(d.y) * 1.25, 0.0, 1.0), 0.55));
        vec2 q = d.xz / (abs(d.y) + 0.22) * 0.9 + vec2(0.0, uPhase);
        float n = fbm(q + fbm(q * 0.5 + uPhase * 0.3) * 0.8);
        float c = smoothstep(0.42, 0.82, n) * uAmt * smoothstep(0.0, 0.12, abs(d.y) + 0.04);
        col = mix(col, uCloud * (0.55 + 0.6 * n), c);
        col += vec3(0.55, 1.0, 0.9) * uFlash * (0.12 + c * 1.1);
        float s = max(dot(d, normalize(uSun)), 0.0);
        col += uSunCol * (pow(s, 700.0) * 5.0 + pow(s, 12.0) * 0.4 + pow(s, 3.0) * 0.12) * uSunAmt;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(480, 40, 24), mat);
  mesh.renderOrder = -10; mesh.frustumCulled = false;
  return { mesh, U };
}

/* ---------------------------------------------------------------- 場景總成 */
export function buildSets(scene) {
  const detail = canvasTex(512, 512, panelDraw);
  const blob = blobTex(), cloudT = cloudTex();
  const groups = {};
  const mkGroup = (name) => { const g = new THREE.Group(); g.name = name; g.visible = false; scene.add(g); groups[name] = g; return g; };
  const sky = buildSky(); scene.add(sky.mesh);
  const tick = [];                       // 每格更新的小函式
  const state = { flash: 0, cargo: 0 };

  /* ============================== 暴風圈 ============================== */
  {
    const g = mkGroup('storm');
    // 雨
    const n = 1500, seed = new Float32Array(n * 6), end = new Float32Array(n * 2);
    for (let i = 0; i < n; i++) { const x = R() * 70 - 35, y = R() * 50 - 25, z = R() * 70 - 35; seed.set([x, y, z, x, y, z], i * 6); end[i * 2 + 1] = 1; }
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 6), 3));
    rg.setAttribute('aSeed', new THREE.BufferAttribute(seed, 3)); rg.setAttribute('aEnd', new THREE.BufferAttribute(end, 1));
    const rainU = { uTime: { value: 0 }, uCenter: { value: new THREE.Vector3() } };
    const rain = new THREE.LineSegments(rg, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: rainU,
      vertexShader: `attribute vec3 aSeed; attribute float aEnd; uniform float uTime; uniform vec3 uCenter; varying float vA;
        void main(){ vec3 p = aSeed; p.y = mod(p.y - uTime * 36.0 + 25.0, 50.0) - 25.0; p.z = mod(p.z + uTime * 24.0 + 35.0, 70.0) - 35.0;
          p += vec3(0.0, -1.5, 1.0) * aEnd; vA = 1.0 - aEnd * 0.8; gl_Position = projectionMatrix * viewMatrix * vec4(p + uCenter, 1.0); }`,
      fragmentShader: `varying float vA; void main(){ gl_FragColor = vec4(vec3(0.55, 0.9, 0.85) * 0.34 * vA, 1.0); }`,
    }));
    rain.frustumCulled = false; g.add(rain);
    // 往後飛逝的雲
    const clouds = [];
    for (let i = 0; i < 30; i++) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: cloudT, color: new THREE.Color(0.1, 0.3, 0.27), transparent: true, opacity: 0.38 + R() * 0.3, depthWrite: false }));
      const a = R() * 6.28, d = 16 + R() * 44; sp.position.set(Math.cos(a) * d, -14 + R() * 26, -80 + R() * 160);
      sp.scale.setScalar(16 + R() * 34); sp.userData.v = 10 + R() * 12; clouds.push(sp); g.add(sp);
    }
    // 閃電
    const boltGeo = new THREE.BufferGeometry(); boltGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(18 * 3), 3));
    const bolt = new THREE.Line(boltGeo, new THREE.LineBasicMaterial({ color: new THREE.Color(2.2, 3.2, 3.0), fog: false })); bolt.visible = false; bolt.frustumCulled = false; g.add(bolt);
    let next = 2.5, second = -1;
    const strike = () => {
      const a = R() * 6.28, d = 60 + R() * 50, p = boltGeo.attributes.position; let x = Math.cos(a) * d, z = Math.sin(a) * d;
      for (let i = 0; i < 18; i++) { p.setXYZ(i, x, 46 - i * 5, z); x += (R() - 0.5) * 9; z += (R() - 0.5) * 9; }
      p.needsUpdate = true; state.flash = 1;
    };
    tick.push((dt, t, cam) => {
      state.flash = Math.max(0, state.flash - dt * 5.5);
      if (t > next) { strike(); second = t + 0.11 + R() * 0.1; next = t + 2.6 + R() * 4.5; }
      if (second > 0 && t > second) { state.flash = 0.8; second = -1; }
      if (!g.visible) return;
      rainU.uTime.value = t; rainU.uCenter.value.copy(cam.position);
      bolt.visible = state.flash > 0.3;
      for (const c of clouds) { c.position.z += c.userData.v * dt; if (c.position.z > 85) c.position.z = -85; }
    });
  }

  /* ============================== 機艙 ============================== */
  let doors = [], cargoDoors = null, cargoLight = null, notes = [], beacons = [], windU = null, deckDress = null;
  {
    const g = mkGroup('deck');
    const K = makeKit(g, detail);
    const { x: X, w: W, h: H, bay: L, bays: NB } = DECK, len = L * NB, half = W / 2;
    const wallC = 0x4d525b, dark = 0x2a2e35;
    const surf = (w, h, rep, color, rough, metal) => new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: canvasTex(512, 512, panelDraw, rep), color, roughness: rough, metalness: metal }));
    const floor = surf(W, len, [W / 4, len / 4], 0x6c717a, 0.36, 0.78); floor.rotation.x = -Math.PI / 2; floor.position.set(X, 0, -len / 2); g.add(floor);
    const ceil = surf(W, len, [W / 4, len / 4], 0x353940, 0.7, 0.4); ceil.rotation.x = Math.PI / 2; ceil.position.set(X, H, -len / 2); g.add(ceil);
    const wl = surf(len, H, [len / 4, 1.4], 0x5a5f68, 0.66, 0.4); wl.rotation.y = Math.PI / 2; wl.position.set(X - half, H / 2, -len / 2); g.add(wl);
    const wr = surf(len, H, [len / 4, 1.4], 0x5a5f68, 0.66, 0.4); wr.rotation.y = -Math.PI / 2; wr.position.set(X + half, H / 2, -len / 2); g.add(wr);
    // 肋骨、橫樑、管線
    for (let z = -2; z > -len; z -= 4) { K.box(X - half + 0.22, H / 2, z, 0.44, H, 0.44, dark); K.box(X + half - 0.22, H / 2, z, 0.44, H, 0.44, dark); K.box(X, H - 0.2, z, W, 0.4, 0.44, dark); }
    for (const s of [-1, 1]) { K.cyl(X + s * (half - 0.5), H - 0.55, -len / 2, 0.14, len, 0x7a5a3c, Math.PI / 2); K.cyl(X + s * (half - 0.85), H - 0.38, -len / 2, 0.08, len, 0x50555e, Math.PI / 2); }

    const accents = WORKS.filter((w) => w.set === 'deck').map((w) => w.accent);
    const lamp = ['#ff6a5a', '#ffd9a0', '#8dffe9', '#93a8ff', '#ffb878'];
    const dw = 3.4, dh = 3.9, sideW = (W - dw) / 2;
    const doorMat = new THREE.MeshStandardMaterial({ map: detail, color: 0x596069, roughness: 0.42, metalness: 0.75 });
    for (let i = 0; i < NB; i++) {
      const zc = -(L * i + L / 2), ac = accents[i];
      // 天花燈條、牆面色條、地面光暈、光錐
      for (const s of [-1, 1]) {
        K.glow(X + s * 2.3, H - 0.44, zc, 0.36, 0.06, 6.5, lamp[i], 1.7);
        K.glow(X + s * (half - 0.05), 1.15, zc, 0.06, 0.07, L - 1.4, ac, 1.5); K.glow(X + s * (half - 0.05), H - 1.0, zc, 0.06, 0.05, L - 1.4, ac, 0.9);
        K.glow(X + s * (half - 0.4), 0.03, zc, 0.07, 0.04, L - 1.4, ac, 1.2);
      }
      const pool = plane(8.4, 8.4, blob, { alpha: true, add: true, color: ac, k: 0.55 }); pool.rotation.x = -Math.PI / 2; pool.position.set(X, 0.015, zc); g.add(pool);
      const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 2.5, H - 0.5, 48, 1, true), coneMat(lamp[i], 0.2)); cone.position.set(X, (H - 0.5) / 2 + 0.02, zc); g.add(cone);
      K.cyl(X, H - 0.3, zc, 0.55, 0.22, dark); K.glow(X, H - 0.43, zc, 0.7, 0.04, 0.7, lamp[i], 2.2);
      // 隔艙牆 + 滑門（往後一間的入口）
      if (i > 0) {
        const z = -L * i;
        K.box(X - (dw / 2 + sideW / 2), H / 2, z, sideW, H, 0.5, wallC); K.box(X + (dw / 2 + sideW / 2), H / 2, z, sideW, H, 0.5, wallC);
        K.box(X, dh + (H - dh) / 2, z, dw, H - dh, 0.5, wallC);
        for (const s of [-1, 1]) K.glow(X + s * (dw / 2 + 0.07), dh / 2, z, 0.08, dh, 0.58, ac, 1.8);
        K.glow(X, dh + 0.07, z, dw + 0.22, 0.08, 0.58, ac, 1.8);
        const mk = (s) => { const d = new THREE.Mesh(new THREE.BoxGeometry(dw / 2, dh, 0.16), doorMat); d.position.set(X + s * dw / 4, dh / 2, z);
          const strip = new THREE.Mesh(new THREE.BoxGeometry(dw / 2 - 0.3, 0.07, 0.19), new THREE.MeshBasicMaterial({ color: new THREE.Color(ac).multiplyScalar(1.6) })); strip.position.y = 0.3; d.add(strip); g.add(d); return d; };
        doors.push({ z, l: mk(-1), r: mk(1), open: 0 });
      }
    }
    // --- 最前面：擋風玻璃 ---
    K.box(X, 0.6, 0, W, 1.2, 0.5, wallC); K.box(X, H - 0.4, 0, W, 0.8, 0.5, wallC);
    for (const s of [-1, 1]) { K.box(X + s * (half - 0.3), H / 2, 0, 0.6, H, 0.5, wallC); K.box(X + s * 2.0, H / 2, -0.05, 0.16, H - 2, 0.3, dark); }
    windU = { uTime: { value: 0 }, uFlash: { value: 0 } };
    const wind = new THREE.Mesh(new THREE.PlaneGeometry(W - 1.2, H - 2), new THREE.ShaderMaterial({
      uniforms: windU,
      vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `varying vec2 vUv; uniform float uTime, uFlash; ${NOISE}
        void main(){ vec2 q = vUv * vec2(3.4, 1.5); q.x += uTime * 0.22; float n = fbm(q * 1.5 + fbm(q + uTime * 0.06));
          vec3 col = mix(vec3(0.003, 0.016, 0.018), vec3(0.03, 0.24, 0.2), smoothstep(0.3, 0.85, n));
          col += vec3(0.5, 0.95, 0.85) * uFlash * (0.2 + n);
          col += step(0.986, fract(sin(floor(vUv.x * 240.0) * 91.7) * 43758.5 + uTime * 1.6 + vUv.y * 0.7)) * 0.06;
          gl_FragColor = vec4(col, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    }));
    wind.rotation.y = Math.PI; wind.position.set(X, 1.2 + (H - 2) / 2, 0.02); g.add(wind);
    // --- 0 駕駛艙 ---
    { const zc = -L / 2;
      K.box(X, 1.0, -1.0, W - 2.4, 0.5, 1.5, dark);
      for (let k = 0; k < 26; k++) K.glow(X - 4.3 + R() * 8.6, 1.27, -0.5 - R() * 1.0, 0.14, 0.03, 0.1, R() < 0.6 ? '#ff3b3b' : '#ffb347', 2.2);
      const alert = textTex(512, 256, [['EMERGENCY', 62, '#ff4a40', 78], ['FAULT LOCKOUT', 44, '#ff6a5a', 148], ['ALERT ▲', 30, '#ffb0a0', 212, 600]], { bg: '#1a0303', frame: '#ff3b30', scan: true });
      for (const s of [-1, 1]) {
        K.box(X + s * (half - 0.75), 1.35, zc - 1.5, 1.3, 2.7, 8.5, dark);
        for (const dz of [1.6, -3.4]) { const p = plane(3.0, 1.5, alert, { k: 1.5 }); p.rotation.y = -s * Math.PI / 2; p.position.set(X + s * (half - 1.42), 1.8, zc + dz); g.add(p); }
        for (let k = 0; k < 14; k++) K.glow(X + s * (half - 1.42), 0.5 + R() * 0.5, zc - 5.2 + R() * 7.6, 0.03, 0.07, 0.16, R() < 0.5 ? '#ff3b3b' : '#39c8ff', 2);
        const b = new THREE.Mesh(new THREE.SphereGeometry(0.2, 16, 12), new THREE.MeshBasicMaterial({ color: 0xff2020 })); b.position.set(X + s * 3.6, H - 0.75, zc + 2.5); g.add(b); beacons.push(b);
      }
    }
    // --- 1 船員艙 ---
    { const zc = -(L + L / 2);
      for (let k = 0; k < 5; k++) { K.box(X - half + 0.75, 1.55, zc - 5.2 + k * 2.6, 1.2, 3.1, 2.3, k % 2 ? 0x56583a : 0x4a4f44); K.glow(X - half + 1.37, 2.5, zc - 5.2 + k * 2.6, 0.03, 0.08, 0.5, '#ffb347', 1.6); }
      K.box(X + half - 0.9, 0.42, zc + 0.5, 1.4, 0.84, 7.5, 0x4b3a2b); K.box(X + half - 0.9, 0.9, zc + 0.5, 1.5, 0.14, 7.7, 0x7a3326);
      K.box(X - 3.9, 0.55, zc + 5.6, 1.5, 1.1, 1.5, 0x6b5536, 0.3); K.box(X - 3.6, 1.45, zc + 5.7, 1.0, 0.7, 1.0, 0x7a6240, -0.4); K.box(X + 3.7, 0.45, zc - 6.0, 1.7, 0.9, 1.2, 0x56583a, 0.2);
      const port = canvasTex(256, 256, (c) => { const gr = c.createRadialGradient(128, 128, 20, 128, 128, 112); gr.addColorStop(0, '#2fd0b0'); gr.addColorStop(1, '#042a26'); c.fillStyle = gr; c.beginPath(); c.arc(128, 128, 104, 0, 7); c.fill(); c.strokeStyle = '#8a8f98'; c.lineWidth = 16; c.stroke(); });
      for (const dz of [-4.5, 0, 4.5]) { const p = plane(1.5, 1.5, port, { alpha: true, k: 1.2 }); p.rotation.y = -Math.PI / 2; p.position.set(X + half - 0.03, 3.3, zc + dz); g.add(p); }
    }
    // --- 2 實驗艙 ---
    { const zc = -(2 * L + L / 2);
      const wave = canvasTex(512, 256, (c, w, h) => { c.fillStyle = '#021412'; c.fillRect(0, 0, w, h); c.strokeStyle = 'rgba(31,255,210,.18)'; for (let x = 0; x < w; x += 32) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); } for (let y = 0; y < h; y += 32) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
        c.strokeStyle = '#1fffd2'; c.lineWidth = 3; c.beginPath(); for (let x = 0; x < w; x += 4) { const y = h / 2 + Math.sin(x * 0.06) * 30 * Math.sin(x * 0.011) + (x % 96 < 8 ? -70 : 0); x ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke();
        c.fillStyle = '#9dffe9'; c.font = '600 22px "JetBrains Mono", monospace'; c.fillText('SPECIMEN 04 — STABLE', 18, 34); });
      for (const s of [-1, 1]) { const p = plane(3.2, 1.6, wave, { k: 1.4 }); p.rotation.y = -s * Math.PI / 2; p.position.set(X + s * (half - 0.04), 3.4, zc); g.add(p);
        for (const dz of [-4.2, 4.2]) { K.cyl(X + s * 3.9, 0.06, zc + dz, 1.1, 0.12, dark); K.cyl(X + s * 2.0, 0.05, zc + dz * 0.5, 0.05, 4.4, 0x15302c, 0, Math.PI / 2); }
        K.cyl(X + s * (half - 0.8), 0.9, zc - 7.0, 0.5, 1.8, 0x3c5a56); K.cyl(X + s * (half - 0.8), 0.9, zc + 7.0, 0.5, 1.8, 0x3c5a56); }
      const mist = plane(11.5, 15, blob, { alpha: true, add: true, color: '#1fffd2', k: 0.42 }); mist.rotation.x = -Math.PI / 2; mist.position.set(X, 0.02, zc); g.add(mist);
    }
    // --- 3 遊戲角落 ---
    { const zc = -(3 * L + L / 2);
      const n1 = textTex(1024, 256, [['PLAY TILL DROP', 96, '#ff3b6b', 128]], { neon: true });
      const p1 = plane(6.4, 1.6, n1, { alpha: true, add: true, k: 1.5 }); p1.rotation.y = Math.PI / 2; p1.position.set(X - half + 0.05, 3.5, zc); g.add(p1);
      const n2 = textTex(1024, 256, [['INSERT COIN', 96, '#39c8ff', 128]], { neon: true });
      const p2 = plane(5.6, 1.4, n2, { alpha: true, add: true, k: 1.5 }); p2.rotation.y = -Math.PI / 2; p2.position.set(X + half - 0.05, 3.5, zc + 1); g.add(p2);
      const chk = canvasTex(256, 256, (c) => { for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { c.fillStyle = (i + j) % 2 ? 'rgba(57,200,255,.5)' : 'rgba(255,59,107,.28)'; c.fillRect(i * 32, j * 32, 32, 32); } });
      const cf = plane(9, 9, chk, { alpha: true, add: true, k: 0.22 }); cf.rotation.x = -Math.PI / 2; cf.position.set(X, 0.018, zc); g.add(cf);
      for (const s of [-1, 1]) for (const dz of [-7, 7]) K.glow(X + s * (half - 0.5), H / 2, zc + dz, 0.07, H - 1.2, 0.07, s * dz > 0 ? '#ff3b6b' : '#39c8ff', 2);
      K.box(X - 3.9, 0.3, zc + 5.5, 1.3, 0.6, 1.3, 0x2c2f4a, 0.3); K.box(X + 4.0, 0.3, zc + 5.0, 1.1, 0.6, 1.1, 0x3a2c4a, -0.2);
    }
    // --- 4 酒吧 ---
    { const zc = -(4 * L + L / 2);
      K.box(X + half - 1.6, 0.6, zc + 0.5, 1.1, 1.2, 8.4, 0x5c3a25); K.box(X + half - 1.6, 1.26, zc + 0.5, 1.5, 0.12, 8.8, 0x2c1a11);
      K.glow(X + half - 2.18, 0.14, zc + 0.5, 0.04, 0.06, 8.2, '#ff9a3d', 1.6);
      for (let k = 0; k < 4; k++) { const z = zc - 2.8 + k * 2.2; K.cyl(X + half - 2.9, 0.42, z, 0.05, 0.84, 0x9a9da3); K.cyl(X + half - 2.9, 0.87, z, 0.34, 0.1, 0x8a2f24); K.cyl(X + half - 2.9, 0.03, z, 0.3, 0.05, 0x9a9da3); }
      K.box(X + half - 0.25, 2.5, zc + 0.5, 0.4, 0.08, 8.0, 0x3a2416); K.box(X + half - 0.25, 3.3, zc + 0.5, 0.4, 0.08, 8.0, 0x3a2416); K.glow(X + half - 0.1, 2.44, zc + 0.5, 0.05, 0.04, 8.0, '#ffb070', 1.8);
      const bc = [0x2f7d5a, 0x8a5a1e, 0x7a2a22, 0x2a4a7a, 0xb99a4a];
      for (let k = 0; k < 26; k++) K.cyl(X + half - 0.3, (k % 2 ? 3.34 : 2.54) + 0.22, zc - 3.3 + (k >> 1) * 0.62 + R() * 0.1, 0.07 + R() * 0.03, 0.36 + R() * 0.18, bc[k % 5]);
      for (const dz of [-3, 0, 3]) { K.cyl(X + half - 1.6, H - 0.9, zc + 0.5 + dz, 0.012, 1.8, dark); K.cyl(X + half - 1.6, H - 1.85, zc + 0.5 + dz, 0.26, 0.3, 0x2a1a12); K.glow(X + half - 1.6, H - 2.02, zc + 0.5 + dz, 0.3, 0.05, 0.3, '#ffcf8a', 2.4); }
      const n3 = textTex(1024, 256, [['FINAL VOYAGE', 100, '#ff9a3d', 128]], { neon: true });
      const p3 = plane(6.2, 1.55, n3, { alpha: true, add: true, k: 1.5 }); p3.rotation.y = Math.PI / 2; p3.position.set(X - half + 0.05, 3.5, zc); g.add(p3);
      K.box(X - half + 1.0, 0.45, zc - 4.5, 1.6, 0.9, 2.6, 0x6a2a22); K.box(X - half + 0.45, 1.15, zc - 4.5, 0.5, 0.9, 2.6, 0x7a3326); K.box(X - half + 1.0, 0.45, zc + 4.5, 1.6, 0.9, 2.6, 0x6a2a22); K.box(X - half + 0.45, 1.15, zc + 4.5, 0.5, 0.9, 2.6, 0x7a3326);
      const noteT = canvasTex(64, 64, (c) => { c.fillStyle = '#fff'; c.font = '700 52px serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('♪', 32, 34); });
      for (let k = 0; k < 9; k++) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: noteT, color: 0xffb060, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })); sp.scale.setScalar(0.28); sp.userData = { ph: R() * 6.28, sp: 0.25 + R() * 0.3, r: 0.4 + R() * 0.7, zc }; notes.push(sp); g.add(sp); }
    }
    // --- 最後面：後艙門（打開後白光湧入，通往天空漁港）---
    { const z = -len, cw = 8, ch = 4.8;
      for (const s of [-1, 1]) { K.box(X + s * (cw / 2 + (W - cw) / 4), H / 2, z, (W - cw) / 2, H, 0.5, wallC); K.glow(X + s * (cw / 2 + 0.08), ch / 2, z + 0.3, 0.1, ch, 0.1, '#ffd27a', 2); }
      K.box(X, ch + (H - ch) / 2, z, cw, H - ch, 0.5, wallC); K.glow(X, ch + 0.08, z + 0.3, cw + 0.3, 0.1, 0.1, '#ffd27a', 2);
      const mk = (s) => { const d = new THREE.Mesh(new THREE.BoxGeometry(cw / 2, ch, 0.22), doorMat); d.position.set(X + s * cw / 4, ch / 2, z + 0.1); g.add(d); return d; };
      cargoDoors = { l: mk(-1), r: mk(1), cw, x: X };
      cargoLight = new THREE.Mesh(new THREE.PlaneGeometry(cw + 3, ch + 2), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.4, 2.6, 2.8) })); cargoLight.position.set(X, ch / 2, z - 0.9); g.add(cargoLight);
    }
    K.build(0.6, 0.5);
    // 場景裡多擺幾台同款模型當陳設（實驗艙的整排生物倉、遊戲角落的其他機台）
    deckDress = (id, src) => {
      const cache = new Map();
      const place = (x, z, ry, s) => {
        const c = src.clone(true), kill = [];
        c.traverse((o) => { if (o.isLine || o.isLineSegments) kill.push(o); else if (o.isMesh) {
          let m = cache.get(o.material);
          if (!m) { m = o.material.clone(); m.vertexColors = false; m.clippingPlanes = null; if (m.name === 'pod_glass') { m.transparent = true; m.opacity = 0.3; m.depthWrite = false; m.side = THREE.DoubleSide; } if (m.emissiveIntensity) m.emissiveIntensity *= 0.7; cache.set(o.material, m); }
          o.material = m; o.frustumCulled = false; } });
        kill.forEach((o) => o.parent.remove(o));
        c.position.set(x, 0, z); c.rotation.y = ry; c.scale.setScalar(s); g.add(c);
      };
      if (id === 'pod') { const zc = -(2 * L + L / 2); for (const s of [-1, 1]) for (const dz of [-4.2, 4.2]) place(X + s * 3.9, zc + dz, s * 0.4, 2.05); }
      if (id === 'arcade') { const zc = -(3 * L + L / 2); place(X + 3.9, zc - 4.6, -0.55, 2.05); place(X - 4.0, zc - 5.2, 0.6, 2.05); place(X + 4.1, zc - 1.6, -1.2, 2.05); }
    };
    tick.push((dt, t, cam) => {
      if (!g.visible) return;
      const inX = Math.abs(cam.position.x - X) < half + 1;
      for (const d of doors) { const o = inX ? 1 - sstep(2.6, 7.5, Math.abs(cam.position.z - d.z)) : 0; d.open += (o - d.open) * Math.min(1, dt * 7); d.l.position.x = X - dw / 4 - d.open * dw / 2 * 0.97; d.r.position.x = X + dw / 4 + d.open * dw / 2 * 0.97; }
      const co = state.cargo; cargoDoors.l.position.x = X - cargoDoors.cw / 4 - co * cargoDoors.cw / 2; cargoDoors.r.position.x = X + cargoDoors.cw / 4 + co * cargoDoors.cw / 2; cargoLight.visible = co > 0.01;
      windU.uTime.value = t; windU.uFlash.value = state.flash;
      const bk = 0.35 + 0.65 * Math.pow(0.5 + 0.5 * Math.sin(t * 5), 2); for (const b of beacons) b.material.color.setRGB(3.2 * bk, 0.25 * bk, 0.2 * bk);
      for (const n of notes) { const u = (t * n.userData.sp + n.userData.ph) % 1; n.position.set(X + Math.sin(n.userData.ph + u * 5) * n.userData.r, 1.6 + u * 2.6, n.userData.zc + Math.cos(n.userData.ph * 2 + u * 4) * n.userData.r * 0.6); n.material.opacity = Math.sin(u * Math.PI) * 0.9; }
    });
  }

  /* ============================== 天空漁港 ============================== */
  {
    const g = mkGroup('port');
    const K = makeKit(g, detail);
    const [px, py, pz] = PORT, z0 = pz - 4.1, deck = py + 3.3;
    const woods = [0x8b5a3c, 0xa9774f, 0x7a4c33, 0x96684a];
    for (let x = -17; x <= 17; x += 1.0) K.box(px + x, deck, z0 + (R() - 0.5) * 0.08, 0.92, 0.14, 3.1 + R() * 0.15, woods[(R() * 4) | 0], (R() - 0.5) * 0.03);
    for (const dz of [-1.2, 1.2]) K.box(px, deck - 0.22, z0 + dz, 35, 0.3, 0.26, 0x5a3a26);
    for (let x = -16; x <= 16; x += 5.33) for (const dz of [-1.45, 1.45]) K.cyl(px + x, deck - 11, z0 + dz, 0.2, 22, 0x4f3323);
    for (let x = -17; x <= 17; x += 2.83) K.cyl(px + x, deck + 0.6, z0 - 1.5, 0.07, 1.2, 0x5a3a26);
    K.cyl(px, deck + 1.15, z0 - 1.5, 0.045, 35, 0x8a6a45, 0, Math.PI / 2); K.cyl(px, deck + 0.7, z0 - 1.5, 0.035, 35, 0x8a6a45, 0, Math.PI / 2);
    for (const x of [-14, 0, 14]) { K.cyl(px + x, deck + 1.8, z0 - 1.45, 0.08, 3.6, 0x3d2a1e); K.box(px + x, deck + 3.55, z0 - 1.1, 0.12, 0.1, 0.8, 0x3d2a1e); K.glow(px + x, deck + 3.2, z0 - 0.78, 0.3, 0.42, 0.3, '#ffd27a', 2.6); }
    K.box(px - 10.5, deck + 0.52, z0 - 0.6, 0.9, 0.9, 0.9, 0x9a7048, 0.3); K.box(px - 9.4, deck + 0.42, z0 - 0.2, 0.7, 0.7, 0.7, 0x86603e, -0.2); K.box(px - 10.2, deck + 1.3, z0 - 0.5, 0.6, 0.6, 0.6, 0xa9774f, 0.5);
    for (const [x, dz] of [[9.2, -0.5], [10.1, 0.1], [9.8, -1.0]]) { K.cyl(px + x, deck + 0.52, z0 + dz, 0.36, 0.9, 0x6b432e); K.cyl(px + x, deck + 0.52, z0 + dz, 0.375, 0.08, 0x2c2f33); }
    K.box(px + 1.5, deck + 0.02, z0 + 2.3, 1.2, 0.1, 2.2, 0xa9774f, 0, 0.1);                          // 登船跳板
    for (const x of [-6, 6]) K.cyl(px + x, deck + 0.9, z0 + 1.9, 0.03, 3.4, 0x8a6a45, 1.05);          // 繫船繩
    // 港口招牌
    K.cyl(px - 15.5, deck + 1.9, z0 + 0.9, 0.09, 3.8, 0x4f3323); K.cyl(px - 12.7, deck + 1.9, z0 + 0.9, 0.09, 3.8, 0x4f3323);
    const sign = plane(3.1, 1.25, textTex(512, 208, [['天空漁港', 78, '#fff0d0', 82, 900], ['SKY PORT', 34, '#ffd27a', 158, 600]], { bg: '#5a3a26', frame: '#2c1a11' }), { double: true }); sign.position.set(px - 14.1, deck + 3.0, z0 + 0.9); g.add(sign);
    K.build(0.85, 0.05);
    // 雲海
    const clouds = [];
    for (let i = 0; i < 46; i++) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: cloudT, color: 0xffffff, transparent: true, opacity: 0.55 + R() * 0.4, depthWrite: false }));
      const a = R() * 6.28, d = 26 + R() * 150, hi = R() < 0.25;
      sp.position.set(px + Math.cos(a) * d, hi ? py + 14 + R() * 40 : py - 13 + R() * 9, pz + Math.sin(a) * d);
      sp.scale.setScalar(hi ? 30 + R() * 50 : 34 + R() * 60); sp.userData.v = 0.25 + R() * 0.5; clouds.push(sp); g.add(sp);
    }
    tick.push((dt) => { if (!g.visible) return; for (const c of clouds) { c.position.x += c.userData.v * dt; if (c.position.x > px + 180) c.position.x = px - 180; } });
    groups.port.userData.clouds = clouds;
  }

  /* ============================== 雕刻暗室 ============================== */
  {
    const g = mkGroup('chamber');
    const K = makeKit(g, detail);
    const [cx, cy, cz] = CHAMBER;
    const floor = new THREE.Mesh(new THREE.CircleGeometry(48, 72), new THREE.MeshStandardMaterial({ color: 0x0b0b10, roughness: 0.22, metalness: 0.85 })); floor.rotation.x = -Math.PI / 2; floor.position.set(cx, cy, cz); g.add(floor);
    K.cyl(cx, cy + 0.06, cz, 3.0, 0.12, 0x101016); K.cyl(cx, cy + 0.24, cz, 2.3, 0.24, 0x18181f);
    for (let i = 0; i < 12; i++) { const a = (i / 12) * 6.28 + 0.26, d = 15 + (i % 3) * 3.5; K.box(cx + Math.cos(a) * d, 8, cz + Math.sin(a) * d, 1.8, 16, 1.8, 0x15151c, -a); }
    K.build(0.5, 0.6);
    const up = new THREE.Vector3(0, 1, 0);
    for (const [ox, oy, oz, col, amp] of [[-4.5, 11, 4, '#ffffff', 0.2], [5, 12, 2, '#b79bff', 0.16], [0.5, 12, -6, '#8a7aff', 0.1]]) {
      const from = new THREE.Vector3(cx + ox, cy + oy, cz + oz), to = new THREE.Vector3(cx, cy + 1.2, cz), dir = to.clone().sub(from), len = dir.length();
      const m = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 2.7, len, 48, 1, true), coneMat(col, amp));
      m.position.copy(from).addScaledVector(dir, 0.5); m.quaternion.setFromUnitVectors(up, dir.clone().normalize().negate()); g.add(m);
    }
    const n = 420, pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const a = R() * 6.28, d = R() * 11; pos[i * 3] = cx + Math.cos(a) * d; pos[i * 3 + 1] = cy + 0.3 + R() * 9; pos[i * 3 + 2] = cz + Math.sin(a) * d; }
    const dg = new THREE.BufferGeometry(); dg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const dust = new THREE.Points(dg, new THREE.PointsMaterial({ size: 0.045, color: 0xd8ccff, transparent: true, opacity: 0.6, depthWrite: false, blending: THREE.AdditiveBlending }));
    g.add(dust);
    tick.push((dt, t) => { if (g.visible) dust.position.y = Math.sin(t * 0.25) * 0.25; });
  }

  /* ============================== 藝廊（圖片由主程式放進來） ============================== */
  mkGroup('gallery');

  return {
    groups, sky, state,
    dress: (id, src) => deckDress && deckDress(id, src),
    addGalleryFloor(cx, cz, r) {
      const f = new THREE.Mesh(new THREE.CircleGeometry(r * 2.4, 64), new THREE.MeshStandardMaterial({ color: 0x0a0b10, roughness: 0.25, metalness: 0.85 })); f.rotation.x = -Math.PI / 2; f.position.set(cx, 0, cz); groups.gallery.add(f);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(r, 0.03, 8, 160), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.3, 1.35, 1.5) })); ring.rotation.x = Math.PI / 2; ring.position.set(cx, 5.1, cz); groups.gallery.add(ring);
      const ring2 = ring.clone(); ring2.position.y = 0.03; groups.gallery.add(ring2);
    },
    update(dt, t, camera) { for (const f of tick) f(dt, t, camera); },
  };
}
