# Levanta WICK en modo desarrollo: backend (uvicorn) + frontend (Vite) y abre el navegador.
# Uso: ./dev.ps1     (Ctrl+C en cada ventana para cerrar)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

foreach ($tool in @('uv', 'npm')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "Falta '$tool'. Instalalo y volvé a correr ./dev.ps1"
    }
}

Push-Location $backend
uv sync
Pop-Location
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Push-Location $frontend
    npm install
    Pop-Location
}

Start-Process powershell -WorkingDirectory $backend -ArgumentList '-NoExit', '-Command', 'uv run uvicorn wick.main:app --host 127.0.0.1 --port 8765'
Start-Process powershell -WorkingDirectory $frontend -ArgumentList '-NoExit', '-Command', 'npm run dev'

# Espera a que el backend responda antes de abrir el navegador.
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/v1/health' -TimeoutSec 2 | Out-Null
        $ok = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ok) { Write-Warning 'El backend no respondió en 60 s; revisá su ventana.' }
Start-Process 'http://localhost:5173'
