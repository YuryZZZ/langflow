FROM langflowai/langflow:latest

# Environment variables for Render deployment
ENV LANGFLOW_AUTO_LOGIN=true
ENV LANGFLOW_SKIP_AUTH_AUTO_LOGIN=true
ENV LANGFLOW_HOST=0.0.0.0
ENV LANGFLOW_PORT=7860

# Create a startup script that ensures directories exist at runtime
# This is needed because mounted volumes overwrite image files
# Render mounts disk at /home/user/.cache/langflow
RUN echo '#!/bin/sh' > /app/entrypoint.sh && \
    echo 'mkdir -p /home/user/.cache/langflow' >> /app/entrypoint.sh && \
    echo 'mkdir -p /app/data/.cache/langflow' >> /app/entrypoint.sh && \
    echo 'mkdir -p /app/logs' >> /app/entrypoint.sh && \
    echo 'exec python -m langflow run "$@"' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
