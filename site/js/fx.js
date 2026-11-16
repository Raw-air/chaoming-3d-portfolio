// 特效模組：後製扭曲、天空、藝廊扭曲材質、游標、跑馬燈大字、文字動態
import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

/* ---------------------------------------------------------------- 後製：鏡頭扭曲 / 色散 / 放射殘影 / 故障切片 / 顆粒 */
export function createWarpPass() {
  return new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uVel: { value: 0 }, uWarp: { value: 0 }, uGlitch: { value: 0 }, uTime: { value: 0 }, uAspect: { value: 1 }, uGrain: { value: 0.02 }, uMouse: { value: new THREE.Vector2(0.5, 0.5) }, uMouseV: { value: 0 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      uniform sampler2D tDiffuse; uniform float uVel, uWarp, uGlitch, uTime, uAspect, uGrain, uMouseV; uniform vec2 uMouse; varying vec2 vUv;
      float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      void main(){
        vec2 uv = vUv;
        if (uGlitch > 0.002) {
          float band = floor(uv.y * 26.0 + uTime * 11.0);
          float h = hash(vec2(band, floor(uTime * 22.0)));
          uv.x += (h - 0.5) * 0.11 * uGlitch * step(0.5, h);
        }
        vec2 dir = uv - 0.5;
        vec2 c = dir; c.x *= uAspect;
        float r2 = dot(c, c), r = sqrt(r2);
        float k = uWarp * 0.5 + abs(uVel) * 0.12;
        vec2 d = dir * (1.0 - k * r2 * 0.85);          // 邊緣往內拉 → 魚眼拉伸
        d.y += uVel * 0.045 * r2;                      // 捲動方向的拖曳
        vec2 m = uv - uMouse; m.x *= uAspect; float md = length(m);                  // 滑鼠移動時的水波扭曲
        d += (m / max(md, 1e-3)) * sin(md * 42.0 - uTime * 9.0) * exp(-md * 6.5) * uMouseV * 0.011;
        float ca = (0.0012 + abs(uVel) * 0.011 + uWarp * 0.022 + uGlitch * 0.01) * (0.25 + r * 1.9);
        vec3 col;
        if (uWarp > 0.02) {
          vec3 acc = vec3(0.0); float tot = 0.0;
          for (int i = 0; i < 8; i++) {
            float t = float(i) / 7.0, s = 1.0 - t * uWarp * 0.17, w = 1.0 - t * 0.65;
            vec2 p = 0.5 + d * s;
            acc += vec3(texture2D(tDiffuse, p + dir * ca).r, texture2D(tDiffuse, p).g, texture2D(tDiffuse, p - dir * ca).b) * w; tot += w;
          }
          col = acc / tot + uWarp * uWarp * 0.012;
        } else {
          vec2 p = 0.5 + d;
          col = vec3(texture2D(tDiffuse, p + dir * ca).r, texture2D(tDiffuse, p).g, texture2D(tDiffuse, p - dir * ca).b);
        }
        col += (hash(uv * vec2(1733.0, 977.0) + fract(uTime) * 71.3) - 0.5) * uGrain;
        col *= 1.0 - smoothstep(0.38, 1.05, r) * (0.3 + uWarp * 0.35);
        gl_FragColor = vec4(max(col, 0.0), 1.0);
      }`,
  });
}

/* ---------------------------------------------------------------- 天空：隨作品主色流動的星雲 */
export function createSky(bg) {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { uColor: { value: new THREE.Color('#ff6a3d') }, uBg: { value: new THREE.Color(bg) }, uTime: { value: 0 } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `
      varying vec3 vDir; uniform vec3 uColor, uBg; uniform float uTime;
      float h3(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float n3(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1,0,0)), f.x), mix(h3(i + vec3(0,1,0)), h3(i + vec3(1,1,0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0,0,1)), h3(i + vec3(1,0,1)), f.x), mix(h3(i + vec3(0,1,1)), h3(i + vec3(1,1,1)), f.x), f.y), f.z); }
      float fbm(vec3 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++){ s += a * n3(p); p = p * 2.03 + 7.1; a *= 0.5; } return s; }
      void main(){
        vec3 d = normalize(vDir);
        float n = fbm(d * 2.6 + vec3(uTime * 0.012, 0.0, uTime * 0.008));
        float n2 = fbm(d * 5.2 - vec3(0.0, uTime * 0.01, 0.0));
        float cloud = smoothstep(0.42, 0.8, n) * (0.35 + 0.65 * n2);
        float horizon = exp(-abs(d.y) * 6.5);
        vec3 col = uBg + uColor * (cloud * 0.05 * smoothstep(0.0, 0.4, d.y) + horizon * 0.03) + vec3(0.012, 0.018, 0.035) * horizon;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const m = new THREE.Mesh(new THREE.SphereGeometry(480, 32, 20), mat);
  m.renderOrder = -10; m.frustumCulled = false;
  return m;
}

