# ============================================================================
# FEDDA Code Update - Fast, minimal, pulls latest code from GitHub
# Used by auto-update in run.bat - focused on speed
# For full maintenance (custom nodes, deps), see update_logic.ps1
# ============================================================================

param([switch]$SilentMode)

$ErrorActionPreference = "Stop"
$ScriptPath = $PSScriptRoot
$RootPath = Split-Path -Parent $ScriptPath
Set-Location $RootPath

if (-not $SilentMode) {
    Write-Host "`n===================================================" -ForegroundColor Cyan
    Write-Host "  FEDDA CODE UPDATE" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}

# ============================================================================
# GIT SETUP
# ============================================================================
$GitEmbedded = Join-Path $RootPath "git_embeded\cmd\git.exe"
if (Test-Path $GitEmbedded) {
    $GitExe = $GitEmbedded
    $env:PATH = "$(Split-Path $GitExe);$env:PATH"
} else {
    $GitExe = "git"
}

# Fix dubious ownership errors (local config only - never modify user's global gitconfig)
$env:GIT_CONFIG_GLOBAL = Join-Path $RootPath ".gitconfig"
& $GitExe config --file "$env:GIT_CONFIG_GLOBAL" --add safe.directory '*' 2>$null

# ============================================================================
# 1. CHECK IF GIT REPO EXISTS
# ============================================================================
if (-not (Test-Path (Join-Path $RootPath ".git"))) {
    if (-not $SilentMode) {
        Write-Host "`n  Initializing git from GitHub..." -ForegroundColor Yellow
    }
    & $GitExe init
    & $GitExe remote add origin https://github.com/Feddakalkun/Fedda_hub_v20.git
}

# ============================================================================
# 2. PULL LATEST CODE
# ============================================================================
if (-not $SilentMode) {
    Write-Host "`n  Pulling latest code from GitHub..." -ForegroundColor Yellow
}

try {
    $ErrorActionPreference = "Continue"
    & $GitExe fetch origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch failed"
    }
    & $GitExe reset --hard origin/main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "git reset failed"
    }
    & $GitExe clean -fd 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    
    if (-not $SilentMode) {
        Write-Host "  [OK] Code updated successfully." -ForegroundColor Green
    }
} catch {
    if (-not $SilentMode) {
        Write-Host "  [WARN] Git update failed: $_" -ForegroundColor Yellow
    }
    exit 1
}

# ============================================================================
# DONE
# ============================================================================
if (-not $SilentMode) {
    Write-Host "`n===================================================" -ForegroundColor Green
    Write-Host "  UPDATE COMPLETE" -ForegroundColor Green
    Write-Host "===================================================" -ForegroundColor Green
}

exit 0
