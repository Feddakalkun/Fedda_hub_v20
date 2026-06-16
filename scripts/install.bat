@echo off
setlocal EnableDelayedExpansion
title FEDDA Installer

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "BASE_DIR=%%~fI"
cd /d "%BASE_DIR%"

:: Skip menu if re-launched as admin with install type argument
if "%1"=="FULL" goto :run_full
if "%1"=="LITE" goto :run_lite

echo.
echo ============================================================================
echo   FEDDA INSTALLER
echo ============================================================================
echo.
echo   Scanning your system...
echo.

:: ============================================================================
:: SYSTEM SCAN
:: ============================================================================

:: GPU Check - nvidia-smi -L gives clean output on all driver versions
set "GPU_OK=0"
set "GPU_NAME=Not detected"
for /f "tokens=1,* delims=:" %%a in ('nvidia-smi -L 2^>nul') do (
    if "!GPU_OK!"=="0" (
        set "GPU_OK=1"
        :: %%b = " NVIDIA GeForce RTX 3090 (UUID: ...)"
        :: Extract name before the UUID parenthesis
        set "_gpu=%%b"
        for /f "tokens=1 delims=(" %%n in ("%%b") do (
            :: Trim leading space
            for /f "tokens=*" %%t in ("%%n") do set "GPU_NAME=%%t"
        )
    )
)
if "!GPU_OK!"=="1" (
    echo   GPU:      !GPU_NAME!
) else (
    echo   GPU:      No NVIDIA GPU found
)

:: Check for system Python + parse version
set "HAS_PYTHON=0"
set "PY_VERSION="
set "PY_MINOR=0"
set "PY_VERSION_OK=0"
set "PY_VERSION_WARN=0"
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_PYTHON=1"
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
    :: Parse minor version - "Python 3.10.11" -> extract 10
    for /f "tokens=2 delims=." %%m in ('python --version 2^>^&1') do set "PY_MINOR=%%m"
    if !PY_MINOR! GEQ 10 set "PY_VERSION_OK=1"
    if !PY_MINOR! EQU 10 set "PY_VERSION_WARN=1"
)

:: Check for system Git
set "HAS_GIT=0"
set "GIT_VERSION="
where git >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_GIT=1"
    for /f "tokens=*" %%v in ('git --version 2^>^&1') do set "GIT_VERSION=%%v"
)

:: Check for system Node
set "HAS_NODE=0"
set "NODE_VERSION="
where node >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_NODE=1"
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do set "NODE_VERSION=%%v"
)

:: Check for system npm
set "HAS_NPM=0"
set "NPM_VERSION="
where npm >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_NPM=1"
    for /f "tokens=*" %%v in ('npm --version 2^>^&1') do set "NPM_VERSION=%%v"
)

:: Check for system Ollama
set "HAS_OLLAMA=0"
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    set "HAS_OLLAMA=1"
)

echo.
echo   System Tools Found:
if "%HAS_PYTHON%"=="1" (
    echo     Python:   %PY_VERSION%  [optional for Lite; embedded 3.11.9 will be used]
) else (
    echo     Python:   not installed  [OK for Lite - embedded 3.11.9 will be downloaded]
)
if "%HAS_GIT%"=="1" (
    echo     Git:      %GIT_VERSION%
) else (
    echo     Git:      not installed
)
if "%HAS_NODE%"=="1" (
    echo     Node.js:  %NODE_VERSION%
) else (
    echo     Node.js:  not installed
)
if "%HAS_NPM%"=="1" (
    echo     npm:      v%NPM_VERSION%
) else (
    echo     npm:      not installed
)
if "%HAS_OLLAMA%"=="1" (
    echo     Ollama:   installed
) else (
    echo     Ollama:   not installed
)

:: ============================================================================
:: CHECK IF ALREADY INSTALLED
:: ============================================================================
if exist "%BASE_DIR%\python_embeded\python.exe" (
    echo.
    echo   [NOTE] Full install already detected (python_embeded found^).
    echo          Run UPDATE.bat from the install root to update, or delete python_embeded to reinstall.
    echo.
    pause
    exit /b 0
)
if exist "%BASE_DIR%\venv\Scripts\python.exe" (
    echo.
    echo   [NOTE] Lite install already detected (venv found^).
    echo          Run UPDATE.bat from the install root to update, or delete venv to reinstall.
    echo.
    pause
    exit /b 0
)

:: ============================================================================
:: NVIDIA CHECK
:: ============================================================================
if "%GPU_OK%"=="0" (
    echo.
    echo   ============================================================
    echo   ERROR: No NVIDIA GPU detected!
    echo   FEDDA requires an NVIDIA GPU with CUDA support.
    echo   AMD and Intel GPUs are not supported.
    echo   ============================================================
    echo.
    pause
    exit /b 1
)

:: ============================================================================
:: OFFER CHOICE
:: ============================================================================
echo.
echo ============================================================================
echo.
echo   Choose installation type:
echo.
echo   [1] FULL  - Fully portable (recommended for distribution^)
echo       Downloads Python, Git, Node, Ollama into this folder.
echo       ComfyUI + pip packages + caches stay inside app\ too.
echo       Does NOT touch system Python or global npm.
echo       ~15 GB total, takes longer.
echo.

if "%HAS_GIT%"=="1" if "%HAS_NODE%"=="1" if "%HAS_NPM%"=="1" (
    echo   [2] LITE  - Faster for pros with Git + Node already
    echo       Embedded Python 3.11.9 still downloaded to app\python_embeded\
    echo       Uses system Git + Node/npm only to build the frontend.
    echo       ML runtime and caches still stay inside the install folder.
    echo.
    set "LITE_AVAILABLE=1"
) else (
    echo   [2] LITE  - Unavailable (needs Git, Node.js 18+, and npm^)
    echo.
    set "LITE_AVAILABLE=0"
)

echo   Neither mode modifies your system Python installation.
echo.

echo ============================================================================
echo.

:ask_choice
set "CHOICE="
set /p "CHOICE=  Enter 1 or 2 (default: 1): "
if "%CHOICE%"=="" set "CHOICE=1"

if "%CHOICE%"=="1" goto :do_full
if "%CHOICE%"=="2" goto :do_lite

echo   Invalid choice. Enter 1 or 2.
goto :ask_choice

:: ============================================================================
:: FULL INSTALL (Portable)
:: ============================================================================
:do_full
echo.
echo   Starting Full Install...
echo.

:: Request admin for portable install (needs to extract executables)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo   Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList 'FULL' -Verb RunAs -Wait"
    exit
)

:run_full
for %%I in ("%~dp0\..") do set "BASE_DIR=%%~fI"
set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"
cd /d "!BASE_DIR!"

echo.
echo   Starting Full Install...
echo.

powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\install.ps1" -AutoConfirm

if %errorlevel% neq 0 (
    echo.
    echo   [ERROR] Installation failed! Check logs\install_full_log.txt
    echo.
    if not "%1"=="FULL" pause
    exit /b %errorlevel%
)

goto :done

:: ============================================================================
:: LITE INSTALL (System tools + venv)
:: ============================================================================
:do_lite
if "%LITE_AVAILABLE%"=="0" (
    echo.
    echo   Lite install requires Git, Node.js, and npm.
    echo   Install the missing tools or choose Full Install.
    echo.
    goto :ask_choice
)

:run_lite
for %%I in ("%~dp0\..") do set "BASE_DIR=%%~fI"
set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"
cd /d "!BASE_DIR!"

echo.
echo   Starting Lite Install...
echo.

powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\install_lite.ps1" -AutoConfirm

if %errorlevel% neq 0 (
    echo.
    echo   [ERROR] Installation failed! Check logs\install_fast_log.txt
    echo.
    if not "%1"=="LITE" pause
    exit /b %errorlevel%
)

goto :done

:: ============================================================================
:: DONE
:: ============================================================================
:done
echo.
echo ============================================================================
echo   INSTALLATION COMPLETE!
echo ============================================================================
echo.
echo   To start FEDDA, run:  RUN.bat from the install root
echo.
echo   Log files saved to: %BASE_DIR%\logs\
echo     - install_report.txt      Quick summary of what was installed
echo     - install_full_log.txt    Full transcript of every command
echo     - install_log.txt         Step-by-step progress log
echo.
if exist "%BASE_DIR%\logs\install_report.txt" (
    echo   --- INSTALL REPORT ---
    type "%BASE_DIR%\logs\install_report.txt"
    echo   --- END REPORT ---
    echo.
)
if "%1"=="" pause

