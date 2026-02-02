# Render.com Deployment Guide for Langflow with MCP Integration

## 📋 Prerequisites

1. **Render.com Account** (https://render.com)
2. **GitHub Account** with access to the Langflow repository
3. **API Keys** for all AI providers you want to use
4. **PostgreSQL Database** (will be created automatically)

## 🚀 Step-by-Step Deployment Guide

### Step 1: Fork and Prepare Repository

1. **Fork the repository** to your GitHub account
2. **Ensure your branch** (`mcp-integration-clean`) is pushed to your fork
3. **Verify** that `render_mcp.yaml` exists in the root directory

### Step 2: Create New Web Service on Render.com

1. **Log in** to Render.com dashboard
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
   - Select your forked repository
   - Select the `mcp-integration-clean` branch

### Step 3: Configure Service Settings

#### Basic Configuration:
- **Name**: `langflow-mcp` (or your preferred name)
- **Environment**: `Docker`
- **Region**: Choose closest to your users
- **Branch**: `mcp-integration-clean`
- **Root Directory**: `/` (leave as default)

#### Build Settings:
- **Dockerfile Path**: `./docker/build_and_push_mcp.Dockerfile`
- **Build Command**: (leave empty - uses Dockerfile)
- **Start Command**: (leave empty - uses Dockerfile)

#### Plan & Resources:
- **Plan**: `Standard` (recommended for production)
- **Instance Type**: `Starter` (512 MB RAM) or larger for better performance

### Step 4: Configure Environment Variables

**Add the following environment variables in Render.com dashboard:**

#### Required Core Variables:
```
LANGFLOW_DATABASE_URL=sqlite:////app/data/.cache/langflow/langflow.db
LANGFLOW_HOST=0.0.0.0
LANGFLOW_PORT=10000
LANGFLOW_LOG_LEVEL=INFO
```

#### MCP Configuration:
```
OPENCODE_CONFIG_DIR=/app/.opencode
OPENCODE_AI_DIR=/app/.ai
OPENCODE_SCRIPTS_DIR=/app/scripts
OPENCODE_STRICT_GATES=1
```

#### PostgreSQL TaskBus Configuration:
```
POSTGRES_HOST=[Render will provide this]
POSTGRES_PORT=5432
POSTGRES_DB=opencode_taskbus
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[Render will generate this]
```

#### API Keys (Required for MCP functionality):
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
ZAI_API_KEY=zai-...
GROQ_API_KEY=gsk_...
PERPLEXITY_API_KEY=pplx-...
TAVILY_API_KEY=tvly-...
GITHUB_TOKEN=ghp_...
```

### Step 5: Set Up PostgreSQL Database

1. **In Render.com dashboard**, go to **"New +"** → **"PostgreSQL"**
2. **Configure Database:**
   - **Name**: `opencode_taskbus`
   - **Database**: `opencode_taskbus`
   - **User**: `postgres`
   - **Plan**: `Free` (or higher for production)
   - **Region**: Same as your web service

3. **Connect Database to Web Service:**
   - Go to your web service settings
   - Under **"Environment"** → **"Advanced"**
   - Add the PostgreSQL database as a linked resource
   - Render will automatically set `POSTGRES_HOST`, `POSTGRES_PASSWORD`, etc.

### Step 6: Configure Disk Storage

1. **In web service settings**, go to **"Disk"** section
2. **Add a persistent disk:**
   - **Name**: `langflow-mcp-data`
   - **Mount Path**: `/app/data`
   - **Size**: 1GB (minimum)

### Step 7: Configure Health Checks

1. **In web service settings**, go to **"Health Check Path"**
2. **Set**: `/health`
3. **Timeout**: 30 seconds

### Step 8: Deploy

1. **Click "Create Web Service"**
2. **Monitor the build process** in the logs
3. **Wait for deployment** to complete (5-10 minutes)

## 🔧 Post-Deployment Configuration

### Step 9: Verify Deployment

1. **Check service URL**: `https://langflow-mcp.onrender.com`
2. **Test health endpoint**: `https://langflow-mcp.onrender.com/health`
3. **Access Langflow UI**: `https://langflow-mcp.onrender.com`

### Step 10: Test MCP Integration

1. **Access the MCP tools** in Langflow interface
2. **Test parallel execution**:
   ```bash
   # Use the test script
   curl -X POST https://langflow-mcp.onrender.com/api/v1/mcp/test
   ```

3. **Verify TaskBus connection**:
   ```bash
   # Check PostgreSQL connection
   curl https://langflow-mcp.onrender.com/api/v1/mcp/status
   ```

### Step 11: Configure Custom Domain (Optional)

1. **In web service settings**, go to **"Custom Domains"**
2. **Add your domain** and follow DNS configuration instructions
3. **Enable HTTPS** automatically with Let's Encrypt

## 🛠️ Troubleshooting

### Common Issues:

#### 1. **Build Fails**
- **Check Dockerfile path** is correct
- **Verify repository access** permissions
- **Check build logs** for specific errors

#### 2. **Service Won't Start**
- **Verify environment variables** are set correctly
- **Check PostgreSQL connection** string
- **Review application logs** for startup errors

#### 3. **MCP Servers Not Working**
- **Verify all API keys** are set correctly
- **Check PostgreSQL database** is accessible
- **Test individual MCP servers** using test scripts

#### 4. **Performance Issues**
- **Upgrade instance type** to larger plan
- **Enable caching** with Redis (additional service)
- **Optimize database queries**

## 📊 Monitoring and Maintenance

### 1. **Logs**
- Access logs in Render.com dashboard
- Set up log aggregation if needed

### 2. **Metrics**
- Monitor CPU, memory, and disk usage
- Set up alerts for resource thresholds

### 3. **Backups**
- Enable automatic PostgreSQL backups
- Regular database exports recommended

### 4. **Updates**
- Enable auto-deploy for main branch updates
- Regular dependency updates
- Security patches

## 🔒 Security Considerations

### 1. **API Keys**
- Never commit API keys to repository
- Use Render.com environment variables
- Rotate keys regularly

### 2. **Database Security**
- Use strong passwords
- Enable SSL connections
- Restrict network access

### 3. **Network Security**
- Enable HTTPS
- Configure CORS appropriately
- Set up rate limiting

## 📈 Scaling

### Vertical Scaling:
- Upgrade to larger instance types
- Increase disk size as needed

### Horizontal Scaling:
- Add more instances (requires load balancer)
- Separate services (API, frontend, workers)

### Database Scaling:
- Upgrade PostgreSQL plan
- Add read replicas
- Implement connection pooling

## 🆘 Support

### Render.com Support:
- Documentation: https://docs.render.com
- Community: https://community.render.com
- Support: https://render.com/contact

### Langflow Support:
- Documentation: https://docs.langflow.org
- GitHub Issues: https://github.com/langflow-ai/langflow/issues
- Discord: https://discord.gg/EqksyE2EX9

### MCP Integration Support:
- Check `INTEGRATION_GUIDE.md` for detailed setup
- Review `MCP_SERVERS.md` for server configuration
- Test with `scripts/test_mcp_integration.py`

---

## ✅ Deployment Checklist

- [ ] Repository forked and branch pushed
- [ ] Web service created on Render.com
- [ ] Environment variables configured
- [ ] PostgreSQL database created and linked
- [ ] Persistent disk configured
- [ ] Health check path set
- [ ] Service deployed successfully
- [ ] Health endpoint responding
- [ ] Langflow UI accessible
- [ ] MCP tools working
- [ ] TaskBus connection verified
- [ ] Custom domain configured (optional)
- [ ] Monitoring set up
- [ ] Security measures implemented

---

**Deployment Time**: 15-30 minutes  
**Cost**: Free tier available, ~$7/month for Standard plan  
**Maintenance**: Low (Render.com handles infrastructure)

**Next Steps**: After deployment, run integration tests and configure your workflows in the Langflow interface.