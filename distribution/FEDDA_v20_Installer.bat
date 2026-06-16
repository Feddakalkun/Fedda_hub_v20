@echo off
setlocal EnableDelayedExpansion
title FEDDA v20 One-Click Installer

:: ============================================================================
:: FEDDA Hub v20 - SINGLE-FILE DISTRIBUTION INSTALLER
::
:: Distribute ONLY this file. On first run it will:
::   1) Clone https://github.com/Feddakalkun/Fedda_hub_v20 into app\
::   2) Let user pick FULL or LITE install
::   3) Run the full inner setup (ComfyUI, Python, frontend, etc.)
::   4) Create run.bat and update.bat next to this file
::
:: Optional: pass LITE or FULL as first argument to skip the menu.
:: Prerequisite: Git for Windows (https://git-scm.com/download/win)
:: ============================================================================

echo.
echo ============================================================
echo   FEDDA Hub v20 - Standalone Installer
echo ============================================================
echo.

set "INSTALL_ROOT=%~dp0"
if "%INSTALL_ROOT:~-1%"=="\" set "INSTALL_ROOT=%INSTALL_ROOT:~0,-1%"

if /i "!INSTALL_ROOT:~0,4!"=="\\?\" set "INSTALL_ROOT=!INSTALL_ROOT:~4!"

set "APP_DIR=%INSTALL_ROOT%\app"
set "LOGS_DIR=%INSTALL_ROOT%\logs"
set "REPO_URL=https://github.com/Feddakalkun/Fedda_hub_v20.git"
set "BRANCH=main"
set "INSTALL_MODE="

if /i "%~1"=="LITE" set "INSTALL_MODE=LITE"
if /i "%~1"=="FULL" set "INSTALL_MODE=FULL"

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

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo         Install Git for Windows: https://git-scm.com/download/win
    echo [%date% %time%] ERROR: Git not found>> "%INSTALL_LOG%"
    pause
    exit /b 1
)

for /f "tokens=*" %%g in ('git --version 2^>^&1') do (
    echo Git              : %%g
    echo [%date% %time%] %%g>> "%INSTALL_LOG%"
)

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
    echo GPU              : No NVIDIA GPU detected - install may fail
    echo [%date% %time%] WARN: No NVIDIA GPU>> "%INSTALL_LOG%"
)

if not exist "%APP_DIR%" mkdir "%APP_DIR%"

if exist "%APP_DIR%\.git" (
    echo.
    echo [1/4] Updating existing app\ from GitHub ...
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
        echo [WARN] Removing stale app\ folder...
        rmdir /s /q "%APP_DIR%"
        mkdir "%APP_DIR%"
    )
    echo.
    echo [1/4] Cloning v20 repository into app\ ...
    git clone --depth 1 --branch %BRANCH% "%REPO_URL%" "%APP_DIR%" >> "%INSTALL_LOG%" 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Git clone failed. See %INSTALL_LOG%
        pause
        exit /b 1
    )
)

if not exist "%APP_DIR%\scripts\install.bat" (
    echo [ERROR] Clone incomplete - scripts\install.bat missing.
    pause
    exit /b 1
)

echo [1/4] Source ready in app\

:: --- Scan system tools (for LITE eligibility) ---
set "HAS_NODE=0"
set "HAS_NPM=0"
set "NODE_VERSION="
where node >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_NODE=1"
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do set "NODE_VERSION=%%v"
)
where npm >nul 2>nul
if %errorlevel% equ 0 set "HAS_NPM=1"

if "%HAS_NODE%"=="1" if "%HAS_NPM%"=="1" (
    set "LITE_AVAILABLE=1"
) else (
    set "LITE_AVAILABLE=0"
)

:: --- Step 2: Choose install mode ---
if not defined INSTALL_MODE goto :choose_mode
goto :mode_chosen

