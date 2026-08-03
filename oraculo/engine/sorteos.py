#!/usr/bin/env python3
"""
Sistemas de sorteo — Tarot, I Ching y Runas.

DISEÑO CLAVE: todo sorteo se registra en un log append-only ANTES de ser
interpretado, con marca de tiempo y semilla. Esto existe por una razón
concreta: sin un registro previo e inmutable, es imposible distinguir una
interpretación honesta de una racionalización posterior. El motor de
validación (registro.py) depende de que esto sea así.

Aleatoriedad: se usa `secrets` (CSPRNG del sistema operativo). No se usa
una semilla derivada de la fecha ni del nombre: eso produciría resultados
"mágicamente coherentes" que en realidad son un artefacto del algoritmo.

Uso:
    python3 sorteos.py tarot --tirada tres-cartas --pregunta "..."
    python3 sorteos.py iching --pregunta "..."
    python3 sorteos.py runas --cantidad 3 --pregunta "..."
"""

import argparse
import json
import os
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Cordoba")
LOG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "data", "sorteos_log.jsonl"))

# --- TAROT -----------------------------------------------------------------
ARCANOS_MAYORES = [
    (0, "El Loco", "The Fool", "Le Mat"), (1, "El Mago", "The Magician", "Le Bateleur"),
    (2, "La Sacerdotisa", "High Priestess", "La Papesse"), (3, "La Emperatriz", "The Empress", "L'Impératrice"),
    (4, "El Emperador", "The Emperor", "L'Empereur"), (5, "El Hierofante", "The Hierophant", "Le Pape"),
    (6, "Los Enamorados", "The Lovers", "L'Amoureux"), (7, "El Carro", "The Chariot", "Le Chariot"),
    (8, "La Fuerza", "Strength", "La Force"), (9, "El Ermitaño", "The Hermit", "L'Hermite"),
    (10, "La Rueda de la Fortuna", "Wheel of Fortune", "La Roue de Fortune"),
    (11, "La Justicia", "Justice", "La Justice"), (12, "El Colgado", "The Hanged Man", "Le Pendu"),
    (13, "La Muerte", "Death", "L'Arcane sans nom"), (14, "La Templanza", "Temperance", "Tempérance"),
    (15, "El Diablo", "The Devil", "Le Diable"), (16, "La Torre", "The Tower", "La Maison Dieu"),
    (17, "La Estrella", "The Star", "L'Étoile"), (18, "La Luna", "The Moon", "La Lune"),
    (19, "El Sol", "The Sun", "Le Soleil"), (20, "El Juicio", "Judgement", "Le Jugement"),
    (21, "El Mundo", "The World", "Le Monde"),
]
PALOS = [("Bastos", "Fuego", "acción, voluntad, proyecto"),
         ("Copas", "Agua", "emoción, vínculo, valor personal"),
         ("Espadas", "Aire", "pensamiento, conflicto, verdad"),
         ("Oros", "Tierra", "materia, dinero, cuerpo, resultado")]
RANGOS = ["As", "Dos", "Tres", "Cuatro", "Cinco", "Seis", "Siete", "Ocho", "Nueve", "Diez",
          "Sota", "Caballo", "Reina", "Rey"]

TIRADAS = {
    "una-carta": ["Situación / consejo central"],
    "tres-cartas": ["Situación actual", "Acción / obstáculo", "Dirección probable"],
    "decision": ["Contexto real", "Si elijo A", "Si elijo B", "Lo que no estoy viendo",
                 "Criterio para decidir"],
    "cruz-celta": ["Situación", "Lo que cruza / desafía", "Fundamento (raíz)", "Pasado reciente",
                   "Meta consciente", "Futuro inmediato", "Cómo me posiciono", "Entorno / otros",
                   "Esperanzas y temores", "Desenlace probable"],
    "trabajo": ["Estado del proyecto", "Recurso disponible", "Fricción principal",
                "Acción con mejor retorno", "Riesgo a vigilar"],
}


