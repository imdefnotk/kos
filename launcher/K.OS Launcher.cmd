@echo off
rem Opens the K.OS launcher prototype full screen in Google Chrome (or Microsoft Edge).
rem Close it with Alt+F4.
setlocal
set "HERE=%~dp0"
set "PAGE=%HERE%index.html"
set "PAGE=%PAGE:\=/%"

set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not exist "%BROWSER%" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%BROWSER%" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%BROWSER%" (
  echo Google Chrome or Microsoft Edge was not found. Please install Google Chrome.
  pause
  exit /b 1
)

start "" "%BROWSER%" --user-data-dir="%LocalAppData%\KOS-Launcher-Profile" --no-first-run --no-default-browser-check --disable-popup-blocking --autoplay-policy=no-user-gesture-required --start-fullscreen --app="file:///%PAGE%"
