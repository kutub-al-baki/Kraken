@echo off
TITLE UIU Mariner ROV - Software Installer
echo ===================================================
echo   UIU MARINER ROV - Software Installer (Windows)
echo ===================================================
echo.

:: 1. Check for Python
echo [1/3] Checking Python installation...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.8+ from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

:: 2. Install Python Packages
echo [2/3] Installing Python dependencies from requirements.txt...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b
)
echo [OK] Python dependencies installed.
echo.

:: 3. Install Frontend Packages
echo [3/3] Installing Frontend (React) dependencies...
if exist "frontend\" (
    cd frontend
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo.
        echo [ERROR] Failed to install NPM packages.
        cd ..
        pause
        exit /b
    )
    cd ..
    echo [OK] Frontend dependencies installed.
) else (
    echo [SKIP] 'frontend' folder not found.
)

echo.
echo ===================================================
echo   🎉 Installation Complete!
echo   To start the ROV software, run: python launch_mariner.py
echo ===================================================
echo.
pause
