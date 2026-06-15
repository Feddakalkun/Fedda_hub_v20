# ============================================================================
# FEDDA Update & Repair - auto-detects portable vs lite mode
# ============================================================================

param([switch]$SilentMode)

$ErrorActionPreference = "Stop"
$ScriptPath = $PSScriptRoot
$RootPath = Split-Path -Parent $ScriptPath
Set-Location $RootPath

if (-not $SilentMode) {
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "      FEDDA UPDATE & REPAIR" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}

# ============================================================================
# DETECT MODE
# ============================================================================
$PortablePy = Join-Path $RootPath "python_embeded\python.exe"
$VenvPy     = Join-Path $RootPath "venv\Scripts\python.exe"
$NodeEmbed  = Join-Path $RootPath "node_embeded\node.exe"
$ComfyDir = Join-Path $RootPath "ComfyUI"
$CustomNodesDir = Join-Path $ComfyDir "custom_nodes"

# Detection order: venv = Lite (even if python_embeded also exists, since
# Lite now embeds Python 3.11.9 but still creates a venv from it).
# Full/portable = has python_embeded AND node_embeded (no venv).
if (Test-Path $VenvPy) {
    $Mode = "lite"
    $PyExe = $VenvPy
    if (-not $SilentMode) { Write-Host "`n  Mode: Lite (venv)" -ForegroundColor Green }
} elseif ((Test-Path $PortablePy) -and (Test-Path $NodeEmbed)) {
    $Mode = "portable"
    $PyExe = $PortablePy
    if (-not $SilentMode) { Write-Host "`n  Mode: Full (portable)" -ForegroundColor Green }
} elseif (Test-Path $PortablePy) {
    # python_embeded only, no venv and no node_embeded - treat as portable
    $Mode = "portable"
    $PyExe = $PortablePy
    if (-not $SilentMode) { Write-Host "`n  Mode: Full (portable - no node_embeded)" -ForegroundColor Yellow }
} else {
    Write-Host "`n  [ERROR] No Python environment found!" -ForegroundColor Red
    Write-Host "  Run install.bat first." -ForegroundColor Yellow
    exit 1
}

# Git setup
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

