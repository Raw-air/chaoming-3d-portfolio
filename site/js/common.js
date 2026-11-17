// 共用：導覽列、進場動畫、圖片占位、燈箱、對照滑桿、頁面淡入淡出。

export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];
export const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ESC[c]);

/* ------------------------------------------------------------------ 圖片＋占位
   每張圖都包在固定比例的 .media 裡：先顯示深色占位（作品名），圖片載入成功才淡入；
   失敗就保持占位（有 data-fallback 的會先試備用圖）。不會出現破圖示，也不會跳版。 */
export function media({ src, alt = '', ratio = '16 / 9', label = '', sub = '', cls = '', eager = false, fallback = '', extra = '' }) {
  return `<div class="media ${cls}"${ratio ? ` style="--ratio:${ratio}"` : ''}>
    <div class="ph" aria-hidden="true"><span class="ph-sub">${esc(sub)}</span><span class="ph-t">${esc(label)}</span></div>
    <img src="${esc(src)}" alt="${esc(alt)}" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async"${fallback ? ` data-fallback="${esc(fallback)}"` : ''}>${extra}
  </div>`;
}

export function bindImage(img, onState) {
  if (img.dataset.bound) return; img.dataset.bound = '1';
  const box = img.closest('.media');
  const ok = () => { box?.classList.add('is-loaded'); box?.classList.remove('is-missing'); onState?.(true, img); };
  const bad = () => {
    const fb = img.dataset.fallback;
    if (fb) { delete img.dataset.fallback; img.src = fb; box?.classList.add('is-fallback'); return; }
    box?.classList.add('is-missing'); onState?.(false, img);
  };
  img.addEventListener('load', ok);
  img.addEventListener('error', bad);
  if (img.complete) { if (img.naturalWidth > 0) ok(); else if (img.getAttribute('src')) bad(); }
}
export const bindMedia = (root = document) => $$('.media img', root).forEach((img) => bindImage(img));

// 不放進 DOM 的探測：檔案存在才 resolve(true)
export function probe(src) {
  return new Promise((res) => { const i = new Image(); i.onload = () => res(true); i.onerror = () => res(false); i.src = src; });
}

export async function fetchJSON(url) {
  try { const r = await fetch(url, { cache: 'no-cache' }); if (!r.ok) return null; return await r.json(); } catch { return null; }
}

/* ------------------------------------------------------------------ 進場：淡入＋上移 16px，只播一次 */
let io;
export function reveal(root = document) {
  const els = $$('[data-reveal]:not(.in)', root);
  if (reduced || !('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('in')); return; }
  io ??= new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  els.forEach((e) => io.observe(e));
}

/* ------------------------------------------------------------------ 數字跳動（只播一次） */
export function countUp(el, to, { dur = 1400 } = {}) {
  const fmt = (n) => Math.round(n).toLocaleString('en-US');
  if (reduced) { el.textContent = fmt(to); return; }
  const start = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - start) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(to * e);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
export function onceVisible(el, fn, margin = '0px') {
  if (!('IntersectionObserver' in window)) { fn(); return; }
  const o = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { o.disconnect(); fn(); } }, { rootMargin: margin, threshold: 0.2 });
  o.observe(el);
}

/* ------------------------------------------------------------------ 導覽列 */
export function initNav() {
  const bar = $('#nav'); if (!bar) return;
  const onScroll = () => bar.classList.toggle('is-solid', scrollY > 24 || document.body.classList.contains('menu-open'));
  addEventListener('scroll', onScroll, { passive: true }); onScroll();
  const btn = $('#nav-toggle'), menu = $('#nav-menu');
  const set = (open) => {
    document.body.classList.toggle('menu-open', open);
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? '關閉選單' : '開啟選單');
    onScroll();
  };
  btn?.addEventListener('click', () => set(!document.body.classList.contains('menu-open')));
  menu?.addEventListener('click', (e) => { if (e.target.closest('a')) set(false); });
  addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.body.classList.contains('menu-open')) set(false); });
  matchMedia('(min-width: 1024px)').addEventListener('change', (m) => { if (m.matches) set(false); });
}

/* ------------------------------------------------------------------ 主視覺視差（≤ 0.3） */
export function heroParallax(img) {
  if (reduced || !img) return;
  let raf = 0;
  const run = () => { raf = 0; const y = scrollY; if (y < innerHeight * 1.2) img.style.transform = `translate3d(0, ${(y * 0.25).toFixed(1)}px, 0)`; };
  addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(run); }, { passive: true });
}

