param(
    [switch]$SilentMode
)

$ErrorActionPreference = "Stop"
$ScriptPath = $PSScriptRoot
$RootPath = Split-Path -Parent $ScriptPath
$ComfyModels = Join-Path $RootPath "ComfyUI\models"

function Write-Info {
    param([string]$Message, [string]$Color = "Gray")
    if (-not $SilentMode) {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Ensure-File {
    param(
        [string]$Label,
        [string]$Url,
        [string]$DestPath,
        [long]$MinBytes = 1048576
    )
    $destDir = Split-Path -Parent $DestPath
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    if ((Test-Path $DestPath) -and ((Get-Item $DestPath).Length -ge $MinBytes)) {
        Write-Info "  [OK] $Label already present" "Green"
        return
    }

    Write-Info "  [DL] $Label" "Yellow"
    & curl.exe -L -C - --retry 4 --retry-delay 3 --progress-bar -o "$DestPath" "$Url"
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed for $Label (exit code $LASTEXITCODE)"
    }
    if (-not (Test-Path $DestPath) -or ((Get-Item $DestPath).Length -lt $MinBytes)) {
        throw "Downloaded file invalid for $Label"
    }
    Write-Info "  [OK] $Label ready" "Green"
}

Write-Info "`n[Z-Image Core] Ensuring required model files..." "Cyan"

Ensure-File `
    -Label "UNET z_image_turbo_bf16.safetensors" `
    -Url "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors" `
    -DestPath (Join-Path $ComfyModels "unet\z_image_turbo_bf16.safetensors") `
    -MinBytes 10485760

Ensure-File `
    -Label "CLIP qwen_3_4b.safetensors" `
    -Url "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" `
    -DestPath (Join-Path $ComfyModels "clip\qwen_3_4b.safetensors") `
    -MinBytes 10485760

Ensure-File `
    -Label "VAE z-image-vae.safetensors" `
    -Url "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" `
    -DestPath (Join-Path $ComfyModels "vae\z-image-vae.safetensors") `
    -MinBytes 5242880

Write-Info "[Z-Image Core] All required files are ready." "Green"
