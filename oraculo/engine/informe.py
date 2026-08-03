#!/usr/bin/env python3
"""
Compositor de informes — Oráculo Personal.

Reúne en una sola salida todo lo que el oráculo necesita para responder:
capa astronómica verificable, capa simbólica, memoria ejecutiva (Hermes)
y estado del motor de validación.

NO interpreta. Produce el dossier de datos sobre el que se interpreta.
La separación es deliberada: los números los hace el código, la lectura
la hace el modelo, y el lector siempre puede ver de dónde salió cada cosa.

IMPORTANTE: este informe NO se genera automáticamente cada día. Se ejecuta
solo cuando Luciano lo pide explícitamente. Es una decisión suya.

Uso:
    python3 informe.py                          # dossier para hoy
    python3 informe.py --fecha 2026-08-03
    python3 informe.py --completo                # + carta natal y tradiciones
    python3 informe.py --markdown                # salida legible
"""

import argparse
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import hermes
import natal as natal_mod
import numerologia
import registro
import tradiciones
import transitos

TZ = ZoneInfo("America/Argentina/Cordoba")


def construir(fecha=None, completo=False):
    f = date.fromisoformat(fecha) if fecha else datetime.now(TZ).date()

    n = natal_mod.calcular()
    t = transitos.informe(f.isoformat(), incluir_ciclos=True)
    perf = numerologia.perfil()
    cic = numerologia.ciclos(f, cv=perf["camino_de_vida"]["numero"])
    brief = hermes.briefing()
    val = registro.validar()
    pend = registro.pendientes()

    # --- Tránsitos que realmente importan hoy ---------------------------
    estructurales = [x for x in t["transitos_a_natal"]
                     if x["peso"] == "estructural" and x["orbe"] <= 2.0]
    coyunturales = [x for x in t["transitos_a_natal"]
                    if x["peso"] == "coyuntural" and x["orbe"] <= 1.5]

    dossier = {
        "cabecera": {
            "sujeto": n["sujeto"]["nombre"],
            "fecha_del_informe": f.isoformat(),
            "generado": datetime.now(TZ).isoformat(),
            "edad": t["ciclos_de_vida"]["edad_exacta_anios"],
            "advertencia_de_lectura": (
                "Este dossier mezcla DOS tipos de información y hay que leerlas "
                "distinto. (A) La capa astronómica —posiciones planetarias, fases "
                "lunares, eclipses, retrogradaciones— es verificable contra "
                "cualquier efeméride y es correcta. (B) Todo lo demás —el "
                "significado atribuido a esas posiciones, la numerología, el "
                "tarot, el I Ching— pertenece a sistemas simbólicos cuya validez "
                "predictiva no está demostrada. Sirven para estructurar la "
                "reflexión, no para saber qué va a pasar."),
        },

        "capa_A_astronomica_verificable": {
            "fase_lunar": t["fase_lunar"],
            "posiciones_actuales": {k: v["posicion"] + (" R" if v["retrogrado"] else "")
                                    for k, v in t["cielo_actual"].items()},
            "proximas_lunaciones": t["proximas_lunaciones"],
            "estaciones_planetarias_proximos_180_dias": t["estaciones_planetarias_180d"],
        },

        "capa_B_simbolica": {
            "advertencia": "Interpretación, no hecho. Ver advertencia de cabecera.",
            "astrologia": {
                "transitos_estructurales_activos": estructurales,
                "transitos_coyunturales_del_dia": coyunturales,
                "progresiones": {
                    "sol_progresado": t["progresiones"]["planetas_progresados"]["Sol"]["posicion"],
                    "luna_progresada": t["progresiones"]["planetas_progresados"]["Luna"]["posicion"],
                    "ascendente_progresado": t["progresiones"]["ascendente_progresado"]["posicion"],
                    "fase_lunar_progresada": t["progresiones"]["fase_lunar_progresada"],
                },
                "retorno_solar_vigente": {
                    k: v for k, v in t["retorno_solar_vigente"].items() if k != "planetas"},
                "ciclos_de_vida": {
                    "proximos_retornos": [r for r in t["ciclos_de_vida"]["retornos"]
                                          if r["estado"] == "futuro"][:3],
                    "ultimos_retornos": [r for r in t["ciclos_de_vida"]["retornos"]
                                         if r["estado"] == "pasado"][-3:],
                    "proximos_hitos": [h for h in t["ciclos_de_vida"]["hitos"]
                                       if h["estado"] == "futuro"][:3],
                },
            },
            "numerologia": {
                "camino_de_vida": perf["camino_de_vida"]["numero"],
                "expresion": perf["expresion_destino"]["reducido"],
                "anio_personal": cic["anio_personal"],
                "mes_personal": cic["mes_personal"],
                "dia_personal": cic["dia_personal"],
            },
        },

        "capa_C_memoria_ejecutiva_hermes": brief,

        "capa_D_estado_del_aprendizaje": {
            "validacion": val,
            "predicciones_vencidas_sin_evaluar": pend["vencidas"],
            "predicciones_en_curso": pend["en_curso"],
            "instruccion": (
                "Si hay predicciones vencidas sin evaluar, PREGUNTAR por ellas antes "
                "de emitir nuevas. Un sistema que predice y nunca verifica no aprende: "
                "solo acumula la ilusión de haber acertado."),
        },
    }

    if completo:
        dossier["anexo_carta_natal"] = n
        dossier["anexo_tradiciones"] = tradiciones.todo()
        dossier["anexo_numerologia_completa"] = perf

    return dossier


