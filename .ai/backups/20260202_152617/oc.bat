@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM OPENCODE v7.0 - UNIFIED PROJECT STARTER
REM ============================================================================
REM Initializes ANY project folder with:
REM   - .ai/ directory structure
REM   - PostgreSQL TaskBus database
REM   - Gate workflow (A->B->C->D)
REM   - 33 agents across 7 providers
REM   - MCP servers (postgres, memory, filesystem, etc.)
REM
REM Usage:
REM   oc              - Initialize project + launch monitor + CLI
REM   oc --init       - Initialize project only
REM   oc --test       - Run system tests
REM   oc --monitor    - Launch monitor window
REM   oc --cli        - Launch CLI window
REM ============================================================================

if "%~1"=="--monitor" goto MONITOR
if "%~1"=="--cli" goto CLI
if "%~1"=="--init" goto INIT
if "%~1"=="--test" goto TEST

REM ============================================================================
REM MAIN: Initialize project and launch terminals
REM ============================================================================

set "PROJECT_ROOT=%CD%"
set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"
REM NOTE: do not force bundled binary; use opencode command on PATH
set "OC_REGULAR=%APPDATA%\npm\node_modules\opencode-ai\node_modules\opencode-windows-x64\bin\opencode.exe"
set "OC_BASELINE=%APPDATA%\npm\node_modules\opencode-ai\node_modules\opencode-windows-x64-baseline\bin\opencode.exe"
set "OPENCODE_BIN_PATH="
set "OC_BIN_LABEL=path"
if exist "%OC_REGULAR%" (
    set "OC_BIN_LABEL=regular-present"
) else if exist "%OC_BASELINE%" (
    set "OC_BIN_LABEL=baseline-present"
)

REM Get project name from current folder
for %%I in (.) do set "PROJECT_NAME=%%~nxI"

echo.
echo =====================================================================
echo  OPENCODE v7.0 - Multi-Model Swarm
echo  Project: %PROJECT_NAME%
echo  Binary: %OC_BIN_LABEL%
echo =====================================================================
echo.

REM Initialize project structure and services
call "%~f0" --init
if errorlevel 1 (
    echo [ERROR] Initialization failed
    pause
    exit /b 1
)

REM Launch MONITOR in new window (green)
start "OPENCODE MONITOR - %PROJECT_NAME%" cmd /k "set \"OPENCODE_PROJECT_ROOT=%PROJECT_ROOT%\" && \"%~f0\" --monitor \"%PROJECT_ROOT%\""
timeout /t 1 /nobreak >nul

REM Launch TASKBUS WORKERS in new window (blue)
start "OPENCODE WORKERS - %PROJECT_NAME%" cmd /k "cd /d \"%PROJECT_ROOT%\" && set \"OPENCODE_PROJECT_ROOT=%PROJECT_ROOT%\" && set \"OPENCODE_BIN_PATH=\" && python \"%GLOBAL_OPENCODE%\\taskbus_worker.py\" --project-root \"%PROJECT_ROOT%\" --workers 5 --run-opencode"
timeout /t 1 /nobreak >nul

REM Launch PROGRESS WATCHDOG in new window (cyan)
start "OPENCODE WATCHDOG - %PROJECT_NAME%" cmd /k "cd /d \"%PROJECT_ROOT%\" && set \"OPENCODE_PROJECT_ROOT=%PROJECT_ROOT%\" && python \"%GLOBAL_OPENCODE%\\progress_watchdog.py\" --project-root \"%PROJECT_ROOT%\" --interval-min 10"
timeout /t 1 /nobreak >nul

REM Launch CLI in new window (white)
start "OPENCODE CLI - %PROJECT_NAME%" cmd /k "set \"OPENCODE_PROJECT_ROOT=%PROJECT_ROOT%\" && \"%~f0\" --cli \"%PROJECT_ROOT%\""

exit /b 0

REM ============================================================================
REM INIT: Initialize project structure, databases, and MCP services
REM ============================================================================
:INIT
set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"

echo.
echo ====================================================================
echo  OPENCODE PROJECT INITIALIZATION
echo ====================================================================
echo.

