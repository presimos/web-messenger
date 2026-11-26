$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$clientDir = Join-Path $repoRoot 'frontend\client'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython) -or -not (Test-Path -LiteralPath (Join-Path $clientDir 'node_modules'))) {
    throw 'Сначала выполните .\scripts\setup-windows.ps1.'
}

$backendCommand = "Set-Location -LiteralPath '$backendDir'; & '$venvPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "Set-Location -LiteralPath '$clientDir'; pnpm dev --host 127.0.0.1"
$backendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendCommand))
$frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendCommand))

Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-EncodedCommand', $backendEncoded)
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-EncodedCommand', $frontendEncoded)
Write-Host 'Backend: http://127.0.0.1:8000/health'
Write-Host 'Клиент:  http://127.0.0.1:5173'
Write-Host 'Для остановки закройте оба окна PowerShell.'
