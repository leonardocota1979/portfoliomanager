#!/usr/bin/env bash
# ==============================================================================
# devctl.sh (v2.2.2) — FastAPI/Uvicorn Multi-Projetos + Detecção por Porta (SAFE STOP)
# ==============================================================================
#
# Novidades v2.2.2 (segurança e UX):
#   - STOP por RANGE:
#       • sempre faz scan e lista portas ocupadas com PROJETO/CWD/CMD
#       • usuário escolhe explicitamente a porta
#       • valida entrada com até 3 tentativas (ou 'q' para sair)
#       • pede confirmação final antes de derrubar
#   - STOP por PORTA ÚNICA:
#       • valida porta, permite cancelar, evita comportamento inesperado
#
# Mantém v2.2.1:
#   - Correções de pipefail/SIGPIPE para não "morrer" silenciosamente
#   - Detecção PROJETO via PID->CWD
#
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ------------------------------------------------------------------------------
# UI (cores)
# ------------------------------------------------------------------------------
if [[ -t 1 ]]; then
  RESET=$'\033[0m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; UNDER=$'\033[4m'
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
  BLUE=$'\033[34m'; MAG=$'\033[35m'; CYAN=$'\033[36m'; GRAY=$'\033[90m'
else
  RESET=""; BOLD=""; DIM=""; UNDER=""
  RED=""; GREEN=""; YELLOW=""; BLUE=""; MAG=""; CYAN=""; GRAY=""
fi

hr()      { printf "%s\n" "────────────────────────────────────────────────────────────────────────────"; }
hr2()     { printf "%s\n" "════════════════════════════════════════════════════════════════════════════"; }
title()   { printf "\n%s%s%s\n" "${BOLD}${MAG}" "$*" "${RESET}"; }
section() { printf "\n%s%s%s\n" "${BOLD}${CYAN}" "$*" "${RESET}"; }
ok()      { printf "%s✓%s %s\n" "${GREEN}" "${RESET}" "$*"; }
warn()    { printf "%s!%s %s\n" "${YELLOW}" "${RESET}" "$*"; }
fail()    { printf "%s✗%s %s\n" "${RED}" "${RESET}" "$*"; }
info()    { printf "• %s\n" "$*"; }
dim()     { printf "%s%s%s\n" "${DIM}" "$*" "${RESET}"; }

pause() {
  printf "\n%sPressione ENTER para continuar...%s" "${DIM}" "${RESET}" >&2
  read -r _ </dev/tty || true
}

ask_yn() {
  local q="$1"
  printf "%s [s/N]: " "$q" >&2
  local ans
  read -r ans </dev/tty || true
  case "${ans,,}" in
    s|sim|y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

need_cmd() { command -v "$1" >/dev/null 2>&1; }

# ------------------------------------------------------------------------------
# Leitura segura do .env (somente DEVCTL_*)
# ------------------------------------------------------------------------------
load_devctl_env() {
  local env_file=""
  if [[ -f "$PROJECT_ROOT/.env.dev" ]]; then env_file="$PROJECT_ROOT/.env.dev"; fi
  if [[ -z "$env_file" && -f "$PROJECT_ROOT/.env" ]]; then env_file="$PROJECT_ROOT/.env"; fi
  [[ -z "$env_file" ]] && return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    [[ "$line" != *"="* ]] && continue

    local key="${line%%=*}"
    local val="${line#*=}"

    key="${key#"${key%%[![:space:]]*}"}"; key="${key%"${key##*[![:space:]]}"}"
    val="${val#"${val%%[![:space:]]*}"}"; val="${val%"${val##*[![:space:]]}"}"

    [[ "$key" != DEVCTL_* ]] && continue

    if [[ "${val:0:1}" == "\"" && "${val: -1}" == "\"" ]]; then val="${val:1:-1}"; fi
    if [[ "${val:0:1}" == "'"  && "${val: -1}" == "'"  ]]; then val="${val:1:-1}"; fi

    printf -v "$key" "%s" "$val"
    export "$key"
  done < "$env_file"
}

load_devctl_env

# ------------------------------------------------------------------------------
# Defaults
# ------------------------------------------------------------------------------
VENV_DIR="${DEVCTL_VENV_DIR:-${VENV_DIR:-.venv}}"
HOST="${DEVCTL_HOST:-${HOST:-127.0.0.1}}"
PORT_DEFAULT="${DEVCTL_PORT_DEFAULT:-${PORT_DEFAULT:-8000}}"
PORT_RANGE_DEFAULT="${DEVCTL_PORT_RANGE_DEFAULT:-${PORT_RANGE_DEFAULT:-8000-8010}}"
APP_IMPORT="${DEVCTL_APP_IMPORT:-${APP_IMPORT:-}}"
RELOAD="${DEVCTL_RELOAD:-${RELOAD:-1}}"
RELOAD_DIRS="${DEVCTL_RELOAD_DIRS:-${RELOAD_DIRS:-app,templates}}"
LOG_TAIL_LINES="${DEVCTL_LOG_TAIL_LINES:-${LOG_TAIL_LINES:-150}}"

RUN_DIR="${RUN_DIR:-$PROJECT_ROOT/var/.run}"
PID_FILE="$RUN_DIR/uvicorn.pid"
PORT_FILE="$RUN_DIR/uvicorn.port"
LOG_FILE="$RUN_DIR/uvicorn.log"

ensure_run_dir() { mkdir -p "$RUN_DIR"; touch "$LOG_FILE"; }

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
is_pid_running() { kill -0 "$1" >/dev/null 2>&1; }
describe_pid() { ps -p "$1" -o pid=,ppid=,command= 2>/dev/null || true; }
pid_cmdline() { ps -p "$1" -o command= 2>/dev/null || true; }

listeners_on_port() {
  if need_cmd lsof; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
  else
    echo ""
  fi
}

pids_on_port() {
  if need_cmd lsof; then
    lsof -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | sort -u || true
  else
    echo ""
  fi
}

pid_cwd() {
  local pid="$1"
  if ! need_cmd lsof; then echo ""; return 0; fi
  ( lsof -nP -p "$pid" -a -d cwd 2>/dev/null | awk 'NR==2 {print $NF; exit}' ) || true
}

project_from_cwd() {
  local cwd="$1"
  [[ -z "$cwd" ]] && { echo "desconhecido"; return 0; }
  basename "$cwd" 2>/dev/null || echo "$cwd"
}

shorten_path() {
  local p="$1" max="${2:-40}"
  [[ -z "$p" ]] && { echo "-"; return 0; }
  if (( ${#p} <= max )); then echo "$p"; return 0; fi
  echo "${p:0:18}…${p: -18}"
}

shorten_cmd() {
  local c="$1" max="${2:-46}"
  [[ -z "$c" ]] && { echo "-"; return 0; }
  if (( ${#c} <= max )); then echo "$c"; return 0; fi
  echo "${c:0:max}…"
}

# ------------------------------------------------------------------------------
# Stop robusto
# ------------------------------------------------------------------------------
wait_for_pid_exit() {
  local pid="$1" timeout="${2:-8}"
  local i=0
  while is_pid_running "$pid" && [[ $i -lt $timeout ]]; do
    sleep 1
    ((i++))
  done
  ! is_pid_running "$pid"
}

stop_pid_robust() {
  local pid="$1"
  info "Tentando parar PID $pid (SIGINT)…" >&2
  kill -INT "$pid" >/dev/null 2>&1 || true
  if wait_for_pid_exit "$pid" 6; then ok "PID $pid finalizado (SIGINT)." >&2; return 0; fi

  warn "PID $pid não saiu. Tentando SIGTERM…" >&2
  kill -TERM "$pid" >/dev/null 2>&1 || true
  if wait_for_pid_exit "$pid" 6; then ok "PID $pid finalizado (SIGTERM)." >&2; return 0; fi

  warn "PID $pid ainda ativo. Aplicando SIGKILL…" >&2
  kill -KILL "$pid" >/dev/null 2>&1 || true
  if wait_for_pid_exit "$pid" 4; then ok "PID $pid finalizado (SIGKILL)." >&2; return 0; fi

  fail "Não consegui finalizar PID $pid." >&2
  return 1
}

# ------------------------------------------------------------------------------
# Venv + imports
# ------------------------------------------------------------------------------
try_activate_venv() {
  if [[ -d "$VENV_DIR" && -f "$VENV_DIR/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    ok "Venv ativado: $VENV_DIR/" >&2
    return 0
  fi
  if [[ -d ".venv" && -f ".venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    ok "Venv ativado: .venv/" >&2
    VENV_DIR=".venv"
    return 0
  fi
  if [[ -d "venv" && -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
    ok "Venv ativado: venv/" >&2
    VENV_DIR="venv"
    return 0
  fi
  return 1
}

python_import_ok() {
  python - <<PY >/dev/null 2>&1
import importlib
importlib.import_module("$1")
PY
}

detect_app_import() {
  if [[ -n "$APP_IMPORT" ]]; then echo "$APP_IMPORT"; return 0; fi
  if [[ -f "$PROJECT_ROOT/app/main.py" ]]; then echo "app.main:app"; return 0; fi
  if [[ -f "$PROJECT_ROOT/main.py" ]]; then echo "main:app"; return 0; fi
  echo ""
}

# ------------------------------------------------------------------------------
# Port/range parsing + scan
# ------------------------------------------------------------------------------
parse_port_or_range() {
  local s="$1"
  if [[ "$s" =~ ^[0-9]+$ ]]; then echo "single:$s"; return 0; fi
  if [[ "$s" =~ ^([0-9]+)-([0-9]+)$ ]]; then
    local a="${BASH_REMATCH[1]}" b="${BASH_REMATCH[2]}"
    if (( a <= 0 || b <= 0 || a > 65535 || b > 65535 || a > b )); then return 1; fi
    echo "range:$a:$b"
    return 0
  fi
  return 1
}

scan_range() {
  local a="$1" b="$2" p
  for ((p=a; p<=b; p++)); do
    local pids
    pids="$(pids_on_port "$p")"
    if [[ -n "$pids" ]]; then printf "%s|busy|%s\n" "$p" "$pids"; else printf "%s|free|\n" "$p"; fi
  done
}

first_free_in_range() {
  local a="$1" b="$2" p
  for ((p=a; p<=b; p++)); do
    [[ -z "$(pids_on_port "$p")" ]] && { echo "$p"; return 0; }
  done
  echo ""
  return 1
}

choose_port_context() {
  {
    title "Seleção de Porta / Range"
    hr2
    dim "Informe:"
    dim "  • Porta única (ex.: 8001)"
    dim "  • Range (ex.: 8000-8010) — com detecção de projeto por porta"
    hr2
    printf "Digite porta ou range (ENTER para default: %s): " "$PORT_RANGE_DEFAULT"
  } >&2

  local input
  read -r input </dev/tty || true
  input="${input:-$PORT_RANGE_DEFAULT}"

  local parsed
  if ! parsed="$(parse_port_or_range "$input")"; then
    fail "Formato inválido. Use 8001 ou 8000-8010." >&2
    return 1
  fi
  echo "$parsed"
}

validate_environment() {
  title "Diagnóstico do Ambiente" >&2
  hr2 >&2
  section "1) Ferramentas" >&2
  for c in ps tail awk; do need_cmd "$c" && ok "$c OK" >&2 || { fail "$c não encontrado" >&2; return 1; }; done
  need_cmd lsof && ok "lsof OK (scan/rastreio por projeto habilitado)" >&2 || warn "lsof ausente (sem scan)" >&2

  section "2) Python/venv" >&2
  try_activate_venv || warn "Venv não ativado (pode falhar se deps não estiverem globais)." >&2
  ok "Python: $(python --version 2>/dev/null || echo 'desconhecido')" >&2

  section "3) Imports mínimos" >&2
  python_import_ok fastapi && ok "Import OK: fastapi" >&2 || warn "Faltando: fastapi" >&2
  python_import_ok uvicorn && ok "Import OK: uvicorn" >&2 || warn "Faltando: uvicorn" >&2

  section "4) App import" >&2
  local imp
  imp="$(detect_app_import)"
  [[ -n "$imp" ]] && ok "Detectado: $imp" >&2 || { fail "Não detectei app import." >&2; return 1; }

  ok "Diagnóstico concluído." >&2
}

# ------------------------------------------------------------------------------
# STATUS (mantido, sem mudanças relevantes aqui)
# ------------------------------------------------------------------------------
action_status() {
  local parsed="$1"
  title "STATUS" >&2
  hr2 >&2

  if [[ "$parsed" == single:* ]]; then
    local port="${parsed#single:}"
    section "Porta $port" >&2
    local listeners
    listeners="$(listeners_on_port "$port")"
    if [[ -z "$listeners" ]]; then
      ok "Nenhum processo ouvindo em $port." >&2
    else
      warn "Processo(s) ouvindo em $port:" >&2
      echo "$listeners" >&2
      local pids pid cwd proj cmd
      pids="$(pids_on_port "$port")"
      pid="$(printf '%s\n' "$pids" | awk 'NR==1{print; exit}')"
      cwd="$(pid_cwd "$pid")"
      proj="$(project_from_cwd "$cwd")"
      cmd="$(pid_cmdline "$pid")"
      info "Detectado: projeto=${proj}  cwd=$(shorten_path "$cwd" 70)" >&2
      info "CMD: $(shorten_cmd "$cmd" 120)" >&2
    fi
    info "URL: http://$HOST:$port" >&2
    pause
    return 0
  fi

  local a b
  a="$(echo "$parsed" | cut -d: -f2)"
  b="$(echo "$parsed" | cut -d: -f3)"

  section "Scan $a-$b (com detecção de projeto)" >&2
  need_cmd lsof || { fail "Scan + detecção requer lsof." >&2; pause; return 1; }

  printf "%s%-7s %-8s %-20s %-42s %-48s%s\n" \
    "$BOLD" "PORTA" "STATUS" "PROJETO" "CWD" "CMD" "$RESET" >&2
  hr >&2

  while IFS='|' read -r p st pids; do
    if [[ "$st" == "free" ]]; then
      printf "%-7s %s%-8s%s %-20s %-42s %-48s\n" \
        "$p" "$GREEN" "FREE" "$RESET" "-" "-" "-" >&2
    else
      local pid cwd proj cmd scwd scmd
      pid="$(printf '%s\n' "$pids" | awk 'NR==1{print; exit}')"
      cwd="$(pid_cwd "$pid")"
      proj="$(project_from_cwd "$cwd")"
      cmd="$(pid_cmdline "$pid")"
      scwd="$(shorten_path "$cwd" 42)"
      scmd="$(shorten_cmd "$cmd" 48)"
      printf "%-7s %s%-8s%s %-20s %-42s %-48s\n" \
        "$p" "$YELLOW" "BUSY" "$RESET" "$proj" "$scwd" "$scmd" >&2
    fi
  done < <(scan_range "$a" "$b")

  pause
}

# ------------------------------------------------------------------------------
# START (mantido)
# ------------------------------------------------------------------------------
start_uvicorn_background() {
  local port="$1"
  ensure_run_dir

  local imp
  imp="$(detect_app_import)"
  [[ -z "$imp" ]] && { fail "APP_IMPORT não detectado. Use DEVCTL_APP_IMPORT." >&2; return 1; }

  local pids
  pids="$(pids_on_port "$port")"
  if [[ -n "$pids" ]]; then
    warn "Porta $port ocupada (PIDs: $pids)" >&2
    listeners_on_port "$port" >&2 || true
    if ask_yn "Encerrar processos dessa porta e continuar?"; then
      for pid in $pids; do
        info "Encerrando PID $pid — $(describe_pid "$pid")" >&2
        stop_pid_robust "$pid" || true
      done
      [[ -n "$(pids_on_port "$port")" ]] && { fail "Não consegui liberar a porta $port." >&2; return 1; }
      ok "Porta $port liberada." >&2
    else
      fail "Start cancelado." >&2
      return 1
    fi
  fi

  local cmd=("uvicorn" "$imp" "--host" "$HOST" "--port" "$port")
  if [[ "$RELOAD" == "1" ]]; then
    cmd+=("--reload")
    IFS=',' read -r -a dirs <<< "$RELOAD_DIRS"
    for d in "${dirs[@]}"; do
      d="${d#"${d%%[![:space:]]*}"}"; d="${d%"${d##*[![:space:]]}"}"
      [[ -d "$PROJECT_ROOT/$d" ]] && cmd+=("--reload-dir" "$d")
    done
  fi

  section "Iniciando Uvicorn" >&2
  info "Comando: ${cmd[*]}" >&2
  dim  "Log: $LOG_FILE" >&2

  ( "${cmd[@]}" >>"$LOG_FILE" 2>&1 ) &
  local pid=$!

  echo "$pid" > "$PID_FILE"
  echo "$port" > "$PORT_FILE"

  ok "Processo iniciado (PID pai): $pid" >&2
  ok "Porta registrada: $port" >&2
  info "URL:  http://$HOST:$port" >&2
  info "Docs: http://$HOST:$port/docs" >&2

  sleep 1
  [[ -n "$(pids_on_port "$port")" ]] && ok "Porta $port em LISTEN." >&2 || warn "LISTEN não detectado ainda. Verifique log." >&2
}

action_start() {
  title "START" >&2
  hr2 >&2
  validate_environment || { pause; return 1; }

  local parsed
  parsed="$(choose_port_context)" || { pause; return 1; }

  local port=""
  if [[ "$parsed" == single:* ]]; then
    port="${parsed#single:}"
  else
    local a b
    a="$(echo "$parsed" | cut -d: -f2)"
    b="$(echo "$parsed" | cut -d: -f3)"
    need_cmd lsof || { fail "Start por range requer lsof." >&2; pause; return 1; }
    port="$(first_free_in_range "$a" "$b")"
    [[ -z "$port" ]] && { fail "Não há portas livres no range $a-$b." >&2; pause; return 1; }
    ok "Primeira porta livre escolhida: $port" >&2
  fi

  start_uvicorn_background "$port"
  pause
}

# ------------------------------------------------------------------------------
# 🛡️ STOP (REESCRITO: seleção segura + validação 3 tentativas)
# ------------------------------------------------------------------------------
prompt_port_choice_from_list() {
  # Args:
  #   $1 = "range_label" (ex.: "8000-8010")
  #   $2..$n = portas ocupadas (array)
  #
  # Retorno:
  #   imprime em STDOUT a porta escolhida, ou vazio se cancelado
  local range_label="$1"; shift
  local -a ports=("$@")

  local tries=0
  while (( tries < 3 )); do
    printf "\n" >&2
    printf "%sEscolha a porta para parar%s %s(ou 'q' para voltar)%s: " \
      "$BOLD" "$RESET" "$DIM" "$RESET" >&2
    local chosen
    read -r chosen </dev/tty || true
    chosen="${chosen:-}"

    if [[ "${chosen,,}" == "q" ]]; then
      echo ""
      return 0
    fi

    if [[ ! "$chosen" =~ ^[0-9]+$ ]]; then
      warn "Entrada inválida. Digite uma porta numérica (ex.: 8009) ou 'q'." >&2
      ((tries++))
      continue
    fi

    local found="0"
    local p
    for p in "${ports[@]}"; do
      if [[ "$p" == "$chosen" ]]; then found="1"; break; fi
    done

    if [[ "$found" == "1" ]]; then
      echo "$chosen"
      return 0
    fi

    warn "A porta $chosen não está na lista de ocupadas do range $range_label." >&2
    ((tries++))
  done

  warn "Muitas tentativas inválidas. Voltando ao menu." >&2
  echo ""
  return 0
}

print_busy_table_for_range() {
  local a="$1" b="$2"
  printf "%s%-7s %-8s %-20s %-42s %-48s%s\n" \
    "$BOLD" "PORTA" "STATUS" "PROJETO" "CWD" "CMD" "$RESET" >&2
  hr >&2
  while IFS='|' read -r p st pids; do
    if [[ "$st" == "busy" ]]; then
      local pid cwd proj cmd scwd scmd
      pid="$(printf '%s\n' "$pids" | awk 'NR==1{print; exit}')"
      cwd="$(pid_cwd "$pid")"
      proj="$(project_from_cwd "$cwd")"
      cmd="$(pid_cmdline "$pid")"
      scwd="$(shorten_path "$cwd" 42)"
      scmd="$(shorten_cmd "$cmd" 48)"
      printf "%-7s %s%-8s%s %-20s %-42s %-48s\n" \
        "$p" "$YELLOW" "BUSY" "$RESET" "$proj" "$scwd" "$scmd" >&2
    fi
  done < <(scan_range "$a" "$b")
}

action_stop() {
  title "STOP" >&2
  hr2 >&2
  ensure_run_dir

  # 1) Preferência: parar PID registrado do projeto atual (mais seguro)
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && is_pid_running "$pid"; then
      section "Encerrando processo registrado do projeto atual (seguro)" >&2
      info "PID: $pid" >&2
      info "Processo: $(describe_pid "$pid")" >&2
      ask_yn "Confirmar STOP do projeto atual?" || { warn "Cancelado." >&2; pause; return 0; }
      stop_pid_robust "$pid" || true
      rm -f "$PID_FILE" "$PORT_FILE" || true
      ok "Stop concluído (via PID do projeto atual)." >&2
      pause
      return 0
    fi
    # PID file órfão
    rm -f "$PID_FILE" "$PORT_FILE" >/dev/null 2>&1 || true
  fi

  # 2) Fallback: por porta/range (multi-projetos) — agora SEM auto-derrubar
  warn "Sem PID do projeto atual. Operação por porta/range (multi-projetos)." >&2
  warn "Aqui o script NUNCA derruba automaticamente: sempre lista e pede escolha + confirmação." >&2

  local parsed
  parsed="$(choose_port_context)" || { pause; return 1; }

  # ---- STOP por porta única
  if [[ "$parsed" == single:* ]]; then
    local port="${parsed#single:}"
    local pids
    pids="$(pids_on_port "$port")"
    if [[ -z "$pids" ]]; then
      ok "Nada ouvindo em $port." >&2
      pause
      return 0
    fi

    section "Processos em $port" >&2
    listeners_on_port "$port" >&2

    local pid cwd proj cmd
    pid="$(printf '%s\n' "$pids" | awk 'NR==1{print; exit}')"
    cwd="$(pid_cwd "$pid")"; proj="$(project_from_cwd "$cwd")"; cmd="$(pid_cmdline "$pid")"
    info "Detectado: projeto=${proj}  cwd=$(shorten_path "$cwd" 70)" >&2
    info "CMD: $(shorten_cmd "$cmd" 120)" >&2

    ask_yn "Confirmar STOP dos processos na porta $port?" || { warn "Cancelado." >&2; pause; return 0; }

    for pid in $pids; do
      info "Encerrando PID $pid — $(describe_pid "$pid")" >&2
      stop_pid_robust "$pid" || true
    done

    pause
    return 0
  fi

  # ---- STOP por range
  local a b
  a="$(echo "$parsed" | cut -d: -f2)"
  b="$(echo "$parsed" | cut -d: -f3)"
  local range_label="${a}-${b}"

  need_cmd lsof || { fail "Stop por range requer lsof." >&2; pause; return 1; }

  section "Portas ocupadas em $range_label" >&2

  # montar lista de portas ocupadas
  local -a busy_ports=()
  while IFS='|' read -r p st pids; do
    [[ "$st" == "busy" ]] && busy_ports+=("$p")
  done < <(scan_range "$a" "$b")

  if [[ ${#busy_ports[@]} -eq 0 ]]; then
    ok "Nenhuma porta ocupada no range." >&2
    pause
    return 0
  fi

  # imprimir tabela bonita para usuário escolher
  print_busy_table_for_range "$a" "$b"

  # perguntar porta com validação
  local chosen
  chosen="$(prompt_port_choice_from_list "$range_label" "${busy_ports[@]}")"
  if [[ -z "$chosen" ]]; then
    warn "Stop cancelado/retornado ao menu." >&2
    pause
    return 0
  fi

  # confirmar com detalhes do processo
  section "Confirmação" >&2
  local pids pid cwd proj cmd
  pids="$(pids_on_port "$chosen")"
  pid="$(printf '%s\n' "$pids" | awk 'NR==1{print; exit}')"
  cwd="$(pid_cwd "$pid")"; proj="$(project_from_cwd "$cwd")"; cmd="$(pid_cmdline "$pid")"

  info "Você escolheu parar a porta: $chosen" >&2
  info "Projeto detectado: $proj" >&2
  info "CWD: $(shorten_path "$cwd" 90)" >&2
  info "CMD: $(shorten_cmd "$cmd" 140)" >&2
  listeners_on_port "$chosen" >&2 || true

  ask_yn "Confirmar STOP dos processos na porta $chosen?" || { warn "Cancelado." >&2; pause; return 0; }

  for pid in $pids; do
    info "Encerrando PID $pid — $(describe_pid "$pid")" >&2
    stop_pid_robust "$pid" || true
  done

  ok "Stop concluído na porta $chosen." >&2
  pause
}

# ------------------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------------------
stream_logs_all() { tail -n "$LOG_TAIL_LINES" -f "$LOG_FILE" | awk '{ print; fflush(); }'; }
stream_logs_errors() {
  tail -n "$LOG_TAIL_LINES" -f "$LOG_FILE" | awk 'BEGIN{IGNORECASE=1} /error|traceback|exception|critical|failed|stack trace/ {print; fflush()}'
}

ensure_running_or_prompt_start() {
  local port=""
  [[ -f "$PORT_FILE" ]] && port="$(cat "$PORT_FILE" 2>/dev/null || true)"
  [[ -n "$port" && -n "$(pids_on_port "$port")" ]] && return 0
  warn "Não detectei este projeto rodando (ou porta desconhecida)." >&2
  ask_yn "Deseja iniciar agora?" || return 1
  action_start
}

action_logs() {
  title "LOGS (Tempo Real)" >&2
  hr2 >&2
  ensure_run_dir
  ensure_running_or_prompt_start || { fail "Cancelado." >&2; pause; return 1; }

  section "Logs gerais" >&2
  info "Arquivo: $LOG_FILE" >&2
  info "Para voltar: pressione Q" >&2
  hr >&2

  stream_logs_all &
  local tail_pid=$!

  while true; do
    IFS= read -rsn1 key </dev/tty || true
    [[ "${key,,}" == "q" ]] && break
  done

  kill -TERM "$tail_pid" >/dev/null 2>&1 || true
  wait "$tail_pid" 2>/dev/null || true
  ok "Voltando ao menu." >&2
}

action_errors() {
  title "ERROS (Tempo Real)" >&2
  hr2 >&2
  ensure_run_dir
  ensure_running_or_prompt_start || { fail "Cancelado." >&2; pause; return 1; }

  section "Somente erros" >&2
  info "Arquivo: $LOG_FILE" >&2
  info "Para voltar: pressione Q" >&2
  hr >&2

  stream_logs_errors &
  local tail_pid=$!

  while true; do
    IFS= read -rsn1 key </dev/tty || true
    [[ "${key,,}" == "q" ]] && break
  done

  kill -TERM "$tail_pid" >/dev/null 2>&1 || true
  wait "$tail_pid" 2>/dev/null || true
  ok "Voltando ao menu." >&2
}

# ------------------------------------------------------------------------------
# Admin helper
# ------------------------------------------------------------------------------
action_create_admin() {
  title "CRIAR/PROMOVER ADMIN" >&2
  hr2 >&2
  try_activate_venv || warn "Venv não ativado (pode falhar se deps não estiverem globais)." >&2

  local username password email make_admin_only
  printf "Username (obrigatório): " >&2
  read -r username </dev/tty || true
  if [[ -z "$username" ]]; then
    warn "Username vazio. Cancelado." >&2
    pause
    return 1
  fi

  printf "Email (opcional): " >&2
  read -r email </dev/tty || true

  printf "Somente promover (sem alterar senha)? [s/N]: " >&2
  local ans
  read -r ans </dev/tty || true
  case "${ans,,}" in
    s|sim|y|yes) make_admin_only="1" ;;
    *) make_admin_only="0" ;;
  esac

  if [[ "$make_admin_only" == "1" ]]; then
    python scripts/create_admin.py --username "$username" --make-admin-only
    pause
    return 0
  fi

  printf "Senha (obrigatório): " >&2
  read -r password </dev/tty || true
  if [[ -z "$password" ]]; then
    warn "Senha vazia. Cancelado." >&2
    pause
    return 1
  fi

  if [[ -n "$email" ]]; then
    python scripts/create_admin.py --username "$username" --password "$password" --email "$email"
  else
    python scripts/create_admin.py --username "$username" --password "$password"
  fi

  pause
}

# ------------------------------------------------------------------------------
# Menu
# ------------------------------------------------------------------------------
print_header() {
  clear || true
  printf "%s%s%s\n" "${BOLD}${MAG}" "devctl.sh v2.2.2  •  FastAPI/Uvicorn  •  Multi-Projetos (STOP seguro)" "${RESET}"
  hr2
  dim "Projeto atual: $PROJECT_ROOT"
  dim "Venv: $VENV_DIR/   Host: $HOST   Range: $PORT_RANGE_DEFAULT"
  dim "Reload: $RELOAD   Reload dirs: $RELOAD_DIRS"
  hr2

  local port=""
  [[ -f "$PORT_FILE" ]] && port="$(cat "$PORT_FILE" 2>/dev/null || true)"
  if [[ -n "$port" && -n "$(pids_on_port "$port")" ]]; then
    ok "Status do projeto atual: ATIVO (porta $port)"
    dim "URL: http://$HOST:$port"
  else
    warn "Status do projeto atual: INATIVO (ou porta desconhecida)"
  fi
  hr
}

main_loop() {
  ensure_run_dir
  while true; do
    print_header
    printf "%s\n" "${BOLD}Escolha uma opção:${RESET}"
    printf "  1) Diagnóstico\n"
    printf "  2) Status (porta ou range) + detecção de projeto por porta\n"
    printf "  3) Start (porta ou range)\n"
    printf "  4) Stop  (PID do projeto; fallback seguro por porta/range)\n"
    printf "  5) Logs (ao vivo)\n"
    printf "  6) Somente erros (ao vivo)\n"
    printf "  7) Criar/Promover Admin\n"
    printf "  8) Sair\n"
    hr
    printf "Digite 1-8 e ENTER: "
    local choice
    read -r choice </dev/tty || true

    case "${choice:-}" in
      1) validate_environment; pause ;;
      2)
        local ctx
        ctx="$(choose_port_context)" || { pause; continue; }
        action_status "$ctx"
        ;;
      3) action_start ;;
      4) action_stop ;;
      5) action_logs ;;
      6) action_errors ;;
      7) action_create_admin ;;
      8) title "Saindo" >&2; hr2 >&2; ok "Até mais." >&2; exit 0 ;;
      *) warn "Opção inválida. Use 1 a 8." >&2; sleep 1 ;;
    esac
  done
}

main_loop

# ==============================================================================
# FIM DO ARQUIVO (COMPLETO)
# ==============================================================================
# TERMINO_OK__DEVCTL_SH_V2_2_2
