# 📁 Folder Upload + RAG - Quick Start

## 🚀 Fastest Way to Get Started

### Option 1: Local Development (2 minutes)

```bash
# 1. Start the watcher
python uploads/start_watcher.py

# 2. Drop files to: uploads/documents/
cp your-file.pdf uploads/documents/

# 3. Ask questions in Langflow!
```

### Option 2: Render Deployment (5 minutes)

```bash
# 1. Add to Render Build Command:
pip install -r uploads/requirements.txt

# 2. Add to Start Command:
python uploads/start_render_watcher.py &
python -m langflow run

# 3. Import flow in Langflow UI
# Upload: FOLDER_UPLOAD_MCP_GATEWAY.json

# 4. Drop files via SSH:
render ssh your-service
echo "test" > uploads/documents/test.txt
```

## 📂 File Structure

```
uploads/
├── 📄 documents/          ← DROP FILES HERE
├── ✅ processed/          Processed files
├── ❌ failed/             Failed with logs
├── 🧠 vector_store/       FAISS database
├── auto_processor.py      Main processor
├── FOLDER_UPLOAD_MCP_GATEWAY.json  MCP flow
├── start_render_watcher.py Render startup
└── INTEGRATION_GUIDE.md   Full docs
```

## 🎯 Common Commands

```bash
# Start watching
python uploads/start_watcher.py

# Process existing files
python -c "from uploads.auto_processor import FileProcessor; p = FileProcessor(); p.process_folder()"

# Search documents
python -c "from uploads.auto_processor import FileProcessor; p = FileProcessor(); print(p.search('your query'))"

# View logs
tail -f uploads/processor.log

# Run tests
python uploads/test_upload_system.py
```

## 🔌 MCP Gateway Integration

The system integrates with Langflow's MCP Gateway:

- **filesystem** MCP: Watches uploads/documents/ folder
- **memory** MCP: Searches vector store for RAG
- **Compatible** with Render deployment
- **Auto-detects** new files via MCP events

## ✅ Supported File Types

| Type | Extensions |
|------|------------|
| Documents | .pdf, .docx, .txt, .md, .html |
| Code | .py, .js, .ts, .json, .yaml |
| Data | .csv, .xlsx, .xml |

## 🎨 Langflow Flow Components

```
[ChatInput] → [MCP File Watcher] → [Document Analyzer] → [Vector Store]
                                                  ↓
[ChatOutput] ← [Response Generator] ← [Context Builder] ← [MCP Search]
```

## 📊 Status Check

```python
# Check processing status
import json
with open('uploads/vector_store/metadata.json') as f:
    data = json.load(f)
    print(f"Files: {len(data['files'])}")
    print(f"Total chunks: {data['total_chunks']}")
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Files not processing | Check `uploads/processor.log` |
| Import error | `pip install -r uploads/requirements.txt` |
| Vector store empty | Run processor manually |
| Render not working | Check environment variables |

## 🎉 Success Indicators

- ✅ Files appear in `uploads/processed/`
- ✅ `uploads/vector_store/index.faiss` exists
- ✅ Logs show "Successfully processed"
- ✅ Langflow can search documents

---

**Just drop files and go!** 🚀