/* ---------------------------------------------------------------- 藝廊：隨轉動速度彎曲、hover 漣漪、色散的圖片材質 */
export function galleryMaterial(maps) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uMap0: { value: maps[0] }, uMap1: { value: maps[1] || maps[0] }, uMap2: { value: maps[2] || maps[0] },
      uMix: { value: new THREE.Vector3(1, 0, 0) }, uVel: { value: 0 }, uHover: { value: 0 }, uTime: { value: 0 }, uDim: { value: 0.9 },
    },
    vertexShader: `
      varying vec2 vUv; uniform float uVel, uHover, uTime;
      void main(){
        vUv = uv; vec3 p = position;
        float bend = sin(uv.x * 3.14159);
        p.z += bend * uVel * 1.1 + (uv.x - 0.5) * uVel * 0.5;
        p.y *= 1.0 + abs(uVel) * 0.1 * bend;
        float dd = distance(uv, vec2(0.5));
        p.z += sin(dd * 20.0 - uTime * 5.0) * 0.04 * uHover * (1.0 - dd) + uHover * 0.18;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
      }`,
    fragmentShader: `
      varying vec2 vUv; uniform sampler2D uMap0, uMap1, uMap2; uniform vec3 uMix; uniform float uVel, uHover, uTime, uDim;
      vec3 S(vec2 uv){ return texture2D(uMap0, uv).rgb * uMix.x + texture2D(uMap1, uv).rgb * uMix.y + texture2D(uMap2, uv).rgb * uMix.z; }
      void main(){
        vec2 uv = (vUv - 0.5) * (1.0 - uHover * 0.05) + 0.5;
        float dd = distance(vUv, vec2(0.5));
        uv += normalize(vUv - 0.5 + 1e-4) * sin(dd * 20.0 - uTime * 5.0) * 0.004 * uHover;
        float sh = uVel * 0.035;
        vec3 col = vec3(S(uv + vec2(sh, 0.0)).r, S(uv).g, S(uv - vec2(sh, 0.0)).b) * uDim;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

/* ---------------------------------------------------------------- 文字：逐字進場、解碼亂碼 */
export function splitText(el) {
  let i = 0;
  const walk = (node) => {
    [...node.childNodes].forEach((n) => {
      if (n.nodeType === 3) {
        const frag = document.createDocumentFragment();
        [...n.textContent].forEach((ch) => {
          if (ch === ' ') { frag.appendChild(document.createTextNode(' ')); return; }
          const s = document.createElement('span'); s.className = 'ch'; s.style.setProperty('--i', i++); s.textContent = ch; frag.appendChild(s);
        });
        n.replaceWith(frag);
      } else if (n.nodeType === 1 && n.tagName !== 'BR') walk(n);
    });
  };
  walk(el); el.classList.add('split');
}
const GLYPHS = '▚▞▙▟░▒#/\\<>01+×';
export function scramble(el) {
  const final = el.dataset.text || (el.dataset.text = el.textContent);
  const t0 = performance.now(), dur = 520 + final.length * 14;
  const tick = (t) => {
    const u = Math.min(1, (t - t0) / dur), n = Math.floor(u * final.length);
    let out = final.slice(0, n);
    for (let k = n; k < final.length; k++) out += final[k] === ' ' ? ' ' : GLYPHS[(Math.random() * GLYPHS.length) | 0];
    el.textContent = out;
    if (u < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ---------------------------------------------------------------- 游標 */
export function createCursor() {
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const el = document.createElement('div'); el.id = 'cursor'; el.innerHTML = '<i></i><span></span>';
  if (!fine) return { update() {}, set() {}, enabled: false };
  document.body.appendChild(el); document.body.classList.add('has-cursor');
  const label = el.querySelector('span');
  let x = innerWidth / 2, y = innerHeight / 2, tx = x, ty = y, state = '';
  addEventListener('pointermove', (e) => { tx = e.clientX; ty = e.clientY; el.classList.add('live'); }, { passive: true });
  document.addEventListener('pointerleave', () => el.classList.remove('live'));
  document.addEventListener('pointerover', (e) => el.classList.toggle('link', !!e.target.closest('a, button')));
  return {
    enabled: true,
    set(s, text) { if (s === state) return; state = s; el.dataset.state = s; label.textContent = text || ''; },
    update(dt) { const k = 1 - Math.exp(-dt * 16); x += (tx - x) * k; y += (ty - y) * k; el.style.transform = `translate3d(${x}px,${y}px,0)`; },
  };
}

/* ---------------------------------------------------------------- 跑馬燈大字 */
export function createMarquee() {
  const el = document.createElement('div'); el.id = 'marquee'; el.setAttribute('aria-hidden', 'true');
  el.innerHTML = '<div></div>'; document.body.appendChild(el);
  const inner = el.firstChild; let text = '', w = 1, op = -1;
  return {
    set(t) { if (t === text) return; text = t; inner.innerHTML = `<span>${t}</span>`.repeat(6); w = inner.firstChild.offsetWidth || 1; },
    update(x, skew, opacity) {
      const o = +opacity.toFixed(3);
      if (o !== op) { el.style.opacity = o; op = o; }
      if (o <= 0) return;
      const tx = -(((x % w) + w) % w);
      inner.style.transform = `translate3d(${tx.toFixed(1)}px,0,0) skewX(${skew.toFixed(2)}deg)`;
    },
  };
}
