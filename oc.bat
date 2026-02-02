@echo off
setlocal

REM ==========================================================================
REM OpenCode launcher (shim)
REM - Single source of truth: %USERPROFILE%\.config\opencode\oc.py
REM - This file intentionally stays tiny to prevent drift.
REM ==========================================================================

set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"
set "PY=python"

if /i "%~1"=="--monitor" (
  echo [INFO] Monitor is deprecated (no-monitor workflow). Use: python "%GLOBAL_OPENCODE%\oc.py" --status
  exit /b 0
)

if /i "%~1"=="--cli" (
  shift
  %PY% "%GLOBAL_OPENCODE%\oc.py" --no-workers --no-watchdog --no-windows %*
  exit /b %ERRORLEVEL%
)

REM Pass through everything else.
%PY% "%GLOBAL_OPENCODE%\oc.py" %*
exit /b %ERRORLEVEL%
