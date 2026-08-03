#!/usr/bin/env python3
"""
Motor de tránsitos, progresiones y ciclos — Oráculo Personal.

Separa estrictamente dos capas:
  * CAPA ASTRONÓMICA (verificable): posiciones reales, fases lunares,
    ingresos, estaciones retrógradas, eclipses.
  * CAPA SIMBÓLICA: la relación de esas posiciones con la carta natal.
    El módulo produce los ÁNGULOS; la interpretación no vive aquí.

Uso:
    python3 transitos.py                      # para hoy
    python3 transitos.py --fecha 2026-08-03
    python3 transitos.py --fecha 2026-08-03 --ciclos   # incluye ciclos de vida
"""

import argparse
import json
import math
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

from natal import (ASPECTOS, CUERPOS, ELEMENTO, MODALIDAD, SIGNOS, SUJETO,
                   calcular as calcular_natal, fmt, gl, sep_angular)

TZ_LOCAL = ZoneInfo("America/Argentina/Cordoba")

_EPHE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ephe"))
swe.set_ephe_path(_EPHE if os.path.isdir(_EPHE) else None)
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

# Orbes de tránsito: más estrechos que los natales. Un tránsito solo
# "cuenta" cerca de la exactitud.
ORBES_TRANSITO = {
    "Conjunción": 3.0, "Oposición": 3.0, "Cuadratura": 3.0,
    "Trígono": 3.0, "Sextil": 2.0, "Quincuncio": 1.5,
}
# Planetas lentos: sus tránsitos duran meses/años y pesan más.
LENTOS = {"Júpiter", "Saturno", "Urano", "Neptuno", "Plutón", "Quirón"}
RAPIDOS = {"Sol", "Luna", "Mercurio", "Venus", "Marte"}

PERIODOS_SIDEREOS = {  # años trópicos aproximados de retorno
    "Júpiter": 11.862, "Saturno": 29.457, "Urano": 84.02,
    "Neptuno": 164.79, "Plutón": 247.94, "Quirón": 50.42,
    "Nodo Norte (verdadero)": 18.613,
}


def jd_de(dt_utc):
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
                      swe.GREG_CAL)


def posiciones_en(jd):
    """Posiciones eclípticas de los cuerpos principales en un Julian Day."""
    res = {}
    for nombre, cuerpo, trad in CUERPOS:
        if nombre == "Nodo Norte (medio)":
            continue
        try:
            v, _ = swe.calc_ut(jd, cuerpo, FLAGS)
        except swe.Error:
            continue
        lon = v[0] % 360
        res[nombre] = {
            "longitud": round(lon, 6), "posicion": fmt(lon), "signo": gl(lon)[0],
            "velocidad_dia": round(v[3], 6), "retrogrado": v[3] < 0,
            "elemento": ELEMENTO[gl(lon)[0]], "modalidad": MODALIDAD[gl(lon)[0]],
        }
    return res


def fase_lunar(jd):
    sol, _ = swe.calc_ut(jd, swe.SUN, FLAGS)
    luna, _ = swe.calc_ut(jd, swe.MOON, FLAGS)
    ang = (luna[0] - sol[0]) % 360
    ilum = 50 * (1 - math.cos(math.radians(ang)))
    nombres = [(0, 45, "Luna Nueva"), (45, 90, "Creciente iluminante"),
               (90, 135, "Cuarto Creciente"), (135, 180, "Gibosa creciente"),
               (180, 225, "Luna Llena"), (225, 270, "Gibosa menguante / diseminante"),
               (270, 315, "Cuarto Menguante"), (315, 360, "Balsámica")]
    nombre = next(n for a, b, n in nombres if a <= ang < b)
    # Edad de la lunación
    edad_dias = ang / 360 * 29.530588
    return {"angulo_sol_luna": round(ang, 3), "fase": nombre,
            "iluminacion_pct": round(ilum, 1),
            "edad_lunacion_dias": round(edad_dias, 2),
            "signo_luna": gl(luna[0])[0], "posicion_luna": fmt(luna[0]),
            "signo_sol": gl(sol[0])[0], "posicion_sol": fmt(sol[0])}


