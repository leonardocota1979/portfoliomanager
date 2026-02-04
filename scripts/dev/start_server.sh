#!/bin/bash
echo "🚀 Iniciando Portfolio Manager..."
cd /Users/leonardocota/Projetos/PortifolioManager
source venv/bin/activate
echo "✅ Ambiente virtual ativado"
echo "🌐 Servidor rodando em: http://localhost:8000"
echo "⚠️  Para parar: pressione Ctrl+C"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
