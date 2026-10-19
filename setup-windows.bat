@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo Tao moi truong Python 3.12 va cai dat VieNeu Video Studio...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Dang tu dong cai dat Python 3.12...
  py install 3.12
  if errorlevel 1 goto error
)
py -3.12 -m venv --clear .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -e ".[tts,ui]"
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
".venv\Scripts\python.exe" -m studio.cli doctor
echo.
echo Hoan tat. Cai FFmpeg neu doctor bao thieu; sau do chay start-windows.bat.
pause
exit /b 0
:error
echo Cai dat that bai. Kiem tra Python 3.12, ket noi Internet va thong bao o tren.
pause
exit /b 1
