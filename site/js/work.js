// 單一作品頁：work.html?id=<id>，所有作品共用這個樣板，內容來自 content.js。
import { WORKS, SHOT_CAPTIONS, renderPath, workById } from './content.js';
import { $, $$, esc, media, bindMedia, bindImage, reveal, initCommon, heroParallax, openLightbox, compareHTML, initCompare,
  fetchJSON, countUp, onceVisible, reduced } from './common.js';

initCommon();

const w = workById(new URLSearchParams(location.search).get('id'));
if (!w) location.replace('index.html#works');
else render(w);

function render(w) {
  const n = WORKS.length, i = WORKS.indexOf(w);
  const prev = WORKS[(i - 1 + n) % n], next = WORKS[(i + 1) % n];
  const P = (f) => renderPath(w.id, f);
  const ph = { label: w.title, sub: w.en };
  const total = String(n).padStart(2, '0');

  document.title = `${w.no} ${w.title} ${w.en} — 陳昭銘 CHEN CHAO MING`;
  document.body.style.setProperty('--accent', w.accent);

  const shots = [
    { file: 's1.jpg', cls: 'full' }, { file: 's2.jpg', cls: 'half' },
    { file: 's3.jpg', cls: 'half' }, { file: 's4.jpg', cls: 'full' },
  ];
  const cap = (f) => SHOT_CAPTIONS[f] || '';

  const dl = [
    w.project ? ['專案', esc(w.project)] : null,
    ['類型', esc(w.cat)],
    ['交付', `<ul class="tags">${w.deliver.map((d) => `<li>${esc(d)}</li>`).join('')}</ul>`],
  ].filter(Boolean);

  const pnItem = (o, dir) => `
    <a class="pn-item pn-${dir}" href="work.html?id=${o.id}" style="--accent:${o.accent}">
      ${media({ src: renderPath(o.id, 'hero.jpg'), fallback: o.still || '', alt: '', ratio: '', ...{ label: o.title, sub: o.en }, cls: 'fill' })}
      <span class="pn-shade" aria-hidden="true"></span>
      <span class="pn-txt">
        <span class="label">${dir === 'prev' ? '← 上一件 PREVIOUS' : '下一件 NEXT →'}</span>
        <b><span class="pn-no">${o.no}</span>${esc(o.title)}</b>
        <span class="label pn-cat">${esc(o.en)}</span>
      </span>
    </a>`;

  $('#work').innerHTML = `
  <section class="hero hero-work" aria-label="${esc(w.title)}">
    <div class="hero-media">${media({ ...ph, src: P('hero.jpg'), fallback: w.still || '', alt: `${w.title} 主視覺`, ratio: '', cls: 'fill', eager: true })}</div>
    <div class="hero-shade" aria-hidden="true"></div>
    <div class="wrap hero-in">
      <div class="wk-head">
        <span class="wk-no"><b>${w.no}</b><span>/ ${total}</span></span>
        <h1 class="h-hero wk-title">${esc(w.title)}</h1>
        <span class="label wk-cat"><i class="dot" aria-hidden="true"></i>${esc(w.en)} — ${esc(w.cat)}</span>
      </div>
    </div>
  </section>

  <section class="section wrap wk-intro" aria-label="作品介紹">
    <a class="back label" href="index.html#works">← 全部作品</a>
    <p class="wk-lead" data-reveal>${esc(w.lead)}</p>
    <dl class="dl" data-reveal>${dl.map(([k, v]) => `<div><dt class="label">${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
  </section>

  <section class="specs" id="specs" aria-label="模型規格" hidden>
    <div class="wrap specs-in"></div>
  </section>

  <section class="section light wk-ga" aria-label="目標與做法">
    <div class="wrap ga">
      <div class="ga-col" data-reveal><span class="label">GOAL</span><h2 class="ga-h">目標</h2><p class="ga-p">${esc(w.goal)}</p></div>
      <div class="ga-col" data-reveal><span class="label">APPROACH</span><h2 class="ga-h">做法</h2><p class="ga-p">${esc(w.approach)}</p></div>
    </div>
  </section>

  <section class="section wk-gallery" aria-labelledby="g-h">
    <div class="wrap">
      <header class="sec-head" data-reveal><span class="label">RENDERS</span><h2 id="g-h" class="h-2">完成渲染</h2></header>
      <div class="shots">
        ${shots.map((s, k) => `
        <figure class="shot ${s.cls}" data-reveal>
          <button class="shot-btn" data-k="${k}" aria-label="放大：${esc(cap(s.file) || w.title)}">
            ${media({ ...ph, src: P(s.file), alt: `${w.title}：${cap(s.file)}`, ratio: '16 / 9' })}
          </button>
          <figcaption><span class="label">${String(k + 1).padStart(2, '0')}</span><span class="cap" data-file="${s.file}">${esc(cap(s.file))}</span></figcaption>
        </figure>`).join('')}
      </div>
    </div>
  </section>

  <section class="section section-tight wk-compare" aria-labelledby="c-h">
    <div class="wrap">
      <div class="split-head" data-reveal>
        <div><span class="label">FINAL / CLAY / WIRE</span><h2 id="c-h" class="h-2">白模與線框</h2></div>
        <p class="muted">${esc(w.clayNote)} 拖曳中間的把手比較。</p>
      </div>
      <div data-reveal id="cmp">${compareHTML(w)}</div>
    </div>
  </section>

  <section class="section wk-turn" aria-labelledby="t-h">
    <div class="wrap">
      <div class="split-head" data-reveal>
        <div><span class="label">360° TURNTABLE</span><h2 id="t-h" class="h-2">轉一圈</h2></div>
        <p class="muted">左右拖曳，或聚焦後用方向鍵轉動。</p>
      </div>
      <div class="turn" id="turn" tabindex="0" role="slider" aria-label="360 度轉台" aria-valuemin="0" aria-valuemax="23" aria-valuenow="0" aria-valuetext="0 度" data-reveal>
        ${media({ ...ph, src: P('turn/00.jpg'), alt: `${w.title} 360 度轉台`, ratio: '16 / 9', sub: '360° TURNTABLE' })}
        <div class="turn-ui" aria-hidden="true">
          <span class="label turn-deg">000°</span>
          <span class="turn-bar"><i></i></span>
          <span class="label turn-hint">DRAG ⟷</span>
        </div>
      </div>
    </div>
  </section>

  <section class="section wk-viewer" id="topology" aria-labelledby="v-h">
    <div class="wrap">
      <div class="split-head" data-reveal>
        <div><span class="label">TOPOLOGY VIEWER</span><h2 id="v-h" class="h-2">檢查拓撲</h2></div>
        <p class="muted">模型真實的多邊形佈線，不是貼圖或特效。拖曳旋轉、滾輪縮放${w.view.explode ? '，用「拆解」把零件分開' : ''}。</p>
      </div>
      <div class="viewer" id="viewer" data-reveal>
        <div class="viewer-poster">
          ${media({ ...ph, src: P('wire.jpg'), alt: '', ratio: '', cls: 'fill', sub: 'TOPOLOGY' })}
          <div class="viewer-cover">
            <button class="btn btn-solid btn-lg" id="viewer-start">檢查拓撲</button>
            <span class="label" id="viewer-size">載入 3D 模型</span>
          </div>
        </div>
        <div class="viewer-canvas" id="viewer-canvas"></div>
        <div class="viewer-ui" id="viewer-ui" hidden>
          <div class="seg" role="group" aria-label="顯示方式">
            <button class="on" data-mode="wire" aria-pressed="true">線框</button>
            <button data-mode="clay" aria-pressed="false">白模</button>
          </div>
          ${w.view.explode ? `<label class="range"><span class="label">拆解</span><input type="range" id="explode" min="0" max="1" step="0.01" value="0" aria-label="拆解程度"></label>` : ''}
          <button class="icon-btn" id="viewer-reset" aria-label="重設視角" title="重設視角"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v5h5"/></svg></button>
        </div>
        <p class="viewer-status label" id="viewer-status" aria-live="polite"></p>
      </div>
      <p class="viewer-note muted" id="viewer-note"></p>
    </div>
  </section>

  <nav class="pn" aria-label="其他作品">${pnItem(prev, 'prev')}${pnItem(next, 'next')}</nav>
  <div class="wrap back-row"><a class="btn btn-line" href="index.html#works">回到作品列表</a></div>`;

  initTurntable(w);                                  // 先綁轉台的圖（要知道第 0 格是否存在）
  bindMedia($('#work'));
  heroParallax($('.hero-media'));
  initCompare($('#cmp'));

  // 圖片說明：shots.json 有寫就取代預設
  fetchJSON(P('shots.json')).then((list) => {
    if (!Array.isArray(list)) return;
    for (const s of list) {
      if (!s || !s.file || !s.caption) continue;
      const el = $(`.cap[data-file="${CSS.escape(s.file)}"]`);
      if (el) { el.textContent = s.caption; const b = el.closest('figure')?.querySelector('.shot-btn'); b?.setAttribute('aria-label', `放大：${s.caption}`); b?.querySelector('img')?.setAttribute('alt', `${w.title}：${s.caption}`); }
    }
  });

  // 圖庫燈箱：只放已經載入成功的圖
  $('.shots').addEventListener('click', (e) => {
    const b = e.target.closest('.shot-btn'); if (!b) return;
    const ready = $$('.shot-btn').filter((x) => $('.media', x)?.classList.contains('is-loaded'));
    if (!ready.includes(b)) return;
    const items = ready.map((x) => {
      const fig = x.closest('figure');
      return { src: $('img', x).currentSrc || $('img', x).src, title: `${w.no} ${w.title}`, note: $('.cap', fig)?.textContent || '' };
    });
    openLightbox(items, ready.indexOf(b));
  });

  initSpecs(w);
  initViewer(w);
  reveal();
}

/* ------------------------------------------------------------------ 規格數字（stats.json） */
async function initSpecs(w) {
  const all = await fetchJSON('models/stats.json');
  const s = all && all[w.id];
  const note = $('#viewer-note'), size = $('#viewer-size');
  if (s && s.bytes) size.textContent = `載入 3D 模型 · ${(s.bytes / 1048576).toFixed(1)} MB`;
  if (s && s.web_tris && s.web_tris < s.tris) note.textContent = `檢視器載入的是減面到約 ${Math.round(s.web_tris / 1e4)} 萬面的網頁版本，原始檔 ${s.tris.toLocaleString('en-US')} 面。`;
  if (w.id === 'venom') note.textContent += (note.textContent ? ' ' : '') + '高模雕刻沒有四邊面拓撲，線框顯示的是三角面。';
  if (!s) return;
  const rows = [['tris', '三角面', 'TRIANGLES'], ['verts', '頂點', 'VERTICES'], ['objects', '部件', 'PARTS'], ['materials', '材質', 'MATERIALS']]
    .filter(([k]) => Number.isFinite(s[k]));
  const sec = $('#specs');
  $('.specs-in', sec).innerHTML = rows.map(([k, zh, en]) => `
    <div class="spec"><span class="spec-n" data-to="${s[k]}">0</span><span class="spec-l"><b>${zh}</b><span class="label">${en}</span></span></div>`).join('');
  sec.hidden = false;
  onceVisible(sec, () => $$('.spec-n', sec).forEach((el) => countUp(el, +el.dataset.to)));
}

/* ------------------------------------------------------------------ 360° 轉台：24 張影格 */
function initTurntable(w) {
  const el = $('#turn'), img = $('img', el), box = $('.media', el);
  const N = 24, frames = new Array(N).fill(null);
  const deg = $('.turn-deg', el), bar = $('.turn-bar i', el);
  let cur = 0, loaded = 0, finished = 0, played = false, touched = false, inView = false, timer = 0;
  const src = (k) => renderPath(w.id, `turn/${String(k).padStart(2, '0')}.jpg`);

  const show = (k) => {
    k = ((k % N) + N) % N;
    if (!frames[k]) return;
    cur = k;
    if (img.getAttribute('src') !== frames[k].src) img.src = frames[k].src;
    const d = Math.round((k / N) * 360);
    deg.textContent = String(d).padStart(3, '0') + '°';
    bar.style.transform = `scaleX(${(k + 1) / N})`;
    el.setAttribute('aria-valuenow', String(k)); el.setAttribute('aria-valuetext', `${d} 度`);
  };

  bindImage(img, (ok) => {
    if (!ok) { el.classList.add('is-off'); el.removeAttribute('tabindex'); el.removeAttribute('role'); }
  });

  const tryPlay = () => {
    if (played || touched || reduced || !inView || finished < N || loaded < N) return;
    played = true;
    let k = 0;
    timer = setInterval(() => { k++; show(k); if (k >= N || touched) { clearInterval(timer); if (!touched) show(0); } }, 140);
  };

  // 接近畫面時才開始預載；第 0 格不存在就不再要其他 23 格
  const load = (k, then) => {
    const im = new Image();
    im.decoding = 'async';
    im.onload = () => { frames[k] = im; loaded++; finished++; el.classList.toggle('is-ready', loaded === N); then?.(); tryPlay(); };
    im.onerror = () => { finished++; };
    im.src = src(k);
  };
  onceVisible(el, () => load(0, () => { for (let k = 1; k < N; k++) load(k); }), '400px');
  if ('IntersectionObserver' in window) {
    new IntersectionObserver((es) => { inView = es.some((e) => e.isIntersecting); tryPlay(); }, { threshold: 0.6 }).observe(el);
  }

  const stop = () => { touched = true; clearInterval(timer); };
  let drag = null;
  el.addEventListener('pointerdown', (e) => {
    if (el.classList.contains('is-off')) return;
    stop(); drag = { x: e.clientX, f: cur, w: el.clientWidth };
    el.setPointerCapture(e.pointerId); el.classList.add('dragging');
  });
  el.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const step = drag.w / N;                       // 拖過整個寬度 = 轉一圈
    show(drag.f - Math.round((e.clientX - drag.x) / step));
  });
  const end = () => { drag = null; el.classList.remove('dragging'); };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  el.addEventListener('keydown', (e) => {
    const d = { ArrowLeft: 1, ArrowRight: -1, Home: -cur, End: N - 1 - cur }[e.key];
    if (d === undefined || el.classList.contains('is-off')) return;
    e.preventDefault(); stop(); show(cur + d);
  });
  el.addEventListener('dragstart', (e) => e.preventDefault());
}

/* ------------------------------------------------------------------ 拓撲檢視器：按下才載入 three.js */
function initViewer(w) {
  const btn = $('#viewer-start'), root = $('#viewer'), status = $('#viewer-status');
  let viewer = null;
  btn.addEventListener('click', async () => {
    btn.disabled = true; root.classList.add('is-loading');
    status.textContent = '載入中…';
    try {
      const { createViewer } = await import('./viewer.js');
      viewer = await createViewer($('#viewer-canvas'), {
        url: `models/${w.id}.glb`, accent: w.accent, ...w.view,
        onProgress: (f) => { status.textContent = f > 0 ? `載入中 ${Math.round(f * 100)}%` : '載入中…'; },
      });
      root.classList.remove('is-loading'); root.classList.add('is-live');
      status.textContent = '';
      $('#viewer-ui').hidden = false;
    } catch (err) {
      console.error(err);
      root.classList.remove('is-loading');
      btn.disabled = false;
      status.textContent = err && err.message === 'webgl' ? '這個瀏覽器不支援 WebGL，無法顯示 3D 模型。' : '模型載入失敗，請稍後再試。';
      return;
    }
    $$('#viewer-ui .seg button').forEach((b) => b.addEventListener('click', () => {
      viewer.setMode(b.dataset.mode);
      $$('#viewer-ui .seg button').forEach((x) => { x.classList.toggle('on', x === b); x.setAttribute('aria-pressed', String(x === b)); });
    }));
    $('#explode')?.addEventListener('input', (e) => viewer.setExplode(+e.target.value));
    $('#viewer-reset').addEventListener('click', () => viewer.reset());
  });
}
