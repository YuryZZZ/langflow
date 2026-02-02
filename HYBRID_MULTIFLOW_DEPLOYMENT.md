# Hybrid Multiflow Multiagent System - Deployment Guide

## Overview
This system integrates **Langflow's visual workflow engine** with **OpenCode's parallel execution system** to create a true hybrid multiflow multiagent platform.

## Architecture Components

### 1. Core Integration
- **Hybrid Agent Component**: `src/backend/base/langflow/components/hybrid/hybrid_agent.py`
- **Docker Integration**: `docker/hybrid.Dockerfile`
- **Startup Script**: `scripts/start-hybrid.sh`
- **Workflow Example**: `agent/workflows/hybrid_multiflow.json`

### 2. Deployment Options

#### Option A: Local Development
```bash
# Build and run hybrid Docker container
docker build -f docker/hybrid.Dockerfile -t langflow-hybrid .
docker run -p 10000:10000 -p 8080:8080 -v langflow-data:/app/data langflow-hybrid
```

#### Option B: Render Deployment
```bash
# Deploy using render-hybrid.yaml
render deploy -f render-hybrid.yaml
```

#### Option C: Manual Integration
1. Start Langflow normally
2. Start OpenCode MCP servers separately
3. Use Hybrid Agent component in Langflow UI

## System Features

### 1. Parallel Execution Bridge
- Langflow visual workflows can trigger OpenCode parallel agent swarms
- Dynamic agent routing based on task complexity
- Cross-model validation within flow execution

### 2. Memory Persistence
- Knowledge graph storage across multiagent sessions
- Execution history tracking
- Context preservation between flow runs

### 3. Scalable Deployment
- Docker container with both Langflow and OpenCode
- Render-ready configuration
- Separate worker services for horizontal scaling

## Usage Examples

### Example 1: Basic Hybrid Flow
```python
from langflow.components.hybrid.hybrid_agent import HybridAgentComponent

agent = HybridAgentComponent()
results = agent.execute_hybrid_flow(
    task_description="Develop AI feature",
    subtasks=[
        "Analyze requirements",
        "Design architecture", 
        "Implement code",
        "Write tests",
        "Review code"
    ],
    enable_validation=True
)
```

### Example 2: Custom Agent Routing
```python
# Custom agent selection based on task content
class CustomHybridAgent(HybridAgentComponent):
    def _select_agent(self, task: str) -> str:
        if "security" in task.lower():
            return "security"
        elif "performance" in task.lower():
            return "coder-deepseek"
        elif "ui" in task.lower():
            return "coder-fast"
        return super()._select_agent(task)
```

## Configuration

### Environment Variables
```bash
LANGFLOW_DATABASE_URL=sqlite:////app/data/.cache/langflow/langflow.db
LANGFLOW_HOST=0.0.0.0
LANGFLOW_PORT=10000
OPENCODE_DATA_DIR=/app/data/.cache/opencode
OPENCODE_PROJECT_ID=langflow_hybrid
OPENCODE_MCP_SERVERS_ENABLED=true
```

### Agent Registry Configuration
Edit `agent/` directory files to customize:
- `orchestrator.md` - Main coordination agent
- `planner-*.md` - Planning agents (1-5)
- `coder-*.md` - Coding agents by specialty
- `validator.md` - Cross-model validation

## Monitoring & Debugging

### Health Checks
- Langflow: `http://localhost:10000/health_check`
- OpenCode MCP servers: Check process status

### Logs
```bash
# View hybrid system logs
docker logs <container_id>

# Monitor specific components
tail -f /app/data/.cache/langflow/langflow.log
tail -f /app/data/.cache/opencode/taskbus.log
```

### Execution Tracking
- Check `execution_history` in Hybrid Agent component
- Monitor TaskBus for parallel task status
- Review memory graph for knowledge persistence

## Performance Optimization

### 1. Worker Scaling
```yaml
# In render-hybrid.yaml
- type: worker
  name: opencode-workers
  plan: standard
  instances: 3  # Scale to 3 worker instances
```

### 2. Memory Optimization
- Adjust `max_parallel_workers` based on available resources
- Configure SQLite connection pooling
- Enable Redis for distributed caching (optional)

### 3. Agent Selection Rules
- Simple tasks → `coder-fast` (Gemini Flash)
- Complex logic → `coder-deepseek` (DeepSeek)
- Testing → `tester` (GLM-4.7)
- Review → `reviewer` (GLM-4.7)
- Validation → `validator` (Gemini Flash)

## Troubleshooting

### Common Issues

1. **Langflow starts but OpenCode doesn't**
   - Check `/app/scripts/start-hybrid.sh` permissions
   - Verify OpenCode dependencies in `requirements-opencode.txt`
   - Check MCP server ports (8081, 8082)

2. **Parallel execution not triggering**
   - Verify Hybrid Agent component is registered
   - Check TaskBus server connectivity
   - Review agent configuration files

3. **Memory persistence not working**
   - Verify `/app/data` volume is mounted
   - Check file permissions in data directory
   - Confirm memory server is running

### Debug Commands
```bash
# Check running processes
ps aux | grep -E "(langflow|opencode|mcp)"

# Test component registration
python -c "from langflow.components.hybrid.hybrid_agent import HybridAgentComponent; print('Component loaded')"

# Test MCP servers
curl http://localhost:8081/health  # TaskBus
curl http://localhost:8082/health  # Memory
```

## Next Steps

### 1. Enhanced Integration
- Real-time progress updates from OpenCode to Langflow UI
- Bidirectional communication between systems
- Shared authentication and authorization

### 2. Advanced Features
- Automated agent training from workflow patterns
- Predictive agent routing based on historical performance
- Multi-tenant support for team collaboration

### 3. Production Readiness
- Database migration from SQLite to PostgreSQL
- Kubernetes deployment manifests
- CI/CD pipeline for hybrid deployments

## Support
- Langflow Documentation: https://docs.langflow.org
- OpenCode System: Check `SYSTEM.md` and `MODELS.md`
- Hybrid Integration Issues: Review `HYBRID_MULTIFLOW_DEPLOYMENT.md`

---

**Status**: Hybrid multiflow system implemented and ready for deployment
**Last Updated**: 2026-01-28
**Version**: 1.0.0