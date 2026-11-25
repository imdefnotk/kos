# K.OS - Windows side setup
#
# Part 1 (no admin needed):
#   Creates the "Return to K.OS" shortcut on the Desktop and in the Start menu.
#   It asks "Restart into K.OS now?" and then restarts the PC.
#
# How to run: double-click kos-windows-setup.cmd in the same folder.
# After the shortcuts are made, it asks Windows for admin permission and then:
#   Turns off Windows Fast Startup (needed for safe dual boot) and shows
#   the Secure Boot state and the firmware boot order for checking.

param([switch]$Admin)

$ErrorActionPreference = 'Stop'

if ($Admin) {
    try { Start-Transcript -Path (Join-Path $PSScriptRoot 'setup-log-admin.txt') -Force | Out-Null } catch {}
}

trap {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host "At: $($_.InvocationInfo.PositionMessage)"
    if ($Admin) { Read-Host 'Press Enter to close' }
    exit 1
}

if (-not $Admin) {
    $kosDir = Join-Path $env:LOCALAPPDATA 'KOS'
    New-Item -ItemType Directory -Force -Path $kosDir | Out-Null

    $returnScript = Join-Path $kosDir 'Return-to-KOS.ps1'
    $body = @'
Add-Type -AssemblyName PresentationFramework
$answer = [System.Windows.MessageBox]::Show("Restart into K.OS now?`n`nSave your work first.", "K.OS", "YesNo", "Question")
if ($answer -eq "Yes") { shutdown.exe /r /t 0 }
'@
    Set-Content -Path $returnScript -Value $body -Encoding ASCII

    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('Desktop')
    $startMenu = [Environment]::GetFolderPath('Programs')

    foreach ($folder in @($desktop, $startMenu)) {
        $lnk = $shell.CreateShortcut((Join-Path $folder 'Return to K.OS.lnk'))
        $lnk.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$returnScript`""
        $lnk.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',27'
        $lnk.Description = 'Restart the PC into K.OS'
        $lnk.Save()
        Write-Host "Created: $(Join-Path $folder 'Return to K.OS.lnk')"
    }

    Write-Host ''
    Write-Host 'Next: Windows will ask for permission to turn off Fast Startup. Click Yes.'
    Start-Sleep -Seconds 2
    Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Verb RunAs -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Admin')
    exit 0
}

# ---------- Admin part ----------
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power' -Name HiberbootEnabled -Value 0 -Type DWord
Write-Host 'Fast Startup: OFF'

try {
    if (Confirm-SecureBootUEFI) { Write-Host 'Secure Boot: ON' } else { Write-Host 'Secure Boot: OFF' }
} catch {
    Write-Host 'Secure Boot: could not be read'
}

Write-Host ''
Write-Host 'Firmware boot list (the first entry under {fwbootmgr} is what the PC boots by default):'
bcdedit /enum firmware
Write-Host ''
Read-Host 'Done. Press Enter to close this window'
