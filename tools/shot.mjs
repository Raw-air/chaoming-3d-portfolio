// Headless-browser screenshots of the site over the Chrome DevTools Protocol.
// No dependencies (Node 22+: global fetch + WebSocket). Used to check pages when no browser window is visible.
//
//   node tools/shot.mjs <url> [--w 1440] [--h 900] [--dpr 1] [--mobile] <ops...>
//
// ops run in order:
//   --sleep <ms>            wait
//   --js <code>             evaluate in the page and print the JSON result
//   --scrollto <y>          window.scrollTo(0, y)
//   --sel <css>             scroll the first match to the middle of the viewport
//   --shot <file.jpg>       screenshot of the viewport
//   --tiles <prefix>        scroll through the whole page: <prefix>-00.jpg, -01.jpg, ...
//   --click <x,y>           mouse click (viewport px)
//   --drag <x1,y1,x2,y2>    mouse drag (viewport px)
//   --key <Key>             key press, e.g. ArrowRight, Escape
// Console errors and failed requests are printed at the end.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const argv = process.argv.slice(2);
const url = argv.shift();
const take = (k, d) => { const i = argv.indexOf('--' + k); if (i < 0) return d; const v = argv[i + 1]; argv.splice(i, 2); return v; };
const W = +take('w', 1440), H = +take('h', 900), DPR = +take('dpr', 1);
const mi = argv.indexOf('--mobile'); const MOBILE = mi >= 0; if (MOBILE) argv.splice(mi, 1);

const EXE = process.env.BROWSER_EXE || [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
].find((p) => existsSync(p));
const port = 9300 + (process.pid % 500);
const profile = mkdtempSync(join(tmpdir(), 'shot-'));
const child = spawn(EXE, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run',
  '--no-default-browser-check', '--hide-scrollbars', '--disable-extensions', '--mute-audio', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pageTarget() {
  for (let i = 0; i < 75; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const p = list.find((t) => t.type === 'page');
      if (p) return p.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error('browser did not start');
}

const problems = [];
let exit = 0;
try {
  const ws = new WebSocket(await pageTarget());
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  let seq = 0; const pending = new Map();
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') problems.push('EXCEPTION ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') problems.push('CONSOLE ' + m.params.args.map((a) => a.value ?? a.description).join(' '));
    if (m.method === 'Network.responseReceived' && m.params.response.status >= 400) problems.push(`HTTP ${m.params.response.status} ${m.params.response.url}`);
    if (m.method === 'Network.loadingFailed' && !m.params.canceled) problems.push(`FAILED ${m.params.errorText} (${m.params.type})`);
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = ++seq;
    pending.set(i, (m) => (m.error ? rej(new Error(`${method}: ${m.error.message}`)) : res(m.result)));
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const ev = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error('page JS: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  };
  const shot = async (file) => {
    const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 82 });
    writeFileSync(file, Buffer.from(r.data, 'base64'));
    console.log('SHOT', file);
  };
  const mouse = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mouseReleased' ? 0 : 1, clickCount: 1, ...extra });

  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: DPR, mobile: MOBILE });
  if (MOBILE) {
    await send('Emulation.setTouchEmulationEnabled', { enabled: true });
    await send('Emulation.setUserAgentOverride', { userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36' });
  }
  await send('Page.navigate', { url });
  for (let i = 0; i < 100 && (await ev('document.readyState')) !== 'complete'; i++) await sleep(150);
  await sleep(900);

  while (argv.length) {
    const op = argv.shift(); const v = argv.shift();
    if (op === '--sleep') await sleep(+v);
    else if (op === '--js') console.log('JS', JSON.stringify(await ev(v)));
    else if (op === '--scrollto') { await ev(`window.scrollTo(0, ${+v})`); await sleep(500); }
    else if (op === '--sel') { await ev(`document.querySelector(${JSON.stringify(v)}).scrollIntoView({block:'center'})`); await sleep(600); }
    else if (op === '--shot') await shot(v);
    else if (op === '--click') { const [x, y] = v.split(',').map(Number); await mouse('mouseMoved', x, y, { buttons: 0 }); await mouse('mousePressed', x, y); await mouse('mouseReleased', x, y); await sleep(500); }
    else if (op === '--drag') {
      const [x1, y1, x2, y2] = v.split(',').map(Number);
      await mouse('mouseMoved', x1, y1, { buttons: 0 }); await mouse('mousePressed', x1, y1);
      for (let i = 1; i <= 12; i++) { await mouse('mouseMoved', x1 + (x2 - x1) * i / 12, y1 + (y2 - y1) * i / 12); await sleep(30); }
      await mouse('mouseReleased', x2, y2); await sleep(400);
    }
    else if (op === '--key') {
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: v, code: v });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: v, code: v }); await sleep(300);
    }
    else if (op === '--tiles') {
      const total = () => ev('Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)');
      // first pass: trigger lazy images and reveal observers
      for (let y = 0; y < (await total()); y += Math.round(H * 0.7)) { await ev(`window.scrollTo(0, ${y})`); await sleep(350); }
      await ev(`Promise.all([...document.images].filter(i => !i.complete).map(i => new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); setTimeout(r, 6000); })))`);
      await sleep(800);
      const full = await total(); let n = 0;
      for (let y = 0; ; y += Math.round(H * 0.92)) {
        const yy = Math.min(y, Math.max(0, full - H));
        await ev(`window.scrollTo(0, ${yy})`); await sleep(700);
        await shot(`${v}-${String(n++).padStart(2, '0')}.jpg`);
        if (yy >= full - H) break;
      }
      console.log('PAGE', JSON.stringify({ height: full, tiles: n }));
    }
    else throw new Error('unknown op ' + op);
  }
  ws.close();
} catch (e) {
  console.error('ERROR', e.message); exit = 1;
} finally {
  child.kill();
  await sleep(300);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* browser may still hold a lock */ }
}
for (const p of [...new Set(problems)]) console.log('PROBLEM', p);
process.exit(exit);
