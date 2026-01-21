FROM langflowai/langflow:latest

# Create a startup script that ensures directories exist at runtime
# This is needed because /app/data is a mounted volume that overwrites image files
RUN echo '#!/bin/sh' > /app/entrypoint.sh && \
    echo 'mkdir -p /app/data/.cache/langflow' >> /app/entrypoint.sh && \
    echo 'mkdir -p /app/logs' >> /app/entrypoint.sh && \
    echo 'exec python -m langflow run "$@"' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
