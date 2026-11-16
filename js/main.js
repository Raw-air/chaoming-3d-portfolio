import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { PROFILE, WORKS, GALLERY, SERVICES, PROCESS, AWARDS } from './data.js';
import { createWarpPass, createSky, galleryMaterial, splitText, scramble, createCursor, createMarquee } from './fx.js';

const $ = (s) => document.querySelector(s);
const DEG = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (t) => t * t * t * (t * (t * 6 - 15) + 10);
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const BG = 0x06070b;

/* ------------------------------------------------------------------ beats (運鏡腳本) */
const beats = [];
const chapters = [];
const heroHTML = `
  <div class="eyebrow" data-scr>${PROFILE.nameZh} ${PROFILE.nameEn} — 3D MODELING</div>
  <h1>${PROFILE.claim.map((l) => `<span class="ln">${l}</span>`).join('')}</h1>
  <p class="lead">${PROFILE.lead}</p>
  <div class="hero-stats">${PROFILE.heroStats.map(([n, l]) => `<div><b>${n}</b><span>${l}</span></div>`).join('')}</div>
  <div class="scroll"><i></i>往下捲動，開始檢查</div>`;
beats.push({ kind: 'orbit', work: 0, az: -34, el: 2, d: 13, f: [0, 2.3, 0], side: 1, mode: 'shaded', html: heroHTML, cls: 'hero', chapter: 'top' });
chapters.push({ id: 'top', label: '首頁', beat: 0 });

WORKS.forEach((w, wi) => {
  chapters.push({ id: w.id, label: `${w.no} ${w.title}`, beat: beats.length, work: wi });
  w.shots.forEach((s) => {
    const spec = s.spec ? `<dl class="spec">${s.spec.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>` : '';
    const chips = s.chips ? `<div class="chips">${s.chips.map((c) => `<span>${c}</span>`).join('')}</div>` : '';
    const stats = s.stats ? `<div class="stats" data-stats="${w.id}"></div><div class="chips">${w.deliver.map((c) => `<span>${c}</span>`).join('')}</div>` : '';
    beats.push({ kind: 'orbit', work: wi, ...s, chapter: w.id,
      html: `<div class="kicker" data-scr>${s.kicker}</div><h2>${s.h}</h2><p>${s.p}</p>${spec}${chips}${stats}` });
  });
});
const firstWorkBeat = 1;

const GC = new THREE.Vector3(GALLERY.center[0], GALLERY.eye, GALLERY.center[1]);
const GYAW0 = Math.PI;
chapters.push({ id: 'gallery', label: '藝廊', beat: beats.length });
[-74, 0, 74].forEach((deg, i) => beats.push({ kind: 'pan', yaw: GYAW0 + deg * DEG, pitch: 1.5 * DEG, side: 0, mode: 'shaded', chapter: 'gallery', cls: 'gal',
  html: i === 0 ? `<div class="kicker" data-scr>RENDER GALLERY — 渲染與劇照</div><h2>環形藝廊</h2><p>繼續捲動環顧四周，點任何一張圖放大。</p>` : null }));

chapters.push({ id: 'about', label: '服務', beat: beats.length });
beats.push({ kind: 'free', pos: [0, 15, 24], target: [-9, 3, -30], side: 0, mode: 'shaded', chapter: 'about', cls: 'about',
  html: `<div class="kicker" data-scr>WHAT I DO — 我能幫你做什麼</div><h2>你出想法，我交模型</h2>
    <div class="svc">${SERVICES.map(([a, b]) => `<div><b>${a}</b><span>${b}</span></div>`).join('')}</div>
    <div class="about-foot">
      <div><h3>HOW IT WORKS — 合作流程</h3><ol class="steps">${PROCESS.map(([n, a, b]) => `<li><i>${n}</i><b>${a}</b><span>${b}</span></li>`).join('')}</ol></div>
      <div><h3>RECOGNITION — 獎項肯定</h3><ul class="awards">${AWARDS.map(([y, t]) => `<li><span>${y}</span>${t}</li>`).join('')}</ul></div>
    </div>` });
chapters.push({ id: 'contact', label: '聯絡', beat: beats.length });
beats.push({ kind: 'free', pos: [-10, 30, 20], target: [-9, 0, -28], side: 0, mode: 'shaded', chapter: 'contact', cls: 'contact',
  html: `<div class="kicker" data-scr>START A PROJECT — 開始合作</div><h2><span class="ln">有模型要做？</span><span class="ln">說說你的專案。</span></h2>
    <p class="lead">附上參考圖、用途與期限，我會回覆可行的做法與報價。角色、道具、場景，或整支動畫的 3D 需求都可以聊。</p>
    <a class="mail" href="mailto:${PROFILE.email}?subject=${encodeURIComponent('3D 建模合作洽詢')}"><span>寫信給我</span><em>${PROFILE.email}</em><b>→</b></a>
    <div class="contact-meta">${PROFILE.phone ? `<a href="tel:${PROFILE.phoneHref}">${PROFILE.phone}</a>` : ''}<span>TAIWAN <b id="tw-time">--:--</b> · 可遠端合作</span><span>BLENDER · AFTER EFFECTS · PHOTOSHOP</span></div>` });
const N = beats.length;

