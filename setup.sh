#!/bin/bash
echo "[SETUP] Removendo pacotes obsoletos..."
pip uninstall -y pinecone-plugin-inference pinecone || echo "Pacotes não encontrados, continuando..."

echo "[SETUP] Instalando dependências..."
pip install --no-cache-dir -r requirements.txt

echo "[SETUP] Baixando documentos..."
chmod +x scripts/download_documents.sh
./scripts/download_documents.sh || echo "⚠️ Falha ao baixar documentos, seguindo sem eles..."

echo "[SETUP] Pronto!"
