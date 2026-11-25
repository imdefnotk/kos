# K.OS - put K.OS (Bazzite) first in the PC's firmware boot order.
# After this, a normal power-on or restart goes to K.OS, and "Return to K.OS" works.
# Windows stays in the list, and "Switch to Windows" in K.OS still works as before.
# Run it again any time a Windows update puts Windows back on top.
#
# How to run: double-click kos-fix-boot-order.cmd (Windows asks for permission, click Yes).

param([switch]$Elevated)

$ErrorActionPreference = 'Stop'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host 'Windows will ask for permission. Click Yes.'
    Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -Verb RunAs -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Elevated')
    exit 0
}

try { Start-Transcript -Path (Join-Path $PSScriptRoot 'boot-order-log.txt') -Force | Out-Null } catch {}

trap {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Read-Host 'Nothing was changed. Press Enter to close'
    exit 1
}

# Find the firmware entry that starts K.OS: the one whose path is \EFI\FEDORA\SHIMX64.EFI
$text = (bcdedit /enum firmware) -join "`n"
$blocks = $text -split "`n\s*`n"
$kosId = $null
foreach ($b in $blocks) {
    if ($b -match '(?im)^path\s+\\EFI\\FEDORA\\SHIMX64\.EFI\s*$' -and $b -match '(?im)^identifier\s+(\{[0-9a-f\-]+\})') {
        $kosId = $Matches[1]
        break
    }
}

if (-not $kosId) {
    throw 'Could not find the K.OS (Bazzite) boot entry.'
}

Write-Host "K.OS boot entry: $kosId"
bcdedit /set '{fwbootmgr}' displayorder $kosId /addfirst
if ($LASTEXITCODE -ne 0) { throw 'bcdedit could not change the boot order.' }

Write-Host ''
Write-Host 'New boot order (first one starts by default):'
bcdedit /enum '{fwbootmgr}'
Write-Host ''
Read-Host 'Done. Press Enter to close this window'