/* ------------------------------------------------------------------ DOM */
const panelsEl = $('#panels');
const panels = beats.map((b) => {
  if (!b.html) return null;
  const el = document.createElement('section');
  const side = b.side === 0 ? 'c' : b.side === 1 ? 'l' : 'r';
  el.className = `panel side-${side} ${b.cls || ''}`;
  if (b.work !== undefined && b.kind === 'orbit') el.style.setProperty('--pa', WORKS[b.work].accent);
  el.innerHTML = `<div class="box">${b.html}</div>`;
  el.querySelectorAll('h1, h2').forEach(splitText);
  panelsEl.appendChild(el);
  return { el, o: -1, y: 0, sk: 0, on: false, scr: [...el.querySelectorAll('[data-scr]')] };
});
const rail = $('#rail');
chapters.forEach((c) => {
  const btn = document.createElement('button');
  btn.innerHTML = `<i></i><span>${c.label}</span>`;
  btn.addEventListener('click', () => jump(c.beat));
  rail.appendChild(btn); c.btn = btn;
});
document.querySelectorAll('[data-jump]').forEach((a) => a.addEventListener('click', (e) => {
  e.preventDefault();
  const k = a.dataset.jump;
  jump(k === 'works' ? firstWorkBeat : k === '0' ? 0 : chapters.find((c) => c.id === k).beat);
}));
const twTime = $('#tw-time');
const tickTime = () => { if (twTime) twTime.textContent = new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Taipei' }); };
tickTime(); setInterval(tickTime, 30000);

let unit = innerHeight * 1.2;
function layoutScroll() {
  unit = innerHeight * 1.2;
  $('#scroll-space').style.height = `${(N - 1) * unit + innerHeight}px`;
}
function jump(beat) { scrollTo({ top: beat * unit + 1, behavior: reduceMotion ? 'auto' : 'smooth' }); }
layoutScroll();
const cursor = createCursor();
const marquee = createMarquee();
const progressEl = $('#progress i');

/* ------------------------------------------------------------------ renderer */
const canvas = $('#stage');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
} catch (e) {
  $('#loader-text').textContent = '此瀏覽器不支援 WebGL，無法顯示 3D 內容';
  throw e;
}
let dpr = Math.min(devicePixelRatio || 1, 1.5);
renderer.setPixelRatio(dpr);
renderer.setSize(innerWidth, innerHeight, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.95;
renderer.localClippingEnabled = true;

const scene = new THREE.Scene();
scene.background = new THREE.Color(BG);
scene.fog = new THREE.FogExp2(BG, 0.0105);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.42;

const camera = new THREE.PerspectiveCamera(36, innerWidth / innerHeight, 0.1, 700);
camera.position.set(0, 3, 16);

const rt = new THREE.WebGLRenderTarget(innerWidth * dpr, innerHeight * dpr, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth / 2, innerHeight / 2), 0.4, 0.6, 0.92);
composer.addPass(bloom);
const warp = createWarpPass();
composer.addPass(warp);
composer.addPass(new OutputPass());
const WU = warp.uniforms;

/* ------------------------------------------------------------------ lights */
scene.add(new THREE.HemisphereLight(0x9fb4d8, 0x0b0b10, 0.55));
const key = new THREE.DirectionalLight(0xfff1e0, 1.55);
key.position.set(6, 10, 8);
scene.add(key, key.target);
const rim = new THREE.PointLight(0xff6a3d, 260, 0, 2);
const fill = new THREE.PointLight(0x9fc4ff, 60, 0, 2);
scene.add(rim, fill);

