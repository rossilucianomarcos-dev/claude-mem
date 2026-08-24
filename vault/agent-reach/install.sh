#!/usr/bin/env bash
# Instala la skill Agent Reach del vault en un directorio de skills de Claude
# Code, y opcionalmente el CLI `agent-reach` que la skill invoca.
#
#   ./install.sh              -> .claude/skills/ del repo (solo este proyecto)
#   ./install.sh --global     -> ~/.claude/skills/      (todos los proyectos)
#   ./install.sh --to <dir>   -> destino explícito
#   ./install.sh --cli        -> además instala/actualiza el CLI agent-reach
#   ./install.sh --cli-only   -> solo el CLI, sin tocar los directorios de skills
#
# La skill sola sirve como router (sabe qué comando corre para cada plataforma),
# pero sin el CLI no hay `agent-reach doctor` ni instalación de canales.
set -euo pipefail

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$VAULT/skills"
REPO_ROOT="$(cd "$VAULT/../.." && pwd)"
DEST="$REPO_ROOT/.claude/skills"
UPSTREAM="https://github.com/Panniantong/agent-reach/archive/main.zip"

install_cli=0
install_skill=1

while [ $# -gt 0 ]; do
  case "$1" in
    --global) DEST="$HOME/.claude/skills"; shift ;;
    --to) DEST="${2:?--to necesita un directorio}"; shift 2 ;;
    --cli) install_cli=1; shift ;;
    --cli-only) install_cli=1; install_skill=0; shift ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
done

if [ "$install_cli" = 1 ]; then
  if command -v agent-reach >/dev/null 2>&1; then
    echo "CLI ya presente: $(agent-reach --version)"
  elif command -v pipx >/dev/null 2>&1; then
    pipx install "$UPSTREAM"
  elif command -v uv >/dev/null 2>&1; then
    uv tool install --from "$UPSTREAM" agent-reach
  else
    # PEP 668 (Homebrew/Debian) rompe `pip install --user`; usamos un venv.
    python3 -m venv "$HOME/.agent-reach-venv"
    "$HOME/.agent-reach-venv/bin/pip" install --quiet "$UPSTREAM"
    echo "Instalado en ~/.agent-reach-venv — agregá ~/.agent-reach-venv/bin al PATH."
  fi
  echo "Chequeo de canales (solo lectura, no toca el sistema):"
  echo "  agent-reach install --env=auto"
  echo "Para instalar dependencias del sistema hace falta aprobación explícita:"
  echo "  agent-reach install --env=auto --system"
fi

if [ "$install_skill" = 1 ]; then
  mkdir -p "$DEST"
  count=0
  for skill in "$SRC"/*/; do
    name="$(basename "$skill")"
    [ -f "$skill/SKILL.md" ] || { echo "  omitida (sin SKILL.md): $name" >&2; continue; }
    rm -rf "${DEST:?}/$name"
    cp -R "$skill" "$DEST/$name"
    count=$((count + 1))
  done
  echo "$count skill instalada en $DEST"
  echo "Reiniciá la sesión de Claude Code (o /reload) para que la detecte."
fi