REM [1] Create .ai directory structure
echo [1/7] Creating project structure...
if not exist ".ai" mkdir ".ai"
if not exist ".ai\logs" mkdir ".ai\logs"
if not exist ".ai\artifacts" mkdir ".ai\artifacts"
if not exist ".ai\artifacts\planner_plans" mkdir ".ai\artifacts\planner_plans"
if not exist ".ai\artifacts\agent_results" mkdir ".ai\artifacts\agent_results"
if not exist ".ai\tasks" mkdir ".ai\tasks"
if not exist ".ai\memory" mkdir ".ai\memory"
if not exist ".ai\mcp" mkdir ".ai\mcp"
if not exist ".mcp" mkdir ".mcp"
echo   [OK] .ai/ directory structure created

REM [2] Copy global opencode.json to project (always overwrite)
echo [2/7] Copying global configuration...
if exist "%GLOBAL_OPENCODE%\opencode.json" (
    copy /Y "%GLOBAL_OPENCODE%\opencode.json" "opencode.json" >nul 2>&1
    echo   [OK] Global opencode.json copied to project
) else (
    echo   [ERROR] No global opencode.json found at %GLOBAL_OPENCODE%
    exit /b 1
)
REM Copy required instruction files referenced by opencode.json
if exist "%GLOBAL_OPENCODE%\SYSTEM.md" (
    copy /Y "%GLOBAL_OPENCODE%\SYSTEM.md" "SYSTEM.md" >nul 2>&1
    echo   [OK] SYSTEM.md copied to project
) else (
    echo   [WARN] SYSTEM.md not found in global config
)
if exist "%GLOBAL_OPENCODE%\MODELS.md" (
    copy /Y "%GLOBAL_OPENCODE%\MODELS.md" "MODELS.md" >nul 2>&1
    echo   [OK] MODELS.md copied to project
) else (
    echo   [WARN] MODELS.md not found in global config
)
if exist "%GLOBAL_OPENCODE%\.ai\PROJECT_KNOWLEDGE.md" (
    if not exist ".ai\PROJECT_KNOWLEDGE.md" (
        copy /Y "%GLOBAL_OPENCODE%\.ai\PROJECT_KNOWLEDGE.md" ".ai\PROJECT_KNOWLEDGE.md" >nul 2>&1
        echo   [OK] .ai\PROJECT_KNOWLEDGE.md copied to project
    ) else (
        echo   [OK] .ai\PROJECT_KNOWLEDGE.md already exists (not overwritten)
    )
) else (
    echo   [WARN] .ai\PROJECT_KNOWLEDGE.md not found in global config
)

REM [3] Initialize PostgreSQL Task Bus
echo [3/7] PostgreSQL TaskBus configured in opencode.json...

REM [4] Create knowledge graph
echo [4/7] Setting up knowledge graph...
if not exist ".ai\knowledge-graph.json" (
    echo {"project": "%CD%", "entities": [], "relations": []} > ".ai\knowledge-graph.json"
    echo   [OK] .ai/knowledge-graph.json created
) else (
    echo   [OK] Knowledge graph already exists
)
REM Create sequential thinking store (do not overwrite)
if not exist ".ai\sequential-thinking.json" (
    echo {"chains": {}, "current_chain_id": null, "updated_at": ""} > ".ai\sequential-thinking.json"
    echo   [OK] .ai/sequential-thinking.json created
) else (
    echo   [OK] Sequential thinking already exists
)
REM Ensure codebase map DB file exists (do not overwrite)
if not exist ".ai\codebase-map.db" (
    type nul > ".ai\codebase-map.db"
    echo   [OK] .ai/codebase-map.db created
) else (
    echo   [OK] Codebase map already exists
)

REM [5] Copy MCP server scripts
echo [5/7] Setting up MCP servers...
if not exist ".mcp" mkdir ".mcp"
if exist "%GLOBAL_OPENCODE%\.mcp" (
    xcopy /E /I /Y "%GLOBAL_OPENCODE%\.mcp\*" ".mcp\" >nul 2>&1
    echo   [OK] MCP servers copied
) else (
    echo   [WARN] No global .mcp directory found
)
REM Remove legacy enforcer (PostgreSQL-only setup)
if exist ".mcp\enforcer_mcp.py" del /f /q ".mcp\enforcer_mcp.py" >nul 2>&1
if exist "%GLOBAL_OPENCODE%\.ai\mcp" (
    if not exist ".ai\mcp" mkdir ".ai\mcp"
    xcopy /E /I /Y "%GLOBAL_OPENCODE%\.ai\mcp\*" ".ai\mcp\" >nul 2>&1
    echo   [OK] .ai\mcp tools copied
)

