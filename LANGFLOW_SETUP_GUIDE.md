# Langflow Setup Guide

This guide details the steps to set up and run Langflow, including its integrated frontend and backend, and the associated MCP (Model Context Protocol) servers.

## 1. Overview of Current Configuration

This setup aims to run Langflow on `http://localhost:7860`, with the backend serving the frontend static files. It also includes Docker Compose configurations for several MCP servers.

### 1.1. Langflow Environment Variables (`.env`)

The `.env` file in the root directory contains the following configuration:

```env
# Description: Example of .env file
# Usage: Copy this file to .env and change the values
#        according to your needs
#        Do not commit .env file to git
#        Do not change .env.example file

# Config directory
# Directory where files, logs and database will be stored
# Example: LANGFLOW_CONFIG_DIR=~/.langflow
LANGFLOW_CONFIG_DIR=

# Save database in the config directory
# Values: true, false
# If false, the database will be saved in Langflow's root directory
# This means that the database will be deleted when Langflow is uninstalled
# and that the database will not be shared between different virtual environments
# Example: LANGFLOW_SAVE_DB_IN_CONFIG_DIR=true
LANGFLOW_SAVE_DB_IN_CONFIG_DIR=false

# Database URL
# Postgres example: LANGFLOW_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langflow
# SQLite example:
LANGFLOW_DATABASE_URL=sqlite:///./langflow.db

# Database connection retry
# Values: true, false
# If true, the database will retry to connect to the database if it fails
# Example: LANGFLOW_DATABASE_CONNECTION_RETRY=true
LANGFLOW_DATABASE_CONNECTION_RETRY=false

# Cache type
LANGFLOW_LANGCHAIN_CACHE=SQLiteCache
LANGFLOW_CACHE_TYPE=memory

# Server host
# Example: LANGFLOW_HOST=localhost
LANGFLOW_HOST=0.0.0.0

# Worker processes
# Example: LANGFLOW_WORKERS=1
LANGFLOW_WORKERS=1

# Server port
# Example: LANGFLOW_PORT=7860
LANGFLOW_PORT=7860

# Logging level
# Example: LANGFLOW_LOG_LEVEL=critical
LANGFLOW_LOG_LEVEL=INFO

# Path to the log file
# Example: LANGFLOW_LOG_FILE=logs/langflow.log
LANGFLOW_LOG_FILE=

# Path to the frontend directory containing build files
# Example: LANGFLOW_FRONTEND_PATH=/path/to/frontend/build/files
LANGFLOW_FRONTEND_PATH=src/backend/base/langflow/frontend

# Whether to open the browser after starting the server
# Values: true, false
# Example: LANGFLOW_OPEN_BROWSER=true
LANGFLOW_OPEN_BROWSER=true

# Whether to remove API keys from the projects saved in the database
# Values: true, false
# Example: LANGFLOW_REMOVE_API_KEYS=false
LANGFLOW_REMOVE_API_KEYS=false

# Set AUTO_LOGIN to false if you want to disable auto login
# and use the login form to login. LANGFLOW_SUPERUSER and LANGFLOW_SUPERUSER_PASSWORD
# must be set if AUTO_LOGIN is set to false
# Values: true, false
LANGFLOW_AUTO_LOGIN=true

# Superuser username
# Example: LANGFLOW_SUPERUSER=admin
LANGFLOW_SUPERUSER=

# Superuser password
# Example: LANGFLOW_SUPERUSER_PASSWORD=123456
LANGFLOW_SUPERUSER_PASSWORD=

# Should store environment variables in the database
# Values: true, false
LANGFLOW_STORE_ENVIRONMENT_VARIABLES=false

# STORE_URL
# Example: LANGFLOW_STORE_URL=https://api.langflow.store
# LANGFLOW_STORE_URL=

# DOWNLOAD_WEBHOOK_URL
#
# LANGFLOW_DOWNLOAD_WEBHOOK_URL=

# LIKE_WEBHOOK_URL
#
# LANGFLOW_LIKE_WEBHOOK_URL=

# Value must finish with slash /
#BACKEND_URL=http://localhost:7860/
BACKEND_URL=http://localhost:7860/
```

