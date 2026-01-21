FROM langflowai/langflow:latest

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
