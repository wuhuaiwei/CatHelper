param(
    [string]$Python = 'python',
    [string]$Iscc = '',
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '1.2.0',
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectDir = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectDir
try {
    if (-not $Iscc) {
        $candidates = @(
            (Join-Path $projectDir '.tools\inno\ISCC.exe'),
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
        )
        $Iscc = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $Iscc) {
            $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($compiler) { $Iscc = $compiler.Source }
        }
    }
    if (-not $Iscc) { throw 'Install Inno Setup 6 or pass -Iscc C:\path\ISCC.exe.' }
    & $Python -c 'import PyInstaller, sys; assert sys.maxsize > 2**32'
    if ($LASTEXITCODE -ne 0) { throw 'Install PyInstaller in a 64-bit Python environment.' }
    if (-not $SkipTests) {
        & $Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed.' }
    }
    $icon = Join-Path $projectDir 'assets\cat.ico'
    & $Python -m PyInstaller --noconfirm --windowed --onedir --noupx --name CatAssistant --icon $icon --add-data "${icon};assets" --specpath build --workpath build/pyinstaller --distpath dist app.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    $reportPath = Join-Path $projectDir 'build\installation-check.json'
    if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
    $appExe = Join-Path $projectDir 'dist\CatAssistant\CatAssistant.exe'
    $check = Start-Process -FilePath $appExe -ArgumentList '--check-installation', "`"$reportPath`"" -WindowStyle Hidden -PassThru
    if (-not $check.WaitForExit(30000)) {
        $check.Kill()
        throw 'Packaged application smoke check timed out.'
    }
    if ($check.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $reportPath)) {
        throw 'Packaged application smoke check failed.'
    }
    $report = Get-Content -Raw -LiteralPath $reportPath -Encoding UTF8 | ConvertFrom-Json
    if (-not ($report.ok -and $report.icon_exists -and $report.settings_rounded -and $report.browse_matches_input_height)) {
        throw 'Packaged UI verification failed. See build\installation-check.json.'
    }
    & $Iscc '/Qp' "/DAppVersion=$Version" 'packaging\installer.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    $installer = Join-Path $projectDir "dist\CatAssistant-Setup-$Version-x64.exe"
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $installer
    "$($hash.Hash.ToLowerInvariant())  $([IO.Path]::GetFileName($installer))" | Set-Content -Encoding ascii 'dist\SHA256SUMS.txt'
    Write-Host "Installer ready: $installer"
} finally {
    Pop-Location
}