**Important Note on API Keys**: The `.env` file currently contains placeholder values. For full functionality of certain MCP servers (e.g., Perplexity, Apify) and Langflow components, you **must** replace these placeholders with your actual API keys. For example:
`PERPLEXITY_API_KEY=your_actual_perplexity_api_key_here`
`APIFY_API_KEY=your_actual_apify_api_key_here`

### 1.2. MCP Docker Compose Configuration (`../../MCP/docker-compose-all-mcps.yml`)

This file defines the Docker services for various MCP servers:

```yaml
version: '3.8'

services:
  # Crawl4AI MCP Server (already working)
  crawl4ai-mcp:
    build:
      context: ./crawl4ai-mcp
      dockerfile: Dockerfile
    ports:
      - "11235:11235"
    environment:
      - DEBUG=mcp:*
      - NODE_ENV=production
      - CRAWL4AI_PORT=11235
    volumes:
      - ./data/crawl4ai:/app/data
      - ./logs/crawl4ai:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11235/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mcp-network

  # Perplexity MCP Server
  perplexity-mcp:
    build:
      context: ./perplexity-docker
      dockerfile: Dockerfile
    ports:
      - "8091:8091"
    environment:
      - PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}
      - DEBUG=mcp:*
      - NODE_ENV=production
      - MCP_PORT=8091
    volumes:
      - ./data/perplexity:/app/data
      - ./logs/perplexity:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mcp-network
    depends_on:
      - crawl4ai-mcp

  # Memory MCP Server (Knowledge Graph)
  memory-mcp:
    build:
      context: ./memory-mcp
      dockerfile: Dockerfile
    ports:
      - "8092:8092"
    environment:
      - DEBUG=mcp:*
      - NODE_ENV=production
      - MCP_PORT=8092
      - MEMORY_PATH=/app/data/knowledge_graph.jsonl
    volumes:
      - ./data/memory:/app/data
      - ./logs/memory:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8092/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mcp-network
    depends_on:
      - crawl4ai-mcp

  # Stagehand MCP Server
  stagehand-mcp:
    build:
      context: ./stagehand-mcp
      dockerfile: Dockerfile
    ports:
      - "8093:8093"
    environment:
      - DEBUG=mcp:*
      - NODE_ENV=production
      - MCP_PORT=8093
    volumes:
      - ./data/stagehand:/app/data
      - ./logs/stagehand:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - mcp-network
    depends_on:
      - crawl4ai-mcp

  # Commenting out services that use mcp/unified image as it's not locally available
  # browser-tools-mcp:
  #   image: mcp/unified
  #   ports:
  #     - "8090:8090"
  #   environment:
  #     - MCP_SERVER=browser-tools
  #     - DEBUG=mcp:*
  #     - NODE_ENV=production
  #     - MCP_PORT=8090
  #   volumes:
  #     - ./data/browser-tools:/app/data
  #     - ./logs/browser-tools:/app/logs
  #     - ./scripts:/app/scripts:ro
  #   restart: unless-stopped
  #   healthcheck:
  #     test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
  #     interval: 30s
  #     timeout: 10s
  #     retries: 3
  #   networks:
  #     - mcp-network
  #   depends_on:
  #     - crawl4ai-mcp

  # langchain-mcp:
  #   image: mcp/unified
  #   ports:
  #     - "8082:8082"
  #   environment:
  #     - MCP_SERVER=langchain
  #     - DEBUG=mcp:*
  #     - NODE_ENV=production
  #     - MCP_PORT=8082
  #   volumes:
  #     - ./data/langchain:/app/data
  #     - ./logs/langchain:/app/logs
  #     - ./scripts:/app/scripts:ro
  #   restart: unless-stopped
  #   healthcheck:
  #     test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
  #     interval: 30s
  #     timeout: 10s
  #     retries: 3
  #   networks:
  #     - mcp-network
  #   depends_on:
  #     - crawl4ai-mcp

  # filesystem-mcp:
  #   image: mcp/unified
  #   ports:
  #     - "8094:8094"
  #   environment:
  #     - MCP_SERVER=filesystem
  #     - DEBUG=mcp:*
  #     - NODE_ENV=production
  #     - MCP_PORT=8094
  #     - FS_PATH=/app/data
  #   volumes:
  #     - ./data/filesystem:/app/data
  #     - ./logs/filesystem:/app/logs
  #     - ./scripts:/app/scripts:ro
  #   restart: unless-stopped
  #   healthcheck:
  #     test: ["CMD", "curl", "-f", "http://localhost:8094/health"]
  #     interval: 30s
  #     timeout: 10s
  #     retries: 3
  #   networks:
  #     - mcp-network
  #   depends_on:
  #     - crawl4ai-mcp

  # sequential-thinking-mcp:
  #   image: mcp/unified
  #   ports:
  #     - "8095:8095"
  #   environment:
  #     - MCP_SERVER=sequential-thinking
  #     - DEBUG=mcp:*
  #     - NODE_ENV=production
  #     - MCP_PORT=8095
  #   volumes:
  #     - ./data/sequential-thinking:/app/data
  #     - ./logs/sequential-thinking:/app/logs
  #     - ./scripts:/app/scripts:ro
  #   restart: unless-stopped
  #   healthcheck:
  #     test: ["CMD", "curl", "-f", "http://localhost:8095/health"]
  #     interval: 30s
  #     timeout: 10s
  #     retries: 3
  #   networks:
  #     - mcp-network
  #   depends_on:
  #     - crawl4ai-mcp

  # fetch-mcp:
  #   image: mcp/unified
  #   ports:
  #     - "8096:8096"
  #   environment:
  #     - MCP_SERVER=fetch
  #     - DEBUG=mcp:*
  #     - NODE_ENV=production
  #     - MCP_PORT=8096
  #   volumes:
  #     - ./data/fetch:/app/data
  #     - ./logs/fetch:/app/logs
  #     - ./scripts:/app/scripts:ro
  #   restart: unless-stopped
  #   healthcheck:
  #     test: ["CMD", "curl", "-f", "http://localhost:8096/health"]
  #     interval: 30s
  #     timeout: 10s
  #     retries: 3
  #   networks:
  #     - mcp-network
  #   depends_on:
  #     - crawl4ai-mcp

networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  crawl4ai-data:
    driver: local
  perplexity-data:
    driver: local
  memory-data:
    driver: local
  browser-tools-data:
    driver: local
  stagehand-data:
    driver: local
  langchain-data:
    driver: local
  filesystem-data:
    driver: local
  sequential-thinking-data:
    driver: local
  fetch-data:
    driver: local
```

