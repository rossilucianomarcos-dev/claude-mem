#!/usr/bin/env python3
"""
MOTOR DE DECISIONES — Oráculo Estratégico.

Distinto del oráculo simbólico. Acá no hay astrología ni tarot: es registro y
evaluación de decisiones reales bajo marcos de análisis racional.

Por qué existe como motor y no solo como texto: una decisión analizada y no
registrada se pierde. Peor —se recuerda mal. El sesgo retrospectivo hace que,
meses después, uno crea que "ya sabía" lo que iba a pasar. La única defensa es
sellar el pronóstico ANTES de conocer el resultado.

Lo que este motor permite medir, y que sin registro es imposible:

  1. CALIBRACIÓN. ¿Cuando decís "confianza alta", acertás más que cuando decís
     "media"? Si no, la confianza declarada no informa nada.
  2. DETECCIÓN DE RIESGOS. De los riesgos que efectivamente se materializaron,
     ¿cuántos estaban en la lista previa? Esa tasa mide si el análisis sirve.
  3. SESGOS RECURRENTES. Si "costo hundido" aparece en 6 de 10 decisiones, eso
     es un patrón personal, no una casualidad.
  4. DECISIÓN vs RESULTADO. Una buena decisión puede salir mal y una mala puede
     salir bien. Se registran por separado a propósito.

Uso:
    python3 decisiones.py nueva --archivo decision.json
    python3 decisiones.py ver [--id ID] [--estado abierta]
    python3 decisiones.py revisar --id ID --archivo revision.json
    python3 decisiones.py pendientes
    python3 decisiones.py aprender
    python3 decisiones.py plantilla > decision.json
"""

import argparse
import json
import math
import os
import secrets
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Cordoba")
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
LEDGER = os.path.join(BASE, "decisiones.jsonl")

AMBITOS = ["politica", "estrategia_electoral", "comunicacion", "marketing", "negocios",
           "emprendimiento", "inversion", "tecnologia", "relaciones_profesionales",
           "contratacion", "organizacion_personal", "compra_grande", "alianza",
           "proyecto", "crisis", "conflicto", "otro"]

IMPACTOS = ["bajo", "medio", "alto", "catastrofico"]

MARCOS = ["primeros_principios", "teoria_de_juegos", "bayesiano", "sistemico",
          "segundo_orden", "coste_oportunidad", "inversion_del_problema",
          "analisis_de_riesgos", "escenarios", "robustez", "valor_esperado",
          "horizonte_temporal", "etica", "evidencia", "sesgos"]

SESGOS = ["confirmacion", "exceso_de_confianza", "anclaje", "disponibilidad",
          "costo_hundido", "aversion_a_la_perdida", "efecto_halo",
          "sesgo_retrospectivo", "sesgo_de_supervivencia", "planificacion_optimista"]


# ---------------------------------------------------------------------------
# ALMACENAMIENTO
# ---------------------------------------------------------------------------

