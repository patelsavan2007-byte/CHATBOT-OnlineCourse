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

echo "=== Rebuilding vector database from knowledge_base/ ==="
python rebuild_vectordb.py

echo "=== Build complete ==="
