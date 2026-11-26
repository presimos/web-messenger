$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$clientDir = Join-Path $repoRoot 'frontend\client'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw 'Установите Python 3.11 или новее и добавьте Python Launcher в PATH.'
}
$pythonVersionText = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0) {
    throw 'Не удалось запустить Python 3.11 или новее через команду py -3.'
}
$pythonVersion = [version]$pythonVersionText.Trim()
if ($pythonVersion -lt [version]'3.11.0') {
    throw "Требуется Python 3.11 или новее; обнаружен $pythonVersion."
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $nodeCommand -or -not $pnpmCommand) {
    throw 'Установите Node.js и pnpm, затем повторите настройку.'
}
$nodeVersionText = (& node --version).Trim().TrimStart('v')
$nodeVersion = [version]$nodeVersionText
$nodeSupported = ($nodeVersion.Major -eq 20 -and $nodeVersion -ge [version]'20.19.0') -or ($nodeVersion.Major -ge 22 -and $nodeVersion -ge [version]'22.12.0')
if (-not $nodeSupported) {
    throw "Для Vite требуется Node.js 20.19+ или 22.12+; обнаружен $nodeVersion."
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3 -m venv (Join-Path $backendDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать виртуальное окружение backend.' }
}
& $venvPython -m pip install -r (Join-Path $backendDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости backend.' }

Push-Location $clientDir
try {
    & pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить зависимости frontend.' }
}
finally {
    Pop-Location
}

$backendEnv = Join-Path $backendDir '.env'
if (-not (Test-Path -LiteralPath $backendEnv)) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 32
    $rng.GetBytes($bytes)
    $rng.Dispose()
    $secret = [Convert]::ToBase64String($bytes)
    $envText = Get-Content -LiteralPath (Join-Path $backendDir '.env.example') -Raw
    $envText = $envText -replace '(?m)^SECRET_KEY=.*$', "SECRET_KEY=$secret"
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($backendEnv, $envText, $utf8WithoutBom)
}

$clientEnv = Join-Path $clientDir '.env'
if (-not (Test-Path -LiteralPath $clientEnv)) {
    Copy-Item -LiteralPath (Join-Path $clientDir '.env.example') -Destination $clientEnv
}

Write-Host "Настройка завершена. Python $pythonVersion, Node.js $nodeVersion."
Write-Host 'Для запуска выполните: .\scripts\start-windows.ps1'
