// 網站內容的唯一來源：個人資料、作品、藝廊、服務、流程、獎項。
// 改文字改這裡；圖片路徑都是相對路徑（網站部署在子目錄下）。
//
// 作品的渲染圖由 Blender 產生，放在 renders/<id>/：
//   hero.jpg 1920x1080、card.jpg 1200x900、s1–s4.jpg 1600x900、clay.jpg / wire.jpg 1600x900（與 s1 同機位）、
//   turn/00.jpg–turn/23.jpg 1280x720（360° 轉台）、shots.json = [{ "file": "s1.jpg", "caption": "說明" }, …]
// 還沒產生的圖會顯示成深色的占位區塊，版面不會跳動。

export const PROFILE = {
  nameZh: '陳昭銘',
  nameEn: 'CHEN CHAO MING',
  role: '3D 建模師',
  email: 'jerry216066@gmail.com',
  // 電話預設不公開。要顯示在聯絡區就填入，例如 phone: '(+886) 9xx xxx xxx', phoneHref: '+8869xxxxxxxx'
  phone: '',
  phoneHref: '',
  claim: ['模型不只好看，', '還要能用。'],
  descriptor: '角色、硬表面載具、場景道具與數位雕刻',
  lead: '從角色、載具、場景道具到數位雕刻。每件作品都附上白模、線框與 360° 轉台——佈線、結構與拆件，經得起逐一檢查。',
  bio: [
    '我是陳昭銘，專注在 3D 建模與材質渲染。畢業專題動畫《CRASH》負責 3D 建模、材質渲染、角色動作調整與後製；動畫《SMASH!》負責 3D 建模、材質渲染、天空場景繪製與 3D/2D 整合後製。',
    '我在意的是模型交出去之後還能不能用：佈線為動畫準備好、零件拆得開、面數花在刀口上。好看是基本，能用才是重點。',
  ],
  heroStats: [['8', '件完整作品，附白模與線框'], ['219 萬', '個三角面'], ['5', '座動畫影展獎項']],
};

const QUAD = ['四邊面佈線', 'UV 已展開', 'FBX'];