if (-not (Test-Path $ComfyDir)) {
    Write-Host "`n  [ERROR] ComfyUI directory not found!" -ForegroundColor Red
    Write-Host "  Run install.bat first." -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# 0. UPDATE COMFYUI CORE
# ============================================================================
Write-Host "`n[0/3] Updating ComfyUI core..." -ForegroundColor Yellow
try {
    Set-Location $ComfyDir
    $ErrorActionPreference = "Continue"
    # ComfyUI is installed at a pinned commit (detached HEAD), so we can't
    # just `git pull`. Fetch latest master and reset hard to it instead.
    & $GitExe fetch origin master 2>&1 | Out-Null
    & $GitExe checkout master 2>&1 | Out-Null
    & $GitExe reset --hard origin/master 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    Set-Location $RootPath
    Write-Host "  ComfyUI core updated to latest master." -ForegroundColor Green
} catch {
    Set-Location $RootPath
    Write-Host "  [WARNING] ComfyUI core update failed (non-fatal): $_" -ForegroundColor Yellow
}

# ============================================================================
# 1. CUSTOM NODES - install missing / update existing (from nodes.json)
# ============================================================================
$NodesConfigFile = Join-Path $RootPath "config\nodes.json"
if (-not (Test-Path $NodesConfigFile)) {
    Write-Host "  [ERROR] config/nodes.json not found!" -ForegroundColor Red
    exit 1
}

$ModuleNodeScript = Join-Path $RootPath "scripts\module_nodes.ps1"
if (Test-Path $ModuleNodeScript) {
    . $ModuleNodeScript
    $NodesConfig = Get-FeddaNodeConfig -RootPath $RootPath -Logger { param($Message, $Color) Write-Host "  $Message" -ForegroundColor $Color }
} else {
    Write-Host "  [WARNING] Module node helper missing; using config/nodes.json directly." -ForegroundColor Yellow
    $NodesConfig = Get-Content $NodesConfigFile -Raw | ConvertFrom-Json
}

if (-not (Test-Path $CustomNodesDir)) {
    New-Item -ItemType Directory -Path $CustomNodesDir -Force | Out-Null
}

# Smart update: only git-pull existing nodes once per week
$NodeUpdateMarker = Join-Path $RootPath ".last_node_update"
$NeedNodeUpdate = $true

if (Test-Path $NodeUpdateMarker) {
    $LastUpdate = (Get-Item $NodeUpdateMarker).LastWriteTime
    $DaysSince = ((Get-Date) - $LastUpdate).TotalDays
    if ($DaysSince -lt 7) {
        $NeedNodeUpdate = $false
        $DaysLeft = [math]::Ceiling(7 - $DaysSince)
        Write-Host "`n[1/3] Custom nodes up to date (next check in ${DaysLeft}d)" -ForegroundColor Green
    }
}

$InstalledCount = 0
$UpdatedCount = 0
$SkippedCount = 0
$FailedCount = 0

function Sync-NodeSubmodules {
    param([string]$NodeDir)
    $GitmodulesFile = Join-Path $NodeDir ".gitmodules"
    if (Test-Path $GitmodulesFile) {
        try {
            Set-Location $NodeDir
            $ErrorActionPreference = "Continue"
            & $GitExe submodule update --init --recursive 2>&1 | Out-Null
            $ErrorActionPreference = "Stop"
            Set-Location $RootPath
        } catch {
            Set-Location $RootPath
        }
    }
}

# Always check for missing nodes
$HasMissing = $false
foreach ($Node in $NodesConfig) {
    if ($Node.local -eq $true) { continue }
    $NodeDir_Check = Join-Path $CustomNodesDir $Node.folder
    if (-not (Test-Path $NodeDir_Check)) { $HasMissing = $true; break }
}

# Always force-update nodes that ship new model architectures regularly
$CriticalNodes = @("ComfyUI-LTXVideo", "RES4LYF", "ComfyUI-KJNodes")
foreach ($CritNode in $CriticalNodes) {
    $CritDir = Join-Path $CustomNodesDir $CritNode
    if (Test-Path $CritDir) {
        try {
            Set-Location $CritDir
            $ErrorActionPreference = "Continue"
            & $GitExe pull 2>&1 | Out-Null
            $ErrorActionPreference = "Stop"
            Set-Location $RootPath
            Sync-NodeSubmodules -NodeDir $CritDir
        } catch {
            Set-Location $RootPath
        }
    }
}

if ($NeedNodeUpdate -or $HasMissing) {
    if ($NeedNodeUpdate) {
        Write-Host "`n[1/3] Syncing custom nodes from config/nodes.json..." -ForegroundColor Yellow
    } else {
        Write-Host "`n[1/3] Installing missing custom nodes..." -ForegroundColor Yellow
    }

    foreach ($Node in $NodesConfig) {
        if ($Node.local -eq $true) {
            Write-Host "  [$($Node.name)] Local node - skipped" -ForegroundColor Gray
            continue
        }

        $NodeDir_Install = Join-Path $CustomNodesDir $Node.folder

        if (-not (Test-Path $NodeDir_Install)) {
            # Clone missing node
            Write-Host "  [$($Node.name)] Installing..." -ForegroundColor White
            try {
                $ErrorActionPreference = "Continue"
                & $GitExe clone --depth 1 $Node.url "$NodeDir_Install" 2>&1 | Out-Null
                $ErrorActionPreference = "Stop"
                if ($LASTEXITCODE -eq 0) {
                    $InstalledCount++
                    Write-Host "  [$($Node.name)] Installed OK" -ForegroundColor Green
                    Sync-NodeSubmodules -NodeDir $NodeDir_Install

                    $ReqFile = Join-Path $NodeDir_Install "requirements.txt"
                    if (Test-Path $ReqFile) {
                        Write-Host "  [$($Node.name)] Installing dependencies..." -ForegroundColor Gray
                        $SkipPkgs = @('^\s*insightface','^\s*byaldi','^\s*nano-graphrag','^\s*kaleido','^\s*qwen-vl-utils','^\s*fastparquet')
                        $ReqContent = Get-Content $ReqFile
                        $Filtered = $ReqContent
                        foreach ($p in $SkipPkgs) { $Filtered = $Filtered | Where-Object { $_ -notmatch $p } }
                        $TmpReq = Join-Path $NodeDir_Install "_req_filtered.txt"
                        Set-Content -Path $TmpReq -Value $Filtered
                        $ErrorActionPreference = "Continue"
                        & $PyExe -m pip install -r "$TmpReq" --no-warn-script-location 2>&1 | Out-Null
                        $ErrorActionPreference = "Stop"
                        Remove-Item $TmpReq -Force -ErrorAction SilentlyContinue
                    }
                } else {
                    Write-Host "  [$($Node.name)] Clone failed!" -ForegroundColor Red
                    $FailedCount++
                }
            }
            catch {
                Write-Host "  [$($Node.name)] Error: $_" -ForegroundColor Red
                $FailedCount++
            }
        }
        elseif ($NeedNodeUpdate) {
            # Update existing node
            Write-Host "  [$($Node.name)] Updating..." -ForegroundColor Gray
            try {
                Set-Location $NodeDir_Install
                & $GitExe pull 2>&1 | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [$($Node.name)] Git pull failed (non-fatal)" -ForegroundColor Yellow
                }
                $UpdatedCount++
                Set-Location $RootPath
                Sync-NodeSubmodules -NodeDir $NodeDir_Install
            }
            catch {
                Write-Host "  [$($Node.name)] Update failed (non-fatal): $_" -ForegroundColor Yellow
                Set-Location $RootPath
            }

            $ReqFile = Join-Path $NodeDir_Install "requirements.txt"
            if (Test-Path $ReqFile) {
                $SkipPkgs = @('^\s*insightface','^\s*byaldi','^\s*nano-graphrag','^\s*kaleido','^\s*qwen-vl-utils','^\s*fastparquet')
                $ReqContent = Get-Content $ReqFile
                $Filtered = $ReqContent
                foreach ($p in $SkipPkgs) { $Filtered = $Filtered | Where-Object { $_ -notmatch $p } }
                $TmpReq = Join-Path $NodeDir_Install "_req_filtered.txt"
                Set-Content -Path $TmpReq -Value $Filtered
                $ErrorActionPreference = "Continue"
                & $PyExe -m pip install -r "$TmpReq" --no-warn-script-location 2>&1 | Out-Null
                $ErrorActionPreference = "Stop"
                Remove-Item $TmpReq -Force -ErrorAction SilentlyContinue
            }
        }
        else {
            $SkippedCount++
        }
    }

    if ($NeedNodeUpdate) {
        "Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $NodeUpdateMarker -Force
    }

    $Parts = @()
    if ($InstalledCount -gt 0) { $Parts += "$InstalledCount installed" }
    if ($UpdatedCount -gt 0)  { $Parts += "$UpdatedCount updated" }
    if ($SkippedCount -gt 0)  { $Parts += "$SkippedCount up to date" }
    if ($FailedCount -gt 0)   { $Parts += "$FailedCount failed" }
    Write-Host "`n  Summary: $($Parts -join ', ')" -ForegroundColor Cyan
}

