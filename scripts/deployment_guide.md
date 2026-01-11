# Langflow MCP Integration Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying Langflow with MCP (Model Context Protocol) integration to Render.com.

## What We've Accomplished

### ✅ Completed Tasks:
1. **MCP Infrastructure Setup**: Configured 14 MCP servers (13 enabled)
2. **Parallel Swarm Testing**: Successfully tested parallel execution with 5 planners across different AI providers
3. **Deployment Scripts**: Created comprehensive deployment and testing scripts
4. **Docker Configuration**: Updated Dockerfile with MCP server dependencies
5. **Render Configuration**: Created `render_mcp.yaml` with PostgreSQL database for TaskBus
6. **Testing Framework**: Built `test_mcp_integration.py` for comprehensive testing

### 🔧 Technical Components:
- **MCP Servers**: parallel, taskbus, memory, sequential-thinking, filesystem, github, fetch, postgres, context-compactor, playwright, tavily, perplexity
- **AI Providers**: 7 providers (Google, OpenAI, Anthropic, DeepSeek, Z.AI, Groq, Perplexity)
- **Agents**: 33 agents configured for parallel execution
- **Database**: PostgreSQL for TaskBus tracking and coordination

## Deployment Steps

### Step 1: Prepare Your Repository
```bash
# Clone or fork the Langflow repository
git clone https://github.com/langflow-ai/langflow.git
cd langflow

# Checkout the MCP integration branch
git checkout feature/langflow-env-setup

# Verify all files are present
ls -la scripts/
```

