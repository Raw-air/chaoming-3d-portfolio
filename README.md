# 陳昭銘 3D 作品集網站

以作品圖為主的專業作品集：首頁是作品索引、白模對照、藝廊、關於與聯絡；
每件作品有自己的頁面（`work.html?id=<作品 key>`），放完成渲染、白模 / 線框對照、360° 轉台，
以及按下「檢查拓撲」才載入的 3D 檢視器（線框 / 白模、旋轉、拆解）。
動態只有幾種、都很節制：進場淡入、卡片慢速放大、燈箱交叉淡化、規格數字跳動、頁面淡入淡出；
系統設定開啟「減少動態效果」的訪客會看到靜態版本。

## 頁面結構

- **首頁 `site/index.html`**：主視覺（飛行艇）→ 簡介數字 → 8 件作品卡片 → 完成圖 ⇄ 白模 / 線框對照（男主角）→ 藝廊 18 張（點圖放大，街角有晨昏夜三個版本）→ 關於（簡介、服務、流程、獎項）→ 聯絡。
- **作品頁 `site/work.html?id=ship`**：主視覺 → 介紹與「專案 / 類型 / 交付」→ 規格數字（三角面、頂點、部件、材質，取自 `models/stats.json`）→ 目標 / 做法 → 完成渲染 s1–s4 → 對照滑桿 → 360° 轉台 → 拓撲檢視器 → 上一件 / 下一件。

作品 key：`ship console char pod arcade jukebox airship venom`

## 資料夾

| 路徑 | 用途 |
| --- | --- |
| `site/` | **網站本體**，上線時只需要上傳這個資料夾 |
| `site/js/content.js` | **所有文字與資料**：個人資料、作品介紹、藝廊、服務、流程、獎項、聯絡 |
| `site/js/home.js` | 首頁 |
| `site/js/work.js` | 作品頁（轉台、規格數字、圖庫） |
| `site/js/viewer.js` | 拓撲檢視器（three.js，按下按鈕才載入） |
| `site/js/common.js` | 共用：導覽列、圖片占位、燈箱、對照滑桿、進場動畫 |
| `site/css/style.css` | 全站樣式 |
| `site/renders/<key>/` | 作品渲染圖（由 Blender 產生，見下方） |
| `site/models/*.glb` | 由 Blender 轉出的網頁用模型（含 Draco 壓縮與拓撲線框），`stats.json` 是面數等規格 |
| `site/img/*.jpg` | 藝廊圖片（從作品集 PDF 與 `素材/作品集沒有的圖` 轉出） |
| `tools/build_models.py`、`tools/modellib.py` | Blender 轉檔腳本：上材質、歸一化、減面、匯出 GLB |
| `tools/render/` | 作品渲染：`scene_<key>.py` 是每件作品的布景、材質與鏡頭，`common.py` 是共用工具，`render_all.ps1` 依序輸出正式圖（細節見 `tools/render/README.md`） |
| `tools/shot.mjs` | 用無頭瀏覽器幫網站截圖、測試拖曳（不必開視窗就能檢查版面） |
| `serve.py`、`預覽網站.bat` | 本機預覽用 |

## 作品渲染圖

每件作品一個資料夾 `site/renders/<key>/`，檔名固定：

| 檔案 | 尺寸 | 用在 |
| --- | --- | --- |
| `hero.jpg` | 1920×1080 | 作品頁主視覺、首頁主視覺與寬卡片、上一件 / 下一件 |
| `card.jpg` | 1200×900 | 首頁作品卡片 |
| `s1.jpg`–`s4.jpg` | 1600×900 | 作品頁圖庫（三分之四視角、背面 / 側面、兩張細節）；滑過卡片時淡入 s1 |
| `clay.jpg`、`wire.jpg` | 1600×900 | 白模、線框（與 s1 同機位），對照滑桿用 |
| `turn/00.jpg`–`turn/23.jpg` | 1280×720 | 360° 轉台，每格 15° |
| `shots.json` | — | 圖說：`[{"file": "s1.jpg", "caption": "說明"}, …]` |

還沒產生的圖會顯示成深色的占位區塊（寫著作品名），版面不會跳動；
飛行艇、男主角、熱氣球飛船在主視覺缺圖時會先用動畫劇照代替（`content.js` 的 `still`）。

### 重新渲染

