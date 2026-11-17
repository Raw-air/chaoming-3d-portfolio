// 場景腳本：每件作品所在的場景、位置、鏡位，以及每個場景的光線氛圍。
// 旅程：暴風圈（飛行艇）→ 衝進擋風玻璃 → 機艙內一路往後走（駕駛艙 → 船員艙 → 實驗艙 → 遊戲角落 → 酒吧）
//       → 後艙門打開 → 天空漁港（熱氣球飛船）→ 雕刻暗室（猛毒）→ 藝廊 → 黃昏漁港（服務、聯絡）
//
// 鏡位 shot：az 水平角（0 = 從 +Z 往 -Z 看）、el 仰角、d 距離、f 對焦點（相對作品位置）
// side：模型在畫面哪一側（-1 左 / 0 中 / 1 右）　mode：shaded / clay / wire　x：爆炸拆解程度 0–1

export const DECK = { x: 200, w: 12, h: 5.6, bay: 16, bays: 5 };          // 機艙：沿 -Z 方向排五個艙間
const bayZ = (i) => -(DECK.bay * i + DECK.bay / 2);
export const PORT = [0, 0, 400];
export const CHAMBER = [-200, 0, 0];

// 氛圍：背景、霧、環境光、主光、天空。場景之間會平滑過渡（機艙內）或在閃光中切換（跨場景）。
const INTERIOR = { sky: 0, skyAmt: 0, sunAmt: 0, stars: 0, env: 0.32, expo: 1.0, bloomS: 0.55, bloomT: 0.86, scrim: 0.25, keyDir: [3, 9, 5] };
export const MOODS = {
  storm:   { bg: '#04090c', fog: '#061513', fogD: 0.012, hemiSky: '#58a89a', hemiGnd: '#05090a', hemiI: 0.62, keyCol: '#d4f2ea', keyI: 1.3, keyDir: [5, 9, 7], env: 0.36, expo: 1.0, bloomS: 0.5, bloomT: 0.9, rimK: 1, fillK: 1,
             sky: 1, skyTop: '#01050a', skyHor: '#06201d', skyCloud: '#1a5a50', skyAmt: 1, skySpeed: 1, sunAmt: 0, sunCol: '#ffffff', sunDir: [0.3, 0.5, -0.8], scrim: 0.1, stars: 0 },
  cockpit: { ...INTERIOR, bg: '#080304', fog: '#1c0708', fogD: 0.02, hemiSky: '#8a3030', hemiGnd: '#0c0505', hemiI: 0.42, keyCol: '#ffb4a4', keyI: 0.4, rimK: 0.6, fillK: 0.9 },
  cabin:   { ...INTERIOR, bg: '#080604', fog: '#191007', fogD: 0.018, hemiSky: '#8a6a40', hemiGnd: '#0b0806', hemiI: 0.7, keyCol: '#ffdcae', keyI: 0.8, rimK: 0.9, fillK: 1 },
  lab:     { ...INTERIOR, bg: '#030807', fog: '#061a18', fogD: 0.026, hemiSky: '#2a8076', hemiGnd: '#040908', hemiI: 0.6, keyCol: '#c6f7ee', keyI: 0.6, rimK: 1, fillK: 0.9 },
  arcade:  { ...INTERIOR, bg: '#05050e', fog: '#0b0c22', fogD: 0.018, hemiSky: '#4458b0', hemiGnd: '#0a0612', hemiI: 0.62, keyCol: '#c0ccff', keyI: 0.6, rimK: 1, fillK: 0.9 },
  lounge:  { ...INTERIOR, bg: '#090503', fog: '#1d0e07', fogD: 0.018, hemiSky: '#9a5430', hemiGnd: '#0c0705', hemiI: 0.68, keyCol: '#ffcc96', keyI: 0.8, rimK: 0.9, fillK: 1 },
  port:    { bg: '#9cc8ee', fog: '#a4cbeb', fogD: 0.004, hemiSky: '#d6eaff', hemiGnd: '#7c8c98', hemiI: 1.2, keyCol: '#fff1d6', keyI: 2.5, keyDir: [-6, 9, 5], env: 0.85, expo: 0.84, bloomS: 0.2, bloomT: 1.0, rimK: 0.2, fillK: 0.3,
             sky: 1, skyTop: '#0c3f9e', skyHor: '#9ccdf0', skyCloud: '#ffffff', skyAmt: 0.7, skySpeed: 0.12, sunAmt: 1, sunCol: '#fff3d0', sunDir: [-0.55, 0.5, 0.67], scrim: 0.85, stars: 0 },
  chamber: { bg: '#030305', fog: '#06060b', fogD: 0.022, hemiSky: '#34345a', hemiGnd: '#020203', hemiI: 0.4, keyCol: '#ffffff', keyI: 1.25, keyDir: [2, 10, 4], env: 0.28, expo: 1.0, bloomS: 0.5, bloomT: 0.9, rimK: 1.2, fillK: 0.8,
             sky: 0, skyAmt: 0, sunAmt: 0, scrim: 0, stars: 1 },
  gallery: { bg: '#06070b', fog: '#06070b', fogD: 0.0105, hemiSky: '#9fb4d8', hemiGnd: '#0b0b10', hemiI: 0.55, keyCol: '#fff1e0', keyI: 1.5, keyDir: [6, 10, 8], env: 0.4, expo: 0.95, bloomS: 0.4, bloomT: 0.92, rimK: 0, fillK: 0,
             sky: 0, skyAmt: 0, sunAmt: 0, scrim: 0, stars: 1 },
  dusk:    { bg: '#1a1d3a', fog: '#4a2f44', fogD: 0.004, hemiSky: '#7e8ed0', hemiGnd: '#3a2a2a', hemiI: 0.8, keyCol: '#ffb070', keyI: 1.9, keyDir: [-8, 3, 6], env: 0.5, expo: 0.9, bloomS: 0.45, bloomT: 0.9, rimK: 0.3, fillK: 0.2,
             sky: 1, skyTop: '#080e2c', skyHor: '#e8743a', skyCloud: '#d0603a', skyAmt: 0.5, skySpeed: 0.1, sunAmt: 1, sunCol: '#ffb070', sunDir: [-0.82, 0.1, 0.56], scrim: 0.7, stars: 0 },
};

