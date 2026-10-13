param([switch]$Uninstall)
$ErrorActionPreference = 'Stop'
function Update-ShellMenus {
    if (-not ('AIHelp.ShellNotification' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace AIHelp {
    public static class ShellNotification {
        [DllImport("shell32.dll")]
        public static extern void SHChangeNotify(uint eventId, uint flags, IntPtr item1, IntPtr item2);
    }
}
'@
    }
    [AIHelp.ShellNotification]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
}
$keys = @(
    'HKCU:\Software\Classes\*\shell\AIHelp',
    'HKCU:\Software\Classes\Directory\shell\AIHelp',
    'HKCU:\Software\Classes\Directory\Background\shell\AIHelp'
)
if ($Uninstall) {
    foreach ($key in $keys) {
        if (Test-Path -LiteralPath $key) { Remove-Item -LiteralPath $key -Recurse }
    }
    Update-ShellMenus
    $settingsKey = 'HKCU:\Software\Classes\Directory\Background\shell\AIHelpSettings'
    if (Test-Path -LiteralPath $settingsKey) { Remove-Item -LiteralPath $settingsKey -Recurse }
    Update-ShellMenus
    Write-Host 'Companion context menu removed.'
    exit
}
$python = (Get-Command python.exe -ErrorAction Stop).Source
$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'pythonw.exe not found. Install Python with Tkinter first.' }
$app = Join-Path $PSScriptRoot 'app.py'
foreach ($key in $keys) {
    $placeholder = if ($key -like '*Background*') { '%V' } else { '%1' }
    New-Item -Path $key -Force | Out-Null
    Set-Item -LiteralPath $key -Value 'AI Help...'
    New-ItemProperty -LiteralPath $key -Name 'MUIVerb' -Value 'AI Help...' -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name 'Position' -Value 'Top' -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name 'Icon' -Value $pythonw -Force | Out-Null
    if ($key -like '*Background*') {
        Remove-ItemProperty -LiteralPath $key -Name 'MultiSelectModel' -ErrorAction SilentlyContinue
    } else {
        New-ItemProperty -LiteralPath $key -Name 'MultiSelectModel' -Value 'Single' -Force | Out-Null
    }
    $commandKey = Join-Path $key 'command'
    New-Item -Path $commandKey -Force | Out-Null
    $command = '"' + $pythonw + '" "' + $app + '" --target "' + $placeholder + '"'
    Set-Item -LiteralPath $commandKey -Value $command
    if ((Get-Item -LiteralPath $commandKey).GetValue('') -ne $command) {
        throw "Failed to verify context menu command: $commandKey"
    }
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $python -c "from ai_help.core import load_config; from ai_help.shell import refresh_menu; refresh_menu(load_config()['nickname'])"
    if ($LASTEXITCODE -ne 0) { throw 'Failed to update companion menu name.' }
} finally {
    Pop-Location
}
Update-ShellMenus
Write-Host 'Companion menu installed for files, folders and folder backgrounds.'