def a_markdown(d):
    L = []
    c = d["cabecera"]
    L.append(f"# Dossier — {c['sujeto']}")
    L.append(f"**Fecha:** {c['fecha_del_informe']} · **Edad:** {c['edad']} años")
    L.append(f"\n> {c['advertencia_de_lectura']}\n")

    a = d["capa_A_astronomica_verificable"]
    L.append("## A. Cielo real (verificable)")
    fl = a["fase_lunar"]
    L.append(f"- **Luna:** {fl['fase']} · {fl['iluminacion_pct']}% iluminada · "
             f"{fl['posicion_luna']} · día {fl['edad_lunacion_dias']} del ciclo")
    L.append(f"- **Sol:** {fl['posicion_sol']}")
    L.append("- **Posiciones:** " + " · ".join(
        f"{k} {v}" for k, v in list(a["posiciones_actuales"].items())[:10]))
    L.append("\n**Próximas lunaciones**")
    for e in a["proximas_lunaciones"]:
        L.append(f"- {e['evento']}: {e['local'][:16].replace('T',' ')} en {e['grado']}")
    if a["estaciones_planetarias_proximos_180_dias"]:
        L.append("\n**Cambios de dirección planetaria (180 días)**")
        for e in a["estaciones_planetarias_proximos_180_dias"][:8]:
            L.append(f"- {e['local'][:10]} · {e['planeta']} · {e['evento']} en {e['grado']}")

    b = d["capa_B_simbolica"]
    L.append("\n## B. Capa simbólica *(interpretación, no hecho)*")
    L.append("\n### Tránsitos estructurales activos")
    if b["astrologia"]["transitos_estructurales_activos"]:
        for x in b["astrologia"]["transitos_estructurales_activos"]:
            r = " ℞" if x["retrogrado"] else ""
            L.append(f"- **{x['transito']}{r} {x['aspecto'].lower()} {x['natal']} natal** "
                     f"— orbe {x['orbe']}° ({x['naturaleza']})")
    else:
        L.append("- Ninguno dentro de 2° de orbe.")
    nu = b["numerologia"]
    L.append(f"\n### Numerología")
    L.append(f"- Camino de vida **{nu['camino_de_vida']}** · Expresión **{nu['expresion']}**")
    L.append(f"- Año personal **{nu['anio_personal']['numero']}** — {nu['anio_personal']['fase_del_ciclo_de_9']}")
    L.append(f"- Mes personal **{nu['mes_personal']['numero']}** · Día personal **{nu['dia_personal']['numero']}**")

    h = d["capa_C_memoria_ejecutiva_hermes"]
    L.append("\n## C. Hermes — contexto real")
    if h["esta_vacio"]:
        L.append(f"> ⚠️ {h['aviso']}")
    else:
        for k in ["prioridades", "objetivos", "proyectos", "problemas_abiertos",
                  "decisiones_pendientes"]:
            if h.get(k):
                L.append(f"\n**{k.replace('_',' ').capitalize()}**")
                for x in h[k]:
                    L.append(f"- [{x['id']}] {x['texto']}")
        if h["compromisos_vencidos"]:
            L.append("\n**⚠️ Vencidos**")
            for x in h["compromisos_vencidos"]:
                L.append(f"- {x['texto']} (hace {abs(x['dias'])} días)")

    v = d["capa_D_estado_del_aprendizaje"]["validacion"]
    L.append("\n## D. Estado del aprendizaje")
    if v.get("estado") == "SIN DATOS":
        L.append(f"> {v['mensaje']}")
    else:
        L.append(f"- Registradas: {v['resumen']['recomendaciones_totales']} · "
                 f"cerradas: {v['resumen']['cerradas_con_resultado']}")
        for al in v.get("alertas", []):
            L.append(f"- {al}")
    if d["capa_D_estado_del_aprendizaje"]["predicciones_vencidas_sin_evaluar"]:
        L.append("\n**Pendientes de evaluar (preguntar por estas)**")
        for x in d["capa_D_estado_del_aprendizaje"]["predicciones_vencidas_sin_evaluar"]:
            L.append(f"- `{x['id']}` {x['claim']} (vencida hace {x['dias']} días)")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--completo", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    d = construir(args.fecha, args.completo)
    print(a_markdown(d) if args.markdown else json.dumps(d, ensure_ascii=False, indent=2))
