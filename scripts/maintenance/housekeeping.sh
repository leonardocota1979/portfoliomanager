#!/usr/bin/env bash
# ==============================================================================
# housekeeping.sh (PortifolioManager)
# ------------------------------------------------------------------------------
# Limpeza segura de artefatos temporários/lixo do projeto.
#
# Princípios de segurança:
# - Modo padrão é DRY-RUN (não remove nada).
# - Remoção real apenas com --apply.
# - Não toca em banco de dados (`data/`), código-fonte ou documentação.
#
# Uso:
#   ./scripts/maintenance/housekeeping.sh
#   ./scripts/maintenance/housekeeping.sh --apply
#   ./scripts/maintenance/housekeeping.sh --apply --with-run-logs
#   ./scripts/maintenance/housekeeping.sh --apply --with-app-logs
#   ./scripts/maintenance/housekeeping.sh --apply --with-upload-cache --older-than-days 7
#
# Opções:
#   --apply              Executa remoção real (sem isso, é simulação).
#   --with-run-logs      Inclui `var/.run/*.log`.
#   --with-app-logs      Inclui `var/logs/*.log` e `var/logs/ocr/*.txt`.
#   --with-upload-cache  Inclui arquivos em `var/logs/uploads/`.
#   --older-than-days N  Restringe limpeza opcional para itens antigos (default: 0 = todos).
#   -h, --help           Exibe ajuda.
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APPLY=0
WITH_RUN_LOGS=0
WITH_APP_LOGS=0
WITH_UPLOAD_CACHE=0
OLDER_THAN_DAYS=0
DELETED=0

print_help() {
  sed -n '1,40p' "$0" | sed 's/^# \{0,1\}//'
}

log_info() {
  printf "[housekeeping] %s\n" "$*"
}

abort() {
  printf "[housekeeping] ERRO: %s\n" "$*" >&2
  exit 1
}

ensure_project_root() {
  [[ -d "$PROJECT_ROOT/app" ]] || abort "diretório app/ não encontrado em $PROJECT_ROOT"
  [[ -f "$PROJECT_ROOT/README.md" ]] || abort "README.md não encontrado em $PROJECT_ROOT"
}

delete_path() {
  local path="$1"
  if [[ $APPLY -ne 1 ]]; then
    log_info "DRY-RUN: removeria $path"
    return 0
  fi

  if [[ -d "$path" ]]; then
    rm -rf -- "$path"
    DELETED=$((DELETED + 1))
    log_info "removido diretório: $path"
    return 0
  fi

  rm -f -- "$path"
  DELETED=$((DELETED + 1))
  log_info "removido arquivo: $path"
}

