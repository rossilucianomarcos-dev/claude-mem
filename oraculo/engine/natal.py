#!/usr/bin/env python3
"""
Motor de cálculo de carta natal — Oráculo Personal.

Usa Swiss Ephemeris (pyswisseph) para posiciones planetarias de precisión
astronómica. Todo lo que este módulo produce es ASTRONÓMICAMENTE VERIFICABLE:
posiciones, ángulos, casas y fases. La interpretación simbólica NO vive aquí.

Uso:
    python3 natal.py                 # imprime JSON de la carta natal
    python3 natal.py --pretty        # imprime informe legible
"""

import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

# ---------------------------------------------------------------------------
# DATOS DE NACIMIENTO (canónicos)
# ---------------------------------------------------------------------------

SUJETO = {
    "nombre": "Luciano Marcos Rossi",
    "sexo": "Masculino",
    "fecha_local": "1990-01-09",
    "hora_local": "08:24:00",
    "ciudad": "Santa Fe de la Vera Cruz",
    "provincia": "Santa Fe",
    "pais": "Argentina",
    "lat": -31.6333,          # 31°38' S
    "lon": -60.7000,          # 60°42' O
    "altitud_m": 25,
    "tz_iana": "America/Argentina/Cordoba",
}

# ---------------------------------------------------------------------------
# TABLAS DE REFERENCIA
# ---------------------------------------------------------------------------

SIGNOS = [
    "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
    "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis",
]
SIGNO_GLIFO = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

ELEMENTO = {
    "Aries": "Fuego", "Leo": "Fuego", "Sagitario": "Fuego",
    "Tauro": "Tierra", "Virgo": "Tierra", "Capricornio": "Tierra",
    "Géminis": "Aire", "Libra": "Aire", "Acuario": "Aire",
    "Cáncer": "Agua", "Escorpio": "Agua", "Piscis": "Agua",
}
MODALIDAD = {
    "Aries": "Cardinal", "Cáncer": "Cardinal", "Libra": "Cardinal", "Capricornio": "Cardinal",
    "Tauro": "Fijo", "Leo": "Fijo", "Escorpio": "Fijo", "Acuario": "Fijo",
    "Géminis": "Mutable", "Virgo": "Mutable", "Sagitario": "Mutable", "Piscis": "Mutable",
}
POLARIDAD = {
    "Aries": "Diurna/+", "Géminis": "Diurna/+", "Leo": "Diurna/+",
    "Libra": "Diurna/+", "Sagitario": "Diurna/+", "Acuario": "Diurna/+",
    "Tauro": "Nocturna/-", "Cáncer": "Nocturna/-", "Virgo": "Nocturna/-",
    "Escorpio": "Nocturna/-", "Capricornio": "Nocturna/-", "Piscis": "Nocturna/-",
}

# Cuerpos calculados. (nombre, constante swisseph, es_planeta_tradicional)
CUERPOS = [
    ("Sol", swe.SUN, True),
    ("Luna", swe.MOON, True),
    ("Mercurio", swe.MERCURY, True),
    ("Venus", swe.VENUS, True),
    ("Marte", swe.MARS, True),
    ("Júpiter", swe.JUPITER, True),
    ("Saturno", swe.SATURN, True),
    ("Urano", swe.URANUS, False),
    ("Neptuno", swe.NEPTUNE, False),
    ("Plutón", swe.PLUTO, False),
    ("Nodo Norte (medio)", swe.MEAN_NODE, False),
    ("Nodo Norte (verdadero)", swe.TRUE_NODE, False),
    ("Quirón", swe.CHIRON, False),
    ("Lilith (Luna Negra media)", swe.MEAN_APOG, False),
    ("Ceres", swe.CERES, False),
    ("Palas", swe.PALLAS, False),
    ("Juno", swe.JUNO, False),
    ("Vesta", swe.VESTA, False),
]

# Regencias tradicionales (sin planetas modernos) y modernas.
REGENTE_TRAD = {
    "Aries": "Marte", "Tauro": "Venus", "Géminis": "Mercurio", "Cáncer": "Luna",
    "Leo": "Sol", "Virgo": "Mercurio", "Libra": "Venus", "Escorpio": "Marte",
    "Sagitario": "Júpiter", "Capricornio": "Saturno", "Acuario": "Saturno", "Piscis": "Júpiter",
}
REGENTE_MOD = dict(REGENTE_TRAD, **{"Escorpio": "Plutón", "Acuario": "Urano", "Piscis": "Neptuno"})

