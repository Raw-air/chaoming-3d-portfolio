// 首頁：主視覺、簡介數字、作品索引、白模對照帶、藝廊、關於、聯絡。
import { PROFILE, WORKS, GALLERY, SERVICES, PROCESS, AWARDS, CONTACT, HOME, renderPath, workById } from './content.js';
import { $, $$, esc, media, bindMedia, reveal, initCommon, heroParallax, openLightbox, compareHTML, initCompare } from './common.js';

initCommon();

const mailto = `mailto:${PROFILE.email}?subject=${encodeURIComponent('3D 建模委託')}`;

/* ------------------------------------------------------------------ 主視覺 */
{
  const w = workById(HOME.hero);
  $('#hero').innerHTML = `
    <div class="hero-media">${media({ src: renderPath(w.id, 'hero.jpg'), fallback: w.still || '', alt: `${w.title}（${w.en}）`, ratio: '', label: w.title, sub: w.en, cls: 'fill', eager: true })}</div>
    <div class="hero-shade" aria-hidden="true"></div>
    <div class="wrap hero-in">
      <span class="label hero-kicker">${esc(PROFILE.role)} — ${esc(PROFILE.nameEn)}</span>
      <h1 class="h-hero">${PROFILE.claim.map(esc).join('<br>')}</h1>
      <p class="hero-desc">${esc(PROFILE.descriptor)}</p>
      <div class="cta-row">
        <a class="btn btn-solid" href="#works">看作品</a>
        <a class="btn btn-line" href="${esc(mailto)}">寫信給我</a>
      </div>
    </div>
    <a class="hero-credit" href="work.html?id=${w.id}"><span class="label">${w.no} — ${esc(w.en)}</span><b>${esc(w.title)}</b><i aria-hidden="true">→</i></a>`;
  bindMedia($('#hero'));
  heroParallax($('#hero .hero-media'));
}

/* ------------------------------------------------------------------ 簡介數字 */
$('#intro-lead').textContent = PROFILE.lead;
$('#figures').innerHTML = PROFILE.heroStats.map(([n, t]) => `<div class="fig" data-reveal><dt>${esc(n)}</dt><dd>${esc(t)}</dd></div>`).join('');

/* ------------------------------------------------------------------ 作品索引
   桌機：01 整列、02–04 三欄、05–06 兩欄、07 寬卡＋08 直卡。平板兩欄、手機一欄。 */
const LAYOUT = { ship: 'w12 feature', console: 'w4', char: 'w4', pod: 'w4', arcade: 'w6', jukebox: 'w6', airship: 'w8 feature', venom: 'w4 stretch' };
$('#works-grid').innerHTML = WORKS.map((w) => {
  const lay = LAYOUT[w.id] || 'w4', feat = lay.includes('feature');
  return `<a class="card ${lay}" href="work.html?id=${w.id}" style="--accent:${w.accent}" data-reveal data-id="${w.id}">
    <div class="card-media">${media({
      src: renderPath(w.id, feat ? 'hero.jpg' : 'card.jpg'), fallback: feat && w.still ? w.still : '',
      alt: `${w.title}（${w.en}）`, ratio: '', label: w.title, sub: w.en })}</div>
    <div class="card-meta">
      <span class="card-no">${w.no}</span>
      <h3 class="card-t">${esc(w.title)}<span class="card-en">${esc(w.en)}</span></h3>
      <span class="card-cat">${esc(w.cat)}</span>
    </div>
  </a>`;
}).join('');
bindMedia($('#works-grid'));

// 滑過時交叉淡化成 s1（第一次滑過才載入，載入成功才淡化）
if (matchMedia('(hover: hover)').matches) {
  $$('#works-grid .card').forEach((card) => {
    card.addEventListener('pointerenter', () => {
      if (card.dataset.alt) return; card.dataset.alt = '1';
      const box = $('.media', card); if (!box || box.classList.contains('is-missing')) return;
      const img = new Image();
      img.className = 'card-alt'; img.alt = ''; img.decoding = 'async';
      img.onload = () => img.classList.add('ok');
      img.onerror = () => img.remove();
      img.src = renderPath(card.dataset.id, 's1.jpg');
      box.appendChild(img);
    });
  });
}

/* ------------------------------------------------------------------ 白模對照帶 */
{
  const w = workById(HOME.compare);
  $('#compare').style.setProperty('--accent', w.accent);
  $('#compare-note').innerHTML = `${esc(w.clayNote)}<br><a class="link" href="work.html?id=${w.id}">${w.no} ${esc(w.title)} — 看完整作品 →</a>`;
  $('#compare-box').innerHTML = compareHTML(w);
  bindMedia($('#compare-box'));
  initCompare($('#compare-box'));
}

/* ------------------------------------------------------------------ 藝廊（等高拼貼＋燈箱） */
{
  const items = GALLERY.map((g) => ({
    src: `img/${g.src}.jpg`, title: g.title, note: g.note,
    alts: g.alt ? g.alt.map(([s, l]) => [`img/${s}.jpg`, l]) : null,
  }));
  $('#gallery-grid').innerHTML = GALLERY.map((g, i) => `
    <button class="jg-item" style="--ar:${(g.w / g.h).toFixed(4)}" data-i="${i}" aria-label="放大圖片：${esc(g.title)}" data-reveal>
      ${media({ src: `img/${g.src}.jpg`, alt: g.title, ratio: `${g.w} / ${g.h}`, label: g.title, sub: 'STILL' })}
      <span class="jg-cap"><b>${esc(g.title)}</b>${g.alt ? `<span class="label">${g.alt.length} 種時段</span>` : ''}</span>
    </button>`).join('');
  bindMedia($('#gallery-grid'));
  $('#gallery-grid').addEventListener('click', (e) => {
    const b = e.target.closest('.jg-item'); if (b) openLightbox(items, +b.dataset.i);
  });
}

/* ------------------------------------------------------------------ 關於 */
$('#bio').innerHTML = PROFILE.bio.map((p) => `<p>${esc(p)}</p>`).join('');
$('#services').innerHTML = SERVICES.map(([t, d], i) => `<li><span class="num">${String(i + 1).padStart(2, '0')}</span><h4>${esc(t)}</h4><p>${esc(d)}</p></li>`).join('');
$('#process').innerHTML = PROCESS.map(([n, t, d]) => `<li><span class="num">${esc(n)}</span><h4>${esc(t)}</h4><p>${esc(d)}</p></li>`).join('');
$('#awards').innerHTML = AWARDS.map(([y, ev, a]) => `<li><span class="aw-y">${esc(y)}</span><span class="aw-e">${esc(ev)}</span><span class="aw-a">${esc(a)}</span></li>`).join('');

/* ------------------------------------------------------------------ 聯絡 */
$('#contact-in').innerHTML = `
  <span class="label" data-reveal>CONTACT</span>
  <h2 id="contact-h" class="h-hero contact-h" data-reveal>${CONTACT.headline.map(esc).join('<br>')}</h2>
  <div class="contact-row" data-reveal>
    <p class="contact-send">${esc(CONTACT.send)}</p>
    <div class="contact-actions">
      <a class="btn btn-solid btn-lg" href="${esc(mailto)}">${esc(PROFILE.email)}<i aria-hidden="true">→</i></a>
      ${PROFILE.phone ? `<a class="btn btn-line btn-lg" href="tel:${esc(PROFILE.phoneHref)}">${esc(PROFILE.phone)}</a>` : ''}
    </div>
  </div>`;

reveal();
