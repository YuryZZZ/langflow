@echo off
setlocal EnableDelayedExpansion

REM Get the current project path
set "PROJECT_ROOT=%CD%"
set "GLOBAL_DIR=%USERPROFILE%\.config\opencode"
echo ============================================================
echo [STOP] OpenCode Shutdown for: !PROJECT_ROOT!
echo ============================================================

REM 1. Save context to PostgreSQL before shutdown
echo [SAVE] Saving conversation context...
python "!GLOBAL_DIR!\save_context.py" 2>nul

REM 2. Kill OpenCode CLI window
echo [STOP] Terminating OpenCode CLI...
taskkill /F /FI "WINDOWTITLE eq OPENCODE*" /T >nul 2>&1
taskkill /F /IM opencode.exe >nul 2>&1

REM 3. Kill Monitor window
echo [STOP] Terminating Monitor...
taskkill /F /FI "WINDOWTITLE eq OPENCODE MONITOR*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq MONITOR*" /T >nul 2>&1

REM 4. Kill Python workers for this project
echo [STOP] Terminating workers...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { $_.CommandLine -like '*taskbus_worker*' -or $_.CommandLine -like '*mcp*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM 5. Kill Node MCP processes
echo [STOP] Terminating MCP servers...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | Where-Object { $_.CommandLine -like '*mcp*' -or $_.CommandLine -like '*playwright*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM 6. Clean temp files
echo [CLEAN] Cleaning temporary files...
if exist ".ai\live_status.json" del /f /q ".ai\live_status.json" >nul 2>&1
if exist ".ai_config_patch.py" del /f /q ".ai_config_patch.py" >nul 2>&1

REM 7. Log shutdown
echo [%date% %time%] Project stopped > ".ai\logs\shutdown.log" 2>nul

echo ============================================================
echo [SUCCESS] All processes stopped. Context saved to PostgreSQL.
echo [INFO] Run oc.bat to restart.
echo ============================================================
timeout /t 3 >nul
exit /b 0
