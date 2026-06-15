param(
  [string]$Backend = "http://127.0.0.1:8000",
  [string]$Comfy = "http://127.0.0.1:8199"
)

$ErrorActionPreference = 'Stop'

$RootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destTurbo = Join-Path $RootPath "frontend\public\lora-previews\zimage_turbo"
$destNsfw = Join-Path $RootPath "frontend\public\lora-previews\zimage_nsfw"
New-Item -ItemType Directory -Force -Path $destTurbo | Out-Null
New-Item -ItemType Directory -Force -Path $destNsfw | Out-Null

$all = Invoke-RestMethod -Uri "$Backend/api/lora/list" -TimeoutSec 20
$loras = @($all.loras | Where-Object {
  $n = $_.ToLower()
  $n.Contains('zimage') -and $n.EndsWith('.safetensors')
})

if ($loras.Count -eq 0) {
  throw "No zimage LoRAs found."
}

Write-Host "Found $($loras.Count) zimage LoRAs"

$ok = 0
$fail = 0
$failedNames = New-Object System.Collections.Generic.List[string]

for ($idx = 0; $idx -lt $loras.Count; $idx++) {
  $lora = $loras[$idx]
  $base = [System.IO.Path]::GetFileNameWithoutExtension($lora)
  $display = $base -replace '_PMv\d+[ab]_ZImage$', '' -replace '_', ' '

  Write-Host "[$($idx+1)/$($loras.Count)] Generating $display"

  $seed = Get-Random -Minimum 1 -Maximum 2147483646
  $prompt = "close-up portrait selfie of $display, face centered and fully visible, eyes sharp, mild 28mm wide-angle selfie perspective, head and shoulders framing, direct eye contact, soft cinematic light, photorealistic skin detail, clean background, high detail"
  $negative = "full body, face out of frame, cropped head, distant subject, blurry, lowres, deformed face, text, watermark"

  $params = @{
    prompt = $prompt
    negative = $negative
    width = 960
    height = 960
    steps = 11
    cfg = 1
    seed = $seed
    loras = @(@{ name = $lora; strength = 1.0 })
  }

  $body = @{ workflow_id = 'z-image'; params = $params } | ConvertTo-Json -Depth 12

  try {
    $resp = Invoke-RestMethod -Uri "$Backend/api/generate" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 60
    if (-not $resp.success -or -not $resp.prompt_id) {
      throw "Generate request rejected"
    }

    $promptId = $resp.prompt_id
    $done = $false

    for ($t = 0; $t -lt 240; $t++) {
      Start-Sleep -Seconds 2
      $status = Invoke-RestMethod -Uri "$Backend/api/generate/status/$promptId" -TimeoutSec 30
      if ($status.status -eq 'completed' -and $status.images.Count -gt 0) {
        $img = $status.images[-1]
        $qs = "filename=$([uri]::EscapeDataString($img.filename))&subfolder=$([uri]::EscapeDataString($img.subfolder))&type=$([uri]::EscapeDataString($img.type))"
        $url = "$Comfy/view?$qs"

        $fileName = "$base.png"
        $dest1 = Join-Path $destTurbo $fileName
        $dest2 = Join-Path $destNsfw $fileName

        Invoke-WebRequest -Uri $url -OutFile $dest1 -TimeoutSec 120
        Copy-Item -LiteralPath $dest1 -Destination $dest2 -Force

        Write-Host "  saved -> $fileName"
        $ok++
        $done = $true
        break
      }
      if ($status.status -eq 'not_found' -and $t -gt 20) {
        throw "Job disappeared from queue/history"
      }
    }

    if (-not $done) {
      throw "Timed out waiting for completion"
    }
  }
  catch {
    $fail++
    $failedNames.Add("$display :: $($_.Exception.Message)") | Out-Null
    Write-Host "  FAILED -> $($_.Exception.Message)"
  }
}

Write-Host ""
Write-Host "Done. Success: $ok  Failed: $fail"
if ($failedNames.Count -gt 0) {
  Write-Host "Failed items:"
  $failedNames | ForEach-Object { Write-Host " - $_" }
}
