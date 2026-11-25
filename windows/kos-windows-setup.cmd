@echo off
echo K.OS Windows setup. Please wait...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0kos-windows-setup.ps1'; & '%~dp0kos-windows-setup.ps1'" > "%~dp0setup-log.txt" 2>&1
type "%~dp0setup-log.txt"
echo.
echo (This text is also saved in setup-log.txt in this folder.)
pause
