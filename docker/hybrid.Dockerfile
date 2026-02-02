# Hybrid Dockerfile - Langflow + OpenCode Integration
# Deploys both Langflow visual engine and OpenCode parallel execution system

FROM langflowai/langflow:latest as langflow-base

# Install OpenCode dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create OpenCode directory structure
WORKDIR /app/opencode
COPY ./.ai /app/opencode/.ai
COPY ./agent /app/opencode/agent
COPY ./oc.bat /app/opencode/
COPY ./opencode.json /app/opencode/
COPY ./SYSTEM.md /app/opencode/
COPY ./MODELS.md /app/opencode/

# Install Python dependencies for OpenCode integration
COPY ./requirements-opencode.txt /app/opencode/
RUN pip3 install -r /app/opencode/requirements-opencode.txt

# Create hybrid startup script
WORKDIR /app
COPY ./scripts/start-hybrid.sh /app/
RUN chmod +x /app/start-hybrid.sh

# Create data directory for persistent storage
RUN mkdir -p /app/data/.cache/langflow
RUN mkdir -p /app/data/.cache/opencode

# Set environment variables
ENV LANGFLOW_DATABASE_URL=sqlite:////app/data/.cache/langflow/langflow.db
ENV LANGFLOW_HOST=0.0.0.0
ENV LANGFLOW_PORT=10000
ENV LANGFLOW_LOG_LEVEL=INFO
ENV OPENCODE_DATA_DIR=/app/data/.cache/opencode
ENV OPENCODE_PROJECT_ID=langflow_hybrid
ENV OPENCODE_MCP_SERVERS_ENABLED=true

# Expose ports
EXPOSE 10000  # Langflow UI
EXPOSE 8080   # OpenCode API (if needed)

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:10000/health_check || exit 1

# Use hybrid startup script
ENTRYPOINT ["/app/start-hybrid.sh"]