$WanAnimatePatch = Join-Path $RootPath "scripts\patch_wan_animate_preprocess.ps1"
if (Test-Path $WanAnimatePatch) {
    Write-Host "  Applying WanAnimate preprocess compatibility patch..." -ForegroundColor Gray
    & powershell -ExecutionPolicy Bypass -File "$WanAnimatePatch" -RootPath "$RootPath"
}

$LtxVideoPatch = Join-Path $RootPath "scripts\patch_ltxvideo_kornia.ps1"
if (Test-Path $LtxVideoPatch) {
    Write-Host "  Applying LTXVideo Kornia compatibility patch..." -ForegroundColor Gray
    & powershell -ExecutionPolicy Bypass -File "$LtxVideoPatch" -RootPath "$RootPath"
}

$KJNodesPatch = Join-Path $RootPath "scripts\patch_kjnodes_ltx_audio_vae.ps1"
if (Test-Path $KJNodesPatch) {
    Write-Host "  Applying KJNodes LTX audio VAE compatibility patch..." -ForegroundColor Gray
    & powershell -ExecutionPolicy Bypass -File "$KJNodesPatch" -RootPath "$RootPath"
}

# ============================================================================
# 1b. PATCH PYTHON DEPENDENCIES - fix known version conflicts
# ============================================================================
Write-Host "`n[1b/3] Patching Python dependencies..." -ForegroundColor Yellow

# Florence2 requires transformers >= 4.45 for is_flash_attn_greater_or_equal_2_10
$TransformersVersion = & $PyExe -c "import transformers; print(transformers.__version__)" 2>$null
$NeedsTransformersUpgrade = $true
if ($TransformersVersion -match '^(\d+)\.(\d+)') {
    $Major = [int]$Matches[1]; $Minor = [int]$Matches[2]
    if ($Major -gt 4 -or ($Major -eq 4 -and $Minor -ge 45)) { $NeedsTransformersUpgrade = $false }
}
if ($NeedsTransformersUpgrade) {
    Write-Host "  Upgrading transformers (Florence2 fix)..." -ForegroundColor White
    & $PyExe -m pip install --upgrade transformers --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  transformers upgraded OK" -ForegroundColor Green
} else {
    Write-Host "  transformers OK ($TransformersVersion)" -ForegroundColor Green
}