### 1.3. Memory MCP Dockerfile (`../../MCP/memory-mcp/Dockerfile`)

This Dockerfile is used to build the `memory-mcp` service:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install git and other build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*

# Install required dependencies
# Install required dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Clone the python-sdk repository
RUN git clone https://github.com/modelcontextprotocol/python-sdk.git /app/python-sdk
# Set PYTHONPATH to include the cloned repository
ENV PYTHONPATH=/app/python-sdk:$PYTHONPATH

# Copy source files
COPY memory_server.py /app/

# Create directories for persistent data
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV MEMORY_PERSIST=true
ENV MEMORY_AUTO_SAVE=120

# Expose port if needed for HTTP-based communication
# EXPOSE 8000

ENTRYPOINT ["python", "memory_server.py"]
```

### 1.4. Memory MCP Requirements (`../../MCP/memory-mcp/requirements.txt`)

This file lists the Python dependencies for the `memory-mcp` service:

```
jsonlines==3.1.0
pydantic>=2.7.2,<3.0.0
```

## 2. Setup and Running Instructions

### 2.1. Prerequisites

*   **Docker Desktop**: Ensure Docker Desktop is installed and running for Docker Compose.
*   **uv**: Python package installer and resolver.
*   **npm**: Node.js package manager.

### 2.2. Start MCP Servers (Docker Compose)

Navigate to the `../../MCP/` directory and run Docker Compose:

```bash
cd ../../MCP/
docker-compose -f docker-compose-all-mcps.yml up -d
```

**Current Status of MCP Servers**:
*   `mcp-crawl4ai-mcp-1`, `mcp-perplexity-mcp-1`, and `mcp-stagehand-mcp-1` Docker containers are running, but their health checks are currently failing (status: `unhealthy`). Their internal logs suggest they are operational, but their `/health` endpoints are not responding as expected.
*   `mcp-memory-mcp-1` Docker container is continuously restarting due to a `ModuleNotFoundError: No module named 'model_context_protocol'`. This server is not functional.

### 2.3. Install Langflow Backend Dependencies

Navigate to the Langflow root directory (`c:/Users/yuryz/Documents/GitHub/Langflow`) and install backend dependencies:

```bash
uv sync --frozen --extra "postgresql"
```

### 2.4. Build Langflow Frontend

Navigate to the Langflow root directory and build the frontend static files:

```bash
cd src/frontend && npm run build
```

Then, copy the built files to the backend's static serving directory:

```bash
Copy-Item -Path src/frontend/build/* -Destination src/backend/base/langflow/frontend -Recurse -Force
```

### 2.5. Run Langflow Application

Ensure all previous Langflow backend and frontend processes are terminated. Then, from the Langflow root directory, run the integrated application:

```bash
uv run langflow run --host 0.0.0.0 --port 7860 --frontend-path src/backend/base/langflow/frontend --env-file .env
```

**Expected Outcome**: The Langflow UI should be accessible at `http://localhost:7860`.

## 3. Confirm PostgreSQL Connection

The `.env` file has been updated to use the Google Cloud PostgreSQL connection string: `LANGFLOW_DATABASE_URL=postgresql://postgres:#v}y3#8W@34.10.108.107:5432/postgres`.

**Current Status**: Attempting to connect to the PostgreSQL database resulted in a "Connection timed out" error. This indicates that the PostgreSQL server at `34.10.108.107` on port `5432` is not reachable from this environment. This is likely due to network configuration, firewall rules, or the server not being publicly accessible. Further troubleshooting of the PostgreSQL server's network accessibility is required outside of this setup process.

## 4. Clean Up Temporary Files

To clean up caches and temporary directories:

### Clean Python Cache
```bash
find . -type d -name '__pycache__' -exec rm -r {} +
find . -type f -name '*.py[cod]' -exec rm -f {} +
find . -type f -name '*~' -exec rm -f {} +
find . -type f -name '.*~' -exec rm -f {} +
# For Windows, you might need to use PowerShell equivalents or Git Bash
# Example for PowerShell: Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force
# Get-ChildItem -Path . -Include *.pyc, *.pyo, *.pyd -Recurse -File | Remove-Item -Force
```

### Clean npm Cache and Frontend Builds
```bash
cd src/frontend && npm cache clean --force
# For Windows, use PowerShell equivalents for directory clearing
# Example for PowerShell: Remove-Item -Path src/frontend/node_modules -Recurse -Force -ErrorAction SilentlyContinue
# Remove-Item -Path src/frontend/build -Recurse -Force -ErrorAction SilentlyContinue
# Remove-Item -Path src/backend/base/langflow/frontend -Recurse -Force -ErrorAction SilentlyContinue
rm -f src/frontend/package-lock.json
```

**Note**: The `find` and `rm` commands are Unix-like. For Windows, you may need to use PowerShell equivalents or a Git Bash terminal.

---

This document provides the current working configuration and steps to get Langflow and its associated MCP servers running. Remember to fill in your actual API keys in the `.env` file for full functionality.
<environment_details>
# VSCode Visible Files
LANGFLOW_SETUP_GUIDE.md

# VSCode Open Tabs
pyproject.toml
src/backend/base/langflow/components/tools/__init__.py
src/backend/base/langflow/components/tools/mcp_tool.py
src/backend/tests/unit/components/tools/test_mcp_tool.py
src/backend/base/langflow/components/data/__init__.py
src/backend/base/langflow/components/data/postgresql_component.py
src/backend/tests/unit/components/data/test_postgresql_component.py
INTEGRATION_GUIDE.md
test_components.py
../../MCP/docker-compose-all-mcps.yml
../../MCP/memory-mcp/requirements.txt
../../MCP/memory-mcp/Dockerfile
.env
LANGFLOW_SETUP_GUIDE.md

# Recently Modified Files
These files have been modified since you last accessed them (file was just edited so you may need to re-read it before editing):
LANGFLOW_SETUP_GUIDE.md

# Current Time
6/24/2025, 6:29:49 PM (Europe/London, UTC+1:00)

# Context Window Usage
340,000 / 1,048.576K tokens used (32%)

# Current Mode
ACT MODE
</environment_details>
