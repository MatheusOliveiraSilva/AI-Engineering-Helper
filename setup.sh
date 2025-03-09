#!/bin/bash
echo "[SETUP] Instalando dependências..."
pip install -r requirements.txt

pip uninstall -y pinecone-plugin-inference || echo "Pacote não encontrado, continuando..."

echo "[SETUP] Baixando documentos..."
chmod +x scripts/download_documents.sh
./scripts/download_documents.sh || echo "Falha ao baixar documentos, seguindo sem eles..."

echo "[SETUP] Pronto!"
