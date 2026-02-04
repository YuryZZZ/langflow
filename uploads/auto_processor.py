#!/usr/bin/env python3
"""
Auto File Processor with RAG + Vector Storage
Simply drop files to uploads/documents/ folder - system handles the rest
"""

import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uploads/processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileProcessor:
    """Processes files and stores in vector database"""
    
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.pdf', '.docx', '.html', '.htm',
        '.py', '.js', '.ts', '.json', '.yaml', '.yml',
        '.csv', '.xlsx', '.xml', '.rst'
    }
    
    def __init__(self, config_path: str = "uploads/config.json"):
        self.config = self._load_config(config_path)
        self.vector_store_path = "uploads/vector_store"
        self.processed_path = "uploads/processed"
        self.failed_path = "uploads/failed"
        self.metadata_path = "uploads/metadata"
        
        # Create directories
        for path in [self.vector_store_path, self.processed_path, 
                     self.failed_path, self.metadata_path]:
            os.makedirs(path, exist_ok=True)
        
        # Initialize vector store
        self._init_vector_store()
        
    def _load_config(self, path: str) -> dict:
        """Load configuration"""
        default_config = {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "embedding_model": "text-embedding-3-large",
            "vector_store": "faiss",
            "auto_process": True,
            "watch_folder": True,
            "supported_extensions": list(self.SUPPORTED_EXTENSIONS)
        }
        
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return {**default_config, **json.load(f)}
        
        # Save default config
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def _init_vector_store(self):
        """Initialize FAISS vector store"""
        try:
            import faiss
            import numpy as np
            
            index_path = os.path.join(self.vector_store_path, "index.faiss")
            metadata_path = os.path.join(self.vector_store_path, "metadata.json")
            
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded existing index with {self.index.ntotal} vectors")
            else:
                # Create new index (1536 dimensions for text-embedding-3-large)
                self.index = faiss.IndexFlatIP(1536)
                self.metadata = {"files": {}, "total_chunks": 0}
                logger.info("Created new FAISS index")
                
        except ImportError:
            logger.warning("FAISS not installed. Running in simulation mode.")
            self.index = None
            self.metadata = {"files": {}, "total_chunks": 0}
    
    def _save_vector_store(self):
        """Save vector store to disk"""
        if self.index is not None:
            import faiss
            index_path = os.path.join(self.vector_store_path, "index.faiss")
            metadata_path = os.path.join(self.vector_store_path, "metadata.json")
            
            faiss.write_index(self.index, index_path)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
    
    def _get_file_hash(self, filepath: str) -> str:
        """Calculate file hash for deduplication"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _extract_text(self, filepath: str) -> str:
        """Extract text from various file types"""
        ext = Path(filepath).suffix.lower()
        
        try:
            if ext in ['.txt', '.md', '.py', '.js', '.ts', '.json', 
                       '.yaml', '.yml', '.xml', '.rst', '.html', '.htm']:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            elif ext == '.pdf':
                try:
                    import PyPDF2
                    with open(filepath, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        return "\n".join(page.extract_text() or "" 
                                       for page in reader.pages)
                except ImportError:
                    logger.warning("PyPDF2 not installed, cannot process PDF")
                    return ""
            
            elif ext == '.docx':
                try:
                    import docx
                    doc = docx.Document(filepath)
                    return "\n".join(paragraph.text for paragraph in doc.paragraphs)
                except ImportError:
                    logger.warning("python-docx not installed, cannot process DOCX")
                    return ""
            
            elif ext == '.csv':
                import csv
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    return "\n".join(", ".join(row) for row in reader)
            
            else:
                logger.warning(f"Unsupported file type: {ext}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {e}")
            return ""
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        chunk_size = self.config.get("chunk_size", 1000)
        overlap = self.config.get("chunk_overlap", 200)
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence or paragraph
            if end < len(text):
                # Look for sentence endings
                for break_char in ['. ', '! ', '? ', '\n\n', '\n']:
                    pos = chunk.rfind(break_char)
                    if pos > chunk_size * 0.5:  # Only break if past halfway
                        end = start + pos + len(break_char)
                        chunk = text[start:end]
                        break
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text (simulation mode if no API key)"""
        try:
            # Try to use OpenAI API if available
            import openai
            from dotenv import load_dotenv
            load_dotenv()
            
            client = openai.OpenAI()
            response = client.embeddings.create(
                input=text[:8000],  # Limit input size
                model=self.config.get("embedding_model", "text-embedding-3-large")
            )
            return response.data[0].embedding
            
        except Exception as e:
            # Simulation mode: create deterministic pseudo-embedding
            logger.debug(f"Using simulation mode for embedding: {e}")
            import random
            random.seed(hash(text) % (2**32))
            return [random.random() for _ in range(1536)]
    
    def process_file(self, filepath: str) -> Dict:
        """Process a single file"""
        filename = os.path.basename(filepath)
        file_hash = self._get_file_hash(filepath)
        
        # Check if already processed
        if file_hash in self.metadata.get("files", {}):
            logger.info(f"File already processed: {filename}")
            return {"status": "skipped", "reason": "already_processed"}
        
        logger.info(f"Processing: {filename}")
        
        try:
            # Extract text
            text = self._extract_text(filepath)
            if not text.strip():
                return {"status": "failed", "reason": "no_text_extracted"}
            
            # Chunk text
            chunks = self._chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks from {filename}")
            
            # Get embeddings and add to index
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                embedding = self._get_embedding(chunk)
                if embedding:
                    if self.index is not None:
                        import numpy as np
                        self.index.add(np.array([embedding], dtype=np.float32))
                    
                    chunk_metadata.append({
                        "chunk_id": i,
                        "text_preview": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                        "char_count": len(chunk)
                    })
            
            # Update metadata
            self.metadata["files"][file_hash] = {
                "filename": filename,
                "filepath": filepath,
                "processed_at": datetime.now().isoformat(),
                "chunks": len(chunks),
                "char_count": len(text),
                "chunk_metadata": chunk_metadata
            }
            self.metadata["total_chunks"] = self.index.ntotal if self.index else len(chunk_metadata)
            
            # Save vector store
            self._save_vector_store()
            
            # Move to processed folder
            dest_path = os.path.join(self.processed_path, filename)
            shutil.move(filepath, dest_path)
            
            logger.info(f"✅ Successfully processed: {filename} ({len(chunks)} chunks)")
            
            return {
                "status": "success",
                "filename": filename,
                "chunks": len(chunks),
                "characters": len(text)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process {filename}: {e}")
            
            # Move to failed folder
            dest_path = os.path.join(self.failed_path, filename)
            shutil.move(filepath, dest_path)
            
            # Save error log
            error_log = os.path.join(self.failed_path, f"{filename}.error.txt")
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"Error processing {filename}:\n{str(e)}\n")
            
            return {"status": "failed", "reason": str(e)}
    
    def process_folder(self, folder_path: str = "uploads/documents"):
        """Process all files in folder"""
        if not os.path.exists(folder_path):
            logger.warning(f"Folder not found: {folder_path}")
            return []
        
        results = []
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                ext = Path(filename).suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    result = self.process_file(filepath)
                    results.append(result)
                else:
                    logger.warning(f"Skipping unsupported file: {filename}")
        
        return results
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search vector store for relevant chunks"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        import numpy as np
        D, I = self.index.search(
            np.array([query_embedding], dtype=np.float32), 
            min(top_k, self.index.ntotal)
        )
        
        results = []
        for idx, distance in zip(I[0], D[0]):
            # Find which file this chunk belongs to
            for file_hash, file_info in self.metadata["files"].items():
                # Simple approximation - in production, store chunk-to-file mapping
                results.append({
                    "score": float(distance),
                    "filename": file_info["filename"],
                    "chunks": file_info.get("chunks", 0)
                })
        
        return results


