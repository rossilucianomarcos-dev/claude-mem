#!/usr/bin/env python3
"""
Registro de recomendaciones y MOTOR DE VALIDACIÓN — Oráculo Personal.

Este es el módulo que impide que el sistema se auto-engañe.

Principios de diseño (no negociables):

1. UNA RECOMENDACIÓN SIN CRITERIO DE FALSACIÓN NO SE REGISTRA COMO PREDICCIÓN.
   "Va a ser un día de cambios" no es evaluable. "Vas a cerrar el acuerdo X
   antes del viernes" sí lo es. Solo lo segundo entra al motor de validación.

2. LA TASA BASE MANDA. Si una disciplina "acierta" el 70% pero el evento
   ocurre el 70% de las veces igual, el aporte informativo es CERO. El
   sistema calcula skill sobre la tasa base, no aciertos brutos.

3. CON N PEQUEÑO NO SE REPESA NADA. Con 5 predicciones, la diferencia entre
   40% y 80% de acierto no es distinguible del azar. El sistema exige un
   mínimo y reporta intervalos de confianza, no porcentajes desnudos.

4. EL SESGO DE CONFIRMACIÓN SE MIDE. Se registra cuántas recomendaciones
   quedaron sin evaluar: si las no evaluadas son sistemáticamente las que
   fallaron, el porcentaje de acierto está inflado.

Uso:
    python3 registro.py agregar --disciplina astrologia --claim "..." \
        --confianza 0.6 --horizonte 7 --falsable
    python3 registro.py evaluar --id abc123 --resultado acierto --nota "..."
    python3 registro.py pendientes
    python3 registro.py validar
"""

import argparse
import json
import math
import os
import secrets
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Cordoba")
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
LEDGER = os.path.join(BASE, "registro.jsonl")
PESOS = os.path.join(BASE, "pesos_disciplinas.json")

N_MINIMO_PARA_REPESAR = 20      # por debajo de esto, no se toca el peso de nada
RESULTADOS = ["acierto", "fallo", "parcial", "no_evaluable", "pendiente"]

DISCIPLINAS = [
    "astrologia_transitos", "astrologia_natal", "astrologia_vedica", "bazi",
    "numerologia", "tarot", "iching", "runas", "cabala", "feng_shui",
    "ayurveda", "mtc", "psicologia_junguiana", "estoicismo", "filosofia",
    "analisis_racional",   # la línea de base: razonamiento sin sistema simbólico
]

PESOS_INICIALES = {d: 1.0 for d in DISCIPLINAS}


# ---------------------------------------------------------------------------
# ESTADÍSTICA
# ---------------------------------------------------------------------------

def wilson(exitos, n, z=1.96):
    """Intervalo de confianza de Wilson al 95%. Honesto con N pequeño."""
    if n == 0:
        return (0.0, 1.0)
    p = exitos / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def brier(predicciones):
    """Brier score: mide CALIBRACIÓN, no solo acierto.
    0 = perfecto, 0.25 = azar con confianza 0.5, 1 = máximamente equivocado
    y seguro de sí mismo. Penaliza la confianza alta en predicciones falsas."""
    if not predicciones:
        return None
    s = sum((conf - real) ** 2 for conf, real in predicciones)
    return s / len(predicciones)


