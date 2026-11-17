// 拓撲檢視器：只在按下「檢查拓撲」後才載入（three.js 由 work.html 的 importmap 指到 CDN）。
// 模型：models/<id>.glb（Draco 壓縮、最長邊 = 1、底部在 y = 0）
//   *_WIRE 線段 = 模型真實的多邊形邊（四邊面拓撲）
//   COLOR_0 = 每個頂點所屬部件的中心（r-0.5, b, -(g-0.5) → x, y, z），用來做拆解圖
// 只提供「線框」（深色隱藏線本體＋拓撲線）與「白模」兩種顯示。
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const DRACO_PATH = 'https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/';
const EXPLODE_GAIN = 1.2;                          // 拆解幅度：拉到底零件要分得開，但不能小到看不清
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}

// 頂點色（部件中心）→ 拆解位移方向 aDir；zero = 自己用 position 移動的節點（SPIN*）
function bakeDir(geo, cy, zero) {
  const col = geo.getAttribute('color');
  const n = geo.getAttribute('position').count, a = new Float32Array(n * 3);
  if (col && !zero) for (let k = 0; k < n; k++) {
    a[k * 3] = col.getX(k) - 0.5;
    a[k * 3 + 1] = col.getZ(k) - cy;
    a[k * 3 + 2] = -(col.getY(k) - 0.5);
  }
  geo.setAttribute('aDir', new THREE.BufferAttribute(a, 3));
  if (col) geo.deleteAttribute('color');
}

