#!/usr/bin/env python3
"""
Render Deployment Watcher - Folder Upload + MCP Gateway
Auto-starts on Render and watches for file uploads
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# Setup logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/uploads/processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_mcp_gateway():
    """Check if MCP Gateway is available"""
    try:
        # Try to import MCP client
        from mcp import ClientSession, StdioServerParameters
        logger.info("✅ MCP Gateway libraries available")
        return True
    except ImportError:
        logger.warning("⚠️  MCP libraries not installed, running in standalone mode")
        return False

def start_file_processor():
    """Start the file processor with MCP integration"""
    logger.info("=" * 60)
    logger.info("🚀 Render File Processor Starting")
    logger.info("=" * 60)
    
    # Check environment
    upload_dir = os.environ.get('UPLOAD_FOLDER', '/uploads/documents')
    vector_dir = os.environ.get('VECTOR_STORE_PATH', '/uploads/vector_store')
    
    logger.info(f"📁 Upload directory: {upload_dir}")
    logger.info(f"🧠 Vector store: {vector_dir}")
    
    # Ensure directories exist
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(vector_dir, exist_ok=True)
    os.makedirs('/uploads/processed', exist_ok=True)
    os.makedirs('/uploads/failed', exist_ok=True)
    
    # Check MCP Gateway
    mcp_enabled = check_mcp_gateway()
    
    if mcp_enabled:
        logger.info("🔌 MCP Gateway: ENABLED")
        # Import MCP-enabled processor
        try:
            from uploads.auto_processor_mcp import FileProcessorMCP
            processor = FileProcessorMCP()
            logger.info("✅ MCP-enabled processor initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP processor: {e}")
            logger.info("⚠️  Falling back to standalone processor")
            from uploads.auto_processor import FileProcessor
            processor = FileProcessor()
    else:
        logger.info("🔌 MCP Gateway: DISABLED (standalone mode)")
        from uploads.auto_processor import FileProcessor
        processor = FileProcessor()
    
    # Process existing files
    logger.info("🔍 Checking for existing files...")
    results = processor.process_folder(upload_dir)
    
    if results:
        success_count = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"✅ Processed {success_count}/{len(results)} existing files")
    
    # Start watching (if watchdog available)
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class RenderFolderHandler(FileSystemEventHandler):
            def __init__(self, processor):
                self.processor = processor
            
            def on_created(self, event):
                if not event.is_directory:
                    time.sleep(1)  # Wait for file to be fully written
                    filepath = event.src_path
                    filename = os.path.basename(filepath)
                    ext = Path(filename).suffix.lower()
                    
                    if ext in self.processor.SUPPORTED_EXTENSIONS:
                        logger.info(f"📝 New file detected: {filename}")
                        result = self.processor.process_file(filepath)
                        logger.info(f"📊 Processing result: {result['status']}")
        
        logger.info("👁️  Starting folder watcher...")
        event_handler = RenderFolderHandler(processor)
        observer = Observer()
        observer.schedule(event_handler, upload_dir, recursive=False)
        observer.start()
        
        logger.info("✅ Watcher started. Monitoring for file uploads...")
        logger.info("💡 Drop files to /uploads/documents/ to auto-process")
        
        # Keep running
        while True:
            time.sleep(60)  # Log heartbeat every minute
            logger.debug("💓 Watcher heartbeat")
            
    except ImportError:
        logger.warning("⚠️  Watchdog not installed, running one-time processing")
        logger.info("💡 Install watchdog for continuous monitoring: pip install watchdog")
    
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down file processor...")
        if 'observer' in locals():
            observer.stop()
            observer.join()
    
    except Exception as e:
        logger.error(f"❌ Error in file processor: {e}", exc_info=True)
        raise

def create_health_endpoint():
    """Create health check endpoint for Render"""
    health_file = '/uploads/health.json'
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "file_processor",
        "version": "2.0.0"
    }
    with open(health_file, 'w') as f:
        json.dump(health_data, f)

if __name__ == "__main__":
    try:
        # Create health endpoint
        create_health_endpoint()
        
        # Start processor
        start_file_processor()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
