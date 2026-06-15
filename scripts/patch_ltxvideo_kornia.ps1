param(
    [string]$RootPath = ""
)

if ([string]::IsNullOrWhiteSpace($RootPath)) {
    $ScriptPath = $PSScriptRoot
    $RootPath = Split-Path -Parent $ScriptPath
}

$RootPath = (Resolve-Path $RootPath).Path
$TargetFile = Join-Path $RootPath "ComfyUI\custom_nodes\ComfyUI-LTXVideo\pyramid_blending.py"

if (-not (Test-Path $TargetFile)) {
    Write-Host "  [LTXVideo] pyramid_blending.py not found, patch skipped." -ForegroundColor Yellow
    exit 0
}

$Text = Get-Content -Path $TargetFile -Raw
if ($Text -match "FEDDA_KORNIA_PAD_COMPAT") {
    Write-Host "  [LTXVideo] Kornia pad compatibility patch already applied." -ForegroundColor Green
    exit 0
}

$Text = $Text -replace "(\r?\n)\s+pad,(\r?\n\))", '$1$2'

$Compat = @'

# FEDDA_KORNIA_PAD_COMPAT:
# Kornia 0.8.x no longer exports `pad` from kornia.geometry.transform.pyramid.
# LTXVideo only needs standard tensor padding here, so keep the node pack
# importable by routing that call through torch.nn.functional.pad.
def pad(input_tensor, padding, border_type="reflect"):
    return F.pad(input_tensor, padding, mode=border_type)
'@

$Needle = "from torch import Tensor"
if ($Text -notlike "*$Needle*") {
    Write-Host "  [LTXVideo] Could not find insertion point, patch skipped." -ForegroundColor Yellow
    exit 0
}

$Text = $Text.Replace($Needle, "$Needle$Compat")
Set-Content -Path $TargetFile -Value $Text -Encoding UTF8
Write-Host "  [LTXVideo] Applied Kornia pad compatibility patch." -ForegroundColor Green
