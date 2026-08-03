#!/usr/bin/env python3
"""
Motor de numerología — Oráculo Personal.

Implementa los sistemas pitagórico y caldeo, más los ciclos personales
(año / mes / día). Todo lo que produce es ARITMÉTICA DETERMINISTA sobre
el nombre y la fecha: no hay nada astronómico ni empírico aquí. La
numerología es un sistema simbólico; este módulo solo garantiza que los
cálculos sean correctos y reproducibles dentro de las reglas de ese sistema.

Uso:
    python3 numerologia.py                    # perfil completo (JSON)
    python3 numerologia.py --fecha 2026-08-03 # ciclos para una fecha dada
"""

import argparse
import json
import unicodedata
from datetime import date

NOMBRE = "Luciano Marcos Rossi"
NACIMIENTO = date(1990, 1, 9)

MAESTROS = {11, 22, 33}
KARMICAS = {13, 14, 16, 19}

# Pitagórico: A=1 … I=9, J=1 … R=9, S=1 … Z=8
PITAGORICO = {c: (i % 9) + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}

# Caldeo: sin el 9 (considerado sagrado / no asignable a letras)
CALDEO = {}
for grupo, val in [("AIJQY", 1), ("BKR", 2), ("CGLS", 3), ("DMT", 4),
                   ("EHNX", 5), ("UVW", 6), ("OZ", 7), ("FP", 8)]:
    for c in grupo:
        CALDEO[c] = val

VOCALES = set("AEIOU")

SIGNIFICADOS = {
    1: "Iniciativa, liderazgo, independencia, comienzo.",
    2: "Cooperación, diplomacia, sensibilidad, mediación.",
    3: "Expresión, comunicación, creatividad, sociabilidad.",
    4: "Estructura, método, disciplina, construcción.",
    5: "Cambio, libertad, versatilidad, experiencia.",
    6: "Responsabilidad, servicio, hogar, armonía, estética.",
    7: "Análisis, introspección, investigación, escepticismo.",
    8: "Poder material, gestión, autoridad, resultados.",
    9: "Cierre, humanitarismo, visión amplia, desapego.",
    11: "MAESTRO. Intuición, inspiración, visibilidad, tensión nerviosa. Vibración de 2 elevada.",
    22: "MAESTRO. Constructor a gran escala, materializar visión. Vibración de 4 elevada.",
    33: "MAESTRO. Servicio y enseñanza a gran escala. Vibración de 6 elevada.",
}


def normalizar(texto):
    """Quita tildes y deja solo A-Z. Ñ -> N (convención hispana estándar)."""
    t = unicodedata.normalize("NFD", texto.upper())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c for c in t if c.isalpha() and c.isascii())


def reducir(n, conservar_maestros=True):
    """Reduce a un dígito, conservando números maestros si corresponde."""
    pasos = [n]
    while n > 9:
        if conservar_maestros and n in MAESTROS:
            break
        n = sum(int(d) for d in str(n))
        pasos.append(n)
    return n, pasos


def valor_nombre(nombre, tabla, filtro=None):
    letras = normalizar(nombre)
    if filtro == "vocales":
        letras = "".join(c for c in letras if c in VOCALES)
    elif filtro == "consonantes":
        letras = "".join(c for c in letras if c not in VOCALES)
    detalle = [(c, tabla[c]) for c in letras if c in tabla]
    bruto = sum(v for _, v in detalle)
    red, pasos = reducir(bruto)
    return {"letras": letras, "detalle": detalle, "suma_bruta": bruto,
            "reducido": red, "cadena_reduccion": pasos,
            "significado": SIGNIFICADOS.get(red, "")}