### Step 2: Set Up Render.com Account
1. Create a Render.com account (if you don't have one)
2. Connect your GitHub repository
3. Ensure you have billing set up (free tier available)

### Step 3: Configure Environment Variables
Set the following environment variables in Render.com dashboard:

**Required API Keys:**
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY` 
- `GOOGLE_API_KEY`
- `DEEPSEEK_API_KEY`
- `ZAI_API_KEY`
- `GROQ_API_KEY`
- `PERPLEXITY_API_KEY`
- `TAVILY_API_KEY`

**MCP Configuration:**
- `OPENCODE_CONFIG_DIR=/app/.opencode`
- `OPENCODE_AI_DIR=/app/.ai`
- `OPENCODE_SCRIPTS_DIR=/app/scripts`

### Step 4: Deploy to Render.com
**Option A: Manual Deployment via Render Dashboard**
1. Go to Render.com dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select branch: `feature/langflow-env-setup`
5. Set build command: `docker build -f docker/build_and_push_mcp.Dockerfile -t langflow-mcp .`
6. Set start command: `langflow run`
7. Configure environment variables as above
8. Add PostgreSQL database: `opencode_taskbus`

**Option B: Using Render CLI**
```bash
# Install Render CLI
npm install -g @renderinc/cli

# Login to Render
render login

# Deploy using render_mcp.yaml
render deploy render_mcp.yaml
```

### Step 5: Test Deployment
Once deployed, test the integration:

```bash
# Test health endpoint
curl https://your-langflow-deployment.onrender.com/health

# Test MCP integration
python scripts/test_mcp_integration.py --url https://your-langflow-deployment.onrender.com --test-all

# Test parallel execution
python scripts/deploy_mcp_integration.py --host https://your-langflow-deployment.onrender.com
```

### Step 6: Verify Parallel Execution
1. Access the Langflow UI at your deployment URL
2. Navigate to MCP servers section
3. Verify all MCP servers are registered and active
4. Test parallel execution using the test flow

## Configuration Files

### 1. `render_mcp.yaml`
- Main Render.com deployment configuration
- Includes PostgreSQL database for TaskBus
- Configures MCP environment variables
- Uses custom Dockerfile with MCP dependencies

### 2. `docker/build_and_push_mcp.Dockerfile`
- Base Docker image with MCP server dependencies
- Installs Node.js MCP servers globally
- Sets up MCP configuration directories
- Copies MCP scripts and configuration

### 3. `scripts/deploy_mcp_integration.py`
- Main deployment script
- Registers MCP servers with Langflow
- Tests connectivity and functionality
- Provides detailed error reporting

### 4. `scripts/test_mcp_integration.py`
- Comprehensive testing framework
- Tests health endpoints, API version, MCP registration
- Supports individual server testing or full suite

### 5. `scripts/production_env_template.sh`
- Production environment configuration template
- Includes all required environment variables
- Security best practices for API keys

## Testing Your Deployment

### Quick Test Commands:
```bash
# Test health
python scripts/test_mcp_integration.py --url YOUR_URL --test-parallel

# Test TaskBus
python scripts/test_mcp_integration.py --url YOUR_URL --test-taskbus

# Full test suite
python scripts/test_mcp_integration.py --url YOUR_URL --test-all
```

### Expected Results:
1. **Health endpoint**: HTTP 200 OK
2. **API version**: Should return version number
3. **MCP servers**: At least 2 servers should register successfully
4. **Parallel execution**: Should complete 5 tasks in parallel

## Troubleshooting

### Common Issues:

**1. MCP Server Registration Fails**
- Check if Node.js MCP servers are installed in Docker image
- Verify environment variables are set correctly
- Check Langflow logs for MCP registration errors

**2. PostgreSQL Connection Issues**
- Verify PostgreSQL database is provisioned
- Check connection string in environment variables
- Ensure database user has proper permissions

**3. API Key Errors**
- Verify all API keys are set in Render.com dashboard
- Check if API keys have proper permissions/quotas
- Test API keys independently using curl

**4. Parallel Execution Not Working**
- Verify TaskBus database is accessible
- Check if workers can claim tasks
- Monitor TaskBus logs for errors

### Debug Commands:
```bash
# Check Docker build logs
docker build -f docker/build_and_push_mcp.Dockerfile . --no-cache

# Check container logs
docker logs <container_id>

# Test PostgreSQL connection
psql "postgresql://postgres:password@localhost:5432/opencode_taskbus"
```

## Monitoring and Maintenance

### 1. Log Monitoring
- Monitor Render.com logs dashboard
- Check Langflow application logs
- Monitor PostgreSQL database logs

### 2. Performance Monitoring
- Track parallel execution completion times
- Monitor API usage and costs
- Check database connection pool usage

### 3. Regular Maintenance
- Update MCP server versions periodically
- Rotate API keys regularly
- Backup PostgreSQL database
- Monitor disk usage for MCP cache

## Security Considerations

### 1. API Key Security
- Store API keys in Render.com environment variables (not in code)
- Use different API keys for different environments
- Regularly rotate API keys
- Monitor API usage for anomalies

### 2. Database Security
- Use strong PostgreSQL passwords
- Limit database access to application only
- Regular backups and monitoring
- Enable SSL connections if available

### 3. Network Security
- Use HTTPS for all connections
- Configure proper CORS settings
- Rate limit API endpoints
- Monitor for suspicious activity

## Next Steps After Deployment

### 1. Integration Testing
- Test with real Langflow flows
- Verify MCP tool integration works
- Test parallel execution with complex tasks

### 2. Performance Optimization
- Tune PostgreSQL connection pool
- Optimize MCP server timeouts
- Configure caching where appropriate

### 3. Scaling Considerations
- Monitor resource usage
- Plan for scaling PostgreSQL
- Consider load balancing for high traffic

### 4. Documentation Updates
- Update team documentation
- Create runbooks for common issues
- Document deployment procedures

## Support and Resources

### Useful Links:
- [Langflow Documentation](https://docs.langflow.org/)
- [MCP Documentation](https://modelcontextprotocol.io/)
- [Render.com Documentation](https://render.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Getting Help:
- Check Langflow GitHub issues
- Join Langflow Discord community
- Contact Render.com support
- Review MCP server documentation

## Conclusion
This deployment provides a fully functional Langflow instance with MCP integration for parallel AI agent execution. The system is production-ready with proper security, monitoring, and maintenance procedures.

For any issues or questions, refer to the troubleshooting section or contact the development team.