def proximas_lunaciones(jd, n=4):
    """Próximas lunas nuevas y llenas (búsqueda por bisección)."""
    def ang(j):
        s, _ = swe.calc_ut(j, swe.SUN, FLAGS)
        l, _ = swe.calc_ut(j, swe.MOON, FLAGS)
        return (l[0] - s[0]) % 360

    eventos = []
    j = jd
    for _ in range(n * 2):
        a0 = ang(j)
        objetivo = 180.0 if a0 < 180 else 360.0
        etiqueta = "Luna Llena" if objetivo == 180.0 else "Luna Nueva"
        lo, hi = j, j + 32
        for _ in range(60):
            mid = (lo + hi) / 2
            am = ang(mid)
            if objetivo == 360.0:
                cruzo = am < a0 or am >= objetivo
            else:
                cruzo = am >= objetivo
            if cruzo:
                hi = mid
            else:
                lo = mid
        jr = (lo + hi) / 2
        y, mo, d, h = swe.revjul(jr, swe.GREG_CAL)
        dt = datetime(y, mo, d, tzinfo=timezone.utc) + timedelta(hours=h)
        s, _ = swe.calc_ut(jr, swe.SUN, FLAGS)
        eventos.append({"evento": etiqueta, "utc": dt.isoformat(),
                        "local": dt.astimezone(TZ_LOCAL).isoformat(),
                        "grado": fmt(s[0] if etiqueta == "Luna Nueva" else (s[0] + 180) % 360)})
        j = jr + 1.0
        if len(eventos) >= n:
            break
    return eventos


def retrogradaciones(jd, dias=180):
    """Estaciones (cambios de dirección) en los próximos N días."""
    cuerpos = [("Mercurio", swe.MERCURY), ("Venus", swe.VENUS), ("Marte", swe.MARS),
               ("Júpiter", swe.JUPITER), ("Saturno", swe.SATURN), ("Urano", swe.URANUS),
               ("Neptuno", swe.NEPTUNE), ("Plutón", swe.PLUTO)]
    eventos = []
    for nombre, c in cuerpos:
        prev = None
        for k in range(dias):
            v, _ = swe.calc_ut(jd + k, c, FLAGS)
            sig = v[3] < 0
            if prev is not None and sig != prev:
                lo, hi = jd + k - 1, jd + k
                for _ in range(40):
                    mid = (lo + hi) / 2
                    vm, _ = swe.calc_ut(mid, c, FLAGS)
                    if (vm[3] < 0) == prev:
                        lo = mid
                    else:
                        hi = mid
                jr = (lo + hi) / 2
                y, mo, d, h = swe.revjul(jr, swe.GREG_CAL)
                dt = datetime(y, mo, d, tzinfo=timezone.utc) + timedelta(hours=h)
                vr, _ = swe.calc_ut(jr, c, FLAGS)
                eventos.append({"planeta": nombre,
                                "evento": "Estación retrógrada" if sig else "Estación directa",
                                "utc": dt.isoformat(),
                                "local": dt.astimezone(TZ_LOCAL).isoformat(),
                                "grado": fmt(vr[0])})
            prev = sig
    eventos.sort(key=lambda e: e["utc"])
    return eventos


def transitos_a_natal(jd, natal):
    """Aspectos de los planetas actuales a los puntos natales."""
    actuales = posiciones_en(jd)
    puntos_natales = {k: v["longitud"] for k, v in natal["planetas"].items()
                      if "medio" not in k}
    puntos_natales["Ascendente"] = natal["angulos"]["Ascendente"]["longitud"]
    puntos_natales["Medio Cielo (MC)"] = natal["angulos"]["Medio Cielo (MC)"]["longitud"]
    puntos_natales["Parte de la Fortuna"] = natal["lotes_helenisticos"]["Parte de la Fortuna"]["longitud"]

    hits = []
    for tn, tp in actuales.items():
        for nn, nl in puntos_natales.items():
            sep = sep_angular(tp["longitud"], nl)
            for asp, orbe_max in ORBES_TRANSITO.items():
                ang = ASPECTOS[asp][0]
                desv = abs(sep - ang)
                if desv > orbe_max:
                    continue
                # La Luna en tránsito se mueve 13°/día: solo se registra
                # con orbe muy estrecho, si no satura el informe.
                if tn == "Luna" and desv > 1.5:
                    continue
                peso = ("estructural" if tn in LENTOS else
                        "coyuntural" if tn in RAPIDOS else "secundario")
                hits.append({
                    "transito": tn, "aspecto": asp, "natal": nn,
                    "orbe": round(desv, 3), "separacion": round(sep, 3),
                    "retrogrado": tp["retrogrado"], "peso": peso,
                    "naturaleza": ASPECTOS[asp][3],
                    "posicion_transito": tp["posicion"],
                    "exactitud_pct": round(100 * (1 - desv / orbe_max), 1),
                })
                break
    hits.sort(key=lambda h: (0 if h["peso"] == "estructural" else 1, h["orbe"]))
    return {"posiciones_actuales": actuales, "transitos": hits}


