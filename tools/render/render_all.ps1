# Final renders, one Blender at a time at BelowNormal priority (4 cores / 8 GB machine).
# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
# Usage:
#   powershell -File tools\render\render_all.ps1                       # all eight works
#   powershell -File tools\render\render_all.ps1 -Keys ship,pod        # some works
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
# "powershell -File" passes a,b as one string, so split it here
$Keys = @($Keys | ForEach-Object { $_ -split "," } | Where-Object { $_ })
$Stills = @($Stills | ForEach-Object { $_ -split "," } | Where-Object { $_ })
$blender = "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
if (-not $Log) { $Log = Join-Path $root "tools\render\render_all.log" }
# child processes inherit BelowNormal
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

"START $($Keys -join ' ') $(Get-Date -Format s)" | Tee-Object -FilePath $Log -Append
foreach ($k in $Keys) {
  if (-not $NoHero) { Pass $k @("--only", "hero", "--samples", "$HeroSamples") }
  if ($Stills.Count) { Pass $k @("--only", ($Stills -join ","), "--samples", "$StillSamples") }
  if (-not $NoTurn) { Pass $k @("--only", "turn", "--turn-samples", "$TurnSamples") }
}
"ALL DONE $(Get-Date -Format s)" | Tee-Object -FilePath $Log -Append
