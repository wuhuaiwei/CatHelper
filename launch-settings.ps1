$ErrorActionPreference = 'Stop'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
$app = Join-Path $PSScriptRoot 'app.py'
Start-Process -FilePath $pythonw -ArgumentList @(('"' + $app + '"'), '--settings') -WindowStyle Hidden
