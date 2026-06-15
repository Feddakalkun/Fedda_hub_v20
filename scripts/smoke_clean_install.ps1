param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$BuildFrontend,
    [switch]$CheckRuntime
)

$ErrorActionPreference = "Stop"

function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Test-RequiredPath {
    param([string]$Base, [string]$Relative)
    $full = Join-Path $Base $Relative
    if (Test-Path -LiteralPath $full) {
        Write-Ok $Relative
        return $true
    }
    Write-Err "$Relative (missing)"
    return $false
}

function Test-ForbiddenPath {
    param([string]$Base, [string]$Relative)
    $full = Join-Path $Base $Relative
    if (Test-Path -LiteralPath $full) {
        Write-Err "$Relative (should not be present in v15)"
        return $false
    }
    Write-Ok "$Relative excluded"
    return $true
}

function Test-Http {
    param([string]$Url, [int]$TimeoutSec = 3)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Get-WorkflowMappings {
    param([string]$Base)
    $mappingPath = Join-Path $Base "config/workflow_api.json"
    if (-not (Test-Path -LiteralPath $mappingPath)) {
        Write-Err "config/workflow_api.json (missing)"
        return $null
    }

    try {
        return Get-Content -LiteralPath $mappingPath -Raw | ConvertFrom-Json
    } catch {
        Write-Err "config/workflow_api.json (invalid JSON: $($_.Exception.Message))"
        return $null
    }
}

function Test-WorkflowMappings {
    param([string]$Base, [object]$Mappings)
    if (-not $Mappings) { return 1 }

    $failures = 0
    $workflowsRoot = Join-Path $Base "backend/workflows"

    foreach ($entry in $Mappings.PSObject.Properties) {
        $workflowId = $entry.Name
        $filename = [string]$entry.Value.filename
        if ([string]::IsNullOrWhiteSpace($filename)) {
            Write-Err "$workflowId has no filename"
            $failures++
            continue
        }

        $workflowPath = Join-Path $workflowsRoot $filename
        if (-not (Test-Path -LiteralPath $workflowPath)) {
            Write-Err "$workflowId -> backend/workflows/$filename (missing)"
            $failures++
            continue
        }

        try {
            $workflow = Get-Content -LiteralPath $workflowPath -Raw | ConvertFrom-Json
        } catch {
            Write-Err "$workflowId -> backend/workflows/$filename (invalid JSON)"
            $failures++
            continue
        }

        foreach ($input in $entry.Value.inputs.PSObject.Properties) {
            $nodeIds = @()
            if ($input.Value.node_ids) {
                $nodeIds = @($input.Value.node_ids)
            } elseif ($input.Value.node_id) {
                $nodeIds = @($input.Value.node_id)
            }

            foreach ($nodeId in $nodeIds) {
                if (-not $workflow.PSObject.Properties[[string]$nodeId]) {
                    Write-Err "$workflowId input '$($input.Name)' references missing node '$nodeId'"
                    $failures++
                }
            }
        }
    }

    if ($failures -eq 0) { Write-Ok "workflow_api.json mappings and node ids" }
    return $failures
}

function Test-FileText {
    param([string]$Path, [string[]]$MustContain, [string[]]$MustNotContain)
    $failures = 0
    $text = Get-Content -LiteralPath $Path -Raw
    foreach ($needle in $MustContain) {
        if ($text.Contains($needle)) { Write-Ok "$(Split-Path $Path -Leaf) contains $needle" }
        else { Write-Err "$(Split-Path $Path -Leaf) missing $needle"; $failures++ }
    }
    foreach ($needle in $MustNotContain) {
        if ($text.Contains($needle)) { Write-Err "$(Split-Path $Path -Leaf) still references $needle"; $failures++ }
        else { Write-Ok "$(Split-Path $Path -Leaf) excludes $needle" }
    }
    return $failures
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " FEDDA Hub v20 Smoke Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Root: $ProjectRoot"
Write-Host ""

$failCount = 0

Write-Host "1) Checking critical v15 files..." -ForegroundColor Cyan
$criticalFiles = @(
    "FEDDA_Installer.bat",
    "frontend/src/App.tsx",
    "frontend/src/components/layout/RichHome.tsx",
    "frontend/src/components/layout/ImageSectionCards.tsx",
    "frontend/src/components/layout/VideoSectionCards.tsx",
    "frontend/src/components/layout/WorkflowShell.tsx",
    "frontend/src/pages/GalleryPage.tsx",
    "frontend/src/pages/LibraryPage.tsx",
    "frontend/src/pages/OllamaModelsPage.tsx",
    "frontend/src/pages/ImageStudioPage.tsx",
    "frontend/src/pages/VideoStudioPage.tsx",
    "frontend/src/services/comfyService.ts",
    "frontend/src/services/ollamaService.ts",
    "frontend/src/hooks/useComfyStatus.ts",
    "frontend/src/hooks/useOllamaManager.ts",
    "frontend/src/hooks/useOllamaStatus.ts",
    "frontend/vite.config.ts",
    "frontend/package.json",
    "run.bat",
    "scripts/install.bat",
    "scripts/install.ps1",
    "scripts/install_lite.ps1",
    "scripts/fix_embedded_ssl.ps1"
)
foreach ($f in $criticalFiles) {
    if (-not (Test-RequiredPath -Base $ProjectRoot -Relative $f)) { $failCount++ }
}
Write-Host ""

Write-Host "2) Checking v15 UI scope..." -ForegroundColor Cyan
$forbiddenPaths = @(
    "frontend/public/cards",
    "frontend/src/pages/AgentChatPage.tsx",
    "frontend/src/pages/VideosPage.tsx",
    "frontend/src/pages/LtxStudioPage.tsx",
    "frontend/src/pages/influencer"
)
foreach ($f in $forbiddenPaths) {
    if (-not (Test-ForbiddenPath -Base $ProjectRoot -Relative $f)) { $failCount++ }
}
$appPath = Join-Path $ProjectRoot "frontend/src/App.tsx"
$failCount += Test-FileText -Path $appPath -MustContain @(
    "ImageStudioPage",
    "VideoStudioPage",
    "GalleryPage",
    "LibraryPage",
    "OllamaModelsPage"
) -MustNotContain @(
    "AgentChatPage",
    "LandingPage",
    "Sidebar",
    "VideosPage",
    "audio",
    "logs",
    "workflows"
)
Write-Host ""

Write-Host "3) Checking workflow registry..." -ForegroundColor Cyan
$workflowMappings = Get-WorkflowMappings -Base $ProjectRoot
if ($workflowMappings) { $failCount += Test-WorkflowMappings -Base $ProjectRoot -Mappings $workflowMappings }
else { $failCount++ }
Write-Host ""

if ($BuildFrontend) {
    Write-Host "4) Running frontend build..." -ForegroundColor Cyan
    $frontendDir = Join-Path $ProjectRoot "frontend"
    if (-not (Test-Path -LiteralPath $frontendDir)) {
        Write-Err "frontend/ folder missing"
        $failCount++
    } else {
        Push-Location $frontendDir
        try {
            & npm.cmd run build
            if ($LASTEXITCODE -eq 0) { Write-Ok "frontend build passed" }
            else { Write-Err "frontend build failed (exit $LASTEXITCODE)"; $failCount++ }
        } catch {
            Write-Err "frontend build failed: $($_.Exception.Message)"
            $failCount++
        } finally {
            Pop-Location
        }
    }
    Write-Host ""
} else {
    Write-Warn "Frontend build check skipped (use -BuildFrontend)"
    Write-Host ""
}

if ($CheckRuntime) {
    Write-Host "5) Probing runtime endpoints..." -ForegroundColor Cyan
    $runtimeChecks = @(
        @{ Name = "Frontend (Vite)"; Url = "http://127.0.0.1:5173/" },
        @{ Name = "Backend API"; Url = "http://127.0.0.1:8000/api/hardware/stats" },
        @{ Name = "ComfyUI"; Url = "http://127.0.0.1:8199/system_stats" },
        @{ Name = "Frontend proxy /comfy"; Url = "http://127.0.0.1:5173/comfy/system_stats" }
    )
    foreach ($c in $runtimeChecks) {
        if (Test-Http -Url $c.Url) { Write-Ok "$($c.Name): reachable" }
        else { Write-Err "$($c.Name): not reachable"; $failCount++ }
    }
    Write-Host ""
} else {
    Write-Warn "Runtime probe skipped (use -CheckRuntime)"
    Write-Host ""
}

Write-Host "------------------------------------------" -ForegroundColor DarkGray
if ($failCount -eq 0) {
    Write-Host "Smoke test PASSED" -ForegroundColor Green
    exit 0
}
Write-Host "Smoke test FAILED ($failCount issue(s))" -ForegroundColor Red
exit 1

