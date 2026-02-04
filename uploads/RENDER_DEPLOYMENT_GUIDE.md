# 🚀 Render Deployment Guide - Folder Upload + MCP Gateway

## ✅ Prerequisites

- Render account (https://render.com)
- Langflow deployed on Render
- MCP servers configured

## 📦 Files to Deploy

```
uploads/
├── auto_processor.py              # Main file processor (with MCP support)
├── config.json                    # Configuration
├── FOLDER_UPLOAD_MCP_GATEWAY.json # MCP-enabled flow
├── requirements.txt               # Python dependencies
└── start_watcher.py               # Render startup script
```

## 🚀 Step-by-Step Deployment

### Step 1: Add Dependencies

In your Render dashboard, add to **Build Command**:

```bash
pip install -r uploads/requirements.txt
```

Or add to your `requirements.txt`:
```
watchdog>=3.0.0
faiss-cpu>=1.7.4
numpy>=1.24.0
openai>=1.0.0
python-dotenv>=1.0.0
PyPDF2>=3.0.0
python-docx>=0.8.11
```

### Step 2: Configure Environment Variables

In Render Dashboard → Environment:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional - MCP Configuration
MCP_GATEWAY_ENABLED=true
MCP_SERVERS=filesystem,memory,sequential-thinking

# Upload Configuration
UPLOAD_FOLDER=uploads/documents
VECTOR_STORE_PATH=uploads/vector_store
MAX_FILE_SIZE_MB=50
CHUNK_SIZE=1000
```

### Step 3: Create Persistent Disk

Render Dashboard → Disks:

```
Name: langflow-uploads
Mount Path: /uploads
Size: 5 GB (or as needed)
```

### Step 4: Update Start Command

In Render Dashboard:

```bash
# Start file watcher in background
python uploads/start_render_watcher.py &

# Start Langflow
python -m langflow run --host 0.0.0.0 --port $PORT
```

### Step 5: Import MCP-Enabled Flow

1. Open your Langflow instance: `https://your-app.onrender.com`
2. Go to **Flows** → **Import**
3. Upload: `uploads/FOLDER_UPLOAD_MCP_GATEWAY.json`
4. Click **Save**

## 🔧 MCP Gateway Configuration

Ensure your `opencode.json` includes MCP servers:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": ["python", "-m", "mcp_server_filesystem", "uploads/documents"],
      "env": {
        "MCP_FILESYSTEM_ROOT": "uploads/documents"
      }
    },
    "memory": {
      "command": ["python", "-m", "mcp_server_memory", "uploads/vector_store/metadata.json"]
    }
  }
}
```

## 🧪 Testing on Render

### Test 1: Upload Files

1. SSH into your Render instance:
```bash
render ssh your-service-name
```

2. Create test file:
```bash
echo "This is a test document for the upload system." > uploads/documents/test.txt
```

3. Check processing:
```bash
tail -f uploads/processor.log
```

### Test 2: Query via API

```bash
curl -X POST "https://your-app.onrender.com/api/v1/run/YOUR_FLOW_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What is in my uploaded documents?",
    "session_id": "test-session"
  }'
```

### Test 3: MCP Gateway Health Check

```bash
curl "https://your-app.onrender.com/api/v1/mcp/health"
```

## 📊 Monitoring on Render

### Logs

```bash
# View application logs
render logs your-service-name

# View processor logs
render ssh your-service-name -- tail -f uploads/processor.log
```

### Metrics

```bash
# Check vector store size
render ssh your-service-name -- du -sh uploads/vector_store

# Count processed files
render ssh your-service-name -- ls uploads/processed | wc -l

# View processing stats
curl "https://your-app.onrender.com/api/v1/stats"
```

## 🔒 Security on Render

### File Upload Security

```python
# In auto_processor.py - add to config.json
{
  "allowed_extensions": [".txt", ".pdf", ".docx", ".md"],
  "max_file_size_mb": 50,
  "scan_uploads": true,
  "sanitize_content": true
}
```

### MCP Server Security

```bash
# Restrict MCP server access
export MCP_ALLOWED_ORIGINS="https://your-app.onrender.com"
export MCP_AUTH_TOKEN="your-secure-token"
```

## 🐛 Troubleshooting

### Issue: Files not processing

```bash
# Check if watcher is running
ps aux | grep auto_processor

# Check folder permissions
ls -la uploads/

# Restart watcher
python uploads/start_render_watcher.py
```

### Issue: MCP Gateway not working

```bash
# Check MCP server status
curl "https://your-app.onrender.com/api/v1/mcp/status"

# Verify MCP configuration
cat opencode.json | grep mcpServers

# Check MCP logs
render logs your-service-name --filter mcp
```

### Issue: Vector store not persisting

```bash
# Verify disk is mounted
df -h | grep uploads

# Check vector store directory
ls -la uploads/vector_store/

# Rebuild index
python -c "from uploads.auto_processor import FileProcessor; p = FileProcessor(); p._init_vector_store()"
```

## 📈 Scaling on Render

### Increase File Limits

```env
# .env
MAX_FILE_SIZE_MB=100
MAX_TOTAL_STORAGE_GB=10
MAX_CONCURRENT_UPLOADS=5
```

### Enable Caching

```python
# auto_processor.py - add caching
{
  "cache_embeddings": true,
  "cache_ttl_hours": 24,
  "redis_url": "${REDIS_URL}"
}
```

### Background Workers

Create `uploads/worker.py`:

```python
from celery import Celery
from auto_processor import FileProcessor

app = Celery('upload_worker', broker=os.environ['REDIS_URL'])

@app.task
def process_file_async(filepath):
    processor = FileProcessor()
    return processor.process_file(filepath)
```

## 🎉 Success Checklist

- [ ] Dependencies installed on Render
- [ ] Environment variables configured
- [ ] Persistent disk created and mounted
- [ ] MCP servers configured
- [ ] Flow imported successfully
- [ ] Test file uploaded and processed
- [ ] RAG queries working via API
- [ ] Logs showing successful operations
- [ ] Vector store persisting across restarts

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Langflow Docs](https://docs.langflow.org)
- [MCP Protocol](https://modelcontextprotocol.io)

---

**Your folder upload + MCP gateway system is now live on Render! 🚀**