// view：互動檢視器的設定（explode 拆解幅度、flying 從中心拆開、wireOpacity 線框濃度）
// still：渲染圖還沒產生時，主視覺改用的既有劇照（只用在同一部動畫的作品上）
// focus：主視覺被裁切時（例如手機直式畫面）要保留的焦點，寫法同 CSS object-position；主體在畫面中央就不用寫
export const WORKS = [
  {
    id: 'ship', no: '01', title: '飛行艇', en: 'AIRCRAFT', cat: '硬表面 · 載具', catEn: 'HARD SURFACE / VEHICLE',
    accent: '#3ff0c8', project: '動畫《CRASH》', feature: true, still: 'img/crash-4.jpg',
    deliver: ['四邊面佈線', 'UV 已展開', 'OBJ'],
    lead: '動畫《CRASH》裡闖進暴風圈、失控墜落的那架飛機。四組渦輪引擎、螺旋槳、起落架與艙門全部拆件製作，27 個零件各自有厚度與背面——要換裝、綁定或做破壞，都接得下去。',
    goal: '遠看輪廓一眼認得，推到特寫也不穿幫。',
    approach: '四組渦輪引擎、螺旋槳、起落架、艙門全部拆件製作。面數花在轉折上，平面一條多餘的線都不留。',
    clayNote: '線是順著曲面走的。拿掉材質，機身的轉折與倒角一樣交代得清楚。',
    view: { explode: 1.25, flying: true },
  },
  {
    id: 'console', no: '02', title: '操控台', en: 'CONTROL CONSOLE', cat: '場景道具', catEn: 'PROP',
    accent: '#ff3b3b', deliver: QUAD,
    lead: '一座駕駛艙操控台。只用 2,276 個三角面做出清楚的機械輪廓，大量擺進場景也不吃效能。',
    goal: '大量擺進場景也不吃效能。',
    approach: '平板不浪費面，只在轉折與倒角加線。拆開來，12 個部件一目了然。',
    clayNote: '面數花在刀口上。白模與線框下，每一道倒角的位置都看得到。',
    view: { explode: 0.7 },
  },
  {
    id: 'char', no: '03', title: '男主角', en: 'PROTAGONIST', cat: '角色', catEn: 'CHARACTER',
    accent: '#ffb347', project: '動畫《CRASH》', still: 'img/crash-3.jpg', deliver: QUAD, focus: '66% 40%',
    lead: '《CRASH》的主角：飛行夾克、圍巾、工裝褲與護目鏡。風格化的比例要能動起來不破面，所以身體與服裝分層、配件獨立成件，方便換裝與綁定。',
    goal: '風格化的比例，動起來不能破面。',
    approach: '身體與服裝分層，配件獨立成件。關節留足環線，皺褶順著布料受力的方向走。',
    clayNote: '好的模型不靠貼圖遮醜。拿掉顏色，臉部結構、髮束與鏡框一樣看得清楚。',
    view: { explode: 0.9 },
  },
  {
    id: 'pod', no: '04', title: '生物倉', en: 'BIO POD', cat: '場景道具', catEn: 'PROP',
    accent: '#1fffd2', deliver: QUAD,
    lead: '泡在青綠色光裡的生物倉。透明的玻璃與金屬外殼要分得開，所以玻璃、艙蓋、管路、儀表盒各自成件。',
    goal: '透明與金屬兩種材質要分得開。',
    approach: '玻璃、艙蓋、管路、儀表盒各自成件。頂蓋的卡榫、環狀管路、側邊儀表盒，每個零件都有厚度。',
    clayNote: '每個零件都有自己的厚度，白模下結構交代得一清二楚。',
    view: { explode: 0.6 },
  },
  {
    id: 'arcade', no: '05', title: '遊戲機', en: 'ARCADE CABINET', cat: '場景道具', catEn: 'PROP',
    accent: '#39c8ff', deliver: QUAD,
    lead: '一眼就是那個年代的街機。弧面映像管螢幕、搖桿、按鈕、投幣口與喇叭，全部實體建模。',
    goal: '一眼就是那個年代的機台。',
    approach: '弧面螢幕、搖桿、按鈕、投幣口、喇叭全部實體建模，不用貼圖假裝。',
    clayNote: '按鍵是真的按鍵。螢幕弧面、搖桿球頭、每一顆按鈕，都是實際的幾何。',
    view: { explode: 0.75 },
  },
  {
    id: 'jukebox', no: '06', title: '點唱機', en: 'JUKEBOX', cat: '場景道具', catEn: 'PROP',
    accent: '#ff9a3d', deliver: QUAD,
    lead: '木質機身、鍍鉻飾條與會發光的弧形燈管。重點是木頭與鍍鉻的對比；正面的菱格網，是一格一格編出來的。',
    goal: '木頭與鍍鉻的對比要漂亮。',
    approach: '正面菱格網一格一格編出來，飾條獨立成件。',
    clayNote: '網格是編出來的。菱格網與弧形飾條，全是實際的幾何。',
    view: { explode: 1.0 },
  },
  {
    id: 'airship', no: '07', title: '熱氣球飛船', en: 'SKY SHIP', cat: '硬表面 · 大型組件', catEn: 'HARD SURFACE / ASSEMBLY',
    accent: '#ffd27a', project: '動畫《SMASH!》', feature: true, still: 'img/smash-3.jpg', deliver: QUAD,
    lead: '動畫《SMASH!》裡船長的船，停在天空漁港的碼頭邊。要做出一艘看得出有人在上面生活的船：補丁氣囊、纜繩、魚鰭尾翼，甲板上堆滿木桶與漁獲。',
    goal: '一艘看得出有人在上面生活的船。',
    approach: '補丁氣囊、纜繩、魚鰭尾翼，甲板上的舵輪、船錨、地籠與油桶。255 個部件，每條繩索、每塊甲板都是獨立物件。',
    clayNote: '這是一個場景的工作量，不只是一個模型。255 個部件，在線框下一件件分得清楚。',
    view: { explode: 1.0, flying: true, wireOpacity: 0.5 },
  },
  {
    id: 'venom', no: '08', title: '猛毒胸像', en: 'DIGITAL SCULPT', cat: '數位雕刻', catEn: 'DIGITAL SCULPT',
    accent: '#b79bff', project: '個人練習 · Fan Art', deliver: ['高模雕刻', '171 萬面', 'FBX'],
    lead: '個人練習的 Fan Art，171 萬面的高模雕刻。黏稠、有重量、會動的生物感——肌肉走向、觸手纏繞、張開的大口，全用筆刷推出來。',
    goal: '黏稠、有重量、會動的生物感。',
    approach: '肌肉走向、觸手纏繞、張開的大口，全用筆刷推出來。每一顆牙都雕過。',
    clayNote: '白模最誠實。牙齒、皺褶、表面肌理，打什麼光都撐得住。',
    view: { explode: 0 },
  },
];

// 作品頁主圖庫的預設說明；renders/<id>/shots.json 有寫的話會取代這裡
export const SHOT_CAPTIONS = {
  's1.jpg': '三分之四視角',
  's2.jpg': '背面與側面',
  's3.jpg': '細節特寫',
  's4.jpg': '細節特寫',
};

// 首頁主視覺用的作品，與白模 / 線框對照帶用的作品
export const HOME = { hero: 'ship', compare: 'char' };

// 藝廊：w、h 是圖片的像素尺寸（用來預留版面）。alt 是同一場景的其他版本。
export const GALLERY = [
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
  { src: 'street-day', w: 1440, h: 810, title: '街角 · 晨昏夜', note: '同一個場景的三種時段打光：早晨、傍晚、夜晚。',
    alt: [['street-day', '早晨'], ['street-dusk', '傍晚'], ['street-night', '夜晚']] },
  { src: 'cake', w: 1200, h: 1200, title: '3D 插畫 · 蛋糕', note: '以手繪筆觸質感呈現的 3D 插畫。' },
];

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
  ['2026', '無限影展', '銀獎'],
  ['2026', '技專院校電腦動畫競賽', '佳作'],
  ['2026', '放視大賞', '決選'],
  ['2026', '新一代設計展', '參展'],
  ['2025', 'ARK 兔騎士影展', '銀獎'],
  ['2025', 'ARK 兔騎士影展', '最佳美術設定獎'],
  ['2025', 'ARK 兔騎士影展', '最佳 2D 動畫獎'],
];

export const CONTACT = {
  headline: ['有模型要做？', '寫信給我。'],
  send: '來信時附上用途、風格參考、規格需求與期限，越具體越好。',
};

export const renderPath = (id, file) => `renders/${id}/${file}`;
export const workById = (id) => WORKS.find((w) => w.id === id);
