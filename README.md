# 陳昭銘 3D 作品集網站

互動式 3D 作品集：每件作品都有自己的場景（暴風圈、機艙各艙間、天空漁港、雕刻暗室……），
捲動頁面時鏡頭沿著編排好的運鏡穿過這些場景，串成一趟連續的旅程。
每件作品都可以拖曳旋轉、切換「上色 / 白模 / 線框」，最後是環形藝廊、服務項目與聯絡方式。

## 場景旅程

暴風圈（飛行艇）→ 駕駛艙（操控台）→ 船員艙（男主角）→ 實驗艙（生物倉）→ 遊戲角落（遊戲機）→ 酒吧（點唱機）→ 天空漁港（熱氣球飛船）→ 雕刻暗室（猛毒）→ 藝廊 → 黃昏漁港（服務、聯絡）

## 特效一覽

| 效果 | 觸發方式 | 程式位置 |
| --- | --- | --- |
| 鏡頭扭曲、色散、放射殘影、FOV 衝刺 | 在作品之間飛行、快速捲動時 | `site/js/fx.js` 的 `createWarpPass` |
| 掃描式材質切換（線框 ⇄ 上色 ⇄ 白模） | 抵達作品、切換檢視模式時 | `site/js/main.js` 的 `scanTo` |
| 爆炸拆解圖 | 捲到「拆解」鏡頭，或按 `X` / 點「拆解」 | 鏡位的 `x` 值；作品的 `explode` 是拆開幅度 |
| 滑鼠水波、故障切片 | 移動滑鼠、切換模式時 | `createWarpPass` |
| 藝廊圖片彎曲、漣漪、色散 | 在藝廊捲動、滑鼠移到圖片上 | `fx.js` 的 `galleryMaterial` |
| 跑馬燈大字、逐字進場、亂碼解碼、自訂游標 | 隨捲動 | `fx.js` 與 `site/css/style.css` 的 v2 區塊 |

系統設定開啟「減少動態效果」的訪客會自動看到沒有扭曲的版本。

## 資料夾

| 路徑 | 用途 |
| --- | --- |
| `site/` | **網站本體**，上線時只需要上傳這個資料夾 |
| `site/js/data.js` | 個人資料、藝廊、服務、流程、獎項——改文字內容改這裡 |
| `site/js/scenes.js` | 場景腳本：每件作品的場景、位置、鏡位、光線氛圍（`MOODS`） |
| `site/js/sets.js` | 場景建構：暴風圈、機艙五個艙間、天空漁港、雕刻暗室 |
| `site/js/main.js` | 運鏡、轉場、互動程式 |
| `site/js/fx.js` | 後製扭曲、天空、藝廊材質、游標、文字動態 |
| `site/models/*.glb` | 由 Blender 轉出的網頁用模型（含 Draco 壓縮與拓撲線框） |
| `site/img/*.jpg` | 藝廊圖片（從作品集 PDF 與 `素材/作品集沒有的圖` 轉出） |
| `tools/build_models.py` | Blender 轉檔腳本：上材質、歸一化、減面、匯出 GLB |
| `serve.py`、`預覽網站.bat` | 本機預覽用 |

## 本機預覽

雙擊 `預覽網站.bat`，瀏覽器會開啟 <http://localhost:5173>。
（直接雙擊 `index.html` 無法運作，瀏覽器不允許從檔案系統載入 3D 模組。）

需要網路：three.js、Draco 解碼器與字型是從 CDN 載入的。

## 修改內容

- **文字 / 聯絡方式 / 得獎紀錄**：`site/js/data.js` 最上方的 `PROFILE`、以及 `SERVICES`、`PROCESS`、`AWARDS`。
- **場景、作品位置、鏡位、光線氛圍**：改 `site/js/scenes.js`（`WORKS`、`MOODS` 等）。每件作品的 `shots`：`az` 水平角、`el` 仰角、`d` 距離、`f` 對焦點、`side` 模型在畫面左右、`mode` 該鏡頭的顯示模式、`x` 爆炸拆解程度（0–1）。
- **藝廊圖片**：把 JPG 放進 `site/img/`，在 `GALLERY.items` 加一筆（`w`、`h` 填圖片的像素尺寸）。

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

改完網站後，更新線上版本的步驟（在專案資料夾的 Git Bash 執行）：

```bash
git add -A && git commit -m "更新網站"
git push
git subtree push --prefix site origin gh-pages
```

推送後約一分鐘生效。`素材/` 與作品集 PDF 已列在 `.gitignore`，不會被上傳。

## 上線到其他主機

`site/` 是純靜態網站，沒有後端。把整個 `site` 資料夾上傳到任何靜態主機即可，例如
Netlify（拖曳資料夾上傳）、Cloudflare Pages、GitHub Pages 或一般虛擬主機。