REM [6] Load environment variables
echo [6/7] Loading API keys...
set "KEY_COUNT=0"
if exist "%GLOBAL_OPENCODE%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%GLOBAL_OPENCODE%\.env") do (
        if not "%%A"=="" (
            set "%%A=%%B"
            set /a KEY_COUNT+=1
        )
    )
    echo   [OK] Loaded !KEY_COUNT! environment variables
) else (
    echo   [WARN] No .env file found - API keys may be missing
)

REM [7] Verify system
echo [7/7] Verifying system...
where opencode >nul 2>&1
if errorlevel 1 (
    where ocode >nul 2>&1
    if errorlevel 1 (
        echo   [ERROR] OpenCode not found. Run: npm install -g opencode-ai@latest
    ) else (
        echo   [OK] ocode found
    )
) else (
    echo   [OK] opencode found
)
if "%OC_BIN_LABEL%"=="missing" (
    echo   [WARN] OpenCode binary not found in npm cache
) else (
    echo   [OK] Using OpenCode binary: %OC_BIN_LABEL%
)

echo.
echo ====================================================================
echo  INITIALIZATION COMPLETE
echo ====================================================================
echo  Project:   %CD%
echo  Database:  PostgreSQL (configured in opencode.json)
echo  Config:    opencode.json
echo  Agents:    33 (7 providers, 3 fallbacks each)
echo  Workflow:  orchestrator -> planner -> workers -> validators
echo ====================================================================
echo.

exit /b 0

REM ============================================================================
REM TEST: Run system tests
REM ============================================================================
:TEST
set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"
echo.
echo =====================================================================
echo  Running OpenCode System Tests
echo =====================================================================
echo.
python "%GLOBAL_OPENCODE%\test_compliance.py"
echo.
echo ---------------------------------------------------------------------
echo.
python "%GLOBAL_OPENCODE%\test_enforcer.py"
echo.
pause
exit /b 0

REM ============================================================================
REM MONITOR: Green terminal - Shows status, API keys, processes, logs
REM IMPORTANT: Do NOT close this terminal - it records debug logs!
REM ============================================================================
:MONITOR
setlocal enabledelayedexpansion
set "TARGET_DIR=%~2"
if "%TARGET_DIR%"=="" set "TARGET_DIR=%CD%"
cd /d "%TARGET_DIR%"
set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"
for %%I in (.) do set "PROJECT_NAME=%%~nxI"
title OPENCODE MONITOR - %PROJECT_NAME% [DO NOT CLOSE - DEBUG LOG]
color 0A

REM Ensure logs directory exists
if not exist ".ai\logs" mkdir ".ai\logs"
set "MONITOR_LOG=.ai\logs\monitor_debug.log"

REM Log session start
echo. >> "%MONITOR_LOG%"
echo ===== MONITOR SESSION STARTED: %DATE% %TIME% ===== >> "%MONITOR_LOG%"
echo Project: %CD% >> "%MONITOR_LOG%"

:LOOP_MONITOR
cls
echo =====================================================================
echo  OPENCODE MONITOR v7.0 - %DATE% %TIME%
echo  Project: %CD%
echo  [DEBUG LOG: .ai\logs\monitor_debug.log]
echo =====================================================================
echo.

REM Log timestamp to file
echo. >> "%MONITOR_LOG%"
echo [%DATE% %TIME%] ----- Monitor Refresh ----- >> "%MONITOR_LOG%"

echo [GATE STATUS]
echo   Gate status monitoring via PostgreSQL TaskBus
echo   (Check opencode.json for connection settings)
echo.