def progresiones_secundarias(jd_natal, jd_ahora, natal):
    """Progresión secundaria: 1 día después del nacimiento = 1 año de vida."""
    dias_vividos = jd_ahora - jd_natal
    anios = dias_vividos / 365.2422
    jd_prog = jd_natal + anios          # un día por año
    prog = posiciones_en(jd_prog)

    # ASC/MC progresados por el método de arco solar
    sol_n = natal["planetas"]["Sol"]["longitud"]
    sol_p = prog["Sol"]["longitud"]
    arco_solar = (sol_p - sol_n) % 360
    asc_p = (natal["angulos"]["Ascendente"]["longitud"] + arco_solar) % 360
    mc_p = (natal["angulos"]["Medio Cielo (MC)"]["longitud"] + arco_solar) % 360

    # Fase lunar progresada (ciclo de ~29,5 años)
    ang_prog = (prog["Luna"]["longitud"] - sol_p) % 360
    fases = [(0, 45, "Luna Nueva progresada — nuevo ciclo de 29,5 años"),
             (45, 90, "Creciente — construir impulso"),
             (90, 135, "Cuarto Creciente — crisis de acción"),
             (135, 180, "Gibosa — refinar antes de la culminación"),
             (180, 225, "Llena progresada — máxima visibilidad/claridad"),
             (225, 270, "Diseminante — compartir lo aprendido"),
             (270, 315, "Cuarto Menguante — crisis de conciencia, reorientar"),
             (315, 360, "Balsámica — soltar, preparar el ciclo siguiente")]
    fase_p = next(n for a, b, n in fases if a <= ang_prog < b)

    return {
        "metodo": "Secundaria (1 día = 1 año) + arco solar para los ángulos",
        "anios_progresados": round(anios, 4),
        "arco_solar_grados": round(arco_solar, 4),
        "planetas_progresados": prog,
        "ascendente_progresado": {"longitud": round(asc_p, 4), "posicion": fmt(asc_p), "signo": gl(asc_p)[0]},
        "mc_progresado": {"longitud": round(mc_p, 4), "posicion": fmt(mc_p), "signo": gl(mc_p)[0]},
        "fase_lunar_progresada": {"angulo": round(ang_prog, 3), "fase": fase_p},
        "sol_progresado_signo": prog["Sol"]["signo"],
        "luna_progresada_signo": prog["Luna"]["signo"],
    }


def retorno_solar(jd_natal, anio, natal):
    """Momento exacto en que el Sol vuelve a su grado natal."""
    sol_natal = natal["planetas"]["Sol"]["longitud"]
    jd_aprox = swe.julday(anio, 1, 9, 10.0, swe.GREG_CAL)
    lo, hi = jd_aprox - 3, jd_aprox + 3
    for _ in range(80):
        mid = (lo + hi) / 2
        v, _ = swe.calc_ut(mid, swe.SUN, FLAGS)
        d = ((v[0] - sol_natal + 180) % 360) - 180
        if d < 0:
            lo = mid
        else:
            hi = mid
    jr = (lo + hi) / 2
    y, mo, d, h = swe.revjul(jr, swe.GREG_CAL)
    dt = datetime(y, mo, d, tzinfo=timezone.utc) + timedelta(hours=h)
    cusps, ascmc = swe.houses(jr, SUJETO["lat"], SUJETO["lon"], b"P")
    return {
        "anio": anio,
        "momento_utc": dt.isoformat(),
        "momento_local": dt.astimezone(TZ_LOCAL).isoformat(),
        "ascendente_del_retorno": fmt(ascmc[0]),
        "signo_ascendente": gl(ascmc[0])[0],
        "mc_del_retorno": fmt(ascmc[1]),
        "planetas": posiciones_en(jr),
        "nota": "El retorno solar rige simbólicamente desde un cumpleaños al siguiente.",
    }


