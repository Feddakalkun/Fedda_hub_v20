@echo off
title FEDDA - Download Free Character LoRAs
color 0A

echo.
echo  ============================================
echo   FEDDA - Free Character LoRA Pack
echo  ============================================
echo.
echo  This will download 3 free character LoRAs:
echo.
echo    Emmy  (~325 MB) - Scandinavian blonde
echo    Sana  (~162 MB) - Character LoRA
echo    Maya  (~324 MB) - Maya character
echo.
echo  Total: ~811 MB
echo.
echo  ============================================
echo.
pause

set "LORA_DIR=%~dp0ComfyUI\models\loras"
set "BASE_URL=https://huggingface.co/datasets/FeddaKalkun/free-loras/resolve/main"

REM --- Emmy ---
echo.
echo  [1/3] Downloading Emmy...
set "EMMY_DIR=%LORA_DIR%\Emmy"
if not exist "%EMMY_DIR%" mkdir "%EMMY_DIR%"

if exist "%EMMY_DIR%\Emmy.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%EMMY_DIR%\Emmy.safetensors" "%BASE_URL%/Emmy/Emmy.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed for Emmy.safetensors
    ) else (
        echo         Done.
    )
)

curl -s -L -o "%EMMY_DIR%\Emmy.metadata.json" "%BASE_URL%/Emmy/Emmy.metadata.json"
curl -s -L -o "%EMMY_DIR%\description.txt" "%BASE_URL%/Emmy/description.txt"

REM --- Sana ---
echo.
echo  [2/3] Downloading Sana...
set "SANA_DIR=%LORA_DIR%\Sana"
if not exist "%SANA_DIR%" mkdir "%SANA_DIR%"

if exist "%SANA_DIR%\sana.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%SANA_DIR%\sana.safetensors" "%BASE_URL%/Sana/sana.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed for sana.safetensors
    ) else (
        echo         Done.
    )
)

curl -s -L -o "%SANA_DIR%\sana.metadata.json" "%BASE_URL%/Sana/sana.metadata.json"

REM --- Maya ---
echo.
echo  [3/3] Downloading Maya...
set "MAYA_DIR=%LORA_DIR%\Maya"
if not exist "%MAYA_DIR%" mkdir "%MAYA_DIR%"

if exist "%MAYA_DIR%\Maya-Sol.safetensors" (
    echo         Already exists, skipping.
) else (
    curl -L -C - --retry 3 --retry-delay 5 --progress-bar -o "%MAYA_DIR%\Maya-Sol.safetensors" "%BASE_URL%/Maya/Maya-Sol.safetensors"
    if errorlevel 1 (
        echo         ERROR: Download failed for Maya-Sol.safetensors
    ) else (
        echo         Done.
    )
)

curl -s -L -o "%MAYA_DIR%\Maya.metadata.json" "%BASE_URL%/Maya/Maya.metadata.json"

echo.
echo  ============================================
echo   All done! LoRAs installed to:
echo   ComfyUI\models\loras\Emmy\
echo   ComfyUI\models\loras\Sana\
echo   ComfyUI\models\loras\Maya\
echo  ============================================
echo.
echo  You can now select Emmy, Sana, or Maya in the
echo  LoRA picker when generating images.
echo.
pause
