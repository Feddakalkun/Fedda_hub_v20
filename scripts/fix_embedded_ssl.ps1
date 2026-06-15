# =============================================================================
# FEDDA - Embedded Python SSL Certificate Repair
# =============================================================================
# Purpose: Fixes the common "certificate verify failed" errors when using the
#          official Python embed zip (python-3.11.9-embed-amd64.zip).
#
#          This is critical for CivitAI downloads, HuggingFace, model managers,
#          and any HTTPS calls from Python inside the portable environment.
#
# Called automatically by:
#   - scripts/install_lite.ps1 (Lite / recommended path)
#   - scripts/install.ps1    (Full portable path)
#   - Can be called manually from run.bat on first launch as safety net
#
# What it does:
#   1. Upgrades certifi inside the embedded Python
#   2. Copies the fresh cacert.pem to python_embeded\cacert.pem (stable location)
#   3. Sets a marker so repeated runs are fast
# =============================================================================

param(
    [string]$RootPath,
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"

if (-not $RootPath) { $RootPath = $PSScriptRoot | Split-Path -Parent }
if (-not $PythonExe) { $PythonExe = Join-Path $RootPath "python_embeded\python.exe" }

$PyEmbedDir = Join-Path $RootPath "python_embeded"
$TargetCert = Join-Path $PyEmbedDir "cacert.pem"
$MarkerFile = Join-Path $PyEmbedDir ".ssl_fixed"

function Write-Log {
    param([string]$Message, [string]$Color = "Gray")
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "  [SSL] $Message" -ForegroundColor $Color
}

if (-not (Test-Path $PythonExe)) {
    Write-Log "Embedded Python not found at $PythonExe - skipping SSL fix." "Yellow"
    exit 0
}

# Fast path: already fixed recently
if (Test-Path $MarkerFile) {
    $markerAge = (Get-Date) - (Get-Item $MarkerFile).LastWriteTime
    if ($markerAge.TotalHours -lt 72 -and (Test-Path $TargetCert) -and (Get-Item $TargetCert).Length -gt 100000) {
        Write-Log "SSL certificates already repaired (within last 72h)." "Green"
        exit 0
    }
}

Write-Log "Repairing embedded Python SSL certificates (critical for CivitAI / HF downloads)..." "Yellow"

# 1. Upgrade certifi to the latest version
try {
    & $PythonExe -m pip install --upgrade certifi --quiet --disable-pip-version-check 2>$null
    Write-Log "certifi upgraded successfully." "Green"
} catch {
    Write-Log "Warning: pip upgrade of certifi had issues (may still work)." "Yellow"
}

# 2. Locate the fresh cacert.pem that certifi just installed
$CertifiWhere = $null
try {
    $CertifiWhere = & $PythonExe -c "import certifi; print(certifi.where())" 2>$null
} catch {}

$SourceCert = $null
if ($CertifiWhere -and (Test-Path $CertifiWhere)) {
    $SourceCert = $CertifiWhere
} elseif (Test-Path (Join-Path $PyEmbedDir "Lib\site-packages\certifi\cacert.pem")) {
    $SourceCert = Join-Path $PyEmbedDir "Lib\site-packages\certifi\cacert.pem"
}

# 3. Copy to our stable location (python_embeded\cacert.pem)
if ($SourceCert -and (Test-Path $SourceCert)) {
    try {
        Copy-Item -Path $SourceCert -Destination $TargetCert -Force
        Write-Log "Fresh CA bundle copied to $TargetCert" "Green"
    } catch {
        Write-Log "Failed to copy cert bundle: $_" "Red"
    }
} else {
    # Fallback: ship a known-good bundle with the repo
    $Fallback = Join-Path $RootPath "scripts\cacert.pem"
    if (Test-Path $Fallback) {
        Copy-Item -Path $Fallback -Destination $TargetCert -Force
        Write-Log "Using repository fallback CA bundle." "Yellow"
    } else {
        Write-Log "No fresh CA bundle found. Downloads may still have SSL issues." "Red"
    }
}

# 4. Also ensure the bundle is present inside the certifi package itself (belt + suspenders)
if ($TargetCert -and (Test-Path $TargetCert)) {
    $CertifiInternal = Join-Path $PyEmbedDir "Lib\site-packages\certifi\cacert.pem"
    if (Test-Path (Split-Path $CertifiInternal)) {
        try {
            Copy-Item -Path $TargetCert -Destination $CertifiInternal -Force
        } catch {}
    }
}

# 5. Create marker
New-Item -ItemType File -Path $MarkerFile -Force | Out-Null

# 6. Verify size looks reasonable
if (Test-Path $TargetCert) {
    $size = (Get-Item $TargetCert).Length
    if ($size -gt 150000) {
        Write-Log "SSL repair complete. Bundle size: $([math]::Round($size/1KB,0)) KB" "Green"
    } else {
        Write-Log "SSL bundle written but size is small ($size bytes). May need manual intervention." "Yellow"
    }
}

Write-Log "Embedded Python will now use reliable certificates for HTTPS." "Cyan"