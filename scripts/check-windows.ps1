$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$clientDir = Join-Path $repoRoot 'frontend\client'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Сначала выполните .\scripts\setup-windows.ps1.'
}

Push-Location $backendDir
try {
    & $venvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Проверки backend завершились с ошибкой.' }
}
finally {
    Pop-Location
}

Push-Location $clientDir
try {
    & pnpm build
    if ($LASTEXITCODE -ne 0) { throw 'Сборка frontend завершилась с ошибкой.' }
    & pnpm lint
    if ($LASTEXITCODE -ne 0) { throw 'Проверка frontend завершилась с ошибкой.' }
}
finally {
    Pop-Location
}

Write-Host 'Проверки backend и frontend завершились успешно.'
