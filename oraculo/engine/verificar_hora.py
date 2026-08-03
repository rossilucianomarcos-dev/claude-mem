#!/usr/bin/env python3
"""
Auditoría de la hora de nacimiento — Oráculo Personal.

La hora es el dato del que más depende una carta natal. Un error de una hora
mueve el Ascendente ~15°, puede cambiar el signo del Medio Cielo y reubicar
planetas en otras casas.

Este script existe para que la corrección aplicada sea VERIFICABLE en
cualquier momento, en lugar de ser una afirmación que hay que creer. Muestra:

  1. Las transiciones reales de huso horario según la base IANA.
  2. La carta con el offset correcto (UTC−2) y con el incorrecto (UTC−3).
  3. Exactamente qué cambia entre ambas.

Uso:
    python3 verificar_hora.py
"""

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

from natal import SUJETO, fmt, gl

TZ = ZoneInfo(SUJETO["tz_iana"])
LAT, LON = SUJETO["lat"], SUJETO["lon"]
_EPHE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ephe"))
swe.set_ephe_path(_EPHE if os.path.isdir(_EPHE) else None)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

PLANETAS = [("Sol", swe.SUN), ("Luna", swe.MOON), ("Mercurio", swe.MERCURY),
            ("Venus", swe.VENUS), ("Marte", swe.MARS), ("Júpiter", swe.JUPITER),
            ("Saturno", swe.SATURN), ("Urano", swe.URANUS),
            ("Neptuno", swe.NEPTUNE), ("Plutón", swe.PLUTO)]


def transiciones_iana():
    """Encuentra los saltos de offset alrededor del nacimiento, según tzdata."""
    d = datetime(1988, 1, 1, tzinfo=timezone.utc)
    fin = datetime(1992, 1, 1, tzinfo=timezone.utc)
    prev = d.astimezone(TZ).utcoffset()
    saltos = []
    while d < fin:
        d += timedelta(hours=1)
        off = d.astimezone(TZ).utcoffset()
        if off != prev:
            saltos.append((d, prev, off))
            prev = off
    return saltos


def carta(hora_utc_decimal):
    jd = swe.julday(1990, 1, 9, hora_utc_decimal, swe.GREG_CAL)
    cusps, ascmc = swe.houses(jd, LAT, LON, b"P")
    cs = list(cusps[:12])

    def casa_de(l):
        for i in range(12):
            a, b = cs[i], cs[(i + 1) % 12]
            if a <= b:
                if a <= l < b:
                    return i + 1
            elif l >= a or l < b:
                return i + 1

    pos = {}
    for n, c in PLANETAS:
        v, _ = swe.calc_ut(jd, c, FLAGS)
        pos[n] = v[0] % 360
    return {"asc": ascmc[0], "mc": ascmc[1], "pos": pos,
            "casas": {n: casa_de(l) for n, l in pos.items()}}


def main():
    nac = datetime.fromisoformat(f"{SUJETO['fecha_local']}T{SUJETO['hora_local']}").replace(tzinfo=TZ)
    off = nac.utcoffset().total_seconds() / 3600
    dst = nac.dst().total_seconds() / 3600

    print("=" * 74)
    print("AUDITORÍA DE LA HORA DE NACIMIENTO")
    print("=" * 74)
    print(f"Declarada     : {SUJETO['fecha_local']} {SUJETO['hora_local']} (hora de reloj)")
    print(f"Lugar         : {SUJETO['ciudad']}, {SUJETO['pais']}  ({LAT}, {LON})")
    print(f"Zona IANA     : {SUJETO['tz_iana']}")
    print(f"Offset UTC    : {off:+.0f}    Horario de verano activo: {dst != 0}")
    print(f"Instante UTC  : {nac.astimezone(timezone.utc).isoformat()}")

    print("\n" + "-" * 74)
    print("1. TRANSICIONES DE HUSO SEGÚN LA BASE IANA (fuente autoritativa)")
    print("-" * 74)
    for cuando, antes, despues in transiciones_iana():
        a = antes.total_seconds() / 3600
        d = despues.total_seconds() / 3600
        marca = "  <<< el nacimiento cae DESPUÉS de este salto" if cuando <= nac.astimezone(timezone.utc) \
            and cuando > datetime(1989, 6, 1, tzinfo=timezone.utc) \
            and cuando < datetime(1990, 2, 1, tzinfo=timezone.utc) else ""
        print(f"   {cuando.strftime('%Y-%m-%d %H:%M UTC')}   UTC{a:+.0f} -> UTC{d:+.0f}{marca}")

    print("\n" + "-" * 74)
    print("2. COMPARACIÓN DE CARTAS")
    print("-" * 74)
    ok = carta(10.4)     # 08:24 local con UTC-2
    mal = carta(11.4)    # 08:24 local con UTC-3 (erróneo)

    print(f"   {'':<22}{'UTC−2 (correcto)':<26}{'UTC−3 (incorrecto)'}")
    print(f"   {'Ascendente':<22}{fmt(ok['asc']):<26}{fmt(mal['asc'])}")
    print(f"   {'Medio Cielo':<22}{fmt(ok['mc']):<26}{fmt(mal['mc'])}")

    d_asc = abs(((mal["asc"] - ok["asc"] + 180) % 360) - 180)
    d_mc = abs(((mal["mc"] - ok["mc"] + 180) % 360) - 180)
    print(f"\n   Desplazamiento del Ascendente : {int(d_asc)}°{int((d_asc%1)*60):02d}'"
          f"   (signo: {gl(ok['asc'])[0]} -> {gl(mal['asc'])[0]})")
    print(f"   Desplazamiento del Medio Cielo: {int(d_mc)}°{int((d_mc%1)*60):02d}'"
          f"   (signo: {gl(ok['mc'])[0]} -> {gl(mal['mc'])[0]})")
    if gl(ok["mc"])[0] != gl(mal["mc"])[0]:
        print("   *** El MC CAMBIA DE SIGNO: cambia el regente de la casa 10. ***")

    sep_ok = abs(((ok["pos"]["Venus"] - ok["asc"] + 180) % 360) - 180)
    sep_mal = abs(((mal["pos"]["Venus"] - mal["asc"] + 180) % 360) - 180)
    print(f"\n   Venus respecto del Ascendente:")
    print(f"      UTC−2 : {sep_ok*60:6.1f}' de arco  -> conjunción exacta")
    print(f"      UTC−3 : {sep_mal*60:6.1f}' de arco  -> sin conjunción")

    print(f"\n   Casas por planeta:")
    cambios = 0
    for n, _ in PLANETAS:
        a, b = ok["casas"][n], mal["casas"][n]
        marca = "  <<< CAMBIA" if a != b else ""
        cambios += a != b
        print(f"      {n:<12} {a:>2}  ->  {b:>2}{marca}")
    print(f"\n   {cambios} de {len(PLANETAS)} planetas cambian de casa.")

    print("\n" + "=" * 74)
    if abs(off + 2.0) < 0.01:
        print("RESULTADO: se está usando UTC−2. CORRECTO.")
    else:
        print(f"RESULTADO: se está usando UTC{off:+.0f}. *** REVISAR ***")
    print("=" * 74)


if __name__ == "__main__":
    main()
