// 內容設定：作品、運鏡腳本、藝廊圖片。要改文字或鏡位，改這個檔案就好。
// 鏡位 shot：az 水平角（0 = 正面，正值往右繞）、el 仰角、d 距離、f 對焦點（相對展台中心，世界單位）
// side：模型在畫面的哪一側（-1 左 / 0 中 / 1 右），文字排在另一側
// mode：shaded 上色 / clay 白模 / wire 線框　　x：爆炸拆解程度 0–1（隨捲動展開）

export const PROFILE = {
  nameZh: '陳昭銘',
  nameEn: 'CHEN CHAO MING',
  email: 'jerry216066@gmail.com',
  // 電話預設不公開。要顯示在聯絡頁就填入，例如 phone: '(+886) 9xx xxx xxx', phoneHref: '+8869xxxxxxxx'
  phone: '',
  phoneHref: '',
  claim: ['模型不只好看，', '還要能用。'],
  lead: '角色、硬表面載具、場景道具到數位雕刻。這裡的每一個模型都能親手轉、拆開、切成線框——不用相信我說的，自己檢查。',
  heroStats: [['8', '件可互動模型'], ['219 萬', '三角面，全部能轉'], ['5', '座動畫影展獎項']],
};

const QUAD = ['四邊面佈線', 'UV 已展開', 'FBX'];