collect_and_delete() {
  local label="$1"
  shift
  local paths=("$@")
  if [[ ${#paths[@]} -eq 0 ]]; then
    log_info "$label: nenhum item encontrado"
    return 0
  fi
  log_info "$label: ${#paths[@]} item(ns)"
  local path
  for path in "${paths[@]}"; do
    delete_path "$path"
  done
}

collect_optional_by_age() {
  local label="$1"
  local base_dir="$2"
  local pattern="$3"
  local -a items=()

  if [[ ! -d "$base_dir" ]]; then
    log_info "$label: diretório ausente ($base_dir)"
    return 0
  fi

  if [[ "$OLDER_THAN_DAYS" -gt 0 ]]; then
    while IFS= read -r file; do
      [[ -n "$file" ]] && items+=("$file")
    done < <(find "$base_dir" -type f -name "$pattern" -mtime +"$OLDER_THAN_DAYS" 2>/dev/null | sort)
  else
    while IFS= read -r file; do
      [[ -n "$file" ]] && items+=("$file")
    done < <(find "$base_dir" -type f -name "$pattern" 2>/dev/null | sort)
  fi

  collect_and_delete "$label" "${items[@]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --with-run-logs)
      WITH_RUN_LOGS=1
      shift
      ;;
    --with-app-logs)
      WITH_APP_LOGS=1
      shift
      ;;
    --with-upload-cache)
      WITH_UPLOAD_CACHE=1
      shift
      ;;
    --older-than-days)
      [[ $# -ge 2 ]] || abort "informe valor após --older-than-days"
      OLDER_THAN_DAYS="$2"
      [[ "$OLDER_THAN_DAYS" =~ ^[0-9]+$ ]] || abort "valor inválido para --older-than-days: $OLDER_THAN_DAYS"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      abort "opção inválida: $1"
      ;;
  esac
done

ensure_project_root

log_info "projeto: $PROJECT_ROOT"
if [[ $APPLY -eq 1 ]]; then
  log_info "modo: APPLY (remoção real habilitada)"
else
  log_info "modo: DRY-RUN (nenhum arquivo será removido)"
fi

# 1) Cache Python apenas no código do projeto (não toca venv).
mapfile -t pycache_dirs < <(
  find "$PROJECT_ROOT/app" "$PROJECT_ROOT/scripts" "$PROJECT_ROOT/tests" \
    -type d -name "__pycache__" 2>/dev/null | sort
)
collect_and_delete "cache python (__pycache__)" "${pycache_dirs[@]}"

mapfile -t pyc_files < <(
  find "$PROJECT_ROOT/app" "$PROJECT_ROOT/scripts" "$PROJECT_ROOT/tests" \
    -type f \( -name "*.pyc" -o -name "*.pyo" \) 2>/dev/null | sort
)
collect_and_delete "bytecode python (*.pyc/*.pyo)" "${pyc_files[@]}"

# 2) Artefatos comuns de tooling/cobertura.
tooling_items=()
[[ -d "$PROJECT_ROOT/.pytest_cache" ]] && tooling_items+=("$PROJECT_ROOT/.pytest_cache")
[[ -d "$PROJECT_ROOT/.mypy_cache" ]] && tooling_items+=("$PROJECT_ROOT/.mypy_cache")
[[ -d "$PROJECT_ROOT/.ruff_cache" ]] && tooling_items+=("$PROJECT_ROOT/.ruff_cache")
[[ -d "$PROJECT_ROOT/htmlcov" ]] && tooling_items+=("$PROJECT_ROOT/htmlcov")
[[ -f "$PROJECT_ROOT/.coverage" ]] && tooling_items+=("$PROJECT_ROOT/.coverage")
collect_and_delete "tooling/cobertura" "${tooling_items[@]}"

# 3) Runtime local (sempre seguro).
runtime_items=()
for pattern in "$PROJECT_ROOT"/var/.run/*.pid "$PROJECT_ROOT"/var/.run/*.port "$PROJECT_ROOT"/var/.run/*.sock; do
  [[ -e "$pattern" ]] && runtime_items+=("$pattern")
done
collect_and_delete "runtime local (var/.run pid/port/sock)" "${runtime_items[@]}"

# 4) Logs opcionais (podem ser úteis para diagnóstico).
if [[ $WITH_RUN_LOGS -eq 1 ]]; then
  collect_optional_by_age "logs runtime (var/.run/*.log)" "$PROJECT_ROOT/var/.run" "*.log"
else
  log_info "logs runtime (var/.run/*.log): ignorado (use --with-run-logs)"
fi

if [[ $WITH_APP_LOGS -eq 1 ]]; then
  collect_optional_by_age "logs aplicação (var/logs/*.log)" "$PROJECT_ROOT/var/logs" "*.log"
  collect_optional_by_age "cache OCR textual (var/logs/ocr/*.txt)" "$PROJECT_ROOT/var/logs/ocr" "*.txt"
else
  log_info "logs aplicação/OCR: ignorado (use --with-app-logs)"
fi

if [[ $WITH_UPLOAD_CACHE -eq 1 ]]; then
  collect_optional_by_age "uploads temporários (var/logs/uploads/*)" "$PROJECT_ROOT/var/logs/uploads" "*"
else
  log_info "uploads temporários: ignorado (use --with-upload-cache)"
fi

# 5) Lixo de sistema/editor (exclui .git e venv).
misc_items=()
while IFS= read -r file; do
  [[ -n "$file" ]] && misc_items+=("$file")
done < <(
  find "$PROJECT_ROOT" \
    \( -path "$PROJECT_ROOT/.git" -o -path "$PROJECT_ROOT/venv" -o -path "$PROJECT_ROOT/.venv" \) -prune \
    -o -type f \( -name ".DS_Store" -o -name "*.swp" -o -name "*~" \) -print
)
collect_and_delete "lixo de sistema/editor" "${misc_items[@]}"

if [[ $APPLY -eq 1 ]]; then
  log_info "limpeza concluída. itens removidos: $DELETED"
else
  log_info "dry-run concluído. use --apply para executar."
fi