export async function createViewer(host, { url, accent = '#ffffff', explode = 0, flying = false, wireOpacity = 0.85, onProgress } = {}) {
  if (!webglOK()) throw new Error('webgl');

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.domElement.setAttribute('aria-label', '可旋轉的 3D 模型');

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x141414);
  const camera = new THREE.PerspectiveCamera(30, 16 / 9, 0.01, 60);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x1c1c1c, 1.0));
  const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(2.5, 4, 3); scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.45); fill.position.set(-3, 1.2, 2); scene.add(fill);
  const rim = new THREE.DirectionalLight(new THREE.Color(accent), 1.6); rim.position.set(-1.5, 2.2, -3.5); scene.add(rim);

  // 拆解位移注入所有材質的頂點著色器
  const uExplode = { value: 0 };
  const inject = (mat) => {
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uExplode = uExplode;
      sh.vertexShader = 'attribute vec3 aDir;\nuniform float uExplode;\n' +
        sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  transformed += aDir * uExplode;');
    };
    mat.customProgramCacheKey = () => 'explode';
    return mat;
  };
  const lineCol = new THREE.Color(accent).lerp(new THREE.Color(0xffffff), 0.35);
  const clayMat = inject(new THREE.MeshStandardMaterial({ color: 0xcdc8c0, roughness: 0.62, metalness: 0 }));
  const darkMat = inject(new THREE.MeshStandardMaterial({ color: 0x0d0d0e, roughness: 0.75, metalness: 0.1,
    polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2 }));
  const lineMat = inject(new THREE.LineBasicMaterial({ color: lineCol, transparent: true, opacity: wireOpacity, depthWrite: false, toneMapped: false }));
  const triMat = inject(new THREE.MeshBasicMaterial({ color: lineCol, wireframe: true, transparent: true, opacity: 0.22, depthWrite: false, toneMapped: false }));

  // 載入模型
  const draco = new DRACOLoader(); draco.setDecoderPath(DRACO_PATH);
  const loader = new GLTFLoader(); loader.setDRACOLoader(draco);
  let gltf;
  try {
    gltf = await loader.loadAsync(url, (e) => onProgress?.(e.total ? e.loaded / e.total : 0));
  } finally { draco.dispose(); }
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  const cy = flying ? (box.min.y + box.max.y) / 2 : box.min.y;    // 飛行器從中心拆開，落地的從底部往外拆

  const meshes = [], lines = [], clones = [], spin = [];
  root.traverse((o) => {
    const isSpin = !!(o.name && o.name.startsWith('SPIN'));
    if (o.isLineSegments || o.isLine) {
      bakeDir(o.geometry, cy, isSpin); o.material = lineMat; o.frustumCulled = false; lines.push(o);
    } else if (o.isMesh) {
      bakeDir(o.geometry, cy, isSpin); o.material = darkMat; o.frustumCulled = false; meshes.push(o);
    }
    if (isSpin) {
      o.userData.base = o.position.clone();
      o.userData.dir = o.position.clone().sub(new THREE.Vector3(0, cy, 0));
      spin.push(o);
    }
  });
  // 高模雕刻沒有匯出拓撲線 → 以三角網格線框代替
  if (!lines.length) for (const o of meshes) {
    const c = new THREE.Mesh(o.geometry, triMat); c.frustumCulled = false; o.add(c); clones.push(c);
  }
  scene.add(root);

  // 鏡頭：依模型繞垂直軸轉一圈時的實際範圍取景（用外接球的話，扁平的模型在畫面裡會太小）
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const center = sphere.center.clone(), R = sphere.radius;
  const size = box.getSize(new THREE.Vector3());
  const az = THREE.MathUtils.degToRad(35), el = THREE.MathUtils.degToRad(16);
  const rH = 0.5 * Math.hypot(size.x, size.z);                     // 轉一圈時水平方向的最大半徑
  const halfV = 0.5 * size.y * Math.cos(el) + rH * Math.sin(el);   // 俯角下畫面上的半高
  const fitDist = () => {
    const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)), th = tv * camera.aspect;
    return Math.max(halfV / tv, rH / th) * 1.12 + rH * 0.6;        // + rH * 0.6：靠近鏡頭的那一側透視會放大
  };
  let baseDist = fitDist();
  const homeDir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el));
  camera.near = R / 50; camera.far = R * 60; camera.updateProjectionMatrix();

  host.appendChild(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.8; controls.enablePan = false;
  controls.minDistance = R * 0.35; controls.maxDistance = R * 14;
  controls.autoRotate = !reduced; controls.autoRotateSpeed = 0.7;
  let touched = false;
  controls.addEventListener('start', () => { controls.autoRotate = false; touched = true; });

  let zoomK = 1;                                   // 拆開時鏡頭跟著退一點（保留使用者的縮放比例）
  const reset = () => {
    camera.position.copy(center).addScaledVector(homeDir, baseDist * zoomK);
    controls.target.copy(center); controls.update(); dirty = true;
  };

  // 尺寸
  const resize = () => {
    const w = host.clientWidth || 1, h = host.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    baseDist = fitDist();
    if (!touched) {                                 // 還沒被拖過：方向不變，只依新的長寬比重算距離
      const off = camera.position.clone().sub(controls.target);
      if (off.lengthSq() > 1e-9) camera.position.copy(controls.target).addScaledVector(off.normalize(), baseDist * zoomK);
    }
    dirty = true;
  };
  const ro = new ResizeObserver(resize); ro.observe(host);

  // 顯示模式
  let mode = 'wire';
  const setMode = (m) => {
    mode = m === 'clay' ? 'clay' : 'wire';
    for (const o of meshes) o.material = mode === 'clay' ? clayMat : darkMat;
    for (const l of lines) l.visible = mode === 'wire';
    for (const c of clones) c.visible = mode === 'wire';
    dirty = true;
  };

  // 拆解
  let exTarget = 0, exNow = 0;
  const setExplode = (v) => { exTarget = Math.max(0, Math.min(1, v)); };

  // 只在看得到的時候算圖；畫面沒變就不重畫
  let dirty = true, visible = true, raf = 0, last = performance.now();
  const vio = new IntersectionObserver((es) => { visible = es.some((e) => e.isIntersecting); }, { threshold: 0 });
  vio.observe(host);
  controls.addEventListener('change', () => { dirty = true; });
  const tick = (t) => {
    raf = requestAnimationFrame(tick);
    const dt = Math.min(0.05, (t - last) / 1000); last = t;
    if (!visible || document.hidden) return;
    if (Math.abs(exTarget - exNow) > 1e-4) {
      exNow += (exTarget - exNow) * (reduced ? 1 : 1 - Math.exp(-dt * 8));
      if (Math.abs(exTarget - exNow) <= 1e-4) exNow = exTarget;
      uExplode.value = exNow * explode * EXPLODE_GAIN;
      for (const s of spin) s.position.copy(s.userData.base).addScaledVector(s.userData.dir, uExplode.value);
      const k = 1 + exNow * explode * EXPLODE_GAIN * 0.6;
      const off = camera.position.clone().sub(controls.target);
      camera.position.copy(controls.target).addScaledVector(off, k / zoomK);
      zoomK = k;
      dirty = true;
    }
    controls.update();
    if (dirty || controls.autoRotate) { renderer.render(scene, camera); dirty = false; }
  };

  setMode('wire');
  resize();
  reset();
  raf = requestAnimationFrame(tick);

  return {
    setMode, setExplode, reset,
    get mode() { return mode; },
    dispose() {
      cancelAnimationFrame(raf); ro.disconnect(); vio.disconnect(); controls.dispose();
      root.traverse((o) => { o.geometry?.dispose?.(); });
      [clayMat, darkMat, lineMat, triMat].forEach((m) => m.dispose());
      renderer.dispose(); renderer.domElement.remove();
    },
  };
}
