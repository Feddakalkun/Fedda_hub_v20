@echo off
setlocal EnableDelayedExpansion
title FEDDA v20 One-Click Installer

:: ============================================================================
:: FEDDA Hub v20 - SINGLE-FILE DISTRIBUTION INSTALLER
::
:: Distribute ONLY this file. On first run it will:
::   1) Clone https://github.com/Feddakalkun/Fedda_hub_v20 into app\
::   2) Run the full inner setup (ComfyUI, Python, frontend, etc.)
::   3) Create run.bat and update.bat next to this file
::
:: Prerequisite: Git for Windows must be installed (https://git-scm.com/download/win)
:: ============================================================================

echo.
echo ============================================================
echo   FEDDA Hub v20 - Standalone Installer
echo ============================================================
echo.

set "INSTALL_ROOT=%~dp0"
if "%INSTALL_ROOT:~-1%"=="\" set "INSTALL_ROOT=%INSTALL_ROOT:~0,-1%"

:: Strip extended-length path prefix if present (\\?\H:\...)
if /i "!INSTALL_ROOT:~0,4!"=="\\?\" set "INSTALL_ROOT=!INSTALL_ROOT:~4!"

set "APP_DIR=%INSTALL_ROOT%\app"
set "LOGS_DIR=%INSTALL_ROOT%\logs"
set "REPO_URL=https://github.com/Feddakalkun/Fedda_hub_v20.git"
set "BRANCH=main"

for /f "delims=" %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%t"
set "INSTALL_LOG=%LOGS_DIR%\installer_%STAMP%.log"

if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

echo [%date% %time%] FEDDA v20 installer started > "%INSTALL_LOG%"
echo Install root     : %INSTALL_ROOT%
echo Target app dir   : %APP_DIR%
echo Git remote       : %REPO_URL%
echo Install log      : %INSTALL_LOG%
echo.
echo [%date% %time%] Install root: %INSTALL_ROOT%>> "%INSTALL_LOG%"
echo [%date% %time%] App dir: %APP_DIR%>> "%INSTALL_LOG%"

:: --- Prerequisite: Git ---
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo         This single installer needs Git to pull the app from GitHub.
    echo         Install Git for Windows: https://git-scm.com/download/win
    echo [%date% %time%] ERROR: Git not found>> "%INSTALL_LOG%"
    pause
    exit /b 1
)

for /f "tokens=*" %%g in ('git --version 2^>^&1') do (
    echo Git              : %%g
    echo [%date% %time%] %%g>> "%INSTALL_LOG%"
)

:: --- Optional GPU hint ---
set "GPU_OK=0"
for /f "tokens=1,* delims=:" %%a in ('nvidia-smi -L 2^>nul') do (
    if "!GPU_OK!"=="0" (
        set "GPU_OK=1"
        for /f "tokens=1 delims=(" %%n in ("%%b") do for /f "tokens=*" %%t in ("%%n") do set "GPU_NAME=%%t"
    )
)
if "!GPU_OK!"=="1" (
    echo GPU              : !GPU_NAME!
    echo [%date% %time%] GPU: !GPU_NAME!>> "%INSTALL_LOG%"
) else (
    echo GPU              : No NVIDIA GPU detected - inner installer may fail
    echo [%date% %time%] WARN: No NVIDIA GPU detected>> "%INSTALL_LOG%"
)

if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: --- Step 1: Clone or update source ---
if exist "%APP_DIR%\.git" (
    echo.
    echo [1/3] Updating existing app\ from GitHub ...
    echo [%date% %time%] Updating existing clone>> "%INSTALL_LOG%"
    pushd "%APP_DIR%"
    git fetch origin >> "%INSTALL_LOG%" 2>&1
    git reset --hard origin/%BRANCH% >> "%INSTALL_LOG%" 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Git update failed. See %INSTALL_LOG%
        popd
        pause
        exit /b 1
    )
    popd
) else (
    if exist "%APP_DIR%\run.bat" (
        echo.
        echo [WARN] app\ exists but is not a git clone. Removing stale folder...
        echo [%date% %time%] Removing stale app folder>> "%INSTALL_LOG%"
        rmdir /s /q "%APP_DIR%"
        mkdir "%APP_DIR%"
    )
    echo.
    echo [1/3] Cloning v20 repository into app\ ...
    echo         This may take a minute.
    echo [%date% %time%] Cloning %REPO_URL%>> "%INSTALL_LOG%"
    git clone --depth 1 --branch %BRANCH% "%REPO_URL%" "%APP_DIR%" >> "%INSTALL_LOG%" 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Git clone failed. See %INSTALL_LOG%
        pause
        exit /b 1
    )
)

if not exist "%APP_DIR%\scripts\install.bat" (
    echo [ERROR] Clone looks incomplete - scripts\install.bat missing.
    echo [%date% %time%] ERROR: scripts\install.bat missing>> "%INSTALL_LOG%"
    pause
    exit /b 1
)

echo [1/3] Source ready in app\
echo [%date% %time%] Source ready>> "%INSTALL_LOG%"

:: --- Step 2: Inner setup (LITE = embedded Python + system Git/Node) ---
echo.
echo [2/3] Running full inner setup (LITE mode)...
echo         ComfyUI, embedded Python, frontend deps - this takes a while.
echo [%date% %time%] Starting inner install.bat LITE>> "%INSTALL_LOG%"
echo.

pushd "%APP_DIR%"
call scripts\install.bat LITE >> "%INSTALL_LOG%" 2>&1
set "INNER_EXIT=!errorlevel!"
popd

if !INNER_EXIT! neq 0 (
    echo.
    echo [WARN] Inner installer exited with code !INNER_EXIT!.
    echo        Check %INSTALL_LOG% and app\logs\ for details.
    echo        You can re-run this same installer to retry.
    echo [%date% %time%] WARN: inner installer exit !INNER_EXIT!>> "%INSTALL_LOG%"
) else (
    echo [2/3] Inner setup completed successfully.
    echo [%date% %time%] Inner setup OK>> "%INSTALL_LOG%"
)

:: --- Step 3: Create launchers ---
echo.
echo [3/3] Creating run.bat and update.bat ...

(
    @echo off
    cd /d "%%~dp0app"
    call run.bat %%*
) > "%INSTALL_ROOT%\run.bat"

(
    @echo off
    cd /d "%%~dp0app"
    if exist "scripts\run_update.bat" ^(
        call scripts\run_update.bat
    ^) else ^(
        powershell -ExecutionPolicy Bypass -File "scripts\update_code.ps1"
    ^)
) > "%INSTALL_ROOT%\update.bat"

echo [%date% %time%] Created run.bat and update.bat>> "%INSTALL_LOG%"

echo.
echo ============================================================
if !INNER_EXIT! equ 0 (
    echo   Installation complete!
) else (
    echo   Installation finished with warnings.
)
echo ============================================================
echo.
echo Next to this installer you now have:
echo   FEDDA_v20_Installer.bat  - re-run to update + reinstall
echo   run.bat                  - double-click to start FEDDA
echo   update.bat               - pull latest code only
echo   app\                     - application + runtime
echo   logs\                    - installer logs
echo.
if !INNER_EXIT! equ 0 (
    echo Ready: double-click run.bat to launch FEDDA Hub v20.
) else (
    echo Review %INSTALL_LOG% then re-run this installer or app\scripts\install.bat
)
echo.
pause
exit /b !INNER_EXIT!