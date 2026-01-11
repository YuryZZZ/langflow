#!/bin/bash
# Production Environment Configuration Template for Langflow on Render.com
# Copy this file to production_env.sh and fill in the values

# ============================================================================
# LANGFLOW CORE CONFIGURATION
# ============================================================================

# Database Configuration
export LANGFLOW_DATABASE_URL="postgresql://postgres:postgres@db:5432/langflow"
export LANGFLOW_SAVE_DB_IN_CONFIG_DIR="false"
export LANGFLOW_DATABASE_CONNECTION_RETRY="true"

# Server Configuration
export LANGFLOW_HOST="0.0.0.0"
export LANGFLOW_PORT="10000"  # Render.com default port
export LANGFLOW_WORKERS="4"   # Number of worker processes

# Logging
export LANGFLOW_LOG_LEVEL="INFO"
export LANGFLOW_LOG_FILE="/app/data/logs/langflow.log"

# Security
export LANGFLOW_AUTO_LOGIN="false"
export LANGFLOW_SUPERUSER="admin"
export LANGFLOW_SUPERUSER_PASSWORD="$(openssl rand -base64 32)"  # Generate secure password
export LANGFLOW_STORE_ENVIRONMENT_VARIABLES="true"
export LANGFLOW_REMOVE_API_KEYS="false"

# ============================================================================
# MCP SERVER CONFIGURATION
# ============================================================================

# PostgreSQL TaskBus (Required for parallel execution)
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="opencode_taskbus"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="postgres"
export POSTGRES_CONNECTION_STRING="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Search API Keys (Optional)
export TAVILY_API_KEY=""  # Get from https://app.tavily.com
export PERPLEXITY_API_KEY=""  # Get from https://www.perplexity.ai
export GITHUB_TOKEN=""  # GitHub Personal Access Token

# OpenCode Configuration
export OPENCODE_STRICT_GATES="1"  # Enable strict gate workflow (A->B->C->D)

# ============================================================================
# EXTERNAL SERVICE INTEGRATION
# ============================================================================

# OpenAI
export OPENAI_API_KEY=""

# Anthropic
export ANTHROPIC_API_KEY=""

# Google AI
export GOOGLE_API_KEY=""

# Groq
export GROQ_API_KEY=""

# Z.AI (GLM)
export ZAI_API_KEY=""

# DeepSeek
export DEEPSEEK_API_KEY=""

# ============================================================================
# DEPLOYMENT SPECIFIC
# ============================================================================

# Render.com specific
export RENDER="true"
export RENDER_EXTERNAL_URL=""  # Will be set by Render.com
export RENDER_SERVICE_NAME="langflow"

# Health check
export HEALTH_CHECK_PATH="/health"
export HEALTH_CHECK_TIMEOUT="30"

# ============================================================================
# DOCKER CONFIGURATION
# ============================================================================

# Docker Compose project name
export COMPOSE_PROJECT_NAME="langflow"

# Traefik configuration
export TRAEFIK_TAG="langflow"
export TRAEFIK_PUBLIC_TAG="langflow-public"
export TRAEFIK_PUBLIC_NETWORK="traefik-public"
export STACK_NAME="langflow"
export DOMAIN=""  # Your domain name if using custom domain

# ============================================================================
# APPLICATION SPECIFIC
# ============================================================================

# Frontend configuration
export LANGFLOW_FRONTEND_PATH="/app/src/backend/base/langflow/frontend"
export LANGFLOW_OPEN_BROWSER="false"

# Cache configuration
export LANGFLOW_LANGCHAIN_CACHE="RedisCache"
export LANGFLOW_CACHE_TYPE="redis"
export REDIS_URL="redis://redis:6379/0"

# Celery configuration
export CELERY_BROKER_URL="redis://redis:6379/0"
export CELERY_RESULT_BACKEND="redis://redis:6379/0"

# ============================================================================
# MONITORING AND OBSERVABILITY
# ============================================================================

# Prometheus
export PROMETHEUS_MULTIPROC_DIR="/tmp/prometheus"

# Log aggregation
export LOG_AGGREGATION_ENABLED="true"
export LOG_LEVEL="INFO"

# ============================================================================
# SECURITY HARDENING
# ============================================================================

# CORS
export CORS_ORIGINS="https://*.onrender.com,http://localhost:3000"

# Rate limiting
export RATE_LIMIT_ENABLED="true"
export RATE_LIMIT_REQUESTS="100"
export RATE_LIMIT_PERIOD="60"  # seconds

# Session security
export SESSION_SECRET_KEY="$(openssl rand -base64 64)"
export SESSION_COOKIE_SECURE="true"
export SESSION_COOKIE_HTTPONLY="true"

# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

echo "================================================"
echo "Production Environment Template"
echo "================================================"
echo ""
echo "1. Copy this file to production_env.sh:"
echo "   cp production_env_template.sh production_env.sh"
echo ""
echo "2. Edit production_env.sh and fill in all required values:"
echo "   - API keys for LLM providers"
echo "   - Search API keys (Tavily, Perplexity)"
echo "   - Database credentials"
echo "   - Domain name (if using custom domain)"
echo ""
echo "3. Source the environment file:"
echo "   source production_env.sh"
echo ""
echo "4. Deploy with Docker Compose:"
echo "   docker-compose -f deploy/docker-compose.yml --env-file production_env.sh up -d"
echo ""
echo "5. For Render.com deployment, add these environment variables"
echo "   in the Render.com dashboard under your service settings."
echo "================================================"