def leer():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def escribir_entrada(e):
    os.makedirs(BASE, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")


def reescribir(entradas):
    """Solo para EVALUAR entradas existentes. El claim original nunca se edita."""
    os.makedirs(BASE, exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entradas:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, LEDGER)


# ---------------------------------------------------------------------------
# OPERACIONES
# ---------------------------------------------------------------------------

def agregar(disciplina, claim, confianza, horizonte_dias, falsable,
            fundamento=None, tasa_base=None, ambito=None):
    if disciplina not in DISCIPLINAS:
        raise SystemExit(f"Disciplina desconocida. Válidas: {', '.join(DISCIPLINAS)}")
    if not 0 <= confianza <= 1:
        raise SystemExit("La confianza debe estar entre 0 y 1.")
    hoy = datetime.now(TZ)
    e = {
        "id": secrets.token_hex(4),
        "creado": hoy.isoformat(),
        "disciplina": disciplina,
        "claim": claim,
        "fundamento": fundamento,
        "confianza": confianza,
        "falsable": bool(falsable),
        "ambito": ambito,
        "tasa_base_estimada": tasa_base,
        "horizonte_dias": horizonte_dias,
        "evaluable_desde": (hoy + timedelta(days=horizonte_dias)).date().isoformat(),
        "resultado": "pendiente",
        "evaluado_el": None,
        "nota_evaluacion": None,
    }
    if not falsable:
        e["advertencia"] = ("Marcada como NO falsable: se guarda como orientación, "
                            "pero NO entra al cálculo de precisión. Una afirmación "
                            "que no puede fallar tampoco puede acertar.")
    escribir_entrada(e)
    return e


def evaluar(id_, resultado, nota=None):
    if resultado not in RESULTADOS:
        raise SystemExit(f"Resultado inválido. Opciones: {', '.join(RESULTADOS)}")
    entradas = leer()
    hallada = None
    for e in entradas:
        if e["id"] == id_:
            if e["resultado"] != "pendiente":
                print(f"AVISO: la entrada {id_} ya estaba evaluada como "
                      f"'{e['resultado']}'. Se sobrescribe y se deja rastro.")
                e.setdefault("historial_evaluaciones", []).append({
                    "resultado_previo": e["resultado"], "nota_previa": e["nota_evaluacion"],
                    "cambiado_el": datetime.now(TZ).isoformat()})
            e["resultado"] = resultado
            e["evaluado_el"] = datetime.now(TZ).isoformat()
            e["nota_evaluacion"] = nota
            hallada = e
            break
    if not hallada:
        raise SystemExit(f"No existe la entrada {id_}.")
    reescribir(entradas)
    return hallada


def pendientes():
    hoy = date.today()
    out = {"vencidas": [], "en_curso": []}
    for e in leer():
        if e["resultado"] != "pendiente":
            continue
        venc = date.fromisoformat(e["evaluable_desde"])
        item = {"id": e["id"], "disciplina": e["disciplina"], "claim": e["claim"],
                "confianza": e["confianza"], "evaluable_desde": e["evaluable_desde"],
                "dias": (hoy - venc).days}
        (out["vencidas"] if venc <= hoy else out["en_curso"]).append(item)
    out["vencidas"].sort(key=lambda x: -x["dias"])
    return out


def validar():
    """El informe honesto: qué está aportando valor y qué no."""
    entradas = leer()
    evaluables = [e for e in entradas if e.get("falsable")]
    cerradas = [e for e in evaluables if e["resultado"] in ("acierto", "fallo", "parcial")]

    total = len(entradas)
    n_falsables = len(evaluables)
    n_cerradas = len(cerradas)
    n_pend = len([e for e in evaluables if e["resultado"] == "pendiente"])
    n_no_eval = len([e for e in evaluables if e["resultado"] == "no_evaluable"])

    informe = {
        "generado": datetime.now(TZ).isoformat(),
        "resumen": {
            "recomendaciones_totales": total,
            "falsables": n_falsables,
            "no_falsables": total - n_falsables,
            "cerradas_con_resultado": n_cerradas,
            "pendientes": n_pend,
            "declaradas_no_evaluables": n_no_eval,
        },
    }

    # --- Guardas de honestidad -------------------------------------------
    alertas = []
    if total == 0:
        informe["estado"] = "SIN DATOS"
        informe["mensaje"] = (
            "No hay ninguna recomendación registrada todavía. El motor de "
            "validación no puede decir nada. Cualquier afirmación sobre qué "
            "disciplina 'funciona mejor' en este momento sería inventada.")
        return informe

    if n_cerradas < N_MINIMO_PARA_REPESAR:
        alertas.append(
            f"N INSUFICIENTE: hay {n_cerradas} predicciones cerradas y se necesitan "
            f"al menos {N_MINIMO_PARA_REPESAR} para repesar disciplinas. Hasta "
            f"entonces todos los pesos quedan en 1.0. Los porcentajes de abajo son "
            f"descriptivos, no concluyentes.")

    if n_falsables and n_no_eval / max(n_falsables, 1) > 0.25:
        alertas.append(
            f"SESGO DE SUPERVIVENCIA: {n_no_eval} de {n_falsables} predicciones "
            f"falsables quedaron 'no evaluables'. Si las que se descartan son "
            f"sistemáticamente las que iban a fallar, la precisión está inflada.")

    if total and (total - n_falsables) / total > 0.5:
        alertas.append(
            f"EXCESO DE VAGUEDAD: más de la mitad de las recomendaciones "
            f"({total - n_falsables}/{total}) no son falsables. El sistema está "
            f"produciendo afirmaciones que no pueden equivocarse — y por lo tanto "
            f"tampoco informan.")

    # --- Por disciplina ---------------------------------------------------
    por_disc = defaultdict(lambda: {"acierto": 0, "fallo": 0, "parcial": 0,
                                    "pendiente": 0, "no_evaluable": 0, "pares": []})
    for e in evaluables:
        d = por_disc[e["disciplina"]]
        d[e["resultado"]] += 1
        if e["resultado"] in ("acierto", "fallo", "parcial"):
            real = 1.0 if e["resultado"] == "acierto" else 0.5 if e["resultado"] == "parcial" else 0.0
            d["pares"].append((e["confianza"], real))
            if e.get("tasa_base_estimada") is not None:
                d.setdefault("tasas_base", []).append(e["tasa_base_estimada"])

    detalle = {}
    for disc, d in por_disc.items():
        n = d["acierto"] + d["fallo"] + d["parcial"]
        if n == 0:
            detalle[disc] = {"n_cerradas": 0,
                             "veredicto": "Sin predicciones cerradas: no evaluable."}
            continue
        exitos = d["acierto"] + 0.5 * d["parcial"]
        tasa = exitos / n
        lo, hi = wilson(exitos, n)
        b = brier(d["pares"])
        tb = (sum(d["tasas_base"]) / len(d["tasas_base"])) if d.get("tasas_base") else None
        skill = (tasa - tb) if tb is not None else None

        if n < 10:
            veredicto = (f"N={n}: demasiado poco para concluir nada. El intervalo de "
                         f"confianza va de {lo:.0%} a {hi:.0%} — es tan ancho que "
                         f"incluye tanto 'inútil' como 'excelente'.")
        elif lo > 0.5 and (skill is None or skill > 0.05):
            veredicto = "Aporta valor por encima del azar de forma medible."
        elif hi < 0.5:
            veredicto = "Rinde por debajo del azar de forma medible. Reducir peso."
        else:
            veredicto = ("Indistinguible del azar con los datos actuales. "
                         "El intervalo cruza el 50%.")

        detalle[disc] = {
            "n_cerradas": n, "aciertos": d["acierto"], "fallos": d["fallo"],
            "parciales": d["parcial"], "pendientes": d["pendiente"],
            "no_evaluables": d["no_evaluable"],
            "tasa_de_acierto": round(tasa, 3),
            "ic95_wilson": [round(lo, 3), round(hi, 3)],
            "brier_score": round(b, 4) if b is not None else None,
            "brier_referencia": {"0.0": "perfecto", "0.25": "azar con confianza 50%",
                                 "1.0": "siempre equivocado y siempre seguro"},
            "tasa_base_media": round(tb, 3) if tb is not None else None,
            "skill_sobre_tasa_base": round(skill, 3) if skill is not None else
                                     "no calculable (faltan tasas base)",
            "veredicto": veredicto,
        }
    informe["por_disciplina"] = detalle

    # --- Calibración global ----------------------------------------------
    todos = [p for d in por_disc.values() for p in d["pares"]]
    if todos:
        informe["calibracion_global"] = {
            "n": len(todos),
            "brier_score": round(brier(todos), 4),
            "confianza_media_declarada": round(sum(c for c, _ in todos) / len(todos), 3),
            "tasa_de_acierto_real": round(sum(r for _, r in todos) / len(todos), 3),
        }
        cm = informe["calibracion_global"]["confianza_media_declarada"]
        tr = informe["calibracion_global"]["tasa_de_acierto_real"]
        if cm - tr > 0.15:
            alertas.append(
                f"EXCESO DE CONFIANZA: la confianza media declarada es {cm:.0%} pero "
                f"la tasa real de acierto es {tr:.0%}. El sistema se cree más certero "
                f"de lo que es. Bajar las confianzas declaradas.")
        elif tr - cm > 0.15:
            alertas.append(
                f"DEFECTO DE CONFIANZA: acierta {tr:.0%} pero solo declara {cm:.0%} "
                f"de confianza. Está siendo innecesariamente tibio.")

    # --- Pesos ------------------------------------------------------------
    pesos = PESOS_INICIALES.copy()
    if os.path.exists(PESOS):
        with open(PESOS, encoding="utf-8") as f:
            pesos.update(json.load(f).get("pesos", {}))

    if n_cerradas >= N_MINIMO_PARA_REPESAR:
        # Se parte de TODAS las disciplinas: las que no tienen datos conservan
        # su peso, no desaparecen del registro.
        nuevos = dict(pesos)
        for disc, d in detalle.items():
            if d.get("n_cerradas", 0) < 10:
                nuevos[disc] = pesos.get(disc, 1.0)
                continue
            lo = d["ic95_wilson"][0]
            hi = d["ic95_wilson"][1]
            actual = pesos.get(disc, 1.0)
            # Ajuste conservador: solo si el IC no cruza el 50%.
            if lo > 0.5:
                nuevos[disc] = round(min(2.0, actual * 1.15), 3)
            elif hi < 0.5:
                nuevos[disc] = round(max(0.2, actual * 0.85), 3)
            else:
                nuevos[disc] = actual
        informe["pesos_actualizados"] = nuevos
        with open(PESOS, "w", encoding="utf-8") as f:
            json.dump({"actualizado": datetime.now(TZ).isoformat(),
                       "n_cerradas_al_actualizar": n_cerradas,
                       "pesos": nuevos}, f, ensure_ascii=False, indent=2)
    else:
        informe["pesos_actualizados"] = pesos
        informe["nota_pesos"] = (
            f"Pesos sin cambios: se requieren {N_MINIMO_PARA_REPESAR} predicciones "
            f"cerradas y hay {n_cerradas}.")

    informe["alertas"] = alertas or ["Sin alertas metodológicas."]
    return informe


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("agregar")
    a.add_argument("--disciplina", required=True)
    a.add_argument("--claim", required=True)
    a.add_argument("--confianza", type=float, required=True)
    a.add_argument("--horizonte", type=int, default=7)
    a.add_argument("--falsable", action="store_true")
    a.add_argument("--fundamento")
    a.add_argument("--tasa-base", type=float)
    a.add_argument("--ambito")

    ev = sub.add_parser("evaluar")
    ev.add_argument("--id", required=True)
    ev.add_argument("--resultado", required=True)
    ev.add_argument("--nota")

    sub.add_parser("pendientes")
    sub.add_parser("validar")

    args = ap.parse_args()
    if args.cmd == "agregar":
        r = agregar(args.disciplina, args.claim, args.confianza, args.horizonte,
                    args.falsable, args.fundamento, args.tasa_base, args.ambito)
    elif args.cmd == "evaluar":
        r = evaluar(args.id, args.resultado, args.nota)
    elif args.cmd == "pendientes":
        r = pendientes()
    else:
        r = validar()
    print(json.dumps(r, ensure_ascii=False, indent=2))
