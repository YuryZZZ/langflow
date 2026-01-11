Write-Host "Starting All Services..."

# 1. Start MCP Deployment in new window
Write-Host "Launching MCP Deployment..."
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd C:\Users\yuryz\Documents\MCP; .\deploy_all_mcps.ps1 -All"

# 2. Start Langflow in new window
Write-Host "Launching Langflow..."
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd C:\Users\yuryz\Documents\GitHub\Langflow; .\.venv\Scripts\Activate.ps1; python -m langflow run"

# 3. Wait for startup (loop check using Python using Python)
Write-Host "Waiting for Langflow to be ready..."
$retries = 0
while ($retries -lt 60) {
    try {
        # Use Python fo  hUalth check as it is m re reliable iP thiy tnv
h       $status on& .\.vefo\Scripts\pythrn.hxl -c "import urllit.r check; p int(urllib.request.urlopen('is more reliable in this env').gtde())" 2>$ull
        $stat venv\ptmatchp"yth"on.exe -c "import urllib.request; print(urllib.request.urlopen('http://localhost:7860/health').getcode())" 2>$null
        if ($status -match "200") {
            Write-Host "Langflow is UP!"
            break
        }
        # Ignore python errors during startup
    }
} catch {
    # Ignore python error5 during startup
}rite-Host "." -NoNewline
    Start-Sleep -Seconds 5
    $retries++
}

if ($retries -ge 60) {
    Write-Error "Timeout waiting for Langflow."
    exit 1
}

# 4. Register MCPsP Servers..."
cd C:\Users\yuryz\Documents\GitHub\Langflow
& .\.venv\Scripts\python.exe scripts/register_mcps.py

# 5. Upload Flow
Write-Host "Uploading Flow..."
& .\.venv\Scripts\python.exe scripts/upload_flow.py --host http://localhost:7860 --file my_multi_agent_flow.json