def leer():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def reescribir(items):
    os.makedirs(BASE, exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    os.replace(tmp, LEDGER)


def agregar_linea(x):
    os.makedirs(BASE, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# PLANTILLA
# ---------------------------------------------------------------------------

PLANTILLA = {
    "titulo": "Título corto y concreto de la decisión",
    "ambito": "negocios",
    "diagnostico": "Cuál es el problema REAL que se intenta resolver (no el síntoma).",
    "reversible": True,
    "coste_de_revertir": "bajo | medio | alto | irreversible",
    "plazo_para_decidir": "YYYY-MM-DD o 'sin plazo'",
    "opciones": [
        {
            "nombre": "Opción A",
            "descripcion": "",
            "a_favor": [],
            "en_contra": [],
            "coste_oportunidad": "Qué se deja de ganar al elegir esta",
            "valor_esperado": "Cuantificado si es posible; si no, 'no cuantificable' y por qué",
        }
    ],
    "recomendada": "Opción A",
    "elegida": None,
    "argumentos_principales": [],
    "marcos_aplicados": ["primeros_principios", "teoria_de_juegos"],
    "escenarios": {
        "optimista": {"descripcion": "", "probabilidad": 0.2},
        "probable": {"descripcion": "", "probabilidad": 0.6},
        "pesimista": {"descripcion": "", "probabilidad": 0.2},
    },
    "riesgos": [
        {
            "descripcion": "",
            "probabilidad": 0.3,
            "impacto": "medio",
            "mitigacion": "",
            "senal_temprana": "Qué se vería PRIMERO si este riesgo empieza a ocurrir",
        }
    ],
    "sesgos_detectados": [
        {"sesgo": "confirmacion", "donde": "", "contramedida": ""}
    ],
    "informacion_faltante": [
        {"dato": "", "cuanto_cambiaria": "alto | medio | bajo",
         "como_conseguirlo": "", "coste_de_conseguirlo": ""}
    ],
    "consideraciones_eticas": {
        "impacto_humano": "", "legitimidad": "", "transparencia": "",
        "sostenibilidad": "", "reputacion": "",
        "alerta": None,
    },
    "confianza": 0.6,
    "que_cambiaria_la_recomendacion": [],
    "resultado_esperado": "Predicción concreta y verificable de qué va a pasar.",
    "metricas_exito": [
        {"metrica": "", "objetivo": "", "como_se_mide": ""}
    ],
    "horizonte_revision_dias": 90,
}


# ---------------------------------------------------------------------------
# OPERACIONES
# ---------------------------------------------------------------------------

def _validar(d):
    problemas = []
    if not d.get("titulo"):
        problemas.append("Falta 'titulo'.")
    if not d.get("diagnostico"):
        problemas.append("Falta 'diagnostico': sin definir el problema real, el análisis flota.")
    ops = d.get("opciones") or []
    if len(ops) < 2:
        problemas.append("Se requieren AL MENOS 2 opciones. Una sola opción no es una "
                         "decisión, es una justificación.")
    if not d.get("resultado_esperado"):
        problemas.append("Falta 'resultado_esperado'. Sin pronóstico no hay nada que "
                         "evaluar después — y toda la memoria del sistema depende de eso.")
    if not d.get("metricas_exito"):
        problemas.append("Falta 'metricas_exito'. Sin métricas, dentro de 3 meses la "
                         "evaluación va a ser una impresión, no una medición.")
    c = d.get("confianza")
    if c is None or not 0 <= c <= 1:
        problemas.append("'confianza' debe ser un número entre 0 y 1.")
    if not d.get("riesgos"):
        problemas.append("Falta 'riesgos'. Si no se ve ningún riesgo, el análisis está "
                         "incompleto, no la decisión libre de peligro.")
    amb = d.get("ambito")
    if amb and amb not in AMBITOS:
        problemas.append(f"'ambito' desconocido: {amb}. Válidos: {', '.join(AMBITOS)}")
    for r in d.get("riesgos", []):
        if r.get("impacto") and r["impacto"] not in IMPACTOS:
            problemas.append(f"Impacto inválido '{r['impacto']}'. Válidos: {', '.join(IMPACTOS)}")
    return problemas


def nueva(d):
    problemas = _validar(d)
    if problemas:
        raise SystemExit("La decisión no se registró:\n  - " + "\n  - ".join(problemas))
    hoy = datetime.now(TZ)
    dias = int(d.get("horizonte_revision_dias", 90))
    reg = dict(d)
    reg.update({
        "id": secrets.token_hex(4),
        "creado": hoy.isoformat(),
        "estado": "abierta",
        "revisar_desde": (hoy + timedelta(days=dias)).date().isoformat(),
        "revision": None,
    })
    # Sella los riesgos como estaban al decidir: no se editan después.
    for r in reg.get("riesgos", []):
        r.setdefault("materializado", None)
    agregar_linea(reg)
    return reg


def revisar(id_, rev):
    """Compara resultado esperado vs real. Es el momento en que el sistema aprende."""
    items = leer()
    obj = next((x for x in items if x["id"] == id_), None)
    if not obj:
        raise SystemExit(f"No existe la decisión {id_}.")
    if obj.get("revision"):
        print(f"AVISO: {id_} ya tenía revisión. Se conserva la anterior en 'revisiones_previas'.",
              file=sys.stderr)
        obj.setdefault("revisiones_previas", []).append(obj["revision"])

    riesgos_previos = len(obj.get("riesgos", []))
    materializados = rev.get("riesgos_materializados", [])   # índices de la lista original
    imprevistos = rev.get("riesgos_no_previstos", [])        # los que nadie vio venir

    for i, r in enumerate(obj.get("riesgos", [])):
        r["materializado"] = i in materializados

    total_ocurridos = len(materializados) + len(imprevistos)
    tasa_deteccion = (len(materializados) / total_ocurridos) if total_ocurridos else None

    obj["revision"] = {
        "fecha": datetime.now(TZ).isoformat(),
        "resultado_real": rev.get("resultado_real"),
        "coincide_con_lo_esperado": rev.get("coincide_con_lo_esperado"),  # 1.0 / 0.5 / 0.0
        "metricas_medidas": rev.get("metricas_medidas", []),
        "riesgos_materializados": materializados,
        "riesgos_no_previstos": imprevistos,
        "tasa_de_deteccion_de_riesgos": round(tasa_deteccion, 3) if tasa_deteccion is not None else None,
        "riesgos_previstos_total": riesgos_previos,
        "calidad_de_la_decision": rev.get("calidad_de_la_decision"),
        "calidad_del_resultado": rev.get("calidad_del_resultado"),
        "sesgos_confirmados": rev.get("sesgos_confirmados", []),
        "aprendizaje": rev.get("aprendizaje"),
        "haria_lo_mismo": rev.get("haria_lo_mismo"),
    }
    obj["estado"] = "revisada"
    reescribir(items)
    return obj


def pendientes():
    hoy = date.today()
    venc, curso = [], []
    for x in leer():
        if x.get("estado") == "revisada":
            continue
        try:
            v = date.fromisoformat(x["revisar_desde"])
        except (KeyError, ValueError):
            continue
        item = {"id": x["id"], "titulo": x["titulo"], "ambito": x.get("ambito"),
                "creado": x["creado"][:10], "revisar_desde": x["revisar_desde"],
                "dias": (hoy - v).days, "confianza_declarada": x.get("confianza"),
                "resultado_esperado": x.get("resultado_esperado"),
                "metricas": [m.get("metrica") for m in x.get("metricas_exito", [])]}
        (venc if v <= hoy else curso).append(item)
    venc.sort(key=lambda x: -x["dias"])
    curso.sort(key=lambda x: x["dias"])
    return {"vencidas": venc, "en_curso": curso}


def _wilson(exitos, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = exitos / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def aprender():
    """Extrae patrones del historial. Se niega a concluir sin datos suficientes."""
    items = leer()
    revisadas = [x for x in items if x.get("revision") and
                 x["revision"].get("coincide_con_lo_esperado") is not None]

    out = {
        "generado": datetime.now(TZ).isoformat(),
        "resumen": {
            "decisiones_registradas": len(items),
            "abiertas": len([x for x in items if x.get("estado") != "revisada"]),
            "revisadas": len(revisadas),
        },
    }

    if not items:
        out["estado"] = "SIN DATOS"
        out["mensaje"] = ("No hay decisiones registradas. El sistema no puede extraer "
                          "ningún patrón. Cualquier afirmación sobre 'cómo decide "
                          "Luciano' en este momento sería inventada.")
        return out

    if len(revisadas) < 5:
        out["advertencia"] = (
            f"Solo {len(revisadas)} decisiones revisadas. Los números de abajo son "
            f"descriptivos, no concluyentes. Se necesitan ~10 para empezar a "
            f"distinguir patrón de ruido, y ~20 para calibración confiable.")

    # --- Calibración de la confianza ------------------------------------
    if revisadas:
        pares = [(x["confianza"], x["revision"]["coincide_con_lo_esperado"]) for x in revisadas]
        brier = sum((c - r) ** 2 for c, r in pares) / len(pares)
        conf_media = sum(c for c, _ in pares) / len(pares)
        acierto_medio = sum(r for _, r in pares) / len(pares)

        # Calibración por tramos de confianza
        tramos = defaultdict(list)
        for c, r in pares:
            k = "baja (<0.5)" if c < 0.5 else "media (0.5-0.75)" if c < 0.75 else "alta (>=0.75)"
            tramos[k].append(r)
        por_tramo = {k: {"n": len(v), "acierto_real": round(sum(v) / len(v), 3)}
                     for k, v in tramos.items()}

        out["calibracion"] = {
            "n": len(pares),
            "brier_score": round(brier, 4),
            "confianza_media_declarada": round(conf_media, 3),
            "acierto_medio_real": round(acierto_medio, 3),
            "por_tramo_de_confianza": por_tramo,
            "interpretacion": (
                "Bien calibrado" if abs(conf_media - acierto_medio) <= 0.1 else
                "EXCESO DE CONFIANZA: declara más seguridad de la que los resultados "
                "justifican. Bajar las confianzas." if conf_media > acierto_medio else
                "DEFECTO DE CONFIANZA: acierta más de lo que declara. Está siendo "
                "innecesariamente tibio."),
        }
        if len(por_tramo) > 1:
            orden = ["baja (<0.5)", "media (0.5-0.75)", "alta (>=0.75)"]
            presentes = [t for t in orden if t in por_tramo]
            vals = [por_tramo[t]["acierto_real"] for t in presentes]
            monotono = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
            out["calibracion"]["confianza_discrimina"] = monotono
            out["calibracion"]["nota_discriminacion"] = (
                "La confianza declarada ordena bien los resultados: cuando dice 'alta' "
                "efectivamente acierta más." if monotono else
                "ATENCIÓN: la confianza declarada NO ordena los resultados. Decir "
                "'confianza alta' no predice mejor acierto que decir 'baja'. Mientras "
                "esto siga así, el nivel de confianza no aporta información.")

    # --- Detección de riesgos --------------------------------------------
    tasas = [x["revision"]["tasa_de_deteccion_de_riesgos"] for x in items
             if x.get("revision") and x["revision"].get("tasa_de_deteccion_de_riesgos") is not None]
    if tasas:
        media = sum(tasas) / len(tasas)
        out["deteccion_de_riesgos"] = {
            "n": len(tasas),
            "tasa_media": round(media, 3),
            "interpretacion": (
                f"De cada 10 riesgos que efectivamente ocurrieron, ~{media*10:.0f} "
                f"estaban identificados de antemano."),
            "riesgos_no_previstos_totales": sum(
                len(x["revision"].get("riesgos_no_previstos", [])) for x in items
                if x.get("revision")),
        }

    # --- Sesgos recurrentes ----------------------------------------------
    detectados = Counter()
    confirmados = Counter()
    for x in items:
        for s in x.get("sesgos_detectados", []):
            detectados[s.get("sesgo")] += 1
        if x.get("revision"):
            for s in x["revision"].get("sesgos_confirmados", []):
                confirmados[s] += 1
    if detectados or confirmados:
        out["sesgos"] = {
            "detectados_al_decidir": dict(detectados.most_common()),
            "confirmados_en_revision": dict(confirmados.most_common()),
            "recurrentes": [s for s, n in confirmados.items() if n >= 3],
            "nota": ("Un sesgo confirmado 3+ veces es un patrón personal, no una "
                     "casualidad. Merece una contramedida estructural, no atención "
                     "puntual."),
        }

    # --- Decisión vs resultado -------------------------------------------
    pares_dr = [(x["revision"].get("calidad_de_la_decision"),
                 x["revision"].get("calidad_del_resultado"))
                for x in items if x.get("revision")]
    pares_dr = [(d, r) for d, r in pares_dr if d is not None and r is not None]
    if pares_dr:
        buenas_mal = len([1 for d, r in pares_dr if d >= 0.6 and r < 0.4])
        malas_bien = len([1 for d, r in pares_dr if d < 0.4 and r >= 0.6])
        out["decision_vs_resultado"] = {
            "n": len(pares_dr),
            "buena_decision_mal_resultado": buenas_mal,
            "mala_decision_buen_resultado": malas_bien,
            "nota": ("Estos dos casos son los más informativos. Una buena decisión con "
                     "mal resultado es mala suerte, no error: NO cambiar el proceso. "
                     "Una mala decisión con buen resultado es suerte disfrazada de "
                     "acierto: SÍ cambiar el proceso, aunque haya salido bien."),
        }

    # --- Por ámbito -------------------------------------------------------
    por_ambito = defaultdict(lambda: {"n": 0, "revisadas": 0, "aciertos": 0.0})
    for x in items:
        a = por_ambito[x.get("ambito", "otro")]
        a["n"] += 1
        if x.get("revision") and x["revision"].get("coincide_con_lo_esperado") is not None:
            a["revisadas"] += 1
            a["aciertos"] += x["revision"]["coincide_con_lo_esperado"]
    out["por_ambito"] = {}
    for k, v in sorted(por_ambito.items(), key=lambda kv: -kv[1]["n"]):
        e = {"decisiones": v["n"], "revisadas": v["revisadas"]}
        if v["revisadas"] >= 3:
            t = v["aciertos"] / v["revisadas"]
            lo, hi = _wilson(v["aciertos"], v["revisadas"])
            e.update({"tasa_de_acierto": round(t, 3), "ic95": [round(lo, 3), round(hi, 3)]})
        elif v["revisadas"]:
            e["nota"] = "menos de 3 revisadas: no se calcula tasa"
        out["por_ambito"][k] = e

    # --- Aprendizajes textuales ------------------------------------------
    out["aprendizajes"] = [
        {"id": x["id"], "titulo": x["titulo"], "fecha": x["revision"]["fecha"][:10],
         "aprendizaje": x["revision"]["aprendizaje"]}
        for x in items if x.get("revision") and x["revision"].get("aprendizaje")
    ]

    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cargar(ruta):
    if ruta == "-":
        return json.load(sys.stdin)
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Motor de decisiones estratégicas")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("nueva"); n.add_argument("--archivo", required=True)
    v = sub.add_parser("ver")
    v.add_argument("--id"); v.add_argument("--estado")
    r = sub.add_parser("revisar")
    r.add_argument("--id", required=True); r.add_argument("--archivo", required=True)
    sub.add_parser("pendientes")
    sub.add_parser("aprender")
    sub.add_parser("plantilla")
    sub.add_parser("marcos")

    a = ap.parse_args()
    if a.cmd == "nueva":
        res = nueva(_cargar(a.archivo))
    elif a.cmd == "revisar":
        res = revisar(a.id, _cargar(a.archivo))
    elif a.cmd == "pendientes":
        res = pendientes()
    elif a.cmd == "aprender":
        res = aprender()
    elif a.cmd == "plantilla":
        res = PLANTILLA
    elif a.cmd == "marcos":
        res = {"marcos": MARCOS, "sesgos": SESGOS, "ambitos": AMBITOS, "impactos": IMPACTOS}
    else:
        items = leer()
        if a.id:
            res = next((x for x in items if x["id"] == a.id), None) or f"No existe {a.id}"
        elif a.estado:
            res = [x for x in items if x.get("estado") == a.estado]
        else:
            res = [{"id": x["id"], "titulo": x["titulo"], "ambito": x.get("ambito"),
                    "estado": x.get("estado"), "creado": x["creado"][:10],
                    "confianza": x.get("confianza"), "revisar_desde": x.get("revisar_desde")}
                   for x in items]
    print(json.dumps(res, ensure_ascii=False, indent=2))
