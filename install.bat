@echo off
REM ###############################################################################
REM # Python-IAM-CLI Installation Script for Windows
REM # 
REM # This script installs the Python-IAM-CLI tool and its dependencies.
REM # 
REM # Usage:
REM #   install.bat
REM #
REM # Requirements:
REM #   - Python 3.10 or higher
REM #   - pip (Python package installer)
REM ###############################################################################

setlocal enabledelayedexpansion

color 0A
REM Set colors for messages
REM Green = 0A, Red = 0C, Yellow = 0E, Blue = 09

echo.
echo ========================================
echo Python-IAM-CLI Installation
echo ========================================
echo.

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10 or higher from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% found

REM Check if pip is installed
echo Checking pip installation...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ERROR: pip is not installed.
    echo.
    pause
    exit /b 1
)

echo pip is installed
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
echo Installing from: %SCRIPT_DIR%

REM Check if pyproject.toml exists
if not exist "%SCRIPT_DIR%pyproject.toml" (
    color 0C
    echo.
    echo ERROR: pyproject.toml not found. Are you running this from the project root?
    echo.
    pause
    exit /b 1
)

REM Ask user for installation method
echo.
echo How would you like to install?
echo 1) System-wide
echo 2) User-wide (recommended)
echo 3) Virtual environment (most recommended)
set /p CHOICE="Enter choice (1-3, default: 3): "
if "%CHOICE%"=="" set CHOICE=3

REM Process choice
if "%CHOICE%"=="1" (
    echo Installing system-wide...
    python -m pip install -e "%SCRIPT_DIR%"
    goto verify
) else if "%CHOICE%"=="2" (
    echo Installing for current user...
    python -m pip install --user -e "%SCRIPT_DIR%"
    goto verify
) else if "%CHOICE%"=="3" (
    echo Creating virtual environment...
    set VENV_PATH=%USERPROFILE%\.python-iam-cli\venv
    
    if exist "%VENV_PATH%" (
        echo Virtual environment already exists at %VENV_PATH%
    ) else (
        mkdir "%USERPROFILE%\.python-iam-cli" 2>nul
        python -m venv "%VENV_PATH%"
        if %errorlevel% neq 0 (
            color 0C
            echo.
            echo ERROR: Failed to create virtual environment.
            echo.
            pause
            exit /b 1
        )
    )
    
    REM Activate virtual environment
    call "%VENV_PATH%\Scripts\activate.bat"
    echo Virtual environment activated
    echo.
    
    python -m pip install -e "%SCRIPT_DIR%"
    goto verify
) else (
    color 0C
    echo Invalid choice. Using virtual environment.
    goto verify
)

:verify
echo.
echo ========================================
echo Verifying Installation
echo ========================================
echo.

where dtiam >nul 2>&1
if %errorlevel% equ 0 (
    echo dtiam command found
    color 0A
    echo.
    dtiam --version
    echo.
    color 0A
) else (
    color 0E
    echo WARNING: dtiam command not found in PATH.
    echo This may be normal if you installed in a virtual environment.
    echo.
)

echo.
color 0A
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo - Run: dtiam --help
echo - Documentation: https://github.com/timstewart-dynatrace/Python-IAM-CLI
echo.
pause