export const WORKS = [
  {
    id: 'ship', no: '01', title: '飛行艇', en: 'AIRCRAFT', project: 'CRASH · 畢業專題', type: '硬表面 · 載具',
    accent: '#ff6a3d', pos: [0, 0], scale: 7, lift: 1.3, yaw: 0, pad: 4.4, explode: 1.25, deliver: ['四邊面佈線', 'UV 已展開', 'OBJ'],
    shots: [
      { az: 36, el: 15, d: 11, f: [0, 2.1, 0], side: -1, mode: 'shaded',
        kicker: 'CASE 01 — 硬表面載具', h: '飛行艇', p: '動畫《CRASH》裡失控墜落的那架飛機。',
        spec: [['目標', '遠看輪廓一眼認得，推到特寫也不穿幫。'], ['做法', '四組渦輪引擎、螺旋槳、起落架、艙門全部拆件製作。'], ['規格', '70,446 面｜27 個部件｜18 組材質']] },
      { az: 150, el: 24, d: 9.6, f: [0, 2.0, -0.4], side: 1, mode: 'wire',
        kicker: 'TOPOLOGY — 佈線', h: '線，是順著曲面走的', p: '你看到的是模型真實的拓撲，不是特效。面數花在轉折上，平面一條多餘的線都不留。', stats: true },
      { az: 205, el: 34, d: 19, f: [0, 2.2, 0], side: -1, mode: 'shaded', x: 1,
        kicker: 'EXPLODED VIEW — 拆解', h: '27 個零件，各自獨立', p: '繼續捲動，把整架飛機拆開。每個零件都有自己的厚度與背面，要換裝、要綁定、要做破壞，都接得下去。', chips: ['可拆件', '可替換', '結構完整'] },
      { az: 308, el: 5, d: 4.3, f: [-2.6, 2.0, 0.9], side: 1, mode: 'shaded',
        kicker: 'DETAIL — 特寫', h: '近到這裡，還有東西看', p: '引擎軸心、管線、葉片都是建出來的幾何，不是貼圖畫的。', chips: ['渦輪引擎', '機械結構'] },
    ],
  },
  {
    id: 'char', no: '02', title: '男主角', en: 'PROTAGONIST', project: 'CRASH · 畢業專題', type: '角色建模',
    accent: '#ffb347', pos: [15, -11], scale: 1.9, lift: 0, yaw: 0, pad: 1.5, explode: 1.15, deliver: QUAD,
    shots: [
      { az: -24, el: 6, d: 4.9, f: [0, 1.32, 0], side: 1, mode: 'shaded',
        kicker: 'CASE 02 — 角色', h: '男主角', p: '《CRASH》的主角：飛行夾克、圍巾、工裝褲、護目鏡。',
        spec: [['目標', '風格化的比例，動起來不能破面。'], ['做法', '身體與服裝分層，配件獨立成件，方便換裝與綁定。'], ['規格', '52,698 面｜24 個部件｜23 組材質']] },
      { az: 162, el: 10, d: 4.5, f: [0, 1.3, 0], side: -1, mode: 'wire',
        kicker: 'TOPOLOGY — 佈線', h: '為了動起來而佈的線', p: '關節留足環線，皺褶順著布料受力的方向走。', stats: true },
      { az: 205, el: 8, d: 8.6, f: [0, 2.45, 0], side: 1, mode: 'clay', x: 1,
        kicker: 'LAYERS — 分層', h: '一層一層穿上去的', p: '夾克、褲子、靴子、頭髮、護目鏡——拆開來，每一件都是完整的模型。', chips: ['服裝分層', '配件獨立'] },
      { az: 376, el: 2, d: 1.9, f: [0, 2.0, 0.05], side: -1, mode: 'clay',
        kicker: 'FORM — 白模', h: '拿掉顏色，造型還在', p: '好的模型不靠貼圖遮醜。臉部結構、髮束、鏡框，白模就看得清楚。', chips: ['臉部造型', '髮型'] },
    ],
  },
  {
    id: 'console', no: '03', title: '操控台', en: 'CONTROL CONSOLE', project: 'CRASH · 場景道具', type: '場景道具',
    accent: '#ff3b3b', pos: [27, -23], scale: 2.25, lift: 0, yaw: 0, pad: 1.4, explode: 0.9, deliver: QUAD,
    shots: [
      { az: -34, el: 10, d: 5.4, f: [0, 1.4, 0], side: 1, mode: 'shaded',
        kicker: 'CASE 03 — 場景道具', h: '操控台', p: '駕駛艙裡亮起紅色警報的那一座。',
        spec: [['目標', '大量擺進場景也不吃效能。'], ['做法', '只用 2,276 面做出清楚的機械輪廓。'], ['規格', '2,276 面｜12 個部件']] },
      { az: 28, el: 12, d: 8.2, f: [0, 2.5, 0.1], side: -1, mode: 'wire', x: 1,
        kicker: 'LOW POLY — 省面', h: '面數花在刀口上', p: '平板不浪費面，只在轉折與倒角加線。', stats: true },
    ],
  },
  {
    id: 'pod', no: '04', title: '生物倉', en: 'BIO POD', project: 'CRASH · 場景道具', type: '場景道具',
    accent: '#1fffd2', pos: [23, -39], scale: 2.4, lift: 0, yaw: 0, pad: 1.4, explode: 0.9, deliver: QUAD,
    shots: [
      { az: 30, el: 8, d: 5.6, f: [0, 1.5, 0], side: -1, mode: 'shaded',
        kicker: 'CASE 04 — 場景道具', h: '生物倉', p: '玻璃艙體、金屬底座、外露管線。',
        spec: [['目標', '透明與金屬兩種材質要分得開。'], ['做法', '玻璃、艙蓋、管路、儀表盒各自成件。'], ['規格', '8,386 面｜7 個部件']] },
      { az: -38, el: 12, d: 8.6, f: [0, 2.7, 0], side: 1, mode: 'clay', x: 1,
        kicker: 'STRUCTURE — 結構', h: '每個零件都有厚度', p: '頂蓋的卡榫、環狀管路、側邊儀表盒，拆開來都交代得清楚。', stats: true },
    ],
  },
  {
    id: 'arcade', no: '05', title: '遊戲機', en: 'ARCADE CABINET', project: 'CRASH · 場景道具', type: '場景道具',
    accent: '#39c8ff', pos: [8, -50], scale: 2.15, lift: 0, yaw: 0, pad: 1.4, explode: 0.9, deliver: QUAD,
    shots: [
      { az: -30, el: 8, d: 5.3, f: [0, 1.4, 0], side: 1, mode: 'shaded',
        kicker: 'CASE 05 — 場景道具', h: '遊戲機', p: '復古大型機台，映像管螢幕還亮著。',
        spec: [['目標', '一眼就是那個年代的機台。'], ['做法', '弧面螢幕、搖桿、按鈕、投幣口、喇叭全部實體建模。'], ['規格', '8,844 面｜12 個部件']] },
      { az: 24, el: 10, d: 8, f: [0, 2.4, 0.2], side: -1, mode: 'wire', x: 1,
        kicker: 'TOPOLOGY — 佈線', h: '按鍵是真的按鍵', p: '螢幕弧面、搖桿球頭、每一顆按鈕，都不是貼圖假裝的。', stats: true },
    ],
  },
  {
    id: 'jukebox', no: '06', title: '點唱機', en: 'JUKEBOX', project: 'CRASH · 場景道具', type: '場景道具',
    accent: '#ff9a3d', pos: [-7, -58], scale: 1.75, lift: 0, yaw: 0, pad: 1.4, explode: 0.9, deliver: QUAD,
    shots: [
      { az: 28, el: 8, d: 4.5, f: [0, 1.2, 0], side: -1, mode: 'shaded',
        kicker: 'CASE 06 — 場景道具', h: '點唱機', p: '木質機身、鍍鉻飾條、會發光的弧形燈管。',
        spec: [['目標', '木頭與鍍鉻的對比要漂亮。'], ['做法', '正面菱格網一格一格編出來，飾條獨立成件。'], ['規格', '7,896 面｜12 個部件']] },
      { az: -24, el: 8, d: 6.6, f: [0, 1.95, 0.1], side: 1, mode: 'wire', x: 1,
        kicker: 'TOPOLOGY — 佈線', h: '網格是編出來的', p: '菱格網與弧形飾條，全是實際的幾何。', stats: true },
    ],
  },
  {
    id: 'airship', no: '07', title: '熱氣球飛船', en: 'SKY SHIP', project: 'SMASH! · 天空漁港', type: '場景 · 載具',
    accent: '#ffd27a', pos: [-26, -47], scale: 6.2, lift: 1.5, yaw: Math.PI / 2, pad: 3.6, wireOpacity: 0.34, explode: 1.0, deliver: QUAD,
    shots: [
      { az: -32, el: 3, d: 13.5, f: [0, 4.3, 0], side: 1, mode: 'shaded',
        kicker: 'CASE 07 — 大型場景物件', h: '熱氣球飛船', p: '動畫《SMASH!》裡，船長的那艘船。',
        spec: [['目標', '一艘看得出有人在上面生活的船。'], ['做法', '補丁氣囊、纜繩、魚鰭尾翼，甲板堆滿木桶與漁獲。'], ['規格', '334,440 面｜255 個部件｜97 組材質']] },
      { az: 138, el: 16, d: 11.5, f: [0, 4.0, 0], side: -1, mode: 'wire',
        kicker: 'SCALE — 規模', h: '255 個部件，組成一艘船', p: '每條繩索、每塊甲板都是獨立物件。網站版自動減面到一半，原始檔細節完整保留。', stats: true },
      { az: 190, el: 8, d: 22, f: [0, 4.6, 0], side: 1, mode: 'shaded', x: 1,
        kicker: 'EXPLODED VIEW — 拆解', h: '把整艘船拆開', p: '繼續捲。255 個零件同時散開——這是一個場景的工作量，不只是一個模型。', chips: ['大型組件', '可拆件'] },
      { az: 384, el: -3, d: 4.6, f: [0, 2.6, 0], side: -1, mode: 'shaded',
        kicker: 'DETAIL — 特寫', h: '甲板上的生活感', p: '舵輪、船錨、地籠、油桶。場景會不會「活」，看的就是這些小東西。', chips: ['船體', '道具擺設'] },
    ],
  },
  {
    id: 'venom', no: '08', title: '猛毒胸像', en: 'DIGITAL SCULPT', project: '個人練習 · Fan Art', type: '數位雕刻',
    accent: '#b79bff', pos: [-38, -27], scale: 2.9, lift: 0, yaw: -0.15, pad: 1.9, explode: 0, deliver: ['高模雕刻', '171 萬面', 'FBX'],
    shots: [
      { az: -22, el: 5, d: 6.6, f: [0, 1.85, 0], side: 1, mode: 'shaded',
        kicker: 'CASE 08 — 數位雕刻', h: '猛毒胸像', p: '個人練習的 Fan Art，171 萬面的高模雕刻。',
        spec: [['目標', '黏稠、有重量、會動的生物感。'], ['做法', '肌肉走向、觸手纏繞、張開的大口，全用筆刷推出來。'], ['規格', '1,712,975 面｜高模雕刻']] },
      { az: 150, el: 14, d: 5.8, f: [0, 1.8, 0], side: -1, mode: 'wire',
        kicker: 'HIGH POLY — 高模', h: '171 萬面的密度', p: '網站上是減面到約 17 萬面的版本，表面起伏一樣完整。', stats: true },
      { az: 10, el: 0, d: 2.5, f: [0, 2.25, 0.25], side: -1, mode: 'clay',
        kicker: 'DETAIL — 特寫', h: '每一顆牙都雕過', p: '白模最誠實。牙齒、皺褶、表面肌理，打什麼光都撐得住。', chips: ['細節雕刻', '生物造型'] },
    ],
  },
];

