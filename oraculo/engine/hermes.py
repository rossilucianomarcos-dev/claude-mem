#!/usr/bin/env python3
"""
HERMES — Memoria ejecutiva del Oráculo Personal.

Obsidian guarda el CONOCIMIENTO (lo que es estable: carta natal, perfil,
patrones consolidados). Hermes guarda el ESTADO (lo que cambia: en qué
está trabajando Luciano ahora, qué decidió, qué quedó abierto).

Regla de oro del sistema: se CONSULTA Hermes antes de responder cualquier
consulta sustantiva, y se ACTUALIZA después. Un consejo que ignora el
contexto real es astrología de revista.

Estructura:
    objetivos      — metas activas, con horizonte y estado
    proyectos      — trabajos en curso
    prioridades    — el foco declarado de este período
    agenda         — reuniones y compromisos con fecha
    problemas      — asuntos abiertos sin resolver
    decisiones     — pendientes de tomar, y ya tomadas (con fundamento)
    restricciones  — límites reales: tiempo, dinero, energía, terceros
    oportunidades  — ventanas detectadas
    ideas          — capturas sin procesar
    aprendizajes   — lo que la experiencia enseñó
    contexto       — estado reciente en prosa breve

Uso:
    python3 hermes.py ver
    python3 hermes.py ver --seccion proyectos
    python3 hermes.py agregar --seccion objetivos --texto "..." --etiquetas trabajo,2026
    python3 hermes.py cerrar --seccion problemas --id 3 --nota "cómo se resolvió"
    python3 hermes.py contexto --texto "..."
    python3 hermes.py briefing
"""

import argparse
import json
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Cordoba")
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hermes"))
ARCHIVO = os.path.join(BASE, "hermes.json")

SECCIONES = ["objetivos", "proyectos", "prioridades", "agenda", "problemas",
             "decisiones", "restricciones", "oportunidades", "ideas", "aprendizajes"]

VACIO = {
    "meta": {
        "sujeto": "Luciano Marcos Rossi",
        "creado": None,
        "actualizado": None,
        "version": 1,
        "proposito": ("Memoria ejecutiva: estado actual, no conocimiento estable. "
                      "El conocimiento estable vive en el vault de Obsidian."),
    },
    "contexto_reciente": [],
    **{s: [] for s in SECCIONES},
}


def cargar():
    if not os.path.exists(ARCHIVO):
        d = json.loads(json.dumps(VACIO))
        d["meta"]["creado"] = datetime.now(TZ).isoformat()
        return d
    with open(ARCHIVO, encoding="utf-8") as f:
        d = json.load(f)
    for s in SECCIONES:
        d.setdefault(s, [])
    d.setdefault("contexto_reciente", [])
    return d


def guardar(d):
    os.makedirs(BASE, exist_ok=True)
    d["meta"]["actualizado"] = datetime.now(TZ).isoformat()
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def _siguiente_id(lista):
    return (max((x.get("id", 0) for x in lista), default=0)) + 1


def agregar(seccion, texto, etiquetas=None, vence=None, estado="activo",
            prioridad=None, fundamento=None):
    if seccion not in SECCIONES:
        raise SystemExit(f"Sección inválida. Opciones: {', '.join(SECCIONES)}")
    d = cargar()
    item = {
        "id": _siguiente_id(d[seccion]),
        "texto": texto,
        "creado": datetime.now(TZ).isoformat(),
        "estado": estado,
        "etiquetas": [e.strip() for e in (etiquetas or "").split(",") if e.strip()],
    }
    if vence:
        item["vence"] = vence
    if prioridad:
        item["prioridad"] = prioridad
    if fundamento:
        item["fundamento"] = fundamento
    d[seccion].append(item)
    guardar(d)
    return item


def cerrar(seccion, id_, nota=None, estado="cerrado"):
    d = cargar()
    for x in d.get(seccion, []):
        if x["id"] == id_:
            x["estado"] = estado
            x["cerrado"] = datetime.now(TZ).isoformat()
            if nota:
                x["nota_cierre"] = nota
            guardar(d)
            return x
    raise SystemExit(f"No existe el ítem {id_} en {seccion}.")