# Dignidades esenciales: domicilio, exaltación (grado), exilio, caída.
DOMICILIO = {
    "Sol": ["Leo"], "Luna": ["Cáncer"], "Mercurio": ["Géminis", "Virgo"],
    "Venus": ["Tauro", "Libra"], "Marte": ["Aries", "Escorpio"],
    "Júpiter": ["Sagitario", "Piscis"], "Saturno": ["Capricornio", "Acuario"],
}
EXALTACION = {
    "Sol": ("Aries", 19), "Luna": ("Tauro", 3), "Mercurio": ("Virgo", 15),
    "Venus": ("Piscis", 27), "Marte": ("Capricornio", 28),
    "Júpiter": ("Cáncer", 15), "Saturno": ("Libra", 21),
}
OPUESTO = {s: SIGNOS[(i + 6) % 12] for i, s in enumerate(SIGNOS)}

# Términos egipcios (dignidad menor): signo -> [(planeta, grado_hasta), ...]
TERMINOS_EGIPCIOS = {
    "Aries": [("Júpiter", 6), ("Venus", 12), ("Mercurio", 20), ("Marte", 25), ("Saturno", 30)],
    "Tauro": [("Venus", 8), ("Mercurio", 14), ("Júpiter", 22), ("Saturno", 27), ("Marte", 30)],
    "Géminis": [("Mercurio", 6), ("Júpiter", 12), ("Venus", 17), ("Marte", 24), ("Saturno", 30)],
    "Cáncer": [("Marte", 7), ("Venus", 13), ("Mercurio", 19), ("Júpiter", 26), ("Saturno", 30)],
    "Leo": [("Júpiter", 6), ("Venus", 11), ("Saturno", 18), ("Mercurio", 24), ("Marte", 30)],
    "Virgo": [("Mercurio", 7), ("Venus", 17), ("Júpiter", 21), ("Marte", 28), ("Saturno", 30)],
    "Libra": [("Saturno", 6), ("Mercurio", 14), ("Júpiter", 21), ("Venus", 28), ("Marte", 30)],
    "Escorpio": [("Marte", 7), ("Venus", 11), ("Mercurio", 19), ("Júpiter", 24), ("Saturno", 30)],
    "Sagitario": [("Júpiter", 12), ("Venus", 17), ("Mercurio", 21), ("Saturno", 26), ("Marte", 30)],
    "Capricornio": [("Mercurio", 7), ("Júpiter", 14), ("Venus", 22), ("Saturno", 26), ("Marte", 30)],
    "Acuario": [("Mercurio", 7), ("Venus", 13), ("Júpiter", 20), ("Marte", 25), ("Saturno", 30)],
    "Piscis": [("Venus", 12), ("Júpiter", 16), ("Mercurio", 19), ("Marte", 28), ("Saturno", 30)],
}

# Triplicidades (sistema de Dorotheo): elemento -> (regente diurno, nocturno, participante)
TRIPLICIDAD = {
    "Fuego": ("Sol", "Júpiter", "Saturno"),
    "Tierra": ("Venus", "Luna", "Marte"),
    "Aire": ("Saturno", "Mercurio", "Júpiter"),
    "Agua": ("Venus", "Marte", "Luna"),
}

# Aspectos: nombre -> (ángulo, orbe_luminarias, orbe_planetas, naturaleza)
ASPECTOS = {
    "Conjunción":    (0.0,   10.0, 8.0, "neutro"),
    "Oposición":     (180.0, 10.0, 8.0, "tenso"),
    "Trígono":       (120.0, 9.0,  7.0, "fluido"),
    "Cuadratura":    (90.0,  9.0,  7.0, "tenso"),
    "Sextil":        (60.0,  6.0,  5.0, "fluido"),
    "Quincuncio":    (150.0, 3.0,  2.5, "ajuste"),
    "Semisextil":    (30.0,  2.5,  2.0, "menor"),
    "Sesquicuadrat.":(135.0, 2.5,  2.0, "menor-tenso"),
    "Semicuadratura":(45.0,  2.5,  2.0, "menor-tenso"),
    "Quintil":       (72.0,  2.0,  1.5, "creativo"),
    "Biquintil":     (144.0, 2.0,  1.5, "creativo"),
}