// 環形藝廊（相機站在圓心往外看）
export const GALLERY = {
  center: [-34, 6], radius: 9.5, eye: 2.3,
  items: [
    { src: 'station', w: 1440, h: 612, title: '機械巨構', note: '以對稱幾何與複雜表面細節表現精密機械的體量感。' },
    { src: 'planet', w: 1004, h: 1200, title: '鋼鐵行星', note: '被高度機械化改造的行星，與一艘散發紅光的探測船。' },
    { src: 'pilgrim', w: 945, h: 1200, title: '朝聖者', note: '神聖的光自上方傾瀉，孤獨的朝聖者伸手觸碰星軌刻痕。' },
    { src: 'deity', w: 1071, h: 1179, title: '紅紗神祇', note: '布料紋理與冰冷金屬的融合，黑暗奇幻的史詩氛圍。' },
    { src: 'ruin', w: 961, h: 1200, title: '崩解', note: '大型結構物的破壞動態，逆光下的沙塵與空間深度。' },
    { src: 'crash-1', w: 1440, h: 603, title: 'CRASH · 劇照', note: '畢業專題《CRASH》：負責 3D 建模、材質渲染、角色動作調整與後製。' },
    { src: 'crash-2', w: 1440, h: 603, title: 'CRASH · 劇照', note: '美式漫畫線條結合 3D 渲染的風格化表現。' },
    { src: 'crash-3', w: 1440, h: 604, title: 'CRASH · 劇照', note: '護目鏡映出的火光——角色特寫鏡頭。' },
    { src: 'crash-4', w: 1440, h: 600, title: 'CRASH · 暴風圈', note: '雷電交加的災難高空。' },
    { src: 'smash-1', w: 1440, h: 612, title: 'SMASH! · 劇照', note: '《SMASH!》：負責 3D 建模、材質渲染、天空場景繪製與 3D/2D 整合後製。' },
    { src: 'smash-2', w: 1344, h: 572, title: 'SMASH! · 天空漁港', note: '懸在雲端的吊橋與港口。' },
    { src: 'smash-3', w: 1440, h: 612, title: 'SMASH! · 啟航', note: '熱氣球飛船駛過積雨雲。' },
    { src: 'diner-robot', w: 1151, h: 648, title: 'The Diner 臨摹', note: '臨摹 Blender 短片《The Diner》，挑戰極致的材質做舊。' },
    { src: 'diner-bar', w: 1440, h: 810, title: 'The Diner · 吧檯', note: '磨損的皮革椅面、鏽蝕的金屬底座與斑駁的黑板。' },
    { src: 'diner-lamp', w: 1440, h: 788, title: 'The Diner · 燈管', note: '燈管內的積垢、粗糙水泥牆與飄動的飛蛾微塵。' },
    { src: 'wave', w: 1440, h: 601, title: '卡通渲染海浪', note: '日系動漫風格的海浪材質探索。' },
    { src: 'street-day', w: 1440, h: 810, title: '街角 · 晨昏夜', note: '同一個場景的三種時段打光：早晨、傍晚、夜晚。', alt: ['street-day', 'street-dusk', 'street-night'], altLabel: ['早晨', '傍晚', '夜晚'] },
    { src: 'cake', w: 1200, h: 1200, title: '3D 插畫 · 蛋糕', note: '以手繪筆觸質感呈現的 3D 插畫。' },
  ],
};