echo =====================================================================
echo [33 AGENTS - 7 PROVIDERS]
echo =====================================================================
echo.
echo  Z.AI (GLM-4.7) - 6 agents:
echo    coder, coder-ts, tester, reviewer, researcher, planner-5
echo.
echo  Google (Gemini 3) - 7 agents:
echo    coder-fast, validator, debugger, analyst, planner-1, gemini-pro, gemini-flash
echo.
echo  OpenAI (GPT-5.x) - 5 agents:
echo    orchestrator, build, planner-3, gpt-5.2, gpt-5.1
echo.
echo  Anthropic (Claude 4.5) - 6 agents:
echo    validator-anthropic, security, planner-2, claude-haiku, claude-sonnet, claude-opus
echo.
echo  DeepSeek (V3.2) - 3 agents:
echo    coder-deepseek, planner-4, deepseek-think
echo.
echo  Groq (Fast) - 5 agents:
echo    coder-groq, kimi, reasoner, mass-worker, cheap-worker
echo.
echo  Perplexity - 1 agent:
echo    search
echo.
echo =====================================================================
echo [WORKFLOW: orchestrator -^> planner[1-5] -^> workers -^> validators]
echo =====================================================================
echo.

echo [API KEYS - 7 Providers]
if exist "%GLOBAL_OPENCODE%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%GLOBAL_OPENCODE%\.env") do (
        set "LINE=%%A"
        if "!LINE:~0,3!"=="ZAI" echo   [OK] %%A
        if "!LINE:~0,6!"=="GOOGLE" echo   [OK] %%A
        if "!LINE:~0,6!"=="OPENAI" echo   [OK] %%A
        if "!LINE:~0,9!"=="ANTHROPIC" echo   [OK] %%A
        if "!LINE:~0,8!"=="DEEPSEEK" echo   [OK] %%A
        if "!LINE:~0,4!"=="GROQ" echo   [OK] %%A
        if "!LINE:~0,10!"=="PERPLEXITY" echo   [OK] %%A
    )
) else (
    echo   [WARN] No .env file
)
echo.

echo [PROJECT FILES]
set "FILES_STATUS="
if exist .ai\knowledge-graph.json (
    echo   [OK] .ai/knowledge-graph.json
    set "FILES_STATUS=!FILES_STATUS! knowledge-graph.json"
)
if exist opencode.json (
    echo   [OK] opencode.json
    set "FILES_STATUS=!FILES_STATUS! opencode.json"
)
echo [FILES]!FILES_STATUS! >> "%MONITOR_LOG%" 2>nul
echo.

echo [MCP SERVERS - 15 Configured]
echo   taskbus, parallel, memory, sequential-thinking, filesystem, github, fetch, codebase-map
echo   postgres, playwright, computer-control, tavily, perplexity, apify, context-compactor
echo.

echo [TASKBUS LIVE]
python -c "import sys,os; sys.path.insert(0, r'%GLOBAL_OPENCODE%'); from postgres_mcp import TaskBusDB; s=TaskBusDB().get_live_status(); print('run_id={0} gate={1} running={2} queued={3} done={4}'.format(s.get('run_id'), s.get('current_gate'), s.get('running_count'), s.get('queued_count'), s.get('done_count')))" 2>nul
if errorlevel 1 echo   [WARN] TaskBus unavailable
python -c "import sys,os; sys.path.insert(0, r'%GLOBAL_OPENCODE%'); from postgres_mcp import TaskBusDB; s=TaskBusDB().get_live_status(); print('run_id={0} gate={1} running={2} queued={3} done={4}'.format(s.get('run_id'), s.get('current_gate'), s.get('running_count'), s.get('queued_count'), s.get('done_count')))" >> "%MONITOR_LOG%" 2>&1
echo.

echo [PROCESSES]
tasklist 2>nul | findstr /i "python node opencode ocode" 2>nul
tasklist 2>nul | findstr /i "python node opencode ocode" >> "%MONITOR_LOG%" 2>&1
echo.

echo [RECENT LOGS]
if exist .ai\logs\opencode.log (
    echo   --- opencode.log ---
    powershell -NoProfile -Command "Get-Content '.ai\logs\opencode.log' -Tail 5 -ErrorAction SilentlyContinue" 2>nul
)
echo.

echo =====================================================================
echo  Refreshing in 10 seconds... (Ctrl+C to stop)
echo  WARNING: DO NOT CLOSE - Recording all activity!
echo =====================================================================
timeout /t 10 /nobreak >nul
goto LOOP_MONITOR