/* ------------------------------------------------------------------ 頁面淡入淡出 */
export function initPageFade() {
  const show = () => document.documentElement.classList.add('ready');
  requestAnimationFrame(show);
  addEventListener('pageshow', (e) => { if (e.persisted) { document.documentElement.classList.remove('leaving'); show(); } });
  if (reduced) return;
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || a.hasAttribute('download') || url.protocol === 'mailto:') return;
    const samePage = url.pathname === location.pathname && url.search === location.search;
    if (samePage) return;
    e.preventDefault();
    document.documentElement.classList.add('leaving');
    setTimeout(() => { location.href = url.href; }, 260);
  });
}

/* ------------------------------------------------------------------ 燈箱（交叉淡化） */
let lb = null;
function buildLightbox() {
  const el = document.createElement('div');
  el.className = 'lb'; el.hidden = true;
  el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-label', '圖片檢視');
  el.innerHTML = `
    <div class="lb-stage"><img class="lb-img a" alt=""><img class="lb-img b" alt=""></div>
    <div class="lb-bar">
      <div class="lb-cap"><span class="lb-count label"></span><b class="lb-title"></b><span class="lb-note"></span></div>
      <div class="lb-alts" role="group" aria-label="版本"></div>
    </div>
    <button class="lb-btn lb-close" aria-label="關閉"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg></button>
    <button class="lb-btn lb-prev" aria-label="上一張"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 4l-8 8 8 8"/></svg></button>
    <button class="lb-btn lb-next" aria-label="下一張"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4l8 8-8 8"/></svg></button>`;
  document.body.appendChild(el);
  const st = { el, items: [], i: 0, alt: 0, front: $('.lb-img.a', el), back: $('.lb-img.b', el), last: null };
  $('.lb-close', el).addEventListener('click', closeLightbox);
  $('.lb-prev', el).addEventListener('click', () => go(-1));
  $('.lb-next', el).addEventListener('click', () => go(1));
  $('.lb-stage', el).addEventListener('click', (e) => { if (!e.target.closest('img')) closeLightbox(); });
  $('.lb-alts', el).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { st.alt = +b.dataset.k; show(); } });
  let sx = null;
  el.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'mouse') sx = e.clientX; });
  el.addEventListener('pointerup', (e) => { if (sx !== null && Math.abs(e.clientX - sx) > 50) go(e.clientX < sx ? 1 : -1); sx = null; });
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowRight') go(1);
    else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'Tab') {                                     // 焦點留在燈箱裡
      const f = $$('button:not([hidden])', el).filter((b) => b.offsetParent !== null);
      const k = f.indexOf(document.activeElement);
      if (e.shiftKey && k <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && k === f.length - 1) { e.preventDefault(); f[0].focus(); }
    }
  });
  return st;
}
function go(d) { if (!lb || lb.items.length < 2) return; lb.i = (lb.i + d + lb.items.length) % lb.items.length; lb.alt = 0; show(); }
function show() {
  const it = lb.items[lb.i], alts = it.alts || [];
  const src = alts.length ? alts[lb.alt][0] : it.src;
  const next = lb.back; next.alt = it.title || '';
  next.classList.remove('on');
  const token = lb.tok = (lb.tok || 0) + 1;
  const done = () => {
    if (token !== lb.tok || next.classList.contains('on')) return;
    next.classList.add('on'); lb.front.classList.remove('on'); [lb.front, lb.back] = [next, lb.front];
  };
  next.onload = done;
  next.src = src;
  if (next.complete && next.naturalWidth) done();
  $('.lb-count', lb.el).textContent = lb.items.length > 1 ? `${String(lb.i + 1).padStart(2, '0')} / ${String(lb.items.length).padStart(2, '0')}` : '';
  $('.lb-title', lb.el).textContent = it.title || '';
  $('.lb-note', lb.el).textContent = it.note || '';
  $('.lb-alts', lb.el).innerHTML = alts.map(([, label], k) => `<button data-k="${k}" class="${k === lb.alt ? 'on' : ''}" aria-pressed="${k === lb.alt}">${esc(label)}</button>`).join('');
  const many = lb.items.length > 1;
  $('.lb-prev', lb.el).hidden = !many; $('.lb-next', lb.el).hidden = !many;
}
export function openLightbox(items, index = 0) {
  if (!items.length) return;
  lb ??= buildLightbox();
  lb.items = items; lb.i = Math.max(0, Math.min(index, items.length - 1)); lb.alt = 0;
  lb.last = document.activeElement;
  lb.front.classList.remove('on'); lb.back.classList.remove('on');
  lb.el.hidden = false;
  document.body.classList.add('lb-open');
  requestAnimationFrame(() => lb.el.classList.add('open'));
  show();
  $('.lb-close', lb.el).focus({ preventScroll: true });
}
export function closeLightbox() {
  if (!lb || lb.el.hidden) return;
  lb.el.classList.remove('open');
  document.body.classList.remove('lb-open');
  setTimeout(() => { lb.el.hidden = true; lb.front.removeAttribute('src'); lb.back.removeAttribute('src'); }, reduced ? 0 : 260);
  lb.last?.focus?.({ preventScroll: true });
}

