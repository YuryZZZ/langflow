@echo off
echo Starting MCP Deployment...
start "MCP Deployment" powershell -NoExit -Command "cd C:\Users\yuryz\Documents\MCP; .\deploy_all_mcps.ps1 -All"

echo Starting Langflow...
start "Langflow" powershell -NoExit -Command "cd C:\Users\yuryz\Documents\GitHub\Langflow; .\.venv\Scripts\Activate.ps1; python -m langflow run"

echo Waiting 30 seconds for services to start...
timeout /t 30

echo Registering MCP Servers...
cd C:\Users\yuryz\Documents\GitHub\Langflow
.venv\Scripts\python.exe scripts\register_mcps.py

echo Uploading Flow...
.venv\Scripts\python.exe scripts\upload_flow.py --host http://localhost:7860 --file my_multi_agent_flow.json

echo All tasks completed.
pause
