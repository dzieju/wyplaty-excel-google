# start-all.ps1
# Single-command starter for Windows (PowerShell)
# Usage:
#   .\start-all.ps1          -> dev mode (backend + frontend dev)
#   .\start-all.ps1 -Mode prod  -> build frontend, serve via backend

param(
  [ValidateSet("dev","prod")]
  [string]$Mode = "dev"
)

$ErrorActionPreference = "Stop"

# Helper: check executable in PATH
function Has-Command($name) {
  return (Get-Command $name -ErrorAction SilentlyContinue) -ne $null
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Repo root: $repoRoot"

# Paths
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$venvDir = Join-Path $backendDir "venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

# 1) Check Python
if (-not (Has-Command "python")) {
  Write-Error "Python not found in PATH. Install Python 3.8+ and try again."
  exit 1
}

# 2) Setup backend venv if missing
if (-not (Test-Path $venvDir)) {
  Write-Host "Creating Python virtualenv..."
  Push-Location $backendDir
  python -m venv venv
  Pop-Location
} else {
  Write-Host "Virtualenv exists."
}

# 3) Install backend requirements
Write-Host "Installing backend dependencies..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $backendDir "requirements.txt")

# 4) Check Node for frontend (prod or dev needs Node)
if (-not (Has-Command "node")) {
  Write-Warning "Node.js not found in PATH. Frontend steps will fail without Node. Install Node.js (LTS) and re-run the script."
  if ($Mode -eq "prod") {
    Write-Error "Mode 'prod' requires Node.js to build the frontend. Aborting."
    exit 1
  }
} else {
  # 5) Install frontend deps (skip optional to avoid native modules issues on Windows)
  Write-Host "Installing frontend dependencies (skipping optional native deps)..."
  Push-Location $frontendDir
  # cleanup potentially broken installs
  if (Test-Path node_modules) {
    Write-Host "Removing existing node_modules (to avoid optional-deps issues)..."
    Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
  }
  if (Test-Path package-lock.json) {
    Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
  }
  npm config set optional false
  npm install --no-optional
  Pop-Location
}

# 6) Start processes
if ($Mode -eq "dev") {
  Write-Host "Starting backend and frontend in dev mode..."

  # Start backend in new PowerShell window
  $backendCmd = "cd `"$backendDir`"; .\venv\Scripts\Activate.ps1; python app.py"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$backendCmd -WindowStyle Normal
  Start-Sleep -Seconds 1

  if (Has-Command "node") {
    # Start frontend dev server in new PowerShell window
    $frontendCmd = "cd `"$frontendDir`"; npm run dev"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$frontendCmd -WindowStyle Normal
  } else {
    Write-Warning "Node not available: cannot start frontend dev server. Install Node and re-run script to launch frontend."
  }

  Write-Host "Dev servers starting. Check new PowerShell windows. Backend on http://localhost:5000, frontend on http://localhost:5173 (if started)."
  exit 0
}
else {
  Write-Host "Starting in PROD mode: building frontend and serving static files from backend."

  if (-not (Has-Command "node")) {
    Write-Error "Node.js required for prod build but not found. Install Node.js and re-run."
    exit 1
  }

  # Build frontend
  Push-Location $frontendDir
  npm run build
  Pop-Location

  # Start backend (serves frontend/dist)
  $backendCmd = "cd `"$backendDir`"; .\venv\Scripts\Activate.ps1; python app.py"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$backendCmd -WindowStyle Normal

  Write-Host "Backend started (serving built frontend). Open http://localhost:5000"
  exit 0
}
