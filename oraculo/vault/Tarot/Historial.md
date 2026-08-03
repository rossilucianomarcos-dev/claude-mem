---
tipo: tarot
---

# Historial de Tiradas

**Registro automático: `data/sorteos_log.jsonl`.** Cada tirada se sella con
marca de tiempo *antes* de interpretarse — para que no se pueda ajustar la
lectura al resultado ya conocido.

```bash
python3 engine/sorteos.py tarot --tirada tres-cartas --pregunta "..."
```

Tiradas disponibles: `una-carta`, `tres-cartas`, `decision`, `cruz-celta`, `trabajo`.

## Cómo se usa acá

El tarot **no se usa para saber qué va a pasar.** Se usa como generador de
perspectivas: 78 imágenes arquetípicas que fuerzan a mirar un problema desde
un ángulo que uno no eligió. El valor está en lo que la carta hace pensar,
no en la carta.

Por eso la pregunta importa más que la tirada. "¿Qué va a pasar con X?" da
respuestas inútiles. "¿Qué no estoy viendo de X?" da respuestas útiles.

## Registro

| Fecha | Tirada | Pregunta | Cartas | Lectura | Resultado real |
|---|---|---|---|---|---|
| — | — | *(vacío)* | — | — | — |

[[../Sistema/Metodología]]
