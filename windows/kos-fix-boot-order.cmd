@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0kos-fix-boot-order.ps1'; & '%~dp0kos-fix-boot-order.ps1'"
pause