def perfil(nombre=NOMBRE, nac=NACIMIENTO):
    d, m, a = nac.day, nac.month, nac.year

    # --- Camino de vida: dos métodos, deben coincidir --------------------
    rd, _ = reducir(d)
    rm, _ = reducir(m)
    ra, _ = reducir(a)
    cv_metodo_periodos, pasos_p = reducir(rd + rm + ra)
    todos = sum(int(x) for x in f"{a:04d}{m:02d}{d:02d}")
    cv_metodo_total, pasos_t = reducir(todos)

    # --- Números núcleo ---------------------------------------------------
    expresion = valor_nombre(nombre, PITAGORICO)
    alma = valor_nombre(nombre, PITAGORICO, "vocales")
    personalidad = valor_nombre(nombre, PITAGORICO, "consonantes")
    caldeo_exp = valor_nombre(nombre, CALDEO)

    cumple_red, _ = reducir(d)
    madurez_bruto = cv_metodo_periodos + expresion["reducido"]
    madurez, _ = reducir(madurez_bruto)

    # --- Deudas kármicas --------------------------------------------------
    deudas = []
    for etiqueta, bruto in [("Camino de vida", rd + rm + ra), ("Expresión", expresion["suma_bruta"]),
                            ("Alma", alma["suma_bruta"]), ("Personalidad", personalidad["suma_bruta"]),
                            ("Día de nacimiento", d), ("Número de madurez", madurez_bruto)]:
        # Se evalúa el último paso de dos dígitos antes de reducir.
        n = bruto
        while n > 99:
            n = sum(int(x) for x in str(n))
        if n in KARMICAS:
            deudas.append({"origen": etiqueta, "numero": n})

    # --- Lecciones kármicas (dígitos ausentes en el nombre) ---------------
    presentes = {v for _, v in expresion["detalle"]}
    lecciones = sorted(set(range(1, 10)) - presentes)

    # --- Pináculos y desafíos --------------------------------------------
    p1, _ = reducir(rd + rm)
    p2, _ = reducir(rd + ra)
    p3, _ = reducir(p1 + p2)
    p4, _ = reducir(rm + ra)
    edad_fin_p1 = 36 - cv_metodo_periodos if cv_metodo_periodos not in MAESTROS else 36 - reducir(cv_metodo_periodos, False)[0]
    pinaculos = [
        {"pinaculo": 1, "numero": p1, "desde_edad": 0, "hasta_edad": edad_fin_p1},
        {"pinaculo": 2, "numero": p2, "desde_edad": edad_fin_p1 + 1, "hasta_edad": edad_fin_p1 + 9},
        {"pinaculo": 3, "numero": p3, "desde_edad": edad_fin_p1 + 10, "hasta_edad": edad_fin_p1 + 18},
        {"pinaculo": 4, "numero": p4, "desde_edad": edad_fin_p1 + 19, "hasta_edad": 120},
    ]
    d1 = abs(reducir(rd, False)[0] - reducir(rm, False)[0])
    d2 = abs(reducir(rd, False)[0] - reducir(ra, False)[0])
    d3 = abs(d1 - d2)
    d4 = abs(reducir(rm, False)[0] - reducir(ra, False)[0])
    desafios = [{"desafio": i + 1, "numero": v} for i, v in enumerate([d1, d2, d3, d4])]

    return {
        "nombre_analizado": nombre,
        "nombre_normalizado": normalizar(nombre),
        "fecha_nacimiento": nac.isoformat(),
        "sistema": "Pitagórico (principal) + Caldeo (contraste)",
        "camino_de_vida": {
            "numero": cv_metodo_periodos,
            "metodo_periodos": {"dia": rd, "mes": rm, "anio": ra, "suma": rd + rm + ra, "pasos": pasos_p},
            "metodo_suma_total": {"suma_digitos": todos, "resultado": cv_metodo_total, "pasos": pasos_t},
            "coinciden_ambos_metodos": cv_metodo_periodos == cv_metodo_total,
            "significado": SIGNIFICADOS.get(cv_metodo_periodos, ""),
            "es_maestro": cv_metodo_periodos in MAESTROS,
        },
        "expresion_destino": expresion,
        "impulso_del_alma": alma,
        "personalidad_externa": personalidad,
        "expresion_caldea": caldeo_exp,
        "numero_de_cumpleanios": {"numero": d, "reducido": cumple_red,
                                  "significado": SIGNIFICADOS.get(cumple_red, "")},
        "numero_de_madurez": {"numero": madurez, "calculo": f"{cv_metodo_periodos} + {expresion['reducido']} = {madurez_bruto}",
                              "significado": SIGNIFICADOS.get(madurez, ""),
                              "nota": "Se activa progresivamente desde ~35 años."},
        "deudas_karmicas": deudas or ["Ninguna deuda kármica detectada (13/14/16/19)."],
        "lecciones_karmicas": {"digitos_ausentes_en_el_nombre": lecciones,
                               "significados": {str(x): SIGNIFICADOS[x] for x in lecciones}},
        "pinaculos": pinaculos,
        "desafios": desafios,
    }