:choose_mode
echo.
echo [2/4] Choose how FEDDA should install
echo.
echo ============================================================
echo   INSTALL OPTIONS
echo ============================================================
echo.
echo   [1] FULL  - Fully portable (recommended for distribution)
echo.
echo       Downloads Python, Git, Node, and Ollama into this folder.
echo       ComfyUI, models cache, and pip packages stay inside app\ too.
echo       Does NOT install into system Python or global npm.
echo       Best when you want zero overlap with existing dev tools.
echo       Larger download (~15 GB), takes longer.
echo.
if "%LITE_AVAILABLE%"=="1" (
    echo   [2] LITE  - Faster for pro users with Git + Node already
    echo.
    echo       Still downloads embedded Python 3.11.9 into app\python_embeded\
    echo       Still keeps ComfyUI, torch, and HF cache inside the install folder.
    echo       Uses your system Git + Node/npm only to build the frontend once.
    echo       Does NOT touch system Python or global pip.
    echo       Your Node: %NODE_VERSION%
    echo       Smaller/faster than FULL.
    echo.
) else (
    echo   [2] LITE  - Unavailable on this PC
    echo.
    echo       Requires Node.js 18+ and npm on PATH.
    echo       Install Node from https://nodejs.org or choose FULL.
    echo.
)
echo ============================================================
echo.
echo   Both modes keep ML runtime inside the install folder.
echo   Neither mode modifies your system Python installation.
echo.

:ask_mode
set "CHOICE="
set /p "CHOICE=  Enter 1 or 2 (default: 1): "
if "%CHOICE%"=="" set "CHOICE=1"
if "%CHOICE%"=="1" (
    set "INSTALL_MODE=FULL"
    goto :mode_chosen
)
if "%CHOICE%"=="2" (
    if "%LITE_AVAILABLE%"=="0" (
        echo.
        echo   LITE needs Node.js 18+ and npm. Choose 1 for FULL, or install Node first.
        goto :ask_mode
    )
    set "INSTALL_MODE=LITE"
    goto :mode_chosen
)
echo   Invalid choice. Enter 1 or 2.
goto :ask_mode

:mode_chosen
echo.
echo [2/4] Selected: !INSTALL_MODE! install
echo [%date% %time%] Install mode: !INSTALL_MODE!>> "%INSTALL_LOG%"

:: --- Step 3: Inner setup ---
echo.
echo [3/4] Running inner setup (!INSTALL_MODE! mode)...
echo         ComfyUI + embedded Python + frontend - this takes a while.
echo.

pushd "%APP_DIR%"
call scripts\install.bat !INSTALL_MODE!
set "INNER_EXIT=!errorlevel!"
popd

if !INNER_EXIT! neq 0 (
    echo.
    echo [WARN] Inner installer exited with code !INNER_EXIT!.
    echo        Check %INSTALL_LOG% and app\logs\
    echo [%date% %time%] WARN: inner exit !INNER_EXIT!>> "%INSTALL_LOG%"
) else (
    echo [3/4] Inner setup completed.
    echo [%date% %time%] Inner setup OK>> "%INSTALL_LOG%"
)

:: --- Step 4: Launchers ---
echo.
echo [4/4] Creating run.bat and update.bat ...

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

echo.
echo ============================================================
if !INNER_EXIT! equ 0 (
    echo   Installation complete ^(!INSTALL_MODE! mode^)
) else (
    echo   Installation finished with warnings ^(!INSTALL_MODE! mode^)
)
echo ============================================================
echo.
echo   FEDDA_v20_Installer.bat  - re-run to update + reinstall
echo   run.bat                  - start FEDDA
echo   update.bat               - pull latest code only
echo   app\                     - everything stays here
echo   logs\                    - installer logs
echo.
if !INNER_EXIT! equ 0 (
    echo Ready: double-click run.bat
) else (
    echo Review %INSTALL_LOG% then re-run this installer
)
echo.
pause
exit /b !INNER_EXIT!