# Nakshatras védicos (27), con su regente de dasha Vimshottari.
NAKSHATRAS = [
    ("Ashwini", "Ketu", 7), ("Bharani", "Venus", 20), ("Krittika", "Sol", 6),
    ("Rohini", "Luna", 10), ("Mrigashira", "Marte", 7), ("Ardra", "Rahu", 18),
    ("Punarvasu", "Júpiter", 16), ("Pushya", "Saturno", 19), ("Ashlesha", "Mercurio", 17),
    ("Magha", "Ketu", 7), ("Purva Phalguni", "Venus", 20), ("Uttara Phalguni", "Sol", 6),
    ("Hasta", "Luna", 10), ("Chitra", "Marte", 7), ("Swati", "Rahu", 18),
    ("Vishakha", "Júpiter", 16), ("Anuradha", "Saturno", 19), ("Jyeshtha", "Mercurio", 17),
    ("Mula", "Ketu", 7), ("Purva Ashadha", "Venus", 20), ("Uttara Ashadha", "Sol", 6),
    ("Shravana", "Luna", 10), ("Dhanishta", "Marte", 7), ("Shatabhisha", "Rahu", 18),
    ("Purva Bhadrapada", "Júpiter", 16), ("Uttara Bhadrapada", "Saturno", 19), ("Revati", "Mercurio", 17),
]
ORDEN_DASHA = ["Ketu", "Venus", "Sol", "Luna", "Marte", "Rahu", "Júpiter", "Saturno", "Mercurio"]
ANIOS_DASHA = {"Ketu": 7, "Venus": 20, "Sol": 6, "Luna": 10, "Marte": 7,
               "Rahu": 18, "Júpiter": 16, "Saturno": 19, "Mercurio": 17}

SIGNOS_SANSCRITO = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
                    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

