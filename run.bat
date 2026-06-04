@echo off
setlocal
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo Error: Virtual environment "venv" not found.
    echo Please follow the setup instructions in the README to configure it.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m src.main %*
if %errorlevel% neq 0 (
    echo.
    echo Execution halted with errors.
    pause
)
endlocal