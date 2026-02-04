#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${VENV_DIR:-venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.txt}"
ENV_FILE="${ENV_FILE:-.env}"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
info() { printf "• %s\n" "$*"; }
warn() { printf "\033[33m! %s\033[0m\n" "$*"; }
err()  { printf "\033[31m✗ %s\033[0m\n" "$*"; }
ok()   { printf "\033[32m✓ %s\033[0m\n" "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

version_ge() {
  # version_ge "3.11" "3.10" -> true
  # naive semver compare para major.minor
  local a="$1" b="$2"
  local a1="${a%%.*}" a2="${a#*.}"
  local b1="${b%%.*}" b2="${b#*.}"
  [[ "$a1" -gt "$b1" ]] && return 0
  [[ "$a1" -lt "$b1" ]] && return 1
  [[ "$a2" -ge "$b2" ]]
}

detect_app_import() {
  # tenta descobrir o módulo do app para o uvicorn
  if [[ -f "$PROJECT_ROOT/main.py" ]]; then
    echo "main:app"
    return 0
  fi
  if [[ -f "$PROJECT_ROOT/app/main.py" ]]; then
    echo "app.main:app"
    return 0
  fi
  # fallback: procura "FastAPI(" em arquivos comuns
  local found
  found="$(grep -R --line-number --max-count=1 "FastAPI(" "$PROJECT_ROOT" 2>/dev/null | head -n1 || true)"
  if [[ -n "$found" ]]; then
    warn "Não encontrei main.py em locais padrão. Achei FastAPI() em: $found"
  fi
  echo ""
}

bold "Bootstrap PortifolioManager (macOS)"
info "Diretório: $PROJECT_ROOT"

# 1) Verificar macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
  warn "Este script foi pensado para macOS (Darwin). Continuando mesmo assim."
else
  ok "Sistema: macOS"
fi

# 2) Checar Python
if ! need_cmd "$PYTHON_BIN"; then
  err "Não encontrei '$PYTHON_BIN' no PATH."
  warn "Sugestão: instale Python via Homebrew: brew install python"
  exit 1
fi

PY_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
info "Python detectado: $PYTHON_BIN (v$PY_VER)"
if ! version_ge "$PY_VER" "3.10"; then
  err "Python >= 3.10 é recomendado. Encontrado: $PY_VER"
  warn "Sugestão: brew install python"
  exit 1
else
  ok "Versão de Python OK (>= 3.10)"
fi

# 3) Criar venv se necessário
if [[ -d "$VENV_DIR" ]]; then
  ok "Ambiente virtual já existe: $VENV_DIR/"
else
  info "Criando ambiente virtual em $VENV_DIR/..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  ok "Ambiente virtual criado"
fi

# 4) Ativar venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
ok "Ambiente virtual ativado: $(python -c 'import sys; print(sys.prefix)')"

# 5) Atualizar pip tooling (somente dentro do venv)
info "Atualizando pip/setuptools/wheel (no venv)..."
python -m pip install --upgrade pip setuptools wheel >/dev/null
ok "Ferramentas do pip atualizadas"

# 6) Instalar dependências (se arquivo existir)
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  info "Instalando dependências de $REQUIREMENTS_FILE..."
  python -m pip install -r "$REQUIREMENTS_FILE"
  ok "Dependências instaladas"
else
  warn "Não encontrei $REQUIREMENTS_FILE. Pulando instalação de dependências."
fi

# 7) Verificar .env
if [[ -f "$ENV_FILE" ]]; then
  ok "Arquivo $ENV_FILE encontrado"
else
  warn "Não encontrei $ENV_FILE."
  warn "Se seu app exigir variáveis (SECRET_KEY etc.), crie um .env na raiz."
fi

# 8) Teste rápido de import do app para uvicorn
APP_IMPORT="$(detect_app_import)"
if [[ -z "$APP_IMPORT" ]]; then
  warn "Não consegui detectar automaticamente o módulo do FastAPI app."
  warn "Você pode subir manualmente com: uvicorn <modulo>:app --reload"
else
  ok "App detectado para uvicorn: $APP_IMPORT"
fi

# 9) Opcional: verificação de Xcode CLT (compilações)
if need_cmd xcode-select; then
  if xcode-select -p >/dev/null 2>&1; then
    ok "Xcode Command Line Tools presentes"
  else
    warn "Xcode Command Line Tools não parecem instalados."
    warn "Se pip falhar ao compilar alguma lib (ex.: bcrypt), rode: xcode-select --install"
  fi
fi

bold "Concluído."
if [[ -n "$APP_IMPORT" ]]; then
  echo
  bold "Para subir o servidor:"
  echo "source $VENV_DIR/bin/activate"
  echo "uvicorn $APP_IMPORT --reload"
  echo
  bold "Endpoints:"
  echo "http://127.0.0.1:8000"
  echo "http://127.0.0.1:8000/docs"
fi

