@echo off
rem Opens K.OS Home full screen in Google Chrome (or Microsoft Edge).
rem With Python installed, it shows your real Steam games through kos-home-helper.py.
rem Without Python, it opens with the sample games.
rem Close it with Alt+F4.
setlocal
set "HERE=%~dp0"
set "PORT=47800"
set "URL=http://127.0.0.1:%PORT%/"
set "PAGE=%HERE%index.html"
set "PAGE=%PAGE:\=/%"
set "PING=$ProgressPreference='SilentlyContinue'; for($i=0;$i -lt 24;$i++){try{Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 '%URL%api/ping' | Out-Null; exit 0}catch{Start-Sleep -Milliseconds 250}}; exit 1"

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

rem Find Python (the py launcher first, then pythonw)
set "PY="
where pyw >nul 2>&1 && set "PY=pyw -3"
if not defined PY (
  where pythonw >nul 2>&1 && set "PY=pythonw"
)

set "TARGET=file:///%PAGE%"
if defined PY (
  powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try{Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 '%URL%api/ping' | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
  if errorlevel 1 start "" %PY% "%HERE%kos-home-helper.py" --port %PORT% --idle-exit 300 --log "%TEMP%\kos-home-helper.log"
  powershell -NoProfile -Command "%PING%" >nul 2>&1
  if not errorlevel 1 set "TARGET=%URL%"
)

start "" "%BROWSER%" --user-data-dir="%LocalAppData%\KOS-Launcher-Profile" --no-first-run --no-default-browser-check --disable-popup-blocking --autoplay-policy=no-user-gesture-required --start-fullscreen --app="%TARGET%"
