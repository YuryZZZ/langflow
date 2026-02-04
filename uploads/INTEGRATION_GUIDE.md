# 📁 Folder Upload + RAG Integration Guide

## 🎯 What You Built

A **simple drop-and-go file upload system** that:
- ✅ Watches a folder for new files
- ✅ Auto-extracts text (PDF, DOCX, TXT, code, etc.)
- ✅ Chunks and vectorizes content
- ✅ Stores in FAISS vector database
- ✅ Integrates with Langflow for RAG queries

## 🚀 Quick Start (3 Steps)

### Step 1: Start the Watcher

**Windows:**
```bash
uploads/start_watcher.bat
```

**Linux/Mac:**
```bash
chmod +x uploads/start_watcher.sh
./uploads/start_watcher.sh
```

### Step 2: Drop Files

Simply copy files to:
```
uploads/documents/
```

Supported formats:
- 📄 Documents: `.pdf`, `.docx`, `.txt`, `.md`, `.html`
- 💻 Code: `.py`, `.js`, `.ts`, `.json`, `.yaml`
- 📊 Data: `.csv`, `.xlsx`

### Step 3: Query in Langflow

1. Import the flow: `uploads/FOLDER_UPLOAD_WITH_RAG.json`
2. Ask questions about your documents
3. System retrieves relevant chunks automatically

## 📊 How It Works

```
User drops file → Auto Processor → Text Extraction → 
Chunking → Embedding → FAISS Storage → Available for RAG
```

### Processing Pipeline:
1. **File Detection**: Watcher detects new files
2. **Text Extraction**: Parses PDF, DOCX, TXT, code files
3. **Smart Chunking**: Splits into 1000-char chunks with 200-char overlap
4. **Embedding**: Generates vector embeddings (OpenAI or simulation mode)
5. **Storage**: Saves to FAISS index + metadata
6. **Organization**: Moves processed files to `uploads/processed/`

## 🔧 Configuration

Edit `uploads/config.json`:

```json
{
  "chunk_size": 1000,           // Characters per chunk
  "chunk_overlap": 200,         // Overlap between chunks
  "embedding_model": "text-embedding-3-large",
  "watch_folder": true,         // Auto-watch for new files
  "max_file_size_mb": 50,       // Skip files larger than this
  "deduplication": true         // Skip duplicate files
}
```

## 🎨 Langflow Integration

### Method 1: Import the Pre-built Flow

1. Open Langflow UI
2. Import: `uploads/FOLDER_UPLOAD_WITH_RAG.json`
3. Configure the Memory component:
   - Vector Store Path: `uploads/vector_store`
4. Run and start asking questions!

### Method 2: Build Your Own

Add these components to any flow:

```
[ChatInput] → [Memory/Vector Search] → [Prompt + Context] → [LLM] → [ChatOutput]
```

**Memory Component Settings:**
- Query: User's question
- Top K: 5 (number of chunks to retrieve)
- Vector Store Path: `uploads/vector_store`

**Prompt Template:**
```
Context from uploaded documents:
{retrieved_context}

User Question: {user_query}

Answer based on the provided context.
```

## 📁 Folder Structure

```
uploads/
├── documents/          # ⬅️ DROP FILES HERE
├── processed/          # ✅ Successfully processed
├── failed/             # ❌ Failed with error logs
├── vector_store/       # 🧠 FAISS index + metadata
├── auto_processor.py   # 🤖 Main processor script
├── config.json         # ⚙️ Configuration
└── processor.log       # 📝 Processing logs
```

## 🔍 Monitoring & Logs

### Real-time Status
```bash
# Watch processing log
tail -f uploads/processor.log

# Check vector store stats
python -c "import json; data=json.load(open('uploads/vector_store/metadata.json')); print(f\"Files: {len(data['files'])}, Chunks: {data['total_chunks']}\")"
```

### Processing Results
- ✅ **Success**: File moved to `uploads/processed/`
- ❌ **Failed**: File moved to `uploads/failed/` with `.error.txt` log
- ⏭️ **Skipped**: Duplicate file (already processed)

## 🛠️ Advanced Usage

### Programmatic Access

```python
from uploads.auto_processor import FileProcessor

# Initialize
processor = FileProcessor()

# Process specific file
result = processor.process_file("path/to/file.pdf")
print(f"Status: {result['status']}")

# Search vector store
results = processor.search("What is the main topic?", top_k=5)
for r in results:
    print(f"{r['filename']}: {r['score']}")

# Process entire folder
results = processor.process_folder("uploads/documents")
```

### Batch Upload

```bash
# Process all files in a directory
python -c "
from uploads.auto_processor import FileProcessor
p = FileProcessor()
p.process_folder('/path/to/your/files')
"
```

### Custom Embeddings

Set OpenAI API key for real embeddings:
```bash
export OPENAI_API_KEY="sk-..."
```

Or use simulation mode (deterministic pseudo-embeddings for testing).

## 🌐 Render Deployment

To deploy on Render with this feature:

1. **Add to Build Command:**
```bash
pip install -r uploads/requirements.txt
```

2. **Add to Start Command:**
```bash
python uploads/auto_processor.py &
python -m langflow run
```

3. **Persistent Storage:**
   - Mount disk at `/uploads/vector_store`
   - Files survive restarts

## 🎓 Example Workflows

### Research Assistant
```
1. Drop 50 research papers to uploads/documents/
2. Wait for processing (auto-completes)
3. Ask: "What are the main findings about climate change?"
4. System searches all papers and synthesizes answer
```

### Code Documentation
```
1. Drop codebase to uploads/documents/
2. Ask: "How does the authentication system work?"
3. System finds relevant code snippets
4. Explains the auth flow with citations
```

### Legal Document Analysis
```
1. Upload contract PDFs
2. Ask: "What are the termination clauses?"
3. System retrieves relevant sections
4. Summarizes key legal points
```

## 🔒 Security Considerations

- Files are processed locally (no cloud upload)
- Sand text extraction environment
- No execution of uploaded code
- Error logs don't include full file content

## 🐛 Troubleshooting

### Issue: "Module not found"
**Fix:**
```bash
pip install -r uploads/requirements.txt
```

### Issue: "FAISS not installed"
**Fix:** Running in simulation mode (works without FAISS for testing)

### Issue: "Permission denied"
**Fix:**
```bash
chmod +x uploads/start_watcher.sh
```

### Issue: Files not processing
**Check:**
```bash
# Check logs
cat uploads/processor.log

# Verify folder exists
ls -la uploads/documents/

# Test with simple file
echo "Test content" > uploads/documents/test.txt
```

## 📈 Performance Tips

1. **Chunk Size**: Larger chunks = fewer results but more context
2. **Overlap**: Higher overlap = better continuity between chunks
3. **Batch Processing**: Drop multiple files at once for efficiency
4. **SSD Storage**: Vector search faster on SSD vs HDD

## 🎉 Success!

You now have a fully functional **folder-based RAG system**!

**Just remember:**
- Drop files → Auto-process → Ask questions
- No complex setup or configuration needed
- Works locally and on Render deployment

---

**Next Steps:**
- Import `FOLDER_UPLOAD_WITH_RAG.json` into Langflow
- Drop some test files
- Start asking questions!
