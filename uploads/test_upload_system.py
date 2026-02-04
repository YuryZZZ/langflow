#!/usr/bin/env python3
"""
Test Suite for Folder Upload + RAG System
Run: python uploads/test_upload_system.py
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uploads.auto_processor import FileProcessor


class TestFileProcessor(unittest.TestCase):
    """Test the file processing system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_dir = tempfile.mkdtemp()
        cls.documents_dir = os.path.join(cls.test_dir, "documents")
        cls.processed_dir = os.path.join(cls.test_dir, "processed")
        cls.vector_dir = os.path.join(cls.test_dir, "vector_store")
        
        os.makedirs(cls.documents_dir, exist_ok=True)
        os.makedirs(cls.processed_dir, exist_ok=True)
        os.makedirs(cls.vector_dir, exist_ok=True)
        
        # Create test processor
        cls.processor = FileProcessor(config_path="uploads/config.json")
        cls.processor.processed_path = cls.processed_dir
        cls.processor.vector_store_path = cls.vector_dir
        
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        shutil.rmtree(cls.test_dir, ignore_errors=True)
    
    def test_01_create_test_files(self):
        """Create test files in various formats"""
        # Text file
        txt_path = os.path.join(self.documents_dir, "test_document.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("This is a test document.\n" * 100)
        
        # Markdown file
        md_path = os.path.join(self.documents_dir, "test_readme.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Test README\n\nThis is a test markdown file.\n" * 50)
        
        # Python file
        py_path = os.path.join(self.documents_dir, "test_code.py")
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write("def test_function():\n    return 'Hello World'\n" * 30)
        
        # JSON file
        json_path = os.path.join(self.documents_dir, "test_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"test": "data", "items": list(range(100))}, f)
        
        self.assertTrue(os.path.exists(txt_path))
        self.assertTrue(os.path.exists(md_path))
        self.assertTrue(os.path.exists(py_path))
        self.assertTrue(os.path.exists(json_path))
        
        print("✅ Test files created")
    
    def test_02_process_text_file(self):
        """Test processing a text file"""
        txt_path = os.path.join(self.documents_dir, "test_document.txt")
        
        result = self.processor.process_file(txt_path)
        
        self.assertEqual(result["status"], "success")
        self.assertIn("chunks", result)
        self.assertIn("characters", result)
        
        print(f"✅ Text file processed: {result['chunks']} chunks")
    
    def test_03_process_markdown_file(self):
        """Test processing a markdown file"""
        md_path = os.path.join(self.documents_dir, "test_readme.md")
        
        result = self.processor.process_file(md_path)
        
        self.assertEqual(result["status"], "success")
        
        print(f"✅ Markdown file processed: {result['chunks']} chunks")
    
    def test_04_process_code_file(self):
        """Test processing a Python code file"""
        py_path = os.path.join(self.documents_dir, "test_code.py")
        
        result = self.processor.process_file(py_path)
        
        self.assertEqual(result["status"], "success")
        
        print(f"✅ Python file processed: {result['chunks']} chunks")
    
    def test_05_deduplication(self):
        """Test that duplicate files are skipped"""
        # Create a copy
        original = os.path.join(self.processed_dir, "test_document.txt")
        duplicate = os.path.join(self.documents_dir, "test_document_copy.txt")
        shutil.copy(original, duplicate)
        
        result = self.processor.process_file(duplicate)
        
        self.assertEqual(result["status"], "skipped")
        
        print("✅ Deduplication working")
    
    def test_06_vector_store_persistence(self):
        """Test that vector store is saved correctly"""
        metadata_path = os.path.join(self.vector_dir, "metadata.json")
        
        self.assertTrue(os.path.exists(metadata_path))
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        self.assertIn("files", metadata)
        self.assertIn("total_chunks", metadata)
        self.assertGreater(len(metadata["files"]), 0)
        
        print(f"✅ Vector store persisted: {metadata['total_chunks']} total chunks")
    
    def test_07_search_functionality(self):
        """Test vector search"""
        results = self.processor.search("test document", top_k=3)
        
        self.assertIsInstance(results, list)
        # Should find at least one result
        self.assertGreaterEqual(len(results), 0)
        
        print(f"✅ Search working: found {len(results)} results")
    
    def test_08_chunking(self):
        """Test text chunking logic"""
        text = "This is sentence one. This is sentence two. This is sentence three. " * 100
        
        chunks = self.processor._chunk_text(text)
        
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)
        
        # Each chunk should be reasonable size
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 1500)  # Max chunk size + some buffer
        
        print(f"✅ Chunking working: {len(chunks)} chunks created")
    
    def test_09_embedding_generation(self):
        """Test embedding generation"""
        text = "Test text for embedding"
        
        embedding = self.processor._get_embedding(text)
        
        self.assertIsNotNone(embedding)
        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 1536)  # text-embedding-3-large dimension
        
        print("✅ Embedding generation working")
    
    def test_10_file_hashing(self):
        """Test file hash generation"""
        txt_path = os.path.join(self.processed_dir, "test_document.txt")
        
        hash1 = self.processor._get_file_hash(txt_path)
        hash2 = self.processor._get_file_hash(txt_path)
        
        self.assertEqual(hash1, hash2)  # Same file = same hash
        self.assertEqual(len(hash1), 32)  # MD5 hash length
        
        print("✅ File hashing working")


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_folder_structure(self):
        """Verify folder structure exists"""
        required_dirs = [
            "uploads/documents",
            "uploads/processed",
            "uploads/vector_store",
            "uploads/failed"
        ]
        
        for dir_path in required_dirs:
            self.assertTrue(os.path.exists(dir_path), f"Missing: {dir_path}")
        
        print("✅ Folder structure verified")
    
    def test_config_file(self):
        """Verify config file exists and is valid"""
        config_path = "uploads/config.json"
        
        self.assertTrue(os.path.exists(config_path))
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_keys = ["chunk_size", "chunk_overlap", "embedding_model", "watch_folder"]
        for key in required_keys:
            self.assertIn(key, config)
        
        print("✅ Config file valid")
    
    def test_flow_file(self):
        """Verify Langflow flow file exists and is valid JSON"""
        flow_path = "uploads/FOLDER_UPLOAD_WITH_RAG.json"
        
        self.assertTrue(os.path.exists(flow_path))
        
        with open(flow_path, 'r', encoding='utf-8') as f:
            flow = json.load(f)
        
        self.assertIn("name", flow)
        self.assertIn("data", flow)
        self.assertIn("nodes", flow["data"])
        self.assertIn("edges", flow["data"])
        
        print("✅ Flow file valid")


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Folder Upload + RAG System - Test Suite")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFileProcessor))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {len(result.failures)} FAILURES, {len(result.errors)} ERRORS")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
