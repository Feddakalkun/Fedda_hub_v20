@echo off
title FEDDA - Download Z-Image Models
color 0A

echo.
echo  ============================================
echo   FEDDA - Z-Image Model Downloader
echo  ============================================
echo.
echo  This will download the core Z-Image models:
echo.
echo    1. Z-Image Turbo UNet      (~11.5 GB)
echo    2. Qwen 3 4B CLIP          (~7.5 GB)
echo    3. Z-Image VAE             (~312 MB)
echo    4. Face YOLOv8 Detector    (~52 MB)
echo    5. SAM ViT-B (FaceDetailer) (~375 MB)
echo.
echo  Total: ~20 GB
echo.
echo  These models are required for image generation
echo  with the Z-Image workflow.
echo.
echo  ============================================
echo.
pause

set "MODEL_DIR=%~dp0ComfyUI\models"
set "BASE_URL_ZIMAGE=https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files"
set "BASE_URL_FACE=https://huggingface.co/Bingsu/adetailer/resolve/main"
set "BASE_URL_SAM=https://huggingface.co/scenario-labs/sam_vit/resolve/main"

REM --- 1. Z-Image Turbo UNet (11.5 GB) ---
echo.
echo  [1/5] Downloading Z-Image Turbo UNet (11.5 GB)...
set "UNET_DIR=%MODEL_DIR%\unet"
if not exist "%UNET_DIR%" mkdir "%UNET_DIR%"

if exist "%UNET_DIR%\z_image_turbo_bf16.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%UNET_DIR%\z_image_turbo_bf16.safetensors" "%BASE_URL_ZIMAGE%/diffusion_models/z_image_turbo_bf16.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed
    ) else (
        echo         Done.
    )
)

REM --- 2. Qwen 3 4B CLIP (7.5 GB) ---
echo.
echo  [2/5] Downloading Qwen 3 4B CLIP (7.5 GB)...
set "CLIP_DIR=%MODEL_DIR%\clip"
if not exist "%CLIP_DIR%" mkdir "%CLIP_DIR%"

if exist "%CLIP_DIR%\qwen_3_4b.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%CLIP_DIR%\qwen_3_4b.safetensors" "%BASE_URL_ZIMAGE%/text_encoders/qwen_3_4b.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed
    ) else (
        echo         Done.
    )
)

REM --- 3. Z-Image VAE (312 MB) ---
echo.
echo  [3/5] Downloading Z-Image VAE (312 MB)...
set "VAE_DIR=%MODEL_DIR%\vae"
if not exist "%VAE_DIR%" mkdir "%VAE_DIR%"

if exist "%VAE_DIR%\z-image-vae.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%VAE_DIR%\z-image-vae.safetensors" "%BASE_URL_ZIMAGE%/vae/ae.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed
    ) else (
        echo         Done.
    )
)

REM --- 4. Face YOLOv8 Detector (52 MB) ---
echo.
echo  [4/5] Downloading Face YOLOv8 Detector (52 MB)...
set "BBOX_DIR=%MODEL_DIR%\ultralytics\bbox"
if not exist "%BBOX_DIR%" mkdir "%BBOX_DIR%"

if exist "%BBOX_DIR%\face_yolov8m.pt" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%BBOX_DIR%\face_yolov8m.pt" "%BASE_URL_FACE%/face_yolov8m.pt"
    if errorlevel 1 (
        echo         ERROR: Download failed
    ) else (
        echo         Done.
    )
)

REM --- 5. SAM ViT-B for FaceDetailer (375 MB) ---
echo.
echo  [5/5] Downloading SAM ViT-B (375 MB)...
set "SAM_DIR=%MODEL_DIR%\sams"
if not exist "%SAM_DIR%" mkdir "%SAM_DIR%"

if exist "%SAM_DIR%\sam_vit_b_01ec64.pth" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%SAM_DIR%\sam_vit_b_01ec64.pth" "%BASE_URL_SAM%/sam_vit_b_01ec64.pth"
    if errorlevel 1 (
        echo         ERROR: Download failed
    ) else (
        echo         Done.
    )
)

echo.
echo  ============================================
echo   All done! Models installed to:
echo   ComfyUI\models\unet\
echo   ComfyUI\models\clip\
echo   ComfyUI\models\vae\
echo   ComfyUI\models\ultralytics\bbox\
echo   ComfyUI\models\sams\
echo  ============================================
echo.
echo  You can now generate images with Z-Image!
echo  Restart FEDDA if it's already running.
echo.
pause