/* ------------------------------------------------------------------ 對照滑桿：完成圖 ⇄ 白模 / 線框
   結構見 compareHTML()。左邊是完成圖，右邊（上層，被裁切）是白模或線框。 */
export function compareHTML(w, { label = true } = {}) {
  const p = (f) => `renders/${w.id}/${f}`;
  const ph = { label: w.title, sub: w.en, ratio: '16 / 9' };
  return `<div class="cmp" style="--pos:50%">
    <div class="cmp-layer cmp-base">${media({ ...ph, src: p('s1.jpg'), alt: `${w.title} 完成渲染` })}</div>
    <div class="cmp-layer cmp-top" data-layer="clay">${media({ ...ph, src: p('clay.jpg'), alt: `${w.title} 白模`, sub: 'CLAY', cls: 'is-clay' })}</div>
    <div class="cmp-layer cmp-top" data-layer="wire" hidden>${media({ ...ph, src: p('wire.jpg'), alt: `${w.title} 線框`, sub: 'WIREFRAME', cls: 'is-wire' })}</div>
    ${label ? '<span class="cmp-tag cmp-tag-l label">FINAL</span><span class="cmp-tag cmp-tag-r label">CLAY</span>' : ''}
    <div class="cmp-handle" role="slider" tabindex="0" aria-label="拖曳比較完成圖與白模" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"><i></i></div>
  </div>
  <div class="cmp-switch" role="group" aria-label="右側顯示">
    <button class="on" data-show="clay" aria-pressed="true">白模 CLAY</button>
    <button data-show="wire" aria-pressed="false">線框 WIRE</button>
  </div>`;
}
export function initCompare(root) {
  const box = $('.cmp', root); if (!box) return;
  const handle = $('.cmp-handle', box), tagR = $('.cmp-tag-r', box);
  let pos = 50;
  const set = (v) => {
    pos = Math.max(0, Math.min(100, v));
    box.style.setProperty('--pos', pos + '%');
    handle.setAttribute('aria-valuenow', String(Math.round(pos)));
  };
  const fromEvent = (e) => { const r = box.getBoundingClientRect(); set(((e.clientX - r.left) / r.width) * 100); };
  let drag = false;
  box.addEventListener('pointerdown', (e) => { drag = true; box.setPointerCapture(e.pointerId); box.classList.add('dragging'); fromEvent(e); });
  box.addEventListener('pointermove', (e) => { if (drag) fromEvent(e); });
  const end = () => { drag = false; box.classList.remove('dragging'); };
  box.addEventListener('pointerup', end); box.addEventListener('pointercancel', end);
  handle.addEventListener('keydown', (e) => {
    const k = { ArrowLeft: -5, ArrowRight: 5, Home: -100, End: 100 }[e.key];
    if (k !== undefined) { e.preventDefault(); set(pos + k); }
  });
  $$('.cmp-switch button', root).forEach((b) => b.addEventListener('click', () => {
    const show = b.dataset.show;
    $$('.cmp-top', box).forEach((l) => { l.hidden = l.dataset.layer !== show; });
    $$('.cmp-switch button', root).forEach((x) => { x.classList.toggle('on', x === b); x.setAttribute('aria-pressed', String(x === b)); });
    if (tagR) tagR.textContent = show === 'wire' ? 'WIRE' : 'CLAY';
    handle.setAttribute('aria-label', `拖曳比較完成圖與${show === 'wire' ? '線框' : '白模'}`);
  }));
}

/* ------------------------------------------------------------------ 共同初始化 */
export function initCommon() {
  initNav();
  initPageFade();
  const y = $('#year'); if (y) y.textContent = String(new Date().getFullYear());
}