# ============================================================================
# 2. FRONTEND - npm install
# ============================================================================
Write-Host "`n[2/3] Updating frontend dependencies..." -ForegroundColor Yellow
$FrontendDir = Join-Path $RootPath "frontend"

if (Test-Path $FrontendDir) {
    Set-Location $FrontendDir

    if ($Mode -eq "portable") {
        $NodeExeDir = Join-Path $RootPath "node_embeded"
        # Ensure npm shims exist
        if (Test-Path $NodeExeDir) {
            $NpmShim = Join-Path $NodeExeDir "node_modules\npm\bin\npm.cmd"
            $NpxShim = Join-Path $NodeExeDir "node_modules\npm\bin\npx.cmd"
            if (Test-Path $NpmShim) { Copy-Item $NpmShim $NodeExeDir -Force }
            if (Test-Path $NpxShim) { Copy-Item $NpxShim $NodeExeDir -Force }
        }
        $NpmCmd = Join-Path $NodeExeDir "npm.cmd"
        if (Test-Path $NpmCmd) {
            & "$NpmCmd" "install" 2>&1 | Out-Null
            Write-Host "  Frontend dependencies updated." -ForegroundColor Green
        }
        else {
            $NodeExe = Join-Path $NodeExeDir "node.exe"
            $NpmCli = Join-Path $NodeExeDir "node_modules\npm\bin\npm-cli.js"
            if (Test-Path $NpmCli) {
                & "$NodeExe" "$NpmCli" "install" 2>&1 | Out-Null
                Write-Host "  Frontend dependencies updated." -ForegroundColor Green
            }
            else {
                Write-Host "  [WARNING] npm not found - run install.bat first" -ForegroundColor Yellow
            }
        }
    } else {
        # Lite mode - use system npm
        & npm install 2>&1 | Out-Null
        Write-Host "  Frontend dependencies updated." -ForegroundColor Green
    }

    Set-Location $RootPath
}

# ============================================================================
# 3. SYNC COMFYUI REQUIREMENTS
# ============================================================================

# Ensure required ComfyUI core dependencies are in sync after ComfyUI updates
Write-Host "`n[2a/3] Syncing ComfyUI requirements..." -ForegroundColor Yellow
$ComfyRequirements = Join-Path $ComfyDir "requirements.txt"
if (Test-Path $ComfyRequirements) {
    try {
        & $PyExe -m pip install -r "$ComfyRequirements" --no-warn-script-location 2>&1 | Out-Null
        Write-Host "  ComfyUI requirements synced." -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] ComfyUI requirements sync failed (non-fatal): $_" -ForegroundColor Yellow
    }
}

# Ensure backend voice fallback dependency exists after update
try {
    & $PyExe -m pip install edge-tts --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  edge-tts synced." -ForegroundColor Green
} catch {
    Write-Host "  [WARNING] edge-tts sync failed (non-fatal): $_" -ForegroundColor Yellow
}

# Keep Comfy preview defaults enabled for end users.
Write-Host "`n[2b/3] Applying Comfy preview defaults..." -ForegroundColor Yellow
$PreviewSetupScript = Join-Path $RootPath "scripts\setup_comfyui_config.py"
if (Test-Path $PreviewSetupScript) {
    try {
        & $PyExe "$PreviewSetupScript" 2>&1 | Out-Null
        Write-Host "  Preview defaults applied (Execution=auto, VHS=Always)." -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] Preview defaults update failed (non-fatal): $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARNING] setup_comfyui_config.py not found, skipping preview defaults." -ForegroundColor Yellow
}

# Ensure Z-Image core model files exist so prompts don't fail validation on fresh installs.
Write-Host "`n[2c/3] Ensuring Z-Image core models..." -ForegroundColor Yellow
$EnsureZImageScript = Join-Path $RootPath "scripts\ensure_zimage_core_models.ps1"
if (Test-Path $EnsureZImageScript) {
    try {
        & powershell -ExecutionPolicy Bypass -File "$EnsureZImageScript" -SilentMode
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Z-Image core models ready." -ForegroundColor Green
        } else {
            Write-Host "  [WARNING] Z-Image core model check returned code $LASTEXITCODE (non-fatal)." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [WARNING] Z-Image core model ensure failed (non-fatal): $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARNING] ensure_zimage_core_models.ps1 not found, skipping." -ForegroundColor Yellow
}


# ============================================================================
# DONE
# ============================================================================
if (-not $SilentMode) {
    Write-Host "`n===================================================" -ForegroundColor Green
    Write-Host "   UPDATE COMPLETE" -ForegroundColor Green
    Write-Host "===================================================" -ForegroundColor Green
    Write-Host "Run RUN.bat to start FEDDA."
}
