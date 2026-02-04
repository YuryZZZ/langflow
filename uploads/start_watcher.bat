@echo off
echo ===========================================
echo  📁 Folder Upload Watcher - Quick Start
echo ===========================================
echo.
echo This will start watching the uploads/documents/ folder
echo and automatically process any files you drop there.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if dependencies are installed
if not exist "uploads\deps_installed.txt" (
    echo 📦 Installing dependencies...
    pip install -r uploads/requirements.txt --quiet
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
    echo. > uploads\deps_installed.txt
    echo ✅ Dependencies installed
) else (
    echo ✅ Dependencies already installed
)

echo.
echo 📂 Folder structure:
echo    uploads/documents/  - Drop files here
echo    uploads/processed/  - Processed files move here
echo    uploads/vector_store/ - Vector database stored here
echo.

REM Create directories if they don't exist
if not exist "uploads\documents" mkdir uploads\documents
if not exist "uploads\processed" mkdir uploads\processed
if not exist "uploads\vector_store" mkdir uploads\vector_store
if not exist "uploads\failed" mkdir uploads\failed

echo 🚀 Starting folder watcher...
echo    (Press Ctrl+C to stop)
echo.
echo 💡 TIP: Open uploads/documents/ in File Explorer
echo     and drag files there to auto-process!
echo.

python uploads/auto_processor.py

pause