REM ============================================================================
REM CLI: White terminal - Interactive OpenCode interface
REM ============================================================================
:CLI
set "TARGET_DIR=%~2"
if "%TARGET_DIR%"=="" set "TARGET_DIR=%CD%"
cd /d "%TARGET_DIR%"
set "GLOBAL_OPENCODE=%USERPROFILE%\.config\opencode"
REM Do not use OPENCODE_BIN_PATH here; prefer opencode on PATH
set "OPENCODE_BIN_PATH="
title OPENCODE CLI - %~2
color 0F
cls

echo =====================================================================
echo  OPENCODE MULTI-MODEL SWARM v7.0
echo  33 Agents - 7 Providers - Project Isolation
echo =====================================================================
echo  Project: %CD%
echo  Config:  opencode.json
echo =====================================================================
echo.

set "OPENCODE_WHERE="
for /f "usebackq delims=" %%P in (`where opencode 2^>nul`) do (
    set "OPENCODE_WHERE=%%P"
    goto OPENCODE_WHERE_DONE
)
:OPENCODE_WHERE_DONE
if not "%OPENCODE_WHERE%"=="" (
    echo [INFO] opencode: %OPENCODE_WHERE%
) else (
    echo [WARN] opencode not found on PATH
)
echo.

REM Load environment variables
if exist "%GLOBAL_OPENCODE%\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%GLOBAL_OPENCODE%\.env") do (
        if not "%%A"=="" set "%%A=%%B"
    )
)

echo [AGENTS BY PROVIDER - 33 Total]
echo.
echo  Z.AI (GLM-4.7):
echo    coder, coder-ts, tester, reviewer, researcher, planner-5
echo.
echo  Google (Gemini 3):
echo    coder-fast, validator, debugger, analyst, planner-1, gemini-pro, gemini-flash
echo.
echo  OpenAI (GPT-5.x):
echo    orchestrator, build, planner-3, gpt-5.2, gpt-5.1
echo.
echo  Anthropic (Claude 4.5):
echo    validator-anthropic, security, planner-2, claude-haiku, claude-sonnet, claude-opus
echo.
echo  DeepSeek (V3.2):
echo    coder-deepseek, planner-4, deepseek-think
echo.
echo  Groq (Fast):
echo    coder-groq, kimi, reasoner, mass-worker, cheap-worker
echo.
echo  Perplexity:
echo    search
echo.
echo =====================================================================
echo [HIERARCHICAL SWARM WORKFLOW]
echo   ORCHESTRATOR (GPT-5.2)
echo       ^|
echo       +--^> PLANNERS [1-5] (round-robin across 5 providers)
echo               ^|
echo               +--^> WORKERS (5+ per planner: coder, coder-fast, etc.)
echo                       ^|
echo                       +--^> VALIDATORS (cross-provider)
echo.
echo   All tasks recorded in PostgreSQL TaskBus. 3 fallbacks per agent.
echo =====================================================================
echo.
echo [COMMANDS]
echo   /auto "task"      Full swarm (orchestrator -^> planners -^> workers -^> validators)
echo   /fast "task"      Skip planner (orchestrator -^> coder-fast -^> validator)
echo   /debug "task"     Debug mode (debugger/DeepSeek Reasoner)
echo   @agent "task"     Direct call (@coder, @planner-1, @claude-opus, etc.)
echo =====================================================================
echo.

timeout /t 1 /nobreak >nul

echo [Starting OpenCode CLI...]
echo.

REM Copy global config to project (OpenCode requires local opencode.json)
copy /Y "%GLOBAL_OPENCODE%\opencode.json" "opencode.json" >nul 2>&1
echo   [OK] Global config copied to project

REM Launch OpenCode TUI (prefer opencode on PATH)
set "OC_CMD=opencode"
where opencode >nul 2>&1
if errorlevel 1 (
    where ocode >nul 2>&1
    if errorlevel 1 (
        set "OC_CMD="
    ) else (
        set "OC_CMD=ocode"
    )
)
if "%OC_CMD%"=="" (
    echo.
    echo [ERROR] OpenCode failed to start
    echo.
    echo Fix: npm install -g opencode-ai@latest
    echo.
) else (
    "%OC_CMD%"
    if errorlevel 1 (
        echo.
        echo [ERROR] OpenCode failed to start
        echo.
        echo Fix: npm install -g opencode-ai@latest
        echo.
    )
)

echo.
echo =====================================================================
echo  Session ended
echo =====================================================================
echo.
pause
