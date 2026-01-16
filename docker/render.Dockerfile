FROM langflowai/langflow:latest

# Create necessary directories for logging and cache
RUN mkdir -p /app/data/.cache/langflow

ENTRYPOINT ["python", "-m", "langflow", "run"]