def ciclos_de_vida(jd_natal, jd_ahora, natal):
    """Retornos planetarios y puntos de inflexión del ciclo vital."""
    edad_anios = (jd_ahora - jd_natal) / 365.2422
    res = {"edad_exacta_anios": round(edad_anios, 3), "retornos": [], "hitos": []}

    mapa = {"Júpiter": swe.JUPITER, "Saturno": swe.SATURN, "Urano": swe.URANUS,
            "Neptuno": swe.NEPTUNE, "Quirón": swe.CHIRON,
            "Nodo Norte (verdadero)": swe.TRUE_NODE}

    for nombre, cuerpo in mapa.items():
        if nombre not in natal["planetas"]:
            continue
        objetivo = natal["planetas"][nombre]["longitud"]
        per = PERIODOS_SIDEREOS[nombre]
        n_retorno = 0
        while True:
            n_retorno += 1
            edad_est = per * n_retorno
            if edad_est > 95:
                break
            jd_est = jd_natal + edad_est * 365.2422
            # Refinar por búsqueda de mínima distancia angular
            mejor, mejor_d = jd_est, 999
            # Barrido grueso ancho primero: los planetas con lazos retrógrados
            # pueden cruzar el grado natal fuera de la ventana estrecha.
            for paso in (25, 6, 1.5, 0.3, 0.05):
                j = mejor - paso * 40
                while j <= mejor + paso * 40:
                    try:
                        v, _ = swe.calc_ut(j, cuerpo, FLAGS)
                    except swe.Error:
                        j += paso
                        continue
                    d = abs(((v[0] - objetivo + 180) % 360) - 180)
                    if d < mejor_d:
                        mejor_d, mejor = d, j
                    j += paso
            if mejor_d > 1.0:
                continue
            y, mo, dd, h = swe.revjul(mejor, swe.GREG_CAL)
            edad_real = (mejor - jd_natal) / 365.2422
            res["retornos"].append({
                "planeta": nombre, "numero_de_retorno": n_retorno,
                "fecha_aprox": f"{y:04d}-{mo:02d}-{dd:02d}",
                "edad": round(edad_real, 2),
                "estado": ("pasado" if mejor < jd_ahora else "futuro"),
                "anios_desde_o_hasta": round((mejor - jd_ahora) / 365.2422, 2),
                "grado_natal_de_retorno": natal["planetas"][nombre]["posicion"],
            })
            if nombre == "Nodo Norte (verdadero)" and n_retorno > 5:
                break

    # Hitos clásicos por edad
    for edad, etiqueta in [
        (29.5, "Primer retorno de Saturno — asumir la propia estructura adulta"),
        (36.0, "Cuadratura menguante de Saturno al natal — revisión de la estructura"),
        (38.0, "Oposición de Urano en aproximación — presión de individuación"),
        (42.0, "Oposición de Urano exacta — 'crisis de la mitad de la vida'"),
        (44.0, "Cuadratura de Neptuno al natal — disolución de certezas"),
        (50.4, "Retorno de Quirón — integración de la herida original"),
        (59.0, "Segundo retorno de Saturno — cosecha estructural"),
    ]:
        res["hitos"].append({
            "edad": edad, "hito": etiqueta,
            "estado": "pasado" if edad_anios > edad else "futuro",
            "anios_de_diferencia": round(edad - edad_anios, 2),
        })
    res["retornos"].sort(key=lambda r: r["edad"])
    return res


def informe(fecha_local=None, incluir_ciclos=False):
    natal = calcular_natal()
    dt_natal = datetime.fromisoformat(natal["tiempo"]["utc_iso"])
    jd_natal = jd_de(dt_natal)

    if fecha_local is None:
        ahora = datetime.now(TZ_LOCAL)
    else:
        ahora = datetime.fromisoformat(fecha_local).replace(tzinfo=TZ_LOCAL)
        if ahora.hour == 0 and ahora.minute == 0:
            ahora = ahora.replace(hour=9)  # mediodía operativo por defecto
    ahora_utc = ahora.astimezone(timezone.utc)
    jd_ahora = jd_de(ahora_utc)

    out = {
        "momento": {"local": ahora.isoformat(), "utc": ahora_utc.isoformat(),
                    "julian_day": jd_ahora},
        "capa": "ASTRONÓMICA (posiciones y fases son verificables) + ángulos a la carta natal",
        "cielo_actual": posiciones_en(jd_ahora),
        "fase_lunar": fase_lunar(jd_ahora),
        "proximas_lunaciones": proximas_lunaciones(jd_ahora, 4),
        "estaciones_planetarias_180d": retrogradaciones(jd_ahora, 180),
    }
    t = transitos_a_natal(jd_ahora, natal)
    out["transitos_a_natal"] = t["transitos"]
    out["progresiones"] = progresiones_secundarias(jd_natal, jd_ahora, natal)
    out["retorno_solar_vigente"] = retorno_solar(
        jd_natal, ahora.year if (ahora.month, ahora.day) >= (1, 9) else ahora.year - 1, natal)
    if incluir_ciclos:
        out["ciclos_de_vida"] = ciclos_de_vida(jd_natal, jd_ahora, natal)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", help="YYYY-MM-DD (hora local Argentina)")
    ap.add_argument("--ciclos", action="store_true", help="incluir retornos y hitos de vida")
    args = ap.parse_args()
    print(json.dumps(informe(args.fecha, args.ciclos), ensure_ascii=False, indent=2))
