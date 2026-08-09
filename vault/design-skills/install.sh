#!/usr/bin/env bash
# Instala las skills de diseño y animación del vault en un directorio de skills
# de Claude Code.
#
#   ./install.sh              -> .claude/skills/ del repo (solo este proyecto)
#   ./install.sh --global     -> ~/.claude/skills/      (todos los proyectos)
#   ./install.sh --to <dir>   -> destino explícito
#
# Se copia, no se enlaza: genjutsu resuelve sus sub-skills con `find` sin
# seguir symlinks, así que un enlace en el nivel superior rompe la carga de
# `_jutsu/`.
set -euo pipefail

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$VAULT/skills"
REPO_ROOT="$(cd "$VAULT/../.." && pwd)"
DEST="$REPO_ROOT/.claude/skills"

while [ $# -gt 0 ]; do
  case "$1" in
    --global) DEST="$HOME/.claude/skills"; shift ;;
    --to) DEST="${2:?--to necesita un directorio}"; shift 2 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$DEST"

count=0
for skill in "$SRC"/*/; do
  name="$(basename "$skill")"
  [ -f "$skill/SKILL.md" ] || { echo "  omitida (sin SKILL.md): $name" >&2; continue; }
  rm -rf "${DEST:?}/$name"
  cp -R "$skill" "$DEST/$name"
  count=$((count + 1))
done

echo "$count skills instaladas en $DEST"
echo "Reiniciá la sesión de Claude Code (o /reload) para que las detecte."
