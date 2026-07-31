@echo off
echo ========================================
echo   Farmitra Backend
echo ========================================
echo.

cd /d "%~dp0backend"

REM Check if venv exists in project folder
if not exist "venv\Scripts\python.exe" (
    if exist "C:\AgriSense_venv\Scripts\python.exe" (
        echo Using venv at C:\AgriSense_venv
        set PYTHON_PATH=C:\AgriSense_venv\Scripts\python.exe
        set PIP_PATH=C:\AgriSense_venv\Scripts\pip.exe
    ) else (
        echo Creating virtual environment...
        python -m venv venv
        set PYTHON_PATH=venv\Scripts\python.exe
        set PIP_PATH=venv\Scripts\pip.exe
    )
) else (
    echo Using project venv
    set PYTHON_PATH=venv\Scripts\python.exe
    set PIP_PATH=venv\Scripts\pip.exe
)

echo.
echo Installing Python packages (this takes 3-5 minutes)...
%PIP_PATH% install -q fastapi==0.111.0 uvicorn[standard]==0.29.0 python-multipart==0.0.9 Pillow==10.3.0 transformers==4.41.2 torch==2.3.0 scikit-learn==1.5.0 pandas==2.2.2 numpy==1.26.4 httpx==0.27.0 openai==1.30.5 python-dotenv==1.0.1

if errorlevel 1 (
    echo.
    echo ERROR: Package installation failed
    echo Try running manually: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Checking .env file...
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your OPENAI_API_KEY
    pause
    exit /b 1
)

findstr /C:"REPLACE_WITH_YOUR_OPENAI_KEY" .env >nul
if not errorlevel 1 (
    echo.
    echo ========================================
    echo   ACTION REQUIRED!
    echo ========================================
    echo.
    echo The .env file still has the placeholder key.
    echo.
    echo 1. Get your OpenAI API key from:
    echo    https://platform.openai.com/api-keys
    echo.
    echo 2. Open backend\.env in a text editor
    echo.
    echo 3. Replace REPLACE_WITH_YOUR_OPENAI_KEY
    echo    with your actual key starting with sk-
    echo.
    echo 4. Save the file and run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo Starting FastAPI backend server...
echo Backend will be available at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

%PYTHON_PATH% -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
