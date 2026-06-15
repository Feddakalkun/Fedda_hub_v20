@echo off
title FEDDA AI Studio - RunPod Deployer
echo.
echo   ========================================
echo     FEDDA AI Studio - RunPod Deployer
echo   ========================================
echo.

:: Check for Python
where python >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install Python 3.8+
    pause
    exit /b 1
)

:: Run deploy script with any arguments passed through
python "%~dp0deploy.py" %*

if errorlevel 1 (
    echo.
    echo   Deploy failed. Check the error above.
)

echo.
pause
