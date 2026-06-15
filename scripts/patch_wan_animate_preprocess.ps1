param(
    [string]$RootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$NodeFile = Join-Path $RootPath "ComfyUI\custom_nodes\ComfyUI-WanAnimatePreprocess\nodes.py"
if (-not (Test-Path $NodeFile)) {
    Write-Host "[WanAnimate patch] Node file not found, skipping: $NodeFile" -ForegroundColor Yellow
    exit 0
}

$Text = Get-Content -Raw $NodeFile
$Changed = $false

$Old = @'
        for idx, meta in enumerate(pose_metas):
            face_bbox_for_image = get_face_bboxes(meta['keypoints_face'][:, :2], scale=1.3, image_shape=(H, W))
            x1, x2, y1, y2 = face_bbox_for_image
'@

$New = @'
        for idx, meta in enumerate(pose_metas):
            try:
                face_bbox_for_image = get_face_bboxes(meta['keypoints_face'][:, :2], scale=1.3, image_shape=(H, W))
                if not np.all(np.isfinite(face_bbox_for_image)):
                    raise ValueError("non-finite face bbox")
            except Exception as exc:
                logging.warning(f"Invalid face bbox on frame {idx}: {exc}. Using fallback crop.")
                fallback_size = max(16, int(min(H, W) * 0.3))
                fallback_x1 = max(0, (W - fallback_size) // 2)
                fallback_x2 = min(W, fallback_x1 + fallback_size)
                fallback_y1 = max(0, int(H * 0.1))
                fallback_y2 = min(H, fallback_y1 + fallback_size)
                face_bbox_for_image = [fallback_x1, fallback_x2, fallback_y1, fallback_y2]
            x1, x2, y1, y2 = face_bbox_for_image
'@

if ($Text -match "Invalid face bbox on frame") {
    Write-Host "[WanAnimate patch] Face bbox fallback already applied." -ForegroundColor Green
} elseif ($Text.Contains($Old)) {
    $Text = $Text.Replace($Old, $New)
    $Changed = $true
} else {
    Write-Host "[WanAnimate patch] Face bbox block not found, skipping that patch." -ForegroundColor Yellow
}

$OldDraw = @'
    def process(self, pose_data, width, height, body_stick_width, hand_stick_width, draw_head, retarget_padding=64):

        retarget_image = pose_data.get("retarget_image", None)
'@

$NewDraw = @'
    def process(self, pose_data, width, height, body_stick_width, hand_stick_width, draw_head, retarget_padding=64):
        try:
            width = int(width)
            height = int(height)
        except Exception:
            logging.warning(f"Invalid DrawViTPose size {width}x{height}; using 512x512.")
            width, height = 512, 512
        if width < 64 or height < 64 or width > 2048 or height > 2048:
            logging.warning(f"Clamping DrawViTPose size from {width}x{height}.")
            width = min(2048, max(64, width))
            height = min(2048, max(64, height))

        retarget_image = pose_data.get("retarget_image", None)
'@

if ($Text -match "Invalid DrawViTPose size") {
    Write-Host "[WanAnimate patch] DrawViTPose size guard already applied." -ForegroundColor Green
} elseif ($Text.Contains($OldDraw)) {
    $Text = $Text.Replace($OldDraw, $NewDraw)
    $Changed = $true
} else {
    Write-Host "[WanAnimate patch] DrawViTPose block not found, skipping that patch." -ForegroundColor Yellow
}

if ($Changed) {
    Set-Content -Path $NodeFile -Value $Text -Encoding UTF8
    Write-Host "[WanAnimate patch] Applied compatibility patch." -ForegroundColor Green
} else {
    Write-Host "[WanAnimate patch] No changes needed." -ForegroundColor Green
}
