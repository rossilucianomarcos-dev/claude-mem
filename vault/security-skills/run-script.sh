#!/usr/bin/env bash
# Ejecuta el script de una skill resolviendo sus dependencias con uv, sin
# instalar nada en el sistema ni dejar un venv en el repo.
#
#   ./run-script.sh <skill> <script.py> [args...]
#   ./run-script.sh securing-github-actions-workflows process.py --help
#
# Las dependencias se declaran por skill en deps.txt. Una skill sin entrada
# usa solo la biblioteca estándar.
set -euo pipefail

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPS_FILE="$VAULT/deps.txt"

usage() { sed -n '2,8p' "${BASH_SOURCE[0]}"; exit "${1:-0}"; }
[ $# -ge 2 ] || usage 2
case "${1:-}" in -h|--help) usage 0 ;; esac

skill="$1"; script="$2"; shift 2
path="$VAULT/skills/$skill/scripts/$script"

if [ ! -f "$path" ]; then
  echo "No existe: $path" >&2
  if [ -d "$VAULT/skills/$skill/scripts" ]; then
    echo "Scripts disponibles en $skill:" >&2
    ls "$VAULT/skills/$skill/scripts" >&2
  else
    echo "Skills con scripts:" >&2
    ls "$VAULT/skills" >&2
  fi
  exit 1
fi

command -v uv >/dev/null || {
  echo "uv no está instalado. claude-mem ya lo requiere; instalalo con:" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
}

# Dependencias declaradas para esta skill (línea "skill: dep dep dep").
deps=""
if [ -f "$DEPS_FILE" ]; then
  deps="$(awk -F: -v s="$skill" '/^[^#]/ && $1==s {sub(/^[^:]*:[[:space:]]*/,""); sub(/[[:space:]]*#.*$/,""); print; exit}' "$DEPS_FILE")"
fi

withargs=()
for d in $deps; do withargs+=(--with "$d"); done

if [ ${#withargs[@]} -gt 0 ]; then
  echo "· resolviendo deps: $deps" >&2
fi
exec uv run --quiet --python 3.11 "${withargs[@]}" "$path" "$@"