const QUAD = ['四邊面佈線', 'UV 已展開', 'FBX'];

export const HERO = { az: -34, el: 4, d: 13, f: [0, 0.9, 0], side: 1, mode: 'shaded' };

export const WORKS = [
  {
    id: 'ship', no: '01', title: '飛行艇', en: 'AIRCRAFT', scene: '暴風圈', set: 'storm', mood: 'storm', flying: true,
    accent: '#3ff0c8', pos: [0, 0, 0], scale: 7, yaw: 0, pad: 4.4, explode: 1.25, deliver: ['四邊面佈線', 'UV 已展開', 'OBJ'],
    shots: [
      { az: 36, el: 14, d: 11, f: [0, 0.8, 0], side: -1, mode: 'shaded',
        kicker: 'SCENE 01 — 暴風圈', h: '飛行艇', p: '動畫《CRASH》裡，闖進暴風圈、失控墜落的那架飛機。',
        spec: [['目標', '遠看輪廓一眼認得，推到特寫也不穿幫。'], ['做法', '四組渦輪引擎、螺旋槳、起落架、艙門全部拆件製作。'], ['規格', '70,446 面｜27 個部件｜18 組材質']] },
      { az: 150, el: 22, d: 9.6, f: [0, 0.7, -0.4], side: 1, mode: 'wire',
        kicker: 'TOPOLOGY — 佈線', h: '線，是順著曲面走的', p: '你看到的是模型真實的拓撲，不是特效。面數花在轉折上，平面一條多餘的線都不留。', stats: true },
      { az: 205, el: 32, d: 19, f: [0, 0.9, 0], side: -1, mode: 'shaded', x: 1,
        kicker: 'EXPLODED VIEW — 拆解', h: '27 個零件，各自獨立', p: '繼續捲動，把整架飛機拆開。每個零件都有自己的厚度與背面，要換裝、要綁定、要做破壞，都接得下去。', chips: ['可拆件', '可替換', '結構完整'] },
      { az: 352, el: 13, d: 5, f: [0, 1.1, 1.7], side: 1, mode: 'shaded',
        kicker: 'NEXT — 進入機艙', h: '從擋風玻璃進去', p: '外面看完了。繼續往下捲，鏡頭會穿過駕駛艙玻璃，帶你走進這架飛機的內部。', chips: ['駕駛艙', '下一站：機艙'] },
    ],
  },
  {
    id: 'console', no: '02', title: '操控台', en: 'CONTROL CONSOLE', scene: '駕駛艙', set: 'deck', mood: 'cockpit', bay: 0,
    accent: '#ff3b3b', pos: [DECK.x, 0, bayZ(0)], scale: 2.25, yaw: Math.PI, pad: 1.4, explode: 0.7, deliver: QUAD,
    shots: [
      { az: 160, el: 8, d: 5.8, f: [0, 1.35, 0], side: -1, mode: 'shaded',
        kicker: 'SCENE 02 — 駕駛艙', h: '操控台', p: '警報亮起，暴風就在擋風玻璃外。這是駕駛艙裡的那座操控台。',
        spec: [['目標', '大量擺進場景也不吃效能。'], ['做法', '只用 2,276 面做出清楚的機械輪廓。'], ['規格', '2,276 面｜12 個部件']] },
      { az: 204, el: 12, d: 6.6, f: [0, 1.95, 0], side: 1, mode: 'wire', x: 1,
        kicker: 'LOW POLY — 省面', h: '面數花在刀口上', p: '平板不浪費面，只在轉折與倒角加線。拆開來，12 個部件一目了然。', stats: true },
    ],
  },
  {
    id: 'char', no: '03', title: '男主角', en: 'PROTAGONIST', scene: '船員艙', set: 'deck', mood: 'cabin', bay: 1,
    accent: '#ffb347', pos: [DECK.x, 0, bayZ(1)], scale: 1.9, yaw: 0, pad: 1.5, explode: 0.9, deliver: QUAD,
    shots: [
      { az: -22, el: 6, d: 5.0, f: [0, 1.02, 0], side: 1, mode: 'shaded',
        kicker: 'SCENE 03 — 船員艙', h: '男主角', p: '穿過艙門，《CRASH》的主角就站在船員艙裡：飛行夾克、圍巾、工裝褲、護目鏡。',
        spec: [['目標', '風格化的比例，動起來不能破面。'], ['做法', '身體與服裝分層，配件獨立成件，方便換裝與綁定。'], ['規格', '52,698 面｜24 個部件｜23 組材質']] },
      { az: 150, el: 10, d: 4.6, f: [0, 1.0, 0], side: -1, mode: 'wire',
        kicker: 'TOPOLOGY — 佈線', h: '為了動起來而佈的線', p: '關節留足環線，皺褶順著布料受力的方向走。', stats: true },
      { az: 197, el: 6, d: 7.2, f: [0, 2.0, 0], side: 1, mode: 'clay', x: 1,
        kicker: 'LAYERS — 分層', h: '一層一層穿上去的', p: '夾克、褲子、靴子、頭髮、護目鏡——拆開來，每一件都是完整的模型。', chips: ['服裝分層', '配件獨立'] },
      { az: 372, el: 2, d: 1.9, f: [0, 1.7, 0.05], side: -1, mode: 'clay',
        kicker: 'FORM — 白模', h: '拿掉顏色，造型還在', p: '好的模型不靠貼圖遮醜。臉部結構、髮束、鏡框，白模就看得清楚。', chips: ['臉部造型', '髮型'] },
    ],
  },
  {
    id: 'pod', no: '04', title: '生物倉', en: 'BIO POD', scene: '實驗艙', set: 'deck', mood: 'lab', bay: 2,
    accent: '#1fffd2', pos: [DECK.x, 0, bayZ(2)], scale: 2.4, yaw: 0, pad: 1.4, explode: 0.6, deliver: QUAD,
    shots: [
      { az: 28, el: 8, d: 5.6, f: [0, 1.2, 0], side: -1, mode: 'shaded',
        kicker: 'SCENE 04 — 實驗艙', h: '生物倉', p: '再往後一間，整排生物倉泡在青綠色的光裡。',
        spec: [['目標', '透明與金屬兩種材質要分得開。'], ['做法', '玻璃、艙蓋、管路、儀表盒各自成件。'], ['規格', '8,386 面｜7 個部件']] },
      { az: -40, el: 10, d: 7, f: [0, 2.0, 0], side: 1, mode: 'clay', x: 1,
        kicker: 'STRUCTURE — 結構', h: '每個零件都有厚度', p: '頂蓋的卡榫、環狀管路、側邊儀表盒，拆開來都交代得清楚。', stats: true },
    ],
  },
  {
    id: 'arcade', no: '05', title: '遊戲機', en: 'ARCADE CABINET', scene: '遊戲角落', set: 'deck', mood: 'arcade', bay: 3,
    accent: '#39c8ff', pos: [DECK.x, 0, bayZ(3)], scale: 2.15, yaw: 0, pad: 1.4, explode: 0.75, deliver: QUAD,
    shots: [
      { az: -30, el: 8, d: 5.3, f: [0, 1.1, 0], side: 1, mode: 'shaded',
        kicker: 'SCENE 05 — 遊戲角落', h: '遊戲機', p: '長途飛行總要有地方殺時間。霓虹燈下，映像管螢幕還亮著。',
        spec: [['目標', '一眼就是那個年代的機台。'], ['做法', '弧面螢幕、搖桿、按鈕、投幣口、喇叭全部實體建模。'], ['規格', '8,844 面｜12 個部件']] },
      { az: 24, el: 9, d: 6.8, f: [0, 1.9, 0.2], side: -1, mode: 'wire', x: 1,
        kicker: 'TOPOLOGY — 佈線', h: '按鍵是真的按鍵', p: '螢幕弧面、搖桿球頭、每一顆按鈕，都不是貼圖假裝的。', stats: true },
    ],
  },
  {
    id: 'jukebox', no: '06', title: '點唱機', en: 'JUKEBOX', scene: '酒吧', set: 'deck', mood: 'lounge', bay: 4,
    accent: '#ff9a3d', pos: [DECK.x, 0, bayZ(4)], scale: 1.75, yaw: 0, pad: 1.4, explode: 1.0, deliver: QUAD,
    exit: { pos: [DECK.x, 2.4, -78.5], tgt: [DECK.x, 2.4, -90] },                  // 離開時飛向後艙門
    shots: [
      { az: 28, el: 8, d: 4.6, f: [0, 0.9, 0], side: -1, mode: 'shaded',
        kicker: 'SCENE 06 — 酒吧', h: '點唱機', p: '機艙最後一間是酒吧。木質機身、鍍鉻飾條、會發光的弧形燈管。',
        spec: [['目標', '木頭與鍍鉻的對比要漂亮。'], ['做法', '正面菱格網一格一格編出來，飾條獨立成件。'], ['規格', '7,896 面｜12 個部件']] },
      { az: -24, el: 8, d: 6.2, f: [0, 1.6, 0.1], side: 1, mode: 'wire', x: 1,
        kicker: 'NEXT — 後艙門', h: '網格是編出來的', p: '菱格網與弧形飾條，全是實際的幾何。繼續捲，後艙門要打開了。', stats: true },
    ],
  },
  {
    id: 'airship', no: '07', title: '熱氣球飛船', en: 'SKY SHIP', scene: '天空漁港', set: 'port', mood: 'port', flying: true, lift: 2.4,
    accent: '#ffd27a', pos: PORT, scale: 6.2, yaw: Math.PI / 2, pad: 3.6, wireOpacity: 0.5, explode: 1.0, deliver: QUAD,
    shots: [
      { az: -32, el: 3, d: 14, f: [0, 4.9, 0], side: 1, mode: 'shaded',
        kicker: 'SCENE 07 — 天空漁港', h: '熱氣球飛船', p: '艙門外是另一個世界：動畫《SMASH!》的天空漁港，船長的船就停在碼頭邊。',
        spec: [['目標', '一艘看得出有人在上面生活的船。'], ['做法', '補丁氣囊、纜繩、魚鰭尾翼，甲板堆滿木桶與漁獲。'], ['規格', '334,440 面｜255 個部件｜97 組材質']] },
      { az: 138, el: 14, d: 12.5, f: [0, 4.7, 0], side: -1, mode: 'wire',
        kicker: 'SCALE — 規模', h: '255 個部件，組成一艘船', p: '每條繩索、每塊甲板都是獨立物件。網站版自動減面到一半，原始檔細節完整保留。', stats: true },
      { az: 190, el: 8, d: 22, f: [0, 5.2, 0], side: 1, mode: 'shaded', x: 1,
        kicker: 'EXPLODED VIEW — 拆解', h: '把整艘船拆開', p: '繼續捲。255 個零件同時散開——這是一個場景的工作量，不只是一個模型。', chips: ['大型組件', '可拆件'] },
      { az: 384, el: -3, d: 4.6, f: [0, 3.5, 0], side: -1, mode: 'shaded',
        kicker: 'DETAIL — 特寫', h: '甲板上的生活感', p: '舵輪、船錨、地籠、油桶。場景會不會「活」，看的就是這些小東西。', chips: ['船體', '道具擺設'] },
    ],
  },
  {
    id: 'venom', no: '08', title: '猛毒胸像', en: 'DIGITAL SCULPT', scene: '雕刻暗室', set: 'chamber', mood: 'chamber', lift: 0.36,
    accent: '#b79bff', pos: CHAMBER, scale: 2.9, yaw: -0.15, pad: 1.9, explode: 0, deliver: ['高模雕刻', '171 萬面', 'FBX'],
    shots: [
      { az: -22, el: 5, d: 6.6, f: [0, 1.9, 0], side: 1, mode: 'shaded',
        kicker: 'SCENE 08 — 雕刻暗室', h: '猛毒胸像', p: '燈全暗，只留一盞聚光燈。個人練習的 Fan Art，171 萬面的高模雕刻。',
        spec: [['目標', '黏稠、有重量、會動的生物感。'], ['做法', '肌肉走向、觸手纏繞、張開的大口，全用筆刷推出來。'], ['規格', '1,712,975 面｜高模雕刻']] },
      { az: 150, el: 14, d: 5.8, f: [0, 1.85, 0], side: -1, mode: 'wire',
        kicker: 'HIGH POLY — 高模', h: '171 萬面的密度', p: '網站上是減面到約 17 萬面的版本，表面起伏一樣完整。', stats: true },
      { az: 10, el: 0, d: 2.5, f: [0, 2.3, 0.25], side: -1, mode: 'clay',
        kicker: 'DETAIL — 特寫', h: '每一顆牙都雕過', p: '白模最誠實。牙齒、皺褶、表面肌理，打什麼光都撐得住。', chips: ['細節雕刻', '生物造型'] },
    ],
  },
];

// 收尾：回到黃昏的天空漁港
export const FINALE = {
  about:   { pos: [-17, 8.5, 423], target: [2, 4.6, 399] },
  contact: { pos: [-30, 15, 442], target: [4, 7, 396] },
};