def ciclos(fecha, nac=NACIMIENTO, cv=None):
    """Año, mes y día personal para una fecha dada."""
    if cv is None:
        cv = perfil()["camino_de_vida"]["numero"]

    # Año personal: día + mes de nacimiento + año en curso.
    # Convención: el año personal cambia el 1 de enero (escuela occidental
    # mayoritaria). El cumpleaños marca su punto de máxima potencia.
    ay, _ = reducir(fecha.year)
    an_bruto = reducir(nac.day, False)[0] + reducir(nac.month, False)[0] + ay
    anio_personal, pasos_ap = reducir(an_bruto)
    anio_personal_simple = reducir(an_bruto, False)[0]

    mes_bruto = anio_personal_simple + fecha.month
    mes_personal, pasos_mp = reducir(mes_bruto)
    mes_personal_simple = reducir(mes_bruto, False)[0]

    dia_bruto = mes_personal_simple + fecha.day
    dia_personal, pasos_dp = reducir(dia_bruto)

    # Ciclo de 9 años: posición dentro de la epopeya
    posicion = anio_personal_simple
    fase = ("Siembra / iniciar" if posicion in (1, 2) else
            "Crecimiento / expandir" if posicion in (3, 4, 5) else
            "Consolidación / responsabilizarse" if posicion in (6, 7) else
            "Cosecha / capitalizar" if posicion == 8 else
            "Cierre / soltar y preparar el próximo ciclo")

    # Edad y semana personal
    edad = fecha.year - nac.year - ((fecha.month, fecha.day) < (nac.month, nac.day))

    return {
        "fecha": fecha.isoformat(),
        "edad": edad,
        "anio_personal": {"numero": anio_personal, "reducido_simple": anio_personal_simple,
                          "calculo": f"{nac.day}→{reducir(nac.day, False)[0]} + {nac.month} + {fecha.year}→{ay} = {an_bruto}",
                          "pasos": pasos_ap, "significado": SIGNIFICADOS.get(anio_personal, ""),
                          "fase_del_ciclo_de_9": fase},
        "mes_personal": {"numero": mes_personal,
                         "calculo": f"{anio_personal_simple} + {fecha.month} = {mes_bruto}",
                         "pasos": pasos_mp, "significado": SIGNIFICADOS.get(mes_personal, "")},
        "dia_personal": {"numero": dia_personal,
                         "calculo": f"{mes_personal_simple} + {fecha.day} = {dia_bruto}",
                         "pasos": pasos_dp, "significado": SIGNIFICADOS.get(dia_personal, "")},
        "camino_de_vida_de_referencia": cv,
        "nota_metodologica": ("El año personal se cuenta desde el 1 de enero. "
                             "Algunas escuelas lo cuentan desde el cumpleaños; "
                             "en el caso de Luciano (9 de enero) la diferencia es de 8 días."),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", help="YYYY-MM-DD para ciclos personales")
    ap.add_argument("--nombre", default=NOMBRE)
    args = ap.parse_args()

    p = perfil(args.nombre)
    salida = {"perfil": p}
    f = date.fromisoformat(args.fecha) if args.fecha else date.today()
    salida["ciclos"] = ciclos(f, cv=p["camino_de_vida"]["numero"])
    print(json.dumps(salida, ensure_ascii=False, indent=2))
