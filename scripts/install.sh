#!/bin/bash
# This script will:
# 1. Install dependencies
# 2. Download documents from the Dropbox

# 1. pip install on requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# 2.
echo "Executing download script..."
chmod +x scripts/download_documents.sh
./scripts/download_documents.sh

echo "Instalação concluída!"