class FolderWatcher(FileSystemEventHandler):
    """Watches folder for new files and auto-processes them"""
    
    def __init__(self, processor: FileProcessor):
        self.processor = processor
        self.processing = False
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        filepath = event.src_path
        filename = os.path.basename(filepath)
        ext = Path(filename).suffix.lower()
        
        if ext in self.processor.SUPPORTED_EXTENSIONS:
            logger.info(f"📝 New file detected: {filename}")
            self.processor.process_file(filepath)
        else:
            logger.warning(f"⚠️ Unsupported file type: {filename}")


def main():
    """Main entry point"""
    print("=" * 60)
    print("📁 Auto File Processor with RAG + Vector Storage")
    print("=" * 60)
    print("\nDrop files to uploads/documents/ folder")
    print("System will automatically process and vectorize them\n")
    
    # Initialize processor
    processor = FileProcessor()
    
    # Process existing files
    print("🔍 Checking for existing files...")
    results = processor.process_folder()
    
    if results:
        success_count = sum(1 for r in results if r.get("status") == "success")
        print(f"✅ Processed {success_count}/{len(results)} existing files")
    else:
        print("📂 No existing files to process")
    
    # Start folder watcher
    if processor.config.get("watch_folder", True):
        print("\n👁️  Starting folder watcher...")
        print("(Press Ctrl+C to stop)\n")
        
        event_handler = FolderWatcher(processor)
        observer = Observer()
        observer.schedule(event_handler, "uploads/documents", recursive=False)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping folder watcher...")
            observer.stop()
        
        observer.join()
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
