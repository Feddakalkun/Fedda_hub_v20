param(
    [string]$RootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$NodeFile = Join-Path $RootPath "ComfyUI\custom_nodes\ComfyUI-KJNodes\nodes\nodes.py"
if (-not (Test-Path $NodeFile)) {
    Write-Host "  [KJNodes] nodes.py not found, patch skipped." -ForegroundColor Yellow
    exit 0
}

$Content = Get-Content -LiteralPath $NodeFile -Raw
if ($Content -match "AudioVAE\(sd, metadata\)") {
    Write-Host "  [KJNodes] LTX audio VAE compatibility patch already applied." -ForegroundColor Green
    exit 0
}

$New = @'
        is_audio_vae = (
            "vocoder.conv_post.weight" in sd
            or "vocoder.vocoder.conv_post.weight" in sd
            or "audio_vae.vocoder.conv_post.weight" in sd
            or "audio_vae.vocoder.vocoder.conv_post.weight" in sd
            or "vocoder.resblocks.0.convs1.0.weight" in sd
            or "vocoder.vocoder.resblocks.0.convs1.0.weight" in sd
            or "audio_vae.vocoder.resblocks.0.convs1.0.weight" in sd
            or "audio_vae.vocoder.vocoder.resblocks.0.convs1.0.weight" in sd
        )
        if is_audio_vae:
            from comfy.ldm.lightricks.vae.audio_vae import AudioVAE
            vae = AudioVAE(sd, metadata)
        else:
            vae = VAE(sd=sd, device=device, dtype=dtype, metadata=metadata)
        if hasattr(vae, "throw_exception_if_invalid"):
            vae.throw_exception_if_invalid()
'@

$Pattern = '(?s)        is_audio_vae = \(\s*            "vocoder\.conv_post\.weight" in sd\s*            or "vocoder\.vocoder\.conv_post\.weight" in sd\s*(?:            or "audio_vae\.vocoder\.conv_post\.weight" in sd\s*)?(?:            or "audio_vae\.vocoder\.vocoder\.conv_post\.weight" in sd\s*)?            or "vocoder\.resblocks\.0\.convs1\.0\.weight" in sd\s*            or "vocoder\.vocoder\.resblocks\.0\.convs1\.0\.weight" in sd\s*(?:            or "audio_vae\.vocoder\.resblocks\.0\.convs1\.0\.weight" in sd\s*)?(?:            or "audio_vae\.vocoder\.vocoder\.resblocks\.0\.convs1\.0\.weight" in sd\s*)?        \)\s*        if is_audio_vae:\s*            sd_audio = state_dict_prefix_replace\(dict\(sd\), \{"audio_vae\.": "autoencoder\.", "vocoder\.": "vocoder\."\}, filter_keys=True\)\s*            vae = VAE\(sd=sd_audio, metadata=metadata\)\s*        else:\s*            vae = VAE\(sd=sd, device=device, dtype=dtype, metadata=metadata\)\s*        vae\.throw_exception_if_invalid\(\)'

if (-not [regex]::IsMatch($Content, $Pattern)) {
    Write-Host "  [KJNodes] Audio VAE detection block not found, patch skipped." -ForegroundColor Yellow
    exit 0
}

$Content = [regex]::Replace($Content, $Pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $New }, 1)
Set-Content -LiteralPath $NodeFile -Value $Content -Encoding UTF8
Write-Host "  [KJNodes] Applied LTX audio VAE compatibility patch." -ForegroundColor Green
