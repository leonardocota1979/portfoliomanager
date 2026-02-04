#!/bin/bash
# Script para corrigir a instalação do Portfolio Manager v2
# Execute na pasta raiz do projeto: bash fix_installation.sh

echo "=================================="
echo "🔧 Corrigindo instalação do Portfolio Manager v2"
echo "=================================="

# Verifica se está na pasta correta
if [ ! -d "app" ]; then
    echo "❌ ERRO: Execute este script na pasta raiz do projeto (onde está a pasta 'app')"
    exit 1
fi

# Verifica se o ZIP existe
if [ ! -f "portfolio_manager_v2.zip" ]; then
    echo "❌ ERRO: Arquivo portfolio_manager_v2.zip não encontrado"
    echo "   Baixe o arquivo e coloque na pasta do projeto"
    exit 1
fi

# Backup
echo ""
echo "📦 Criando backup..."
BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r app "$BACKUP_DIR/"
cp portfoliomanager.db "$BACKUP_DIR/" 2>/dev/null || true
echo "   Backup salvo em: $BACKUP_DIR"

# Extrai ZIP se não foi extraído
if [ ! -d "portfolio_manager_v2" ]; then
    echo ""
    echo "📂 Extraindo portfolio_manager_v2.zip..."
    unzip -q portfolio_manager_v2.zip -d portfolio_manager_v2
fi

# Cria pasta services se não existir
echo ""
echo "📁 Criando estrutura de pastas..."
mkdir -p app/services

# Cria __init__.py se não existir
touch app/services/__init__.py

# Copia arquivos
echo ""
echo "📋 Copiando arquivos atualizados..."

# Services
cp portfolio_manager_v2/app/services/price_service.py app/services/
echo "   ✅ app/services/price_service.py"

# Routers
cp portfolio_manager_v2/app/routers/dashboard.py app/routers/
echo "   ✅ app/routers/dashboard.py"

cp portfolio_manager_v2/app/routers/portfolios.py app/routers/
echo "   ✅ app/routers/portfolios.py"

cp portfolio_manager_v2/app/routers/assets.py app/routers/
echo "   ✅ app/routers/assets.py"

cp portfolio_manager_v2/app/routers/portfolio_assets.py app/routers/
echo "   ✅ app/routers/portfolio_assets.py"

cp portfolio_manager_v2/app/routers/search.py app/routers/
echo "   ✅ app/routers/search.py"

# Database
cp portfolio_manager_v2/app/database.py app/
echo "   ✅ app/database.py"

# Templates
cp portfolio_manager_v2/app/templates/dashboard.html app/templates/
echo "   ✅ app/templates/dashboard.html"

cp portfolio_manager_v2/app/templates/portfolio_list.html app/templates/
echo "   ✅ app/templates/portfolio_list.html"

# Script de migração
mkdir -p scripts
cp portfolio_manager_v2/scripts/migrate_add_price_columns.py scripts/
echo "   ✅ scripts/migrate_add_price_columns.py"

# Instala httpx se necessário
echo ""
echo "📦 Verificando dependências..."
if python -c "import httpx" 2>/dev/null; then
    echo "   ✅ httpx já instalado"
else
    echo "   📥 Instalando httpx..."
    pip install httpx
fi

# Executa migração
echo ""
echo "🗄️ Executando migração do banco de dados..."
python scripts/migrate_add_price_columns.py

echo ""
echo "=================================="
echo "✅ Instalação concluída!"
echo "=================================="
echo ""
echo "Agora execute:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
