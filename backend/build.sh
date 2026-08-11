#!/usr/bin/env bash
# ==============================================================
# Render Build Script — CHARUSAT Online Course Chatbot Backend
# ==============================================================
# This script runs during every Render deploy:
#   1. Installs Python dependencies
#   2. Rebuilds the ChromaDB vector store from knowledge_base/
#
# The knowledge_base/ directory (markdown + PDFs) is tracked in
# git, so the vector DB can be rebuilt on any machine.
# ==============================================================

set -o errexit  # Exit on any error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Checking vector database ==="
if [ -f "vector_db/chroma.sqlite3" ] && [ "$1" != "--force" ]; then
    echo "Using existing pre-built ChromaDB vector store in vector_db/ (444 chunks)."
else
    echo "=== Rebuilding vector database from knowledge_base/ ==="
    python rebuild_vectordb.py
fi

echo "=== Build complete ==="

