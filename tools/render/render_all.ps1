# 依序輸出正式渲染圖（低優先權，一次只跑一個 Blender，避免拖垮 4 核 / 8 GB 的機器）。
# 用法：
#   powershell -File tools\render\render_all.ps1                       # 全部八件作品
#   powershell -File tools\render\render_all.ps1 -Keys ship,pod        # 指定作品
#   powershell -File tools\render\render_all.ps1 -Keys ship -Stills card,s2 -NoHero -NoTurn
param(
  [string[]]$Keys = @("ship", "console", "char", "pod", "arcade", "jukebox", "airship", "venom"),
  [string[]]$Stills = @("card", "s1", "s2", "s3", "s4", "clay", "wire"),
  [int]$HeroSamples = 64,
  [int]$StillSamples = 32,
  [int]$TurnSamples = 24,
  [switch]$NoHero,
  [switch]$NoTurn,
  [string]$Log = ""
)
$blender = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
if (-not $Log) { $Log = Join-Path $root "tools\render\render_all.log" }
# 子行程會繼承 BelowNormal
(Get-Process -Id $PID).PriorityClass = "BelowNormal"

function Pass([string]$key, [string[]]$extra) {
  $script = "tools\render\scene_$key.py"
  if (-not (Test-Path $script)) { "SKIP $key (no $script)" | Tee-Object -FilePath $Log -Append; return }
  $t = Get-Date
  & $blender -b --factory-startup --python $script -- --quality final @extra |
    Select-String -Pattern "TIME|Traceback|Error|error" |
    ForEach-Object { $_.Line } | Tee-Object -FilePath $Log -Append
  "PASS $key $($extra -join ' ') : $([int]((Get-Date) - $t).TotalSeconds)s exit=$LASTEXITCODE" | Tee-Object -FilePath $Log -Append
}

foreach ($k in $Keys) {
  if (-not $NoHero) { Pass $k @("--only", "hero", "--samples", "$HeroSamples") }
  if ($Stills.Count) { Pass $k @("--only", ($Stills -join ","), "--samples", "$StillSamples") }
  if (-not $NoTurn) { Pass $k @("--only", "turn", "--turn-samples", "$TurnSamples") }
}
"ALL DONE $(Get-Date -Format s)" | Tee-Object -FilePath $Log -Append
