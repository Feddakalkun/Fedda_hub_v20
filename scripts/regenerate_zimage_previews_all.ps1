param(
  [string]$Backend = "http://127.0.0.1:8000",
  [string]$Comfy = "http://127.0.0.1:8199"
)

$ErrorActionPreference = 'Stop'

$RootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dest = Join-Path $RootPath "frontend\public\lora-previews\zimage_turbo"
$backupRoot = Join-Path $RootPath "frontend\public\lora-previews\_backup"
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $backupRoot ("zimage_turbo_" + $stamp)

New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path $backup | Out-Null

# Backup current previews
Get-ChildItem -Path $dest -File -Filter *.png | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $backup $_.Name) -Force
}

$all = Invoke-RestMethod -Uri "$Backend/api/lora/list" -TimeoutSec 20
$loras = @($all.loras | Where-Object {
  $_ -match '_PMv\d+[ab]_ZImage\.safetensors$' -and $_.ToLower().Contains('zimage')
})

if ($loras.Count -eq 0) {
  throw "No celeb zimage LoRAs found."
}

Write-Host "Backup created: $backup"
Write-Host "Found $($loras.Count) celeb zimage LoRAs"

$ok = 0
$fail = 0
$failed = New-Object System.Collections.Generic.List[string]

for ($idx = 0; $idx -lt $loras.Count; $idx++) {
  $lora = $loras[$idx]
  $base = [System.IO.Path]::GetFileNameWithoutExtension($lora)
  $name = ($base -replace '_PMv\d+[ab]_ZImage$', '') -replace '_', ' '

  Write-Host "[$($idx+1)/$($loras.Count)] $name"

  $seed = Get-Random -Minimum 1 -Maximum 2147483646
  $prompt = "portrait photo of $name, head and upper torso clearly visible, shoulders included, face centered and sharp, direct eye contact, mild wide-angle look around 30mm, soft cinematic key light with subtle rim light, uniform dark charcoal gray studio background (#2f3136), clean minimal composition, photorealistic skin detail, high quality"
  $negative = "full body, face out of frame, cropped forehead, extreme fisheye, busy background, colorful background, clutter, blurry, lowres, deformed, bad anatomy, text, watermark"

  $params = @{
    prompt = $prompt
    negative = $negative
    width = 1024
    height = 1024
    steps = 11
    cfg = 1
    seed = $seed
    loras = @(@{ name = $lora; strength = 1.0 })
  }

  $body = @{ workflow_id = 'z-image'; params = $params } | ConvertTo-Json -Depth 12

  try {
    $resp = Invoke-RestMethod -Uri "$Backend/api/generate" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
    if (-not $resp.success -or -not $resp.prompt_id) { throw "Generate rejected" }
    $promptId = $resp.prompt_id

    $done = $false
    for ($i = 0; $i -lt 240; $i++) {
      Start-Sleep -Seconds 2
      $status = Invoke-RestMethod -Uri "$Backend/api/generate/status/$promptId" -TimeoutSec 30
      if ($status.status -eq 'completed' -and $status.images.Count -gt 0) {
        $img = $status.images[-1]
        $qs = "filename=$([uri]::EscapeDataString($img.filename))&subfolder=$([uri]::EscapeDataString($img.subfolder))&type=$([uri]::EscapeDataString($img.type))"
        $url = "$Comfy/view?$qs"

        $out = Join-Path $dest ($base + '.png')
        Invoke-WebRequest -Uri $url -OutFile $out -TimeoutSec 120
        Write-Host "  ok -> $($base).png"
        $ok++
        $done = $true
        break
      }
      if ($status.status -eq 'not_found' -and $i -gt 20) { throw "Job disappeared" }
    }

    if (-not $done) { throw "Timeout waiting for completion" }
  }
  catch {
    $fail++
    $msg = "$name :: $($_.Exception.Message)"
    $failed.Add($msg) | Out-Null
    Write-Host "  FAILED -> $($_.Exception.Message)"
  }
}

Write-Host ""
Write-Host "=== DONE ==="
Write-Host "Success: $ok"
Write-Host "Failed:  $fail"
Write-Host "Backup:  $backup"
if ($failed.Count -gt 0) {
  Write-Host "Failed items:"
  $failed | ForEach-Object { Write-Host " - $_" }
}