def contexto(texto, limite=12):
    d = cargar()
    d["contexto_reciente"].insert(0, {"fecha": datetime.now(TZ).isoformat(), "texto": texto})
    d["contexto_reciente"] = d["contexto_reciente"][:limite]
    guardar(d)
    return d["contexto_reciente"][0]


def briefing():
    """Lo que el oráculo debe leer ANTES de responder cualquier consulta."""
    d = cargar()
    hoy = date.today()
    activos = {s: [x for x in d[s] if x.get("estado") == "activo"] for s in SECCIONES}

    vencidos, proximos = [], []
    for s in SECCIONES:
        for x in activos[s]:
            if not x.get("vence"):
                continue
            try:
                v = date.fromisoformat(x["vence"])
            except ValueError:
                continue
            dias = (v - hoy).days
            reg = {"seccion": s, "id": x["id"], "texto": x["texto"],
                   "vence": x["vence"], "dias": dias}
            (vencidos if dias < 0 else proximos).append(reg)
    vencidos.sort(key=lambda x: x["dias"])
    proximos.sort(key=lambda x: x["dias"])

    esta_vacio = all(len(v) == 0 for v in activos.values())
    return {
        "generado": datetime.now(TZ).isoformat(),
        "esta_vacio": esta_vacio,
        "aviso": ("HERMES ESTÁ VACÍO. No hay contexto real cargado. Cualquier consejo "
                  "que se dé ahora es genérico por definición: el sistema no sabe en qué "
                  "está trabajando Luciano, qué decidió ni qué tiene pendiente. "
                  "Antes de dar recomendaciones estratégicas hay que cargar objetivos, "
                  "proyectos y problemas abiertos.") if esta_vacio else None,
        "conteos": {s: len(activos[s]) for s in SECCIONES},
        "prioridades": activos["prioridades"],
        "objetivos": activos["objetivos"],
        "proyectos": activos["proyectos"],
        "decisiones_pendientes": [x for x in activos["decisiones"]
                                  if x.get("estado") == "activo"],
        "problemas_abiertos": activos["problemas"],
        "restricciones": activos["restricciones"],
        "oportunidades": activos["oportunidades"],
        "compromisos_vencidos": vencidos,
        "compromisos_proximos": [p for p in proximos if p["dias"] <= 14],
        "aprendizajes_recientes": activos["aprendizajes"][-5:],
        "contexto_reciente": d["contexto_reciente"][:5],
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("ver")
    v.add_argument("--seccion")
    v.add_argument("--todos", action="store_true", help="incluir ítems cerrados")

    a = sub.add_parser("agregar")
    a.add_argument("--seccion", required=True)
    a.add_argument("--texto", required=True)
    a.add_argument("--etiquetas")
    a.add_argument("--vence", help="YYYY-MM-DD")
    a.add_argument("--prioridad", choices=["alta", "media", "baja"])
    a.add_argument("--fundamento")

    c = sub.add_parser("cerrar")
    c.add_argument("--seccion", required=True)
    c.add_argument("--id", type=int, required=True)
    c.add_argument("--nota")
    c.add_argument("--estado", default="cerrado")

    ct = sub.add_parser("contexto")
    ct.add_argument("--texto", required=True)

    sub.add_parser("briefing")

    args = ap.parse_args()
    if args.cmd == "ver":
        d = cargar()
        if args.seccion:
            items = d.get(args.seccion, [])
            r = items if args.todos else [x for x in items if x.get("estado") == "activo"]
        else:
            r = d
    elif args.cmd == "agregar":
        r = agregar(args.seccion, args.texto, args.etiquetas, args.vence,
                    prioridad=args.prioridad, fundamento=args.fundamento)
    elif args.cmd == "cerrar":
        r = cerrar(args.seccion, args.id, args.nota, args.estado)
    elif args.cmd == "contexto":
        r = contexto(args.texto)
    else:
        r = briefing()
    print(json.dumps(r, ensure_ascii=False, indent=2))