每件作品的布景都是 Blender 腳本（`tools/render/scene_<key>.py`），改完後在專案資料夾執行（PowerShell）：

```powershell
# 先用草稿看結果（640×360，一張約半分鐘），輸出到別的資料夾，不會蓋掉正式圖
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --factory-startup --python tools\render\scene_ship.py -- --quality draft --only hero,s1 --out D:\temp\ship
# 正式輸出到 site\renders\：一次一個 Blender、低優先權，一件作品約 40 分鐘（這台電腦只能用 CPU 算）
powershell -ExecutionPolicy Bypass -File tools\render\render_all.ps1 -Keys ship
powershell -ExecutionPolicy Bypass -File tools\render\render_all.ps1 -Keys console -Stills s1,s2 -NoHero -NoTurn   # 只重算幾張
```

## 本機預覽

雙擊 `預覽網站.bat`，瀏覽器會開啟 <http://localhost:5173>。
（直接雙擊 `index.html` 無法運作，瀏覽器不允許從檔案系統載入 JS 模組。）

需要網路：字型、three.js 與 Draco 解碼器（只有拓撲檢視器會用到）是從 CDN 載入的。

## 修改內容

- **所有文字**：`site/js/content.js`。`PROFILE` 是個人資料與首頁標語，`WORKS` 是 8 件作品（介紹、目標、做法、交付、強調色 `accent`），`GALLERY`、`SERVICES`、`PROCESS`、`AWARDS`、`CONTACT` 各自對應首頁區塊。
- **電話**：`PROFILE.phone` 預設空白不顯示，填入後聯絡區會多一個撥號按鈕。
- **首頁主視覺 / 對照帶用哪件作品**：`content.js` 的 `HOME`。
- **藝廊圖片**：把 JPG 放進 `site/img/`，在 `GALLERY` 加一筆（`w`、`h` 填圖片的像素尺寸）。
- **作品圖說**：寫在 `renders/<key>/shots.json`（由渲染腳本產生，要改請改 `scene_<key>.py` 裡的說明文字）；沒有的話用 `content.js` 的 `SHOT_CAPTIONS`。

## 檢查版面

改完樣式或程式後，可以不開瀏覽器視窗直接截圖檢查（需要先啟動本機預覽）：

```powershell
D:\Nodejs\node.exe tools\shot.mjs "http://localhost:5173/work.html?id=ship" --tiles D:\temp\ship           # 桌機寬度，整頁分段截圖
D:\Nodejs\node.exe tools\shot.mjs "http://localhost:5173/" --w 390 --h 800 --mobile --tiles D:\temp\home   # 手機寬度
```

指令最後會列出載入失敗的檔案與主控台錯誤；拖曳、點擊、按鍵等操作的寫法見 `tools/shot.mjs` 開頭的說明。

## 重新轉出模型

原始模型沒有貼圖，顏色是轉檔腳本依部件名稱指定的（`tools/build_models.py` 裡的 `PAL` 色票與各個 `color_*` 函式）。
換了模型或想調顏色後，在專案資料夾執行（PowerShell）：

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" -b --factory-startup --python tools\build_models.py -- 素材 site\models
```

只想重轉其中幾個，在最後加上 key，例如 `ship char`
（可用的 key：`ship char console pod arcade jukebox airship venom`）。

## 線上版本（GitHub Pages）

- 預覽網址：<https://raw-air.github.io/chaoming-3d-portfolio/>
- 原始碼：<https://github.com/Raw-air/chaoming-3d-portfolio>（`main` 分支是整個專案，`gh-pages` 分支只有 `site/` 的內容）

改完網站後，更新線上版本的步驟（在專案資料夾的 PowerShell 執行；這台電腦用的是資料夾裡的可攜版 Git）：

```powershell
.\Git\bin\git.exe add -A
.\Git\bin\git.exe commit -m "更新網站"
.\Git\bin\git.exe push
.\Git\bin\git.exe subtree push --prefix site origin gh-pages
```

第一次推送會跳出 GitHub 登入視窗，登入後就會記住。推送後約一分鐘生效。
`素材/` 與作品集 PDF 已列在 `.gitignore`，不會被上傳。

## 上線到其他主機

`site/` 是純靜態網站，沒有後端。把整個 `site` 資料夾上傳到任何靜態主機即可，例如
Netlify（拖曳資料夾上傳）、Cloudflare Pages、GitHub Pages 或一般虛擬主機。
