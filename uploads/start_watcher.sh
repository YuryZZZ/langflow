#!/bin/bash

echo "==========================================="
echo "  📁 Folder Upload Watcher - Quick Start"
echo "==========================================="
echo ""
echo "This will start watching the uploads/documents/ folder"
echo "and automatically process any files you drop there."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

echo "✅ Python found"
echo ""

# Check if dependencies are installed
if [ ! -f "uploads/deps_installed.txt" ]; then
    echo "📦 Installing dependencies..."
    pip3 install -r uploads/requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    touch uploads/deps_installed.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "📂 Folder structure:"
echo "   uploads/documents/   - Drop files here"
echo "   uploads/processed/   - Processed files move here"
echo "   uploads/vector_store/ - Vector database stored here"
echo ""

# Create directories if they don't exist
mkdir -p uploads/documents uploads/processed uploads/vector_store uploads/failed

echo "🚀 Starting folder watcher..."
echo "   (Press Ctrl+C to stop)"
echo ""
echo "💡 TIP: Open uploads/documents/ in Finder/File Manager"
echo "    and drag files there to auto-process!"
echo ""

python3 uploads/auto_processor.py