// 服務：寫「你會拿到什麼」
export const SERVICES = [
  ['角色', '造型、服裝、配件分層製作，佈線為動畫準備好。'],
  ['硬表面 · 載具', '飛行器、機械、武器——結構說得通，特寫撐得住。'],
  ['場景道具', '大量、省面數、風格一致，擺進場景就能用。'],
  ['數位雕刻', '生物、胸像、造型開發的高模雕刻。'],
  ['材質與渲染', '從寫實做舊到卡通渲染，跟著專案的風格走。'],
  ['動態與合成', '角色動作調整、3D 與 2D 的整合後製。'],
];

export const PROCESS = [
  ['01', '聊需求', '用途、風格、規格、期限。'],
  ['02', '報價排程', '確認範圍、修改次數與交期。'],
  ['03', '製作確認', '粗模、細節、材質，每個階段都給你看。'],
  ['04', '交付', '模型檔與規格說明，一次交齊。'],
];

export const AWARDS = [
  ['2026', '無限影展 銀獎'],
  ['2026', '技專院校電腦動畫競賽 佳作'],
  ['2026', '放視大賞 決選'],
  ['2026', '新一代設計展 參展'],
  ['2025', 'ARK 兔騎士影展 銀獎'],
  ['2025', 'ARK 兔騎士影展 最佳美術設定獎'],
  ['2025', 'ARK 兔騎士影展 最佳 2D 動畫獎'],
];
