#!/usr/bin/env bash
# Instalación del Oráculo Personal.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Dependencias Python"
pip install --quiet pyswisseph 2>/dev/null || pip3 install --quiet pyswisseph

echo "==> Efemérides Swiss Ephemeris"
mkdir -p ephe
BASE="https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"
for f in sepl_18.se1 semo_18.se1 seas_18.se1; do
  if [ -f "ephe/$f" ]; then
    echo "    $f ya presente"
  else
    echo "    descargando $f"
    curl -sSL -o "ephe/$f" "$BASE/$f"
  fi
done

echo "==> Instalando la skill de Claude Code"
# El repositorio ignora .claude/skills/ por convención propia, así que la
# fuente versionada vive en oraculo/skill/ y desde acá se instala.
SKILLDIR="../.claude/skills/oraculo"
mkdir -p "$SKILLDIR"
cp skill/SKILL.md "$SKILLDIR/SKILL.md"
echo "    instalada en .claude/skills/oraculo/"

echo "==> Verificación"
cd engine && python3 - << 'PY'
import natal, numerologia, tradiciones

d = natal.calcular()
off = d["tiempo"]["offset_utc_horas"]
asc = d["angulos"]["Ascendente"]["posicion"]
assert abs(off + 2.0) < 0.01, f"Offset UTC incorrecto: {off} (debe ser -2)"
assert asc.startswith("04°05"), f"Ascendente inesperado: {asc}"
casa12 = len([p for p in d["planetas"].values() if p.get("casa_placidus") == 12])

p = numerologia.perfil()
assert p["camino_de_vida"]["numero"] == 11, "Camino de vida incorrecto"
assert p["camino_de_vida"]["coinciden_ambos_metodos"], "Los dos métodos discrepan"

t = tradiciones.todo()
assert t["bazi"]["anio_bazi"] == 1989, "Año BaZi incorrecto (debe ser 1989)"
assert t["feng_shui"]["numero_kua"] == 2, "Kua incorrecto (debe ser 2)"

print(f"    Ascendente {asc} · offset UTC{off:+.0f} · {casa12} cuerpos en casa 12")
print(f"    Camino de vida {p['camino_de_vida']['numero']} · "
      f"BaZi {t['bazi']['anio_bazi']} · Kua {t['feng_shui']['numero_kua']}")
print("    OK")
PY

echo
echo "Listo. Uso:"
echo "    cd oraculo/engine"
echo "    python3 informe.py --markdown"