def mazo_completo():
    cartas = [{"tipo": "Arcano Mayor", "numero": n, "nombre": es,
               "rider_waite": rw, "marsella": ma}
              for n, es, rw, ma in ARCANOS_MAYORES]
    for palo, elem, sentido in PALOS:
        for i, r in enumerate(RANGOS, start=1):
            cartas.append({"tipo": "Arcano Menor", "numero": i, "nombre": f"{r} de {palo}",
                           "palo": palo, "elemento": elem, "ambito": sentido})
    return cartas


def tirar_tarot(tipo="tres-cartas", pregunta=None, invertidas=True):
    if tipo not in TIRADAS:
        raise SystemExit(f"Tirada desconocida. Opciones: {', '.join(TIRADAS)}")
    posiciones = TIRADAS[tipo]
    mazo = mazo_completo()
    # Barajado Fisher-Yates con CSPRNG
    for i in range(len(mazo) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        mazo[i], mazo[j] = mazo[j], mazo[i]
    sacadas = []
    for k, pos in enumerate(posiciones):
        c = dict(mazo[k])
        c["posicion"] = pos
        c["invertida"] = bool(secrets.randbelow(2)) if invertidas else False
        sacadas.append(c)
    return {"sistema": "Tarot", "tirada": tipo, "pregunta": pregunta, "cartas": sacadas}


# --- I CHING ---------------------------------------------------------------
TRIGRAMAS = [("☷", "Kūn", "Tierra", "receptividad"), ("☳", "Zhèn", "Trueno", "movimiento"),
             ("☵", "Kǎn", "Agua", "peligro / abismo"), ("☱", "Duì", "Lago", "alegría"),
             ("☶", "Gèn", "Montaña", "quietud"), ("☲", "Lí", "Fuego", "adherencia / claridad"),
             ("☴", "Xùn", "Viento", "penetración suave"), ("☰", "Qián", "Cielo", "creatividad")]
# Orden de la tabla de King Wen: Qián, Duì, Lí, Zhèn, Xùn, Kǎn, Gèn, Kūn
ORDEN_KW = [7, 3, 5, 1, 6, 2, 4, 0]
TABLA_KW = [  # fila = trigrama INFERIOR, columna = trigrama SUPERIOR
    [1, 43, 14, 34, 9, 5, 26, 11],
    [10, 58, 38, 54, 61, 60, 41, 19],
    [13, 49, 30, 55, 37, 63, 22, 36],
    [25, 17, 21, 51, 42, 3, 27, 24],
    [44, 28, 50, 32, 57, 48, 18, 46],
    [6, 47, 64, 40, 59, 29, 4, 7],
    [33, 31, 56, 62, 53, 39, 52, 15],
    [12, 45, 35, 16, 20, 8, 23, 2],
]
HEXAGRAMAS = {
    1: ("乾 Qián", "Lo Creativo"), 2: ("坤 Kūn", "Lo Receptivo"), 3: ("屯 Zhūn", "La Dificultad Inicial"),
    4: ("蒙 Méng", "La Necedad Juvenil"), 5: ("需 Xū", "La Espera"), 6: ("訟 Sòng", "El Conflicto"),
    7: ("師 Shī", "El Ejército"), 8: ("比 Bǐ", "La Solidaridad"), 9: ("小畜", "La Fuerza Domesticadora de lo Pequeño"),
    10: ("履 Lǚ", "El Porte / El Pisar"), 11: ("泰 Tài", "La Paz"), 12: ("否 Pǐ", "El Estancamiento"),
    13: ("同人", "Comunidad con los Hombres"), 14: ("大有", "La Posesión de lo Grande"),
    15: ("謙 Qiān", "La Modestia"), 16: ("豫 Yù", "El Entusiasmo"), 17: ("隨 Suí", "El Seguimiento"),
    18: ("蠱 Gǔ", "El Trabajo en lo Echado a Perder"), 19: ("臨 Lín", "El Acercamiento"),
    20: ("觀 Guān", "La Contemplación"), 21: ("噬嗑", "La Mordedura Tajante"), 22: ("賁 Bì", "La Gracia"),
    23: ("剝 Bō", "La Desintegración"), 24: ("復 Fù", "El Retorno"), 25: ("無妄", "La Inocencia"),
    26: ("大畜", "La Fuerza Domesticadora de lo Grande"), 27: ("頤 Yí", "Las Comisuras / La Nutrición"),
    28: ("大過", "La Preponderancia de lo Grande"), 29: ("坎 Kǎn", "Lo Abismal"), 30: ("離 Lí", "Lo Adherente"),
    31: ("咸 Xián", "El Influjo"), 32: ("恆 Héng", "La Duración"), 33: ("遯 Dùn", "La Retirada"),
    34: ("大壯", "El Poder de lo Grande"), 35: ("晉 Jìn", "El Progreso"), 36: ("明夷", "El Oscurecimiento de la Luz"),
    37: ("家人", "El Clan / La Familia"), 38: ("睽 Kuí", "El Antagonismo"), 39: ("蹇 Jiǎn", "El Impedimento"),
    40: ("解 Xiè", "La Liberación"), 41: ("損 Sǔn", "La Merma"), 42: ("益 Yì", "El Aumento"),
    43: ("夬 Guài", "El Desbordamiento / La Resolución"), 44: ("姤 Gòu", "El Ir al Encuentro"),
    45: ("萃 Cuì", "La Reunión"), 46: ("升 Shēng", "La Subida"), 47: ("困 Kùn", "La Desazón / La Opresión"),
    48: ("井 Jǐng", "El Pozo"), 49: ("革 Gé", "La Revolución / La Muda"), 50: ("鼎 Dǐng", "El Caldero"),
    51: ("震 Zhèn", "Lo Suscitativo / La Conmoción"), 52: ("艮 Gèn", "El Aquietamiento"),
    53: ("漸 Jiàn", "El Desarrollo Gradual"), 54: ("歸妹", "La Muchacha que se Casa"),
    55: ("豐 Fēng", "La Plenitud"), 56: ("旅 Lǚ", "El Andariego"), 57: ("巽 Xùn", "Lo Suave / El Viento"),
    58: ("兌 Duì", "Lo Sereno / El Lago"), 59: ("渙 Huàn", "La Disolución"), 60: ("節 Jié", "La Restricción"),
    61: ("中孚", "La Verdad Interior"), 62: ("小過", "La Preponderancia de lo Pequeño"),
    63: ("既濟", "Después de la Consumación"), 64: ("未濟", "Antes de la Consumación"),
}


def _linea_yarrow():
    """Distribución real del método de las varillas de milenrama.
    old-yin 1/16, young-yang 5/16, young-yin 7/16, old-yang 3/16.
    NO es lo mismo que el método de las tres monedas (1/8, 3/8, 3/8, 1/8)."""
    r = secrets.randbelow(16)
    if r < 1:
        return 6
    if r < 6:
        return 7
    if r < 13:
        return 8
    return 9


def _linea_monedas():
    v = sum(2 if secrets.randbelow(2) else 3 for _ in range(3))
    return v


def _kingwen(lineas):
    """lineas: lista de 6 valores (6/7/8/9), de abajo hacia arriba."""
    bits = [1 if l in (7, 9) else 0 for l in lineas]
    inf = bits[0] + bits[1] * 2 + bits[2] * 4
    sup = bits[3] + bits[4] * 2 + bits[5] * 4
    return TABLA_KW[ORDEN_KW.index(inf)][ORDEN_KW.index(sup)]


def tirar_iching(pregunta=None, metodo="yarrow"):
    gen = _linea_yarrow if metodo == "yarrow" else _linea_monedas
    lineas = [gen() for _ in range(6)]
    mutantes = [i + 1 for i, l in enumerate(lineas) if l in (6, 9)]
    hex1 = _kingwen(lineas)
    lineas2 = [(7 if l == 6 else 8 if l == 9 else l) for l in lineas]
    hex2 = _kingwen(lineas2) if mutantes else None

    def describir(n):
        car, nom = HEXAGRAMAS[n]
        return {"numero": n, "chino": car, "nombre": nom}

    bits = [1 if l in (7, 9) else 0 for l in lineas]
    inf = bits[0] + bits[1] * 2 + bits[2] * 4
    sup = bits[3] + bits[4] * 2 + bits[5] * 4

    return {
        "sistema": "I Ching", "metodo": f"{metodo} (distribución tradicional)",
        "pregunta": pregunta,
        "lineas_abajo_arriba": lineas,
        "representacion": [("———" if l in (7, 9) else "— —") +
                           ("  ○ (muta)" if l == 9 else "  × (muta)" if l == 6 else "")
                           for l in reversed(lineas)],
        "trigrama_inferior": {"glifo": TRIGRAMAS[inf][0], "nombre": TRIGRAMAS[inf][1],
                              "imagen": TRIGRAMAS[inf][2], "atributo": TRIGRAMAS[inf][3]},
        "trigrama_superior": {"glifo": TRIGRAMAS[sup][0], "nombre": TRIGRAMAS[sup][1],
                              "imagen": TRIGRAMAS[sup][2], "atributo": TRIGRAMAS[sup][3]},
        "hexagrama_principal": describir(hex1),
        "lineas_mutantes": mutantes,
        "hexagrama_resultante": describir(hex2) if hex2 else None,
        "lectura_estructural": (
            "Sin líneas mutantes: la situación es estable; el hexagrama describe el estado."
            if not mutantes else
            f"{len(mutantes)} línea(s) mutante(s): la situación está en transición "
            f"de «{HEXAGRAMAS[hex1][1]}» hacia «{HEXAGRAMAS[hex2][1]}»."),
    }


# --- RUNAS -----------------------------------------------------------------
FUTHARK = [
    ("ᚠ", "Fehu", "Ganado / riqueza móvil", "Recurso que circula; lo que se tiene solo si se mueve"),
    ("ᚢ", "Uruz", "Uro / fuerza bruta", "Vitalidad no domesticada; salud, empuje"),
    ("ᚦ", "Thurisaz", "Gigante / espina", "Fuerza reactiva, conflicto, defensa; cuidado con la impulsividad"),
    ("ᚨ", "Ansuz", "Dios / boca", "Palabra, mensaje, autoridad comunicativa, enseñanza"),
    ("ᚱ", "Raidho", "Cabalgata / viaje", "Movimiento con dirección; ritmo correcto"),
    ("ᚲ", "Kenaz", "Antorcha", "Conocimiento técnico, artesanía, iluminar lo oscuro"),
    ("ᚷ", "Gebo", "Regalo", "Intercambio, reciprocidad, alianza, contrato"),
    ("ᚹ", "Wunjo", "Alegría", "Armonía lograda, satisfacción, pertenencia"),
    ("ᚺ", "Hagalaz", "Granizo", "Disrupción externa no elegida; lo que rompe para reordenar"),
    ("ᚾ", "Nauthiz", "Necesidad", "Restricción, carencia, la lección de la limitación"),
    ("ᛁ", "Isa", "Hielo", "Detención, congelamiento, paciencia forzada"),
    ("ᛃ", "Jera", "Año / cosecha", "Ciclo completado, resultado a su debido tiempo"),
    ("ᛇ", "Eihwaz", "Tejo", "Eje entre mundos, resistencia, transformación profunda"),
    ("ᛈ", "Perthro", "Cubilete / suerte", "Lo oculto, el azar, lo aún no revelado"),
    ("ᛉ", "Algiz", "Alce / protección", "Defensa, límite sano, conexión superior"),
    ("ᛊ", "Sowilo", "Sol", "Victoria, energía, claridad, éxito visible"),
    ("ᛏ", "Tiwaz", "Tyr / justicia", "Sacrificio por un principio, rectitud, liderazgo justo"),
    ("ᛒ", "Berkano", "Abedul", "Crecimiento, gestación, cuidado, comienzos fértiles"),
    ("ᛖ", "Ehwaz", "Caballo", "Asociación, progreso conjunto, confianza mutua"),
    ("ᛗ", "Mannaz", "Hombre", "El yo social, la comunidad, la condición humana"),
    ("ᛚ", "Laguz", "Agua / lago", "Intuición, flujo, inconsciente, adaptabilidad"),
    ("ᛜ", "Ingwaz", "Ing / semilla", "Potencial contenido a punto de liberarse; fertilidad"),
    ("ᛞ", "Dagaz", "Día / amanecer", "Avance repentino, claridad, punto de inflexión"),
    ("ᛟ", "Othala", "Herencia / hogar", "Patrimonio, raíces, lo que se recibe y se transmite"),
]
# Runas que no admiten inversión (simétricas)
NO_INVERTIBLES = {"Gebo", "Hagalaz", "Isa", "Jera", "Eihwaz", "Sowilo", "Ingwaz", "Dagaz"}


def tirar_runas(cantidad=3, pregunta=None):
    posiciones = {1: ["Consejo central"],
                  3: ["Situación / raíz", "Acción / desafío", "Resultado probable"],
                  5: ["Presente", "Obstáculo", "Recurso", "Consejo", "Desenlace"]}.get(
        cantidad, [f"Posición {i+1}" for i in range(cantidad)])
    idx = list(range(len(FUTHARK)))
    for i in range(len(idx) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    sacadas = []
    for k in range(cantidad):
        glifo, nombre, sentido_lit, sentido = FUTHARK[idx[k]]
        inv = (nombre not in NO_INVERTIBLES) and bool(secrets.randbelow(2))
        sacadas.append({"posicion": posiciones[k], "glifo": glifo, "nombre": nombre,
                        "significado_literal": sentido_lit, "campo_semantico": sentido,
                        "invertida": inv,
                        "nota_inversion": ("Runa simétrica: no admite inversión."
                                           if nombre in NO_INVERTIBLES else None)})
    return {"sistema": "Runas (Futhark Antiguo, 24)", "pregunta": pregunta, "runas": sacadas}


# --- REGISTRO --------------------------------------------------------------
def registrar(resultado):
    """Append-only. El sorteo queda sellado ANTES de interpretarse."""
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    entrada = {
        "timestamp": datetime.now(TZ).isoformat(),
        "id": secrets.token_hex(8),
        "resultado": resultado,
        "interpretacion": None,      # se completa después, nunca se edita el sorteo
        "resultado_real": None,      # para el motor de validación
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return entrada


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sorteos con registro auditable")
    ap.add_argument("sistema", choices=["tarot", "iching", "runas"])
    ap.add_argument("--tirada", default="tres-cartas", help=f"Tarot: {', '.join(TIRADAS)}")
    ap.add_argument("--pregunta")
    ap.add_argument("--cantidad", type=int, default=3)
    ap.add_argument("--metodo", default="yarrow", choices=["yarrow", "monedas"])
    ap.add_argument("--sin-registro", action="store_true")
    a = ap.parse_args()

    if a.sistema == "tarot":
        r = tirar_tarot(a.tirada, a.pregunta)
    elif a.sistema == "iching":
        r = tirar_iching(a.pregunta, a.metodo)
    else:
        r = tirar_runas(a.cantidad, a.pregunta)

    if not a.sin_registro:
        e = registrar(r)
        r["_registro"] = {"id": e["id"], "timestamp": e["timestamp"], "archivo": LOG}
    print(json.dumps(r, ensure_ascii=False, indent=2))