def gl(lon):
    """Longitud eclíptica -> (signo, grado, minuto, segundo)."""
    lon = lon % 360.0
    idx = int(lon // 30)
    resto = lon - idx * 30
    g = int(resto)
    m_f = (resto - g) * 60
    m = int(m_f)
    s = int(round((m_f - m) * 60))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        g += 1
    return SIGNOS[idx], g, m, s


def fmt(lon):
    """Formato astrológico estándar: 12°34'56\" Capricornio."""
    signo, g, m, s = gl(lon)
    return f"{g:02d}°{m:02d}'{s:02d}\" {signo}"


def sep_angular(a, b):
    """Separación angular mínima entre dos longitudes (0-180)."""
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


# ---------------------------------------------------------------------------
# CÁLCULO PRINCIPAL
# ---------------------------------------------------------------------------

def calcular():
    s = SUJETO
    tz = ZoneInfo(s["tz_iana"])
    dt_local = datetime.fromisoformat(f"{s['fecha_local']}T{s['hora_local']}").replace(tzinfo=tz)
    dt_utc = dt_local.astimezone(timezone.utc)

    offset_horas = dt_local.utcoffset().total_seconds() / 3600.0
    dst_horas = dt_local.dst().total_seconds() / 3600.0

    jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                       dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
                       swe.GREG_CAL)

    # Archivos de efemérides Swiss Ephemeris (ver oraculo/setup.sh).
    # Sin ellos, pyswisseph usa Moshier internamente para los 10 planetas
    # principales (precisión < 1"), pero Quirón y los asteroides no se calculan.
    import os
    ephe_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ephe")
    ephe_dir = os.path.normpath(ephe_dir)
    swe.set_ephe_path(ephe_dir if os.path.isdir(ephe_dir) else None)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    out = {
        "sujeto": s,
        "tiempo": {
            "local_iso": dt_local.isoformat(),
            "utc_iso": dt_utc.isoformat(),
            "offset_utc_horas": offset_horas,
            "horario_verano_activo": dst_horas != 0,
            "dst_horas": dst_horas,
            "julian_day_ut": jd_ut,
            "nota": ("Argentina observó horario de verano del 15-oct-1989 al 4-mar-1990. "
                     "El 9-ene-1990 el offset real fue UTC-2, NO UTC-3. "
                     "Usar UTC-3 desplazaría el Ascendente ~15 grados."),
        },
        "ubicacion": {"lat": s["lat"], "lon": s["lon"]},
    }

    # --- Planetas y puntos ------------------------------------------------
    posiciones = {}
    for nombre, cuerpo, tradicional in CUERPOS:
        try:
            vals, _ = swe.calc_ut(jd_ut, cuerpo, flags)
        except swe.Error:
            continue
        lon, lat_ecl, dist, vlon = vals[0], vals[1], vals[2], vals[3]
        signo, g, m, sec = gl(lon)
        posiciones[nombre] = {
            "longitud": round(lon, 6),
            "signo": signo,
            "grado": g, "minuto": m, "segundo": sec,
            "posicion": fmt(lon),
            "latitud_ecliptica": round(lat_ecl, 6),
            "distancia_ua": round(dist, 8),
            "velocidad_dia": round(vlon, 6),
            "retrogrado": vlon < 0,
            "elemento": ELEMENTO[signo],
            "modalidad": MODALIDAD[signo],
            "grado_absoluto": round(lon, 4),
            "planeta_tradicional": tradicional,
        }

    # Nodo Sur = Nodo Norte + 180
    nn = posiciones["Nodo Norte (verdadero)"]["longitud"]
    ns = (nn + 180.0) % 360.0
    signo, g, m, sec = gl(ns)
    posiciones["Nodo Sur (verdadero)"] = {
        "longitud": round(ns, 6), "signo": signo, "grado": g, "minuto": m, "segundo": sec,
        "posicion": fmt(ns), "retrogrado": True, "elemento": ELEMENTO[signo],
        "modalidad": MODALIDAD[signo], "grado_absoluto": round(ns, 4),
        "planeta_tradicional": False, "velocidad_dia": posiciones["Nodo Norte (verdadero)"]["velocidad_dia"],
    }
    out["planetas"] = posiciones

    # --- Casas (Placidus + Whole Sign + otros sistemas) -------------------
    sistemas = {"Placidus": b"P", "Whole Sign": b"W", "Koch": b"K",
                "Casas Iguales": b"A", "Regiomontanus": b"R", "Campanus": b"C",
                "Porfirio": b"O"}
    casas_out = {}
    for nom, code in sistemas.items():
        cusps, ascmc = swe.houses(jd_ut, s["lat"], s["lon"], code)
        casas_out[nom] = {
            "cuspides": [round(c, 6) for c in cusps[:12]],
            "cuspides_fmt": [fmt(c) for c in cusps[:12]],
        }
        if nom == "Placidus":
            asc, mc, armc, vertex = ascmc[0], ascmc[1], ascmc[2], ascmc[3]
            equasc, coasc1, polasc = ascmc[4], ascmc[5], ascmc[7]
    out["casas"] = casas_out

    cusps_pl, ascmc = swe.houses(jd_ut, s["lat"], s["lon"], b"P")
    asc, mc, armc, vertex = ascmc[0], ascmc[1], ascmc[2], ascmc[3]

    out["angulos"] = {
        "Ascendente": {"longitud": round(asc, 6), "posicion": fmt(asc),
                       "signo": gl(asc)[0], "elemento": ELEMENTO[gl(asc)[0]],
                       "modalidad": MODALIDAD[gl(asc)[0]],
                       "regente_tradicional": REGENTE_TRAD[gl(asc)[0]],
                       "regente_moderno": REGENTE_MOD[gl(asc)[0]]},
        "Descendente": {"longitud": round((asc + 180) % 360, 6), "posicion": fmt((asc + 180) % 360),
                        "signo": gl((asc + 180) % 360)[0]},
        "Medio Cielo (MC)": {"longitud": round(mc, 6), "posicion": fmt(mc), "signo": gl(mc)[0],
                             "regente_tradicional": REGENTE_TRAD[gl(mc)[0]],
                             "regente_moderno": REGENTE_MOD[gl(mc)[0]]},
        "Fondo del Cielo (IC)": {"longitud": round((mc + 180) % 360, 6),
                                 "posicion": fmt((mc + 180) % 360), "signo": gl((mc + 180) % 360)[0]},
        "Vertex": {"longitud": round(vertex, 6), "posicion": fmt(vertex), "signo": gl(vertex)[0]},
        "ARMC": round(armc, 6),
    }

    # --- Asignación de planetas a casas (Placidus) ------------------------
    def casa_de(lon_p, cusps):
        for i in range(12):
            a = cusps[i]
            b = cusps[(i + 1) % 12]
            if a <= b:
                if a <= lon_p < b:
                    return i + 1
            else:  # cruza 0° Aries
                if lon_p >= a or lon_p < b:
                    return i + 1
        return None

    asc_signo_idx = SIGNOS.index(gl(asc)[0])
    for nombre, p in posiciones.items():
        p["casa_placidus"] = casa_de(p["longitud"], list(cusps_pl[:12]))
        p["casa_whole_sign"] = ((SIGNOS.index(p["signo"]) - asc_signo_idx) % 12) + 1

    # --- Sol sobre/bajo horizonte: secta -------------------------------
    sol_casa = posiciones["Sol"]["casa_placidus"]
    diurna = sol_casa in (7, 8, 9, 10, 11, 12)
    out["secta"] = {
        "carta": "Diurna" if diurna else "Nocturna",
        "explicacion": ("El Sol está sobre el horizonte (casas 7-12)." if diurna
                        else "El Sol está bajo el horizonte (casas 1-6)."),
        "luminaria_de_secta": "Sol" if diurna else "Luna",
        "benefico_de_secta": "Júpiter" if diurna else "Venus",
        "malefico_de_secta": "Saturno" if diurna else "Marte",
        "malefico_fuera_de_secta": "Marte" if diurna else "Saturno",
    }

    # --- Parte de la Fortuna y otros lotes helenísticos -------------------
    sol_l = posiciones["Sol"]["longitud"]
    luna_l = posiciones["Luna"]["longitud"]
    if diurna:
        fortuna = (asc + luna_l - sol_l) % 360
        espiritu = (asc + sol_l - luna_l) % 360
    else:
        fortuna = (asc + sol_l - luna_l) % 360
        espiritu = (asc + luna_l - sol_l) % 360
    venus_l = posiciones["Venus"]["longitud"]
    eros = (asc + venus_l - espiritu) % 360 if diurna else (asc + espiritu - venus_l) % 360

    out["lotes_helenisticos"] = {
        "Parte de la Fortuna": {"longitud": round(fortuna, 6), "posicion": fmt(fortuna),
                                "signo": gl(fortuna)[0], "casa": casa_de(fortuna, list(cusps_pl[:12]))},
        "Parte del Espíritu": {"longitud": round(espiritu, 6), "posicion": fmt(espiritu),
                               "signo": gl(espiritu)[0], "casa": casa_de(espiritu, list(cusps_pl[:12]))},
        "Parte de Eros": {"longitud": round(eros, 6), "posicion": fmt(eros), "signo": gl(eros)[0]},
    }

    # --- Aspectos ---------------------------------------------------------
    puntos_asp = {k: v["longitud"] for k, v in posiciones.items()
                  if "Nodo Norte (medio)" not in k}
    puntos_asp["Ascendente"] = asc
    puntos_asp["Medio Cielo (MC)"] = mc

    luminarias = {"Sol", "Luna"}
    nombres = list(puntos_asp.keys())
    aspectos = []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            n1, n2 = nombres[i], nombres[j]
            # Los nodos son opuestos por definición: no es un aspecto informativo.
            if {n1, n2} == {"Nodo Norte (verdadero)", "Nodo Sur (verdadero)"}:
                continue
            sep = sep_angular(puntos_asp[n1], puntos_asp[n2])
            for asp, (ang, orb_lum, orb_pla, nat) in ASPECTOS.items():
                orbe_max = orb_lum if (n1 in luminarias or n2 in luminarias) else orb_pla
                desv = abs(sep - ang)
                if desv <= orbe_max:
                    v1 = posiciones.get(n1, {}).get("velocidad_dia", 0)
                    v2 = posiciones.get(n2, {}).get("velocidad_dia", 0)
                    aspectos.append({
                        "p1": n1, "p2": n2, "aspecto": asp, "angulo_exacto": ang,
                        "separacion_real": round(sep, 4), "orbe": round(desv, 4),
                        "naturaleza": nat,
                        "exactitud_pct": round(100 * (1 - desv / orbe_max), 1),
                        "aplicativo": (v1 - v2) * (sep - ang) < 0 if (v1 or v2) else None,
                        "mayor": asp in ("Conjunción", "Oposición", "Trígono", "Cuadratura", "Sextil"),
                    })
                    break
    aspectos.sort(key=lambda a: a["orbe"])
    out["aspectos"] = aspectos

    # --- Balance de elementos / modalidades / polaridad --------------------
    def balance(clave, tabla, solo=None):
        cnt = {}
        pond = {}
        pesos = {"Sol": 3, "Luna": 3, "Ascendente": 3, "Mercurio": 2, "Venus": 2,
                 "Marte": 2, "Júpiter": 1.5, "Saturno": 1.5, "Medio Cielo (MC)": 2,
                 "Urano": 1, "Neptuno": 1, "Plutón": 1}
        items = list(posiciones.items())
        items.append(("Ascendente", {"signo": gl(asc)[0]}))
        items.append(("Medio Cielo (MC)", {"signo": gl(mc)[0]}))
        for nombre, p in items:
            if solo and nombre not in solo:
                continue
            v = tabla[p["signo"]]
            cnt[v] = cnt.get(v, 0) + 1
            pond[v] = pond.get(v, 0) + pesos.get(nombre, 0.5)
        return {"conteo": cnt, "ponderado": {k: round(v, 2) for k, v in pond.items()}}

    principales = ["Sol", "Luna", "Mercurio", "Venus", "Marte", "Júpiter", "Saturno",
                   "Urano", "Neptuno", "Plutón", "Ascendente", "Medio Cielo (MC)"]
    out["balance"] = {
        "elementos": balance("elemento", ELEMENTO, principales),
        "modalidades": balance("modalidad", MODALIDAD, principales),
        "polaridad": balance("polaridad", POLARIDAD, principales),
    }

    # Hemisferios y cuadrantes
    hemis = {"Norte (casas 1-6, bajo horizonte)": 0, "Sur (casas 7-12, sobre horizonte)": 0,
             "Este (casas 10-3, autodeterminación)": 0, "Oeste (casas 4-9, otros)": 0}
    for n in principales[:10]:
        c = posiciones[n]["casa_placidus"]
        if c <= 6:
            hemis["Norte (casas 1-6, bajo horizonte)"] += 1
        else:
            hemis["Sur (casas 7-12, sobre horizonte)"] += 1
        if c in (10, 11, 12, 1, 2, 3):
            hemis["Este (casas 10-3, autodeterminación)"] += 1
        else:
            hemis["Oeste (casas 4-9, otros)"] += 1
    out["hemisferios"] = hemis

    # --- Dignidades esenciales y puntaje de almuten -----------------------
    dignidades = {}
    for n in ["Sol", "Luna", "Mercurio", "Venus", "Marte", "Júpiter", "Saturno"]:
        p = posiciones[n]
        sg, gr = p["signo"], p["grado"]
        d = []
        pts = 0
        if sg in DOMICILIO.get(n, []):
            d.append("Domicilio (+5)"); pts += 5
        if n in EXALTACION and EXALTACION[n][0] == sg:
            d.append(f"Exaltación (+4), grado exacto {EXALTACION[n][1]}°"); pts += 4
        if sg in [OPUESTO[x] for x in DOMICILIO.get(n, [])]:
            d.append("Exilio / Detrimento (-5)"); pts -= 5
        if n in EXALTACION and OPUESTO[EXALTACION[n][0]] == sg:
            d.append("Caída (-4)"); pts -= 4
        # Triplicidad
        trip = TRIPLICIDAD[ELEMENTO[sg]]
        reg_trip = trip[0] if diurna else trip[1]
        if n == reg_trip:
            d.append("Regente de triplicidad de secta (+3)"); pts += 3
        elif n == trip[2]:
            d.append("Regente participante de triplicidad (+1)"); pts += 1
        # Términos
        for pl, lim in TERMINOS_EGIPCIOS[sg]:
            if gr < lim:
                if pl == n:
                    d.append("En sus propios términos egipcios (+2)"); pts += 2
                break
        dignidades[n] = {"posicion": p["posicion"], "dignidades": d or ["Peregrino (sin dignidad esencial)"],
                         "puntaje": pts,
                         "regente_del_signo_trad": REGENTE_TRAD[sg],
                         "retrogrado": p["retrogrado"]}
    out["dignidades_esenciales"] = dignidades

    # --- Dominantes (planeta, signo, casa) --------------------------------
    # Solo los 10 planetas puntúan como dominantes; asteroides y puntos
    # calculados (Quirón, Juno, Lilith, nodos) se excluyen deliberadamente.
    ELEGIBLES_DOM = set(principales[:10])
    dom_planeta = {}
    for a in aspectos:
        if not a["mayor"]:
            continue
        peso = a["exactitud_pct"] / 100 * (2 if a["aspecto"] in ("Conjunción", "Oposición") else 1.5)
        for p in (a["p1"], a["p2"]):
            if p in ELEGIBLES_DOM:
                dom_planeta[p] = dom_planeta.get(p, 0) + peso
    # Bonus: regente del ASC, regente del MC, ubicaciones angulares
    reg_asc_t = REGENTE_TRAD[gl(asc)[0]]
    reg_asc_m = REGENTE_MOD[gl(asc)[0]]
    reg_mc_t = REGENTE_TRAD[gl(mc)[0]]
    for p, b in [(reg_asc_t, 6), (reg_asc_m, 5), (reg_mc_t, 4), ("Sol", 5), ("Luna", 5)]:
        dom_planeta[p] = dom_planeta.get(p, 0) + b
    for n in principales[:10]:
        c = posiciones[n]["casa_placidus"]
        if c in (1, 4, 7, 10):
            dom_planeta[n] = dom_planeta.get(n, 0) + 4
        elif c in (2, 5, 8, 11):
            dom_planeta[n] = dom_planeta.get(n, 0) + 1.5
    for n, v in dignidades.items():
        dom_planeta[n] = dom_planeta.get(n, 0) + v["puntaje"]

    dom_signo = {}
    dom_casa = {}
    pesos_d = {"Sol": 4, "Luna": 4, "Ascendente": 4, "Mercurio": 2.5, "Venus": 2.5,
               "Marte": 2.5, "Júpiter": 2, "Saturno": 2, "Urano": 1, "Neptuno": 1,
               "Plutón": 1, "Medio Cielo (MC)": 3}
    for n in principales:
        if n == "Ascendente":
            sg, ca = gl(asc)[0], 1
        elif n == "Medio Cielo (MC)":
            sg, ca = gl(mc)[0], 10
        else:
            sg, ca = posiciones[n]["signo"], posiciones[n]["casa_placidus"]
        dom_signo[sg] = dom_signo.get(sg, 0) + pesos_d.get(n, 1)
        dom_casa[ca] = dom_casa.get(ca, 0) + pesos_d.get(n, 1)

    out["dominantes"] = {
        "planetas": sorted(({"planeta": k, "puntaje": round(v, 2)} for k, v in dom_planeta.items()),
                           key=lambda x: -x["puntaje"])[:10],
        "signos": sorted(({"signo": k, "puntaje": round(v, 2)} for k, v in dom_signo.items()),
                         key=lambda x: -x["puntaje"])[:6],
        "casas": sorted(({"casa": k, "puntaje": round(v, 2)} for k, v in dom_casa.items()),
                        key=lambda x: -x["puntaje"])[:6],
        "regente_ascendente_tradicional": reg_asc_t,
        "regente_ascendente_moderno": reg_asc_m,
        "regente_mc_tradicional": reg_mc_t,
        "metodologia": ("Puntaje compuesto: aspectos mayores ponderados por exactitud + "
                        "regencias angulares + dignidades esenciales + angularidad. "
                        "Es una heurística astrológica, no una medida física."),
    }

    # --- Fase lunar de nacimiento ----------------------------------------
    fase_ang = (luna_l - sol_l) % 360
    fases = [(0, 45, "Luna Nueva (creciente balsámica→nueva)"), (45, 90, "Creciente Iluminante"),
             (90, 135, "Cuarto Creciente"), (135, 180, "Gibosa Creciente"),
             (180, 225, "Luna Llena"), (225, 270, "Diseminante"),
             (270, 315, "Cuarto Menguante"), (315, 360, "Balsámica (última)")]
    fase_nombre = next(n for a, b, n in fases if a <= fase_ang < b)
    out["fase_lunar_natal"] = {
        "angulo_sol_luna": round(fase_ang, 4),
        "fase": fase_nombre,
        "iluminacion_pct": round(50 * (1 - __import__("math").cos(__import__("math").radians(fase_ang))), 2),
    }

    # --- ASTROLOGÍA VÉDICA (sideral, ayanamsa Lahiri) ---------------------
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    ayan = swe.get_ayanamsa_ut(jd_ut)
    sid_flags = flags | swe.FLG_SIDEREAL
    vedico = {"ayanamsa_lahiri": round(ayan, 6), "sistema": "Sideral / Jyotish", "grahas": {}}
    for nombre, cuerpo, _ in CUERPOS[:10] + [("Nodo Norte (verdadero)", swe.TRUE_NODE, False)]:
        try:
            vals, _ = swe.calc_ut(jd_ut, cuerpo, sid_flags)
        except swe.Error:
            continue
        lon = vals[0] % 360
        idx_n = int(lon // (360 / 27))
        pada = int((lon % (360 / 27)) // (360 / 108)) + 1
        nk, reg, _yrs = NAKSHATRAS[idx_n]
        nom_v = {"Nodo Norte (verdadero)": "Rahu"}.get(nombre, nombre)
        vedico["grahas"][nom_v] = {
            "longitud_sideral": round(lon, 6),
            "rasi": SIGNOS[int(lon // 30)],
            "rasi_sanscrito": SIGNOS_SANSCRITO[int(lon // 30)],
            "posicion": fmt(lon),
            "nakshatra": nk, "pada": pada, "regente_nakshatra": reg,
            "retrogrado": vals[3] < 0,
        }
    # Ketu
    rahu_l = vedico["grahas"]["Rahu"]["longitud_sideral"]
    ketu_l = (rahu_l + 180) % 360
    idx_n = int(ketu_l // (360 / 27))
    vedico["grahas"]["Ketu"] = {
        "longitud_sideral": round(ketu_l, 6), "rasi": SIGNOS[int(ketu_l // 30)],
        "rasi_sanscrito": SIGNOS_SANSCRITO[int(ketu_l // 30)], "posicion": fmt(ketu_l),
        "nakshatra": NAKSHATRAS[idx_n][0], "pada": int((ketu_l % (360 / 27)) // (360 / 108)) + 1,
        "regente_nakshatra": NAKSHATRAS[idx_n][1], "retrogrado": True,
    }
    # Lagna sideral
    asc_sid = (asc - ayan) % 360
    vedico["lagna"] = {"longitud_sideral": round(asc_sid, 6), "rasi": SIGNOS[int(asc_sid // 30)],
                       "rasi_sanscrito": SIGNOS_SANSCRITO[int(asc_sid // 30)],
                       "posicion": fmt(asc_sid),
                       "nakshatra": NAKSHATRAS[int(asc_sid // (360 / 27))][0]}
    # Bhavas (casas de signo completo desde el Lagna)
    lagna_idx = int(asc_sid // 30)
    for g in vedico["grahas"].values():
        g["bhava"] = ((SIGNOS.index(g["rasi"]) - lagna_idx) % 12) + 1

    # Vimshottari Dasha desde la Luna
    luna_sid = vedico["grahas"]["Luna"]["longitud_sideral"]
    idx_luna = int(luna_sid // (360 / 27))
    nk_luna, reg_luna, _ = NAKSHATRAS[idx_luna]
    frac_recorrida = (luna_sid % (360 / 27)) / (360 / 27)
    restante = ANIOS_DASHA[reg_luna] * (1 - frac_recorrida)
    secuencia = []
    start_idx = ORDEN_DASHA.index(reg_luna)
    edad = -ANIOS_DASHA[reg_luna] * frac_recorrida
    for k in range(10):
        pl = ORDEN_DASHA[(start_idx + k) % 9]
        dur = ANIOS_DASHA[pl]
        secuencia.append({
            "mahadasha": pl, "duracion_anios": dur,
            "edad_inicio": round(edad, 2), "edad_fin": round(edad + dur, 2),
            "anio_inicio": round(1990 + 0.02 + edad, 1), "anio_fin": round(1990 + 0.02 + edad + dur, 1),
        })
        edad += dur
    vedico["vimshottari_dasha"] = {
        "nakshatra_lunar_natal": nk_luna, "regente": reg_luna,
        "fraccion_recorrida_al_nacer": round(frac_recorrida, 4),
        "anios_restantes_de_la_primera_dasha": round(restante, 3),
        "secuencia": secuencia,
    }
    out["vedico"] = vedico
    swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)  # restaurar

    return out


if __name__ == "__main__":
    data = calcular()
    if "--pretty" in sys.argv:
        print(f"CARTA NATAL — {data['sujeto']['nombre']}")
        print(f"{data['tiempo']['local_iso']}  (UTC {data['tiempo']['utc_iso']})")
        print(f"Offset real: UTC{data['tiempo']['offset_utc_horas']:+.0f}  "
              f"DST activo: {data['tiempo']['horario_verano_activo']}\n")
        print(f"ASC {data['angulos']['Ascendente']['posicion']}   "
              f"MC {data['angulos']['Medio Cielo (MC)']['posicion']}\n")
        for n, p in data["planetas"].items():
            r = " R" if p["retrogrado"] else "  "
            print(f"  {n:<28} {p['posicion']:<24}{r}  casa {p['casa_placidus']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