/* ------------------------------------------------------------------ environment */
const sky = createSky(BG);
scene.add(sky);
const groundMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uCam: { value: new THREE.Vector3() }, uPos: { value: new THREE.Vector2() }, uColor: { value: new THREE.Color('#ff6a3d') }, uTime: { value: 0 } },
  vertexShader: `varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
  fragmentShader: `
    varying vec3 vW; uniform vec3 uCam; uniform vec2 uPos; uniform vec3 uColor; uniform float uTime;
    float grid(vec2 p){ vec2 fw = fwidth(p); vec2 a = abs(fract(p - 0.5) - 0.5) / max(fw, vec2(1e-4)); return 1.0 - min(min(a.x, a.y), 1.0); }
    void main(){
      float l = grid(vW.xz / 2.0) * 0.6 + grid(vW.xz / 10.0) * 0.5;
      float dc = distance(vW.xz, uCam.xz);
      float fade = exp(-dc * 0.03);
      float ds = distance(vW.xz, uPos);
      float wave = mod(uTime * 3.2, 18.0);
      float ring = smoothstep(0.5, 0.0, abs(ds - wave)) * exp(-ds * 0.13);
      float glow = exp(-ds * 0.2);
      vec3 col = vec3(0.32, 0.4, 0.55) * l * fade * 0.5 + uColor * (ring * (0.12 + l * 0.8) + glow * (0.018 + l * 0.32));
      gl_FragColor = vec4(col, 1.0);
    }`,
});
const ground = new THREE.Mesh(new THREE.PlaneGeometry(600, 600), groundMat);
ground.rotation.x = -Math.PI / 2;
ground.position.set(-5, 0, -25);
scene.add(ground);

function makePoints(n, fn, size, color, opacity, fog) {
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) fn(pos, i * 3);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ size, color, transparent: true, opacity, depthWrite: false, sizeAttenuation: fog, fog, blending: THREE.AdditiveBlending }));
}
const stars = makePoints(2200, (p, i) => {
  const v = new THREE.Vector3().randomDirection(); v.y = Math.abs(v.y) * 0.9 + 0.03; v.normalize().multiplyScalar(260 + Math.random() * 60);
  p[i] = v.x; p[i + 1] = v.y; p[i + 2] = v.z;
}, 1.5, 0xcfd8ff, 0.8, false);
scene.add(stars);
const dust = makePoints(1400, (p, i) => { p[i] = -60 + Math.random() * 110; p[i + 1] = 0.3 + Math.random() * 12; p[i + 2] = -80 + Math.random() * 100; }, 0.035, 0xfff0dd, 0.5, true);
scene.add(dust);

function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'); const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
const glowTex = glowTexture();

/* ------------------------------------------------------------------ stages */
const timeU = { value: 0 };
const pedMat = new THREE.MeshStandardMaterial({ color: 0x090a0e, roughness: 0.62, metalness: 0.35 });
function beamMaterial(color) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending,
    uniforms: { uColor: { value: new THREE.Color(color) }, uAmp: { value: 0 } },
    vertexShader: `varying vec2 vUv; varying float vF; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position,1.0); vec3 n = normalize(normalMatrix * normal); vF = abs(dot(n, normalize(-mv.xyz))); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec2 vUv; varying float vF; uniform vec3 uColor; uniform float uAmp; void main(){ float a = pow(clamp(1.0 - vUv.y, 0.0, 1.0), 3.0) * 0.16 * uAmp * pow(clamp(vF, 0.0, 1.0), 2.2); gl_FragColor = vec4(uColor * a, 1.0); }`,
  });
}
// 所有作品材質共用的頂點注入：爆炸拆解位移（aDir）＋抵達時的表面波動
function inject(mat, w, useNormal) {
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uExplode = w.uExplode; sh.uniforms.uWobble = w.uWobble; sh.uniforms.uFxTime = timeU;
    sh.vertexShader = 'attribute vec3 aDir;\nuniform float uExplode, uWobble, uFxTime;\n' + sh.vertexShader.replace('#include <begin_vertex>',
      '#include <begin_vertex>\n  transformed += aDir * uExplode;' + (useNormal ? '\n  transformed += normal * sin(position.y * 46.0 + uFxTime * 9.0) * 0.012 * uWobble;' : ''));
  };
  mat.customProgramCacheKey = () => (useNormal ? 'fxn' : 'fx');
  return mat;
}

const works = WORKS.map((w, i) => {
  const stage = new THREE.Group();
  stage.position.set(w.pos[0], 0, w.pos[1]);
  const accent = new THREE.Color(w.accent);
  const baseY = w.lift > 0 ? w.lift : 0.3;
  if (w.lift === 0) {
    const ped = new THREE.Mesh(new THREE.CylinderGeometry(w.pad, w.pad * 1.1, 0.3, 72), pedMat);
    ped.position.y = 0.15; stage.add(ped);
  }
  const ring = new THREE.Mesh(new THREE.TorusGeometry(w.pad * 1.02, 0.02, 8, 160), new THREE.MeshBasicMaterial({ color: accent.clone().multiplyScalar(1.7) }));
  ring.rotation.x = Math.PI / 2; ring.position.y = w.lift > 0 ? 0.03 : 0.31; stage.add(ring);
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(w.pad * 1.55, 0.008, 6, 160), new THREE.MeshBasicMaterial({ color: accent.clone().multiplyScalar(0.5) }));
  ring2.rotation.x = Math.PI / 2; ring2.position.y = 0.02; stage.add(ring2);
  const beamMat = beamMaterial(w.accent);
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(w.pad * 1.02, w.pad * 1.02, 9, 64, 1, true), beamMat);
  beam.position.y = 4.5 + ring.position.y; stage.add(beam);
  // 掃描環：材質切換時由下往上掃過模型
  const scanRing = new THREE.Group();
  const sr1 = new THREE.Mesh(new THREE.TorusGeometry(w.pad * 0.98, 0.025, 8, 128), new THREE.MeshBasicMaterial({ color: accent.clone().lerp(new THREE.Color(0xffffff), 0.4).multiplyScalar(2.4) }));
  sr1.rotation.x = Math.PI / 2;
  const sr2 = new THREE.Mesh(new THREE.CircleGeometry(w.pad * 0.98, 64), new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  sr2.rotation.x = -Math.PI / 2;
  scanRing.add(sr1, sr2); scanRing.visible = false; stage.add(scanRing);

  const holder = new THREE.Group();
  holder.position.y = baseY; holder.rotation.y = w.yaw;
  stage.add(holder);
  scene.add(stage);
  const lineColor = accent.clone().lerp(new THREE.Color(0xffffff), 0.3).multiplyScalar(1.25);
  const o = { ...w, i, stage, holder, baseY, accentColor: accent, beamMat, scanRing, meshes: [], lines: [], clones: [], spin: [], pulse: [], origMats: [], fx: new THREE.Group(),
    uExplode: { value: 0 }, uWobble: { value: 0 }, explodeT: 0, wobble: 0, height: w.scale,
    pAll: new THREE.Plane(new THREE.Vector3(0, 1, 0), 1e5), pAbove: new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), pBelow: new THREE.Plane(new THREE.Vector3(0, -1, 0), 0),
    mode: 'shaded', scan: null, userYaw: 0, yawVel: 0, amp: 0, loaded: false };
  o.cAll = [o.pAll]; o.cAbove = [o.pAbove]; o.cBelow = [o.pBelow];
  o.lineMat = inject(new THREE.LineBasicMaterial({ color: lineColor, transparent: true, opacity: w.wireOpacity || 0.9, depthWrite: false, clippingPlanes: o.cAll }), o, false);
  o.clayMat = inject(new THREE.MeshStandardMaterial({ color: 0xcfc8bc, roughness: 0.72, metalness: 0, clippingPlanes: o.cAll }), o, true);
  o.darkMat = inject(new THREE.MeshStandardMaterial({ color: 0x0a0d13, roughness: 0.55, metalness: 0.3, polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2, clippingPlanes: o.cAll }), o, true);
  return o;
});

/* ------------------------------------------------------------------ model loading */
const draco = new DRACOLoader();
draco.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/');
const gltfLoader = new GLTFLoader();
gltfLoader.setDRACOLoader(draco);
let stats = {};
let loadedCount = 0;
const loadFill = $('#loader-fill'), loadPct = $('#loader-pct');
function setProgress(f) { loadFill.style.transform = `scaleX(${f})`; loadPct.textContent = String(Math.round(f * 100)).padStart(3, '0'); }

// 頂點色裡存的是「所屬部件中心」→ 轉成由模型中心往外的位移向量 aDir
// 爆炸圖 = 以原點為中心把各部件的位置等比放大（離中心越遠推得越開）
const spread = () => 1;
function bakeDir(geo, cy, zero) {
  const col = geo.getAttribute('color'); if (!col) return;
  const n = col.count, a = new Float32Array(n * 3);
  if (!zero) for (let k = 0; k < n; k++) {
    const x = col.getX(k) - 0.5, y = col.getZ(k) - cy, z = -(col.getY(k) - 0.5), s = spread(Math.hypot(x, y, z));
    a[k * 3] = x * s; a[k * 3 + 1] = y * s; a[k * 3 + 2] = z * s;
  }
  geo.setAttribute('aDir', new THREE.BufferAttribute(a, 3));
  geo.deleteAttribute('color');
}

function setupModel(w, root) {
  const box = new THREE.Box3().setFromObject(root);
  // 拆解的原點：浮空的模型從中心炸開；站在展台上的從底部往上、往外拆（不會穿進地板）
  const cy = w.lift > 0 ? (box.min.y + box.max.y) / 2 : box.min.y;
  w.height = (box.max.y - box.min.y) * w.scale;
  root.scale.setScalar(w.scale);
  w.holder.add(root);
  root.traverse((o) => {
    const isSpin = !!(o.name && o.name.startsWith('SPIN'));
    if (o.isLineSegments || o.isLine) { bakeDir(o.geometry, cy, isSpin); o.material = w.lineMat; o.visible = false; o.frustumCulled = false; w.lines.push(o); }
    else if (o.isMesh) {
      bakeDir(o.geometry, cy, isSpin);
      const m = o.material;
      m.vertexColors = false;
      if (m.name === 'jb_glass') m.emissiveIntensity = 0.05;
      if (m.name === 'pod_glass') { m.transparent = true; m.opacity = 0.3; m.depthWrite = false; m.side = THREE.DoubleSide; m.roughness = 0.04; }
      if (!w.origMats.includes(m)) {
        w.origMats.push(m); m.clippingPlanes = w.cAll; inject(m, w, true);
        if (m.emissiveIntensity > 0 && m.emissive && (m.emissive.r + m.emissive.g + m.emissive.b) > 0) w.pulse.push({ m, base: m.emissiveIntensity, name: m.name });
      }
      o.userData.orig = m; o.frustumCulled = false; w.meshes.push(o);
    }
    if (isSpin) { o.userData.base = o.position.clone(); const dv = o.position.clone().sub(new THREE.Vector3(0, cy, 0)); o.userData.dir = dv.multiplyScalar(spread(dv.length())); w.spin.push(o); }
  });
  // 每個網格配一個「替身」：掃描轉場時同時顯示新舊兩種材質
  for (const o of w.meshes) { const t = new THREE.Mesh(o.geometry, w.clayMat); t.visible = false; t.frustumCulled = false; o.add(t); o.userData.twin = t; }
  // 高模雕刻沒有匯出拓撲線 → 用三角網格線框
  if (!w.lines.length) {
    w.cloneMat = inject(new THREE.MeshBasicMaterial({ color: w.lineMat.color, wireframe: true, transparent: true, opacity: 0.32, depthWrite: false, clippingPlanes: w.cAll }), w, false);
    w.meshes.forEach((o) => { const c = new THREE.Mesh(o.geometry, w.cloneMat); c.visible = false; c.frustumCulled = false; o.add(c); w.clones.push(c); });
  }
  root.add(w.fx);
  buildFx(w);
  w.loaded = true;
}

function buildFx(w) {
  const sprite = (x, y, z, s, color) => {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
    sp.position.set(x, y, z); sp.scale.setScalar(s); w.fx.add(sp); return sp;
  };
  if (w.id === 'ship') {
    w.glows = [[0.112, 0.156, -0.392, 0.11], [-0.112, 0.156, -0.392, 0.11], [0.375, 0.1, -0.215, 0.13], [-0.375, 0.1, -0.215, 0.13]]
      .map(([x, y, z, s]) => sprite(x, y, z, s, 0xff7a3a));
  }
  if (w.id === 'pod') {
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.5, 24, 1, true),
      new THREE.MeshBasicMaterial({ color: 0x1fffd2, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    core.position.set(0.032, 0.585, 0); w.fx.add(core);
    w.glows = [sprite(0.032, 0.585, 0, 0.5, 0x1fffd2)];
    const n = 36, pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const a = Math.random() * 6.28, r = Math.random() * 0.085; pos[i * 3] = 0.032 + Math.cos(a) * r; pos[i * 3 + 1] = 0.34 + Math.random() * 0.5; pos[i * 3 + 2] = Math.sin(a) * r; }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    w.bubbles = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.035, color: 0xbffff2, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
    w.fx.add(w.bubbles);
  }
}

/* ------------------------------------------------------------------ display modes + scan transition */
const matFor = (w, o, mode) => (mode === 'shaded' ? o.userData.orig : mode === 'clay' ? w.clayMat : w.darkMat);
const modeMats = (w, mode) => (mode === 'shaded' ? w.origMats : mode === 'clay' ? [w.clayMat] : [w.darkMat, w.lineMat, w.cloneMat].filter(Boolean));
function setClip(w, mode, planes) { for (const m of modeMats(w, mode)) m.clippingPlanes = planes; }
function showWire(w, on) { for (const l of w.lines) l.visible = on; for (const c of w.clones) c.visible = on; }

function instantMode(w, mode) {
  if (!w.loaded) return;
  if (w.scan) { setClip(w, w.scan.from, w.cAll); setClip(w, w.scan.to, w.cAll); w.scan = null; w.scanRing.visible = false; }
  for (const o of w.meshes) { o.material = matFor(w, o, mode); o.userData.twin.visible = false; }
  showWire(w, mode === 'wire');
  w.fx.visible = mode === 'shaded';
  w.mode = mode;
}
function scanTo(w, to) {
  if (!w.loaded || w.mode === to) return;
  if (reduceMotion) { instantMode(w, to); return; }
  if (w.scan) instantMode(w, w.mode);
  const from = w.mode;
  for (const o of w.meshes) { const t = o.userData.twin; t.material = matFor(w, o, to); t.visible = true; }
  setClip(w, from, w.cAbove); setClip(w, to, w.cBelow);
  showWire(w, from === 'wire' || to === 'wire');
  w.fx.visible = false;
  w.scan = { from, to, t: 0 };
  w.mode = to;
  w.scanRing.visible = true;
}
function updateScan(w, dt) {
  const s = w.scan; if (!s) return;
  s.t = Math.min(1, s.t + dt / 0.95);
  const e = s.t * s.t * (3 - 2 * s.t), m = 0.35 + w.uExplode.value * w.scale * 0.7;
  const h = lerp(w.holder.position.y - m, w.holder.position.y + w.height + m, e);
  w.pAbove.constant = -h; w.pBelow.constant = h;
  w.scanRing.position.y = h;
  w.scanRing.scale.setScalar(1 + Math.sin(e * Math.PI) * 0.12 + w.uExplode.value * 0.8);
  if (s.t >= 1) { const to = s.to; instantMode(w, to); }
}

async function loadAll() {
  try { stats = await (await fetch('models/stats.json')).json(); } catch (e) { stats = {}; }
  await Promise.all(works.map((w) => gltfLoader.loadAsync(`models/${w.id}.glb`).then((g) => {
    setupModel(w, g.scene);
    setProgress(++loadedCount / works.length);
  })));
  fillStats();
  buildGallery();
  start();
}

function fillStats() {
  document.querySelectorAll('[data-stats]').forEach((el) => {
    const s = stats[el.dataset.stats]; if (!s) return;
    const rows = [['三角面 TRIS', s.tris], ['頂點 VERTS', s.verts], ['部件 PARTS', s.objects], ['材質 MATERIALS', s.materials]];
    el.innerHTML = rows.map(([k, v]) => `<div><b data-n="${v}">0</b><span>${k}</span></div>`).join('');
  });
}
function countUp(el) {
  el.querySelectorAll('b[data-n]').forEach((b) => {
    const n = +b.dataset.n, t0 = performance.now();
    const tick = (t) => { const u = clamp((t - t0) / 900, 0, 1); b.textContent = Math.round(n * (1 - Math.pow(1 - u, 3))).toLocaleString('en-US'); if (u < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
}

/* ------------------------------------------------------------------ gallery (環形藝廊) */
const galleryGroup = new THREE.Group();
scene.add(galleryGroup);
const galleryMeshes = [];
let hovered = null;
function buildGallery() {
  const R = GALLERY.radius, H = 2.05, gap = 0.32;
  const rows = [{ y: 3.48, w: 0, items: [] }, { y: 1.22, w: 0, items: [] }];
  GALLERY.items.forEach((it) => { const r = rows[0].w <= rows[1].w ? rows[0] : rows[1]; it.pw = H * it.w / it.h; r.items.push(it); r.w += it.pw + gap; });
  const texLoader = new THREE.TextureLoader();
  const load = (name) => { const t = texLoader.load(`img/${name}.jpg`); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
  rows.forEach((r) => {
    let s = -(r.w - gap) / 2;
    r.items.forEach((it) => {
      const a = GYAW0 + (s + it.pw / 2) / R; s += it.pw + gap;
      const g = new THREE.Group();
      g.position.set(GC.x + Math.sin(a) * R, r.y, GC.z - Math.cos(a) * R);
      g.lookAt(GC.x, r.y, GC.z);
      const back = new THREE.Mesh(new THREE.PlaneGeometry(it.pw + 0.1, H + 0.1), new THREE.MeshBasicMaterial({ color: 0x1a1d25 }));
      back.position.z = -0.03; g.add(back);
      it.mat = galleryMaterial((it.alt || [it.src]).map(load));
      const m = new THREE.Mesh(new THREE.PlaneGeometry(it.pw, H, 28, 14), it.mat);
      m.userData.item = it; g.add(m);
      it.group = g; it.hover = 0;
      galleryMeshes.push(m);
      galleryGroup.add(g);
    });
  });
}
const lb = $('#lightbox');
function openLightbox(it) {
  const set = (k) => { $('#lb-img').src = `img/${(it.alt || [it.src])[k]}.jpg`; document.querySelectorAll('#lb-alts button').forEach((b, j) => b.classList.toggle('on', j === k)); };
  $('#lb-title').textContent = it.title; $('#lb-note').textContent = it.note;
  $('#lb-alts').innerHTML = it.alt ? it.altLabel.map((l) => `<button>${l}</button>`).join('') : '';
  document.querySelectorAll('#lb-alts button').forEach((b, k) => b.addEventListener('click', () => set(k)));
  set(0); lb.hidden = false;
}
const closeLightbox = () => { lb.hidden = true; };
$('#lb-close').addEventListener('click', closeLightbox);
lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });

/* ------------------------------------------------------------------ camera choreography */
const _v = new THREE.Vector3(), _a = new THREE.Vector3(), _b = new THREE.Vector3(), _ta = new THREE.Vector3(), _tb = new THREE.Vector3();
let portrait = innerWidth < innerHeight;
function orbitPose(w, az, el, d, f, outPos, outTgt) {
  const dd = d * (portrait ? 1.3 : 1);
  outTgt.set(w.pos[0] + f[0], f[1], w.pos[1] + f[2]);
  outPos.set(Math.sin(az * DEG) * Math.cos(el * DEG), Math.sin(el * DEG), Math.cos(az * DEG) * Math.cos(el * DEG)).multiplyScalar(dd).add(outTgt);
}
function beatPose(b, outPos, outTgt) {
  if (b.kind === 'orbit') orbitPose(WORKS[b.work], b.az, b.el, b.d, b.f, outPos, outTgt);
  else if (b.kind === 'pan') { outPos.copy(GC); outTgt.set(GC.x + Math.sin(b.yaw) * 10, GC.y + Math.sin(b.pitch) * 10, GC.z - Math.cos(b.yaw) * 10); }
  else { outPos.fromArray(b.pos); outTgt.fromArray(b.target); if (portrait) outPos.sub(outTgt).multiplyScalar(1.35).add(outTgt); }
}
const pose = { pos: new THREE.Vector3(), tgt: new THREE.Vector3(), side: 0, explode: 0, warp: 0 };
function computePose(p) {
  const i = clamp(Math.floor(p), 0, N - 1), j = Math.min(i + 1, N - 1), u = clamp(p - i, 0, 1), e = smooth(u);
  const A = beats[i], B = beats[j];
  pose.warp = 0; pose.explode = 0;
  if (A.kind === 'orbit' && B.kind === 'orbit' && A.work === B.work) {
    const f = [lerp(A.f[0], B.f[0], e), lerp(A.f[1], B.f[1], e), lerp(A.f[2], B.f[2], e)];
    orbitPose(WORKS[A.work], lerp(A.az, B.az, e), lerp(A.el, B.el, e), lerp(A.d, B.d, e), f, pose.pos, pose.tgt);
    pose.explode = lerp(A.x || 0, B.x || 0, e);
  } else if (A.kind === 'pan' && B.kind === 'pan') {
    const yaw = lerp(A.yaw, B.yaw, e), pitch = lerp(A.pitch, B.pitch, e);
    pose.pos.copy(GC); pose.tgt.set(GC.x + Math.sin(yaw) * 10, GC.y + Math.sin(pitch) * 10, GC.z - Math.cos(yaw) * 10);
  } else {
    beatPose(A, _a, _ta); beatPose(B, _b, _tb);
    pose.pos.lerpVectors(_a, _b, e);
    pose.pos.y += Math.sin(Math.PI * e) * Math.min(5, _a.distanceTo(_b) * 0.1);
    pose.tgt.lerpVectors(_ta, _tb, smooth(clamp(u * 1.35, 0, 1)));
    pose.warp = Math.pow(Math.sin(Math.PI * u), 1.3);          // 作品之間的飛行段 → 扭曲轉場
    pose.explode = (u < 0.5 ? (A.x || 0) : (B.x || 0)) * Math.abs(1 - 2 * u) * (i === j ? 1 : 1);
    if (i === j) pose.explode = A.x || 0;
  }
  pose.side = lerp(A.side, B.side, e);
  pose.pos.y = Math.max(pose.pos.y, 0.45);
}

/* ------------------------------------------------------------------ interaction */
let userMode = 'auto', userExplode = false, glitch = 0;
const modeBtns = [...document.querySelectorAll('#modes button[data-mode]')];
function setUserMode(m) { userMode = m; glitch = Math.max(glitch, 0.5); modeBtns.forEach((b) => b.classList.toggle('on', b.dataset.mode === m)); }
modeBtns.forEach((b) => b.addEventListener('click', () => setUserMode(b.dataset.mode)));
const explodeBtn = $('#explode');
function toggleExplode() { userExplode = !userExplode; explodeBtn.classList.toggle('on', userExplode); }
explodeBtn.addEventListener('click', toggleExplode);

const mouse = new THREE.Vector2(), mouseS = new THREE.Vector2(), mouseUv = new THREE.Vector2(0.5, 0.5);
const ndc = new THREE.Vector2();
let drag = null, activeWork = works[0], curBeat = beats[0], inGallery = false, overCanvas = false, mouseSpeed = 0;
const ray = new THREE.Raycaster();
function pickGallery(e) {
  ndc.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(galleryMeshes, false)[0];
  return hit ? hit.object.userData.item : null;
}
canvas.addEventListener('pointerdown', (e) => {
  drag = { x: e.clientX, x0: e.clientX, y0: e.clientY, moved: false };
  try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events */ }
  if (!inGallery) canvas.classList.add('dragging');
});
addEventListener('pointermove', (e) => {
  const nx = e.clientX / innerWidth, ny = e.clientY / innerHeight;
  mouseSpeed = Math.min(1, mouseSpeed + Math.hypot(nx - mouseUv.x, ny - (1 - mouseUv.y)) * 9);
  mouseUv.set(nx, 1 - ny);
  mouse.set(nx * 2 - 1, ny * 2 - 1);
  overCanvas = e.target === canvas;
  if (drag) {
    const dx = e.clientX - drag.x; drag.x = e.clientX;
    if (Math.abs(e.clientX - drag.x0) + Math.abs(e.clientY - drag.y0) > 5) drag.moved = true;
    if (!inGallery && curBeat.kind === 'orbit') { activeWork.yawVel = dx * 0.0085; activeWork.userYaw += activeWork.yawVel; $('#hint').style.opacity = 0.35; }
  } else if (inGallery && overCanvas) {
    hovered = pickGallery(e); canvas.classList.toggle('pointing', !!hovered);
  }
});
const endDrag = (e) => {
  if (!drag) return;
  if (!drag.moved && inGallery) { const it = pickGallery(e); if (it) openLightbox(it); }
  drag = null; canvas.classList.remove('dragging');
};
canvas.addEventListener('pointerup', endDrag);
canvas.addEventListener('pointercancel', endDrag);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
  const k = { 1: 'auto', 2: 'shaded', 3: 'clay', 4: 'wire' }[e.key]; if (k) setUserMode(k);
  if (e.key === '5' || e.key === 'x' || e.key === 'X') toggleExplode();
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') jump(clamp(Math.round(scrollY / unit) + (e.key === 'ArrowRight' ? 1 : -1), 0, N - 1));
});

function resize() {
  portrait = innerWidth < innerHeight;
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(dpr); renderer.setSize(innerWidth, innerHeight, false);
  composer.setPixelRatio(dpr); composer.setSize(innerWidth, innerHeight);
  WU.uAspect.value = innerWidth / innerHeight;
  layoutScroll();
}
addEventListener('resize', resize);

/* ------------------------------------------------------------------ main loop */
const clock = new THREE.Clock();
let p = 0, pPrev = 0, vel = 0, warpS = 0, started = false, intro = 0, lastBeatIdx = -1, frames = 0, acc = 0, lastChapter = null, lastActive = null;
const root = document.documentElement;
const hud = $('#hud'), hudNo = $('#hud-no'), hudTitle = $('#hud-title');
$('#hud-total').textContent = String(works.length).padStart(2, '0');
const camPos = new THREE.Vector3(), camTgt = new THREE.Vector3();
const rimTarget = new THREE.Vector3(), fillTarget = new THREE.Vector3(), accentNow = new THREE.Color(WORKS[0].accent);

function start() {
  started = true;
  $('#loader').classList.add('done');
  document.body.classList.add('ready');
  resize();
}

function updatePanels() {
  const sk = +clamp(-vel * 1.6, -4, 4).toFixed(1);
  for (let i = 0; i < N; i++) {
    const pn = panels[i]; if (!pn) continue;
    const d = Math.abs(p - i);
    const o = +(1 - sstep(0.2, 0.47, d)).toFixed(3) * (intro > 0.55 ? 1 : 0);
    if (o !== pn.o) {
      if (o > 0 && pn.o <= 0) pn.el.style.visibility = 'visible';
      if (o <= 0) pn.el.style.visibility = 'hidden';
      pn.el.style.opacity = o; pn.o = o;
    }
    const on = o > 0.45;
    if (on !== pn.on) {
      pn.on = on; pn.el.classList.toggle('in', on);
      if (on) { pn.scr.forEach(scramble); if (pn.el.querySelector('.stats')) countUp(pn.el); }
    }
    if (o > 0) {
      const y = Math.round((i - p) * 110);
      if (y !== pn.y || sk !== pn.sk) { pn.el.style.transform = `translate3d(0,${y}px,0) skewY(${sk}deg)`; pn.y = y; pn.sk = sk; }
    }
  }
}

function frame() {
  requestAnimationFrame(frame);
  step(Math.min(clock.getDelta(), 0.05));
}
function step(dt) {
  const t = clock.elapsedTime;
  timeU.value = t;
  if (!started) { renderer.render(scene, camera); return; }
  intro = Math.min(1, intro + dt / 2.8);
  const ie = 1 - Math.pow(1 - intro, 3);

  const target = clamp(scrollY / unit, 0, N - 1);
  p += (target - p) * (1 - Math.exp(-dt * (reduceMotion ? 30 : 4.2)));
  vel = lerp(vel, (p - pPrev) / Math.max(dt, 1e-3), 1 - Math.exp(-dt * 9)); pPrev = p;
  const uVel = reduceMotion ? 0 : clamp(vel * 0.3, -1, 1);
  const bi = clamp(Math.round(p), 0, N - 1);
  curBeat = beats[bi];
  const finale = curBeat.kind === 'free';
  inGallery = curBeat.kind === 'pan';
  if (curBeat.kind === 'orbit') activeWork = works[curBeat.work];

  if (bi !== lastBeatIdx) {
    lastBeatIdx = bi;
    root.style.setProperty('--accent', curBeat.kind === 'orbit' ? activeWork.accent : '#ecebe6');
    hudNo.textContent = activeWork.no; hudTitle.textContent = activeWork.title;
    hud.classList.toggle('hide', curBeat.kind !== 'orbit');
    marquee.set(`${activeWork.no} ${activeWork.en} — ${activeWork.title} — `);
    if (!inGallery) { hovered = null; canvas.classList.remove('pointing'); }
    if (curBeat.chapter !== lastChapter) { lastChapter = curBeat.chapter; chapters.forEach((c) => c.btn.classList.toggle('on', c.id === lastChapter)); }
  }

  // camera
  computePose(p);
  if (intro < 1) { _v.copy(pose.pos).sub(pose.tgt).applyAxisAngle(THREE.Object3D.DEFAULT_UP, (1 - ie) * -1.1).multiplyScalar(1 + (1 - ie) * 1.1); pose.pos.copy(pose.tgt).add(_v); }
  const warpT = reduceMotion ? 0 : pose.warp * (0.4 + 0.6 * clamp(Math.abs(vel) * 0.9, 0, 1)) + (1 - ie) * 0.9;
  warpS = lerp(warpS, warpT, 1 - Math.exp(-dt * 7));
  mouseS.lerp(mouse, 1 - Math.exp(-dt * 3));
  camPos.copy(pose.pos); camTgt.copy(pose.tgt);
  camera.position.copy(camPos); camera.lookAt(camTgt);
  if (!reduceMotion) {
    const dist = camPos.distanceTo(camTgt), k = inGallery ? 0.012 : 0.035;
    camera.translateX(mouseS.x * dist * k); camera.translateY(-mouseS.y * dist * k * 0.6);
    camera.translateY(Math.sin(t * 0.7) * dist * 0.004);
    camera.lookAt(camTgt);
    camera.rotateZ(-uVel * 0.035 + warpS * 0.05 * Math.sign(vel || 1));   // 飛行時微微側傾
  }
  camera.fov = (portrait ? 50 : 36) + warpS * 17 + Math.abs(uVel) * 5;      // FOV 衝刺
  const W = innerWidth, H = innerHeight;
  if (W > 820) camera.setViewOffset(W, H, -pose.side * W * 0.17, 0, W, H);
  else camera.setViewOffset(W, H, 0, Math.abs(pose.side) * H * 0.13, W, H);

  // post fx
  glitch = Math.max(0, glitch - dt * 2.6);
  mouseSpeed = Math.max(0, mouseSpeed - dt * 2.2);
  WU.uVel.value = uVel; WU.uWarp.value = warpS; WU.uGlitch.value = reduceMotion ? 0 : glitch; WU.uTime.value = t;
  WU.uMouse.value.copy(mouseUv); WU.uMouseV.value = reduceMotion ? 0 : mouseSpeed;

  // lights + ground follow the active stage
  const sp = activeWork.stage.position, r = activeWork.pad;
  rimTarget.set(sp.x - r * 1.5, activeWork.baseY + r * 1.4 + 1, sp.z - r * 1.9);
  fillTarget.set(sp.x + r * 1.6, activeWork.baseY + r * 0.6 + 0.5, sp.z + r * 2.2);
  const lk = 1 - Math.exp(-dt * 3);
  rim.position.lerp(rimTarget, lk); fill.position.lerp(fillTarget, lk);
  accentNow.lerp(activeWork.accentColor, lk); rim.color.copy(accentNow);
  rim.intensity = (finale ? 0 : 22) * r * r + 18; fill.intensity = 4.5 * r * r;
  key.target.position.copy(camTgt); key.position.copy(camTgt).add(_v.set(7, 11, 9));
  scene.fog.density = lerp(scene.fog.density, finale ? 0.0035 : 0.0105, lk);
  groundMat.uniforms.uCam.value.copy(camera.position);
  groundMat.uniforms.uPos.value.set(sp.x, sp.z);
  groundMat.uniforms.uColor.value.copy(accentNow);
  groundMat.uniforms.uTime.value = t;
  sky.position.copy(camera.position);
  sky.material.uniforms.uColor.value.copy(accentNow); sky.material.uniforms.uTime.value = t;
  stars.position.copy(camera.position).setY(0);
  dust.rotation.y = Math.sin(t * 0.05) * 0.02; dust.position.y = Math.sin(t * 0.2) * 0.3;

  // 抵達新作品：先以線框（或上色）出現，再掃描成目標模式
  const orbiting = curBeat.kind === 'orbit';
  const activeNow = orbiting ? activeWork : null;
  if (activeNow !== lastActive) {
    if (activeNow && activeNow.loaded) {
      const want = userMode === 'auto' ? curBeat.mode : userMode;
      instantMode(activeNow, want === 'wire' ? 'shaded' : 'wire');
      activeNow.wobble = 1; glitch = Math.max(glitch, intro < 1 ? 0 : 0.45);
    }
    lastActive = activeNow;
  }

  // works
  for (const w of works) {
    const isActive = w === activeNow;
    const near = finale || isActive || w.stage.position.distanceTo(camera.position) < 44;
    w.holder.visible = near && w.loaded;
    w.amp = lerp(w.amp, isActive ? 1 : finale ? 5 : 0.3, lk);
    w.beamMat.uniforms.uAmp.value = w.amp;
    if (!w.loaded) continue;
    if (isActive) { if (intro > 0.25) scanTo(w, userMode === 'auto' ? curBeat.mode : userMode); }
    else if (w.mode !== 'shaded' || w.scan) instantMode(w, 'shaded');
    // 爆炸拆解
    const ex = isActive ? Math.max(pose.explode, userExplode ? 1 : 0) : 0;
    w.explodeT = lerp(w.explodeT, ex, 1 - Math.exp(-dt * 5));
    w.uExplode.value = w.explodeT * w.explode;
    w.wobble = Math.max(0, w.wobble - dt * 1.1);
    w.uWobble.value = w.wobble * w.wobble;
    updateScan(w, dt);
    // drag rotation with inertia; eases back when leaving
    if (isActive) { if (!drag) { w.userYaw += w.yawVel; w.yawVel *= 0.94; } }
    else { w.yawVel = 0; w.userYaw = lerp(w.userYaw, Math.round(w.userYaw / (Math.PI * 2)) * Math.PI * 2, lk); }
    w.holder.rotation.y = w.yaw + w.userYaw;
    if (!near) continue;
    w.holder.scale.setScalar(1 - w.uWobble.value * 0.07);
    if (w.lift > 0) { w.holder.position.y = w.baseY + Math.sin(t * 0.8 + w.i) * 0.09; w.holder.rotation.z = Math.sin(t * 0.5 + w.i) * 0.012; }
    for (const s of w.spin) { s.rotation.z += dt * 13; s.position.copy(s.userData.base).addScaledVector(s.userData.dir, w.uExplode.value); }
    for (const pm of w.pulse) {
      let k = 1;
      if (pm.name === 'arc_screen') k = 0.85 + 0.15 * Math.sin(t * 40) * Math.sin(t * 3.1) + 0.1 * Math.sin(t * 1.3);
      else if (pm.name === 'emit_red') k = 0.55 + 0.45 * (0.5 + 0.5 * Math.sin(t * 5));
      else if (pm.name === 'jb_tube') { k = 0.9 + 0.1 * Math.sin(t * 2); pm.m.emissive.setHSL(0.06 + 0.05 * Math.sin(t * 0.6), 1, 0.55); }
      else if (pm.name === 'ch_lens') k = 0.8 + 0.2 * Math.sin(t * 1.7);
      pm.m.emissiveIntensity = pm.base * k;
    }
    if (w.glows) for (let g = 0; g < w.glows.length; g++) w.glows[g].material.opacity = 0.75 + 0.25 * Math.sin(t * 9 + g * 1.7);
    if (w.bubbles) {
      const a = w.bubbles.geometry.attributes.position;
      for (let k = 0; k < a.count; k++) { let y = a.getY(k) + dt * (0.04 + (k % 5) * 0.012); if (y > 0.84) y = 0.34; a.setY(k, y); }
      a.needsUpdate = true;
    }
  }

  // gallery：隨轉動速度彎曲、hover 漣漪、晨昏夜切換
  galleryGroup.visible = finale || GC.distanceTo(camera.position) < 60;
  if (galleryGroup.visible) {
    const gv = inGallery ? clamp(vel * 0.42, -0.9, 0.9) : 0;
    for (const it of GALLERY.items) {
      if (!it.group) continue;
      it.hover = lerp(it.hover, hovered === it ? 1 : 0, 1 - Math.exp(-dt * 7));
      const U = it.mat.uniforms;
      U.uVel.value = lerp(U.uVel.value, gv, 1 - Math.exp(-dt * 6)); U.uHover.value = it.hover; U.uTime.value = t;
      U.uDim.value = lerp(U.uDim.value, hovered && hovered !== it ? 0.45 : 0.9 + it.hover * 0.15, 0.12);
      if (it.alt) {
        const ph = (t / 3.5) % 3, k = Math.floor(ph), f = sstep(0.7, 1, ph - k);
        U.uMix.value.set(k === 0 ? 1 - f : k === 2 ? f : 0, k === 0 ? f : k === 1 ? 1 - f : 0, k === 1 ? f : k === 2 ? 1 - f : 0);
      }
    }
  }

  // DOM fx
  updatePanels();
  marquee.update(p * W * 0.85 + t * 26, clamp(-vel * 9, -20, 20), orbiting && p > 0.6 ? 0.07 + warpS * 0.55 + Math.abs(uVel) * 0.12 : 0);
  if (progressEl) progressEl.style.transform = `scaleX(${(p / (N - 1)).toFixed(4)})`;
  if (cursor.enabled) {
    if (!overCanvas || !lb.hidden) cursor.set('');
    else if (inGallery) cursor.set(hovered ? 'zoom' : 'look', hovered ? '放大' : '');
    else if (orbiting) cursor.set(drag ? 'grab' : 'drag', drag ? '' : '拖曳');
    else cursor.set('');
    cursor.update(dt);
  }

  composer.render(dt);

  // adaptive quality
  acc += dt; frames++;
  if (frames >= 80) {
    const ms = (acc / frames) * 1000; acc = 0; frames = 0;
    if (intro >= 1 && !document.hidden) {
      if (ms > 30 && dpr > 1) { dpr = Math.max(1, dpr - 0.25); resize(); }
      else if (ms > 38 && bloom.enabled) { bloom.enabled = false; }
    }
  }
}

// 開發用：網址加上 ?debug 才會開啟。snap(b) 直接跳到第 b 拍並輸出目前 3D 畫面
function snap(b, n = 30, mode, opts = {}) {
  scrollTo(0, b * unit); p = b; pPrev = b; vel = opts.vel || 0; intro = 1; if (mode) setUserMode(mode);
  for (let i = 0; i < n; i++) { if (opts.vel) { vel = opts.vel; pPrev = p - opts.vel * 0.05; } if (opts.hold) glitch = opts.hold; step(0.05); }
  return canvas.toDataURL('image/jpeg', 0.82);
}
if (new URLSearchParams(location.search).has('debug')) window.__site = { beats, works, jump, camera, scene, renderer, pose, snap, step, WU,
  setP(v) { p = v; pPrev = v; scrollTo(0, v * unit); }, setQuality(b, d) { bloom.enabled = b; if (d) { dpr = d; resize(); } },
  get p() { return p; }, get fps() { return frames ? 1 / (acc / frames) : 0; }, get quality() { return { dpr, bloom: bloom.enabled }; } };
frame();
loadAll().catch((e) => { console.error(e); $('#loader-text').textContent = '載入失敗，請重新整理頁面'; });
