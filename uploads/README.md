# 📁 Simple File Upload System with Auto-RAG

## 🎯 How It Works

**For Users: Just Drop Files!**
1. Copy any files to `uploads/documents/` folder
2. System automatically processes them
3. Files are vectorized and stored
4. Available for RAG queries immediately

## 📂 Folder Structure

```
uploads/
├── documents/          # Drop files here
├── processed/          # System moves files here after processing
├── vector_store/       # FAISS vector database (auto-created)
└── metadata/           # File metadata and embeddings
```

## ✅ Supported File Types

- **Documents**: `.pdf`, `.docx`, `.txt`, `.md`, `.html`
- **Code Files**: `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`
- **Data Files**: `.csv`, `.xlsx`, `.json`
- **Images** (OCR): `.png`, `.jpg`, `.jpeg`

## 🚀 Quick Start

### Method 1: Simple Copy
```bash
# Just copy files to the documents folder
cp my-document.pdf uploads/documents/
cp *.txt uploads/documents/
```

### Method 2: Drag & Drop
1. Open `uploads/documents/` in file explorer
2. Drag files from anywhere
3. Done! Auto-processing starts

### Method 3: API Upload
```bash
curl -X POST "https://langflow-7vd3.onrender.com/api/v1/upload" \
  -F "files=@document.pdf" \
  -F "files=@data.csv"
```

## ⚙️ Auto-Processing Pipeline

```
[File Drop] → [Detect] → [Extract Text] → [Chunk] → [Embed] → [Store]
     │            │            │            │          │         │
     ▼            ▼            ▼            ▼          ▼         ▼
  Watch    File Type    Parse Content   Split into   Vector    FAISS
  Folder   Detection    (OCR/Parser)    Chunks      Embed    Index
```

## 📊 Processing Status

Check processing status in real-time:
- `uploads/status.json` - Current queue and progress
- `uploads/processed/` - Successfully processed files
- `uploads/failed/` - Files that failed (with error logs)

## 🔍 Using RAG in Flows

Once files are processed, use them in any Langflow flow:

### Component: Knowledge Retrieval
```
[Query] → [Vector Search] → [Retrieve Chunks] → [LLM with Context]
```

### Example Prompt Template:
```
Context from uploaded documents:
{retrieved_context}

User Question: {user_query}

Answer based on the provided context.
```

## 🛠️ Configuration

Edit `uploads/config.json` to customize:

```json
{
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "embedding_model": "text-embedding-3-large",
  "vector_store": "faiss",
  "auto_process": true,
  "watch_folder": true,
  "supported_extensions": [".pdf", ".txt", ".docx"]
}
```

## 📈 Monitoring

- **Files Processed**: Check `uploads/stats.json`
- **Vector Count**: FAISS index size
- **Last Update**: Timestamp in status file

## 🔒 Security

- Files are scanned before processing
- Sandboxed extraction environment
- No external API calls without permission

---

**Just drop files and go!** The system handles everything automatically.
