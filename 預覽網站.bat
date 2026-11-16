@echo off
rem Double-click to preview the site locally (uses the Python bundled with Blender).
cd /d "%~dp0"
set "PY=C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe"
if not exist "%PY%" set "PY=python"
start "" http://localhost:5173
"%PY%" serve.py site 5173
pause
