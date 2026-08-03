---
tipo: predicciones
---

# Seguimiento de Predicciones

**Fuente de verdad: `data/registro.jsonl`.** Esta nota es la vista legible.

```bash
python3 engine/registro.py pendientes   # qué falta evaluar
python3 engine/registro.py validar      # informe de precisión
```

## Estado

**Sin predicciones registradas.** El motor de validación no puede decir nada
todavía, y correctamente se niega a hacerlo.

## Reglas

1. Solo entran predicciones **falsables**. "Semana de cambios" no cuenta.
2. Toda predicción declara **confianza** (0–1) y **horizonte** en días.
3. Toda predicción declara su **tasa base** estimada: ¿con qué frecuencia
   pasaría esto igual, sin ningún sistema?
4. **Si falló, falló.** No se reinterpreta. Esta regla es la que sostiene
   todo lo demás.
5. Se requieren **20 predicciones cerradas** antes de repesar ninguna
   disciplina, y **10 por disciplina** individual.

## Registro

| ID | Fecha | Disciplina | Predicción | Conf. | Tasa base | Vence | Resultado |
|---|---|---|---|---|---|---|---|
| — | — | — | *(vacío)* | — | — | — | — |

## Precisión por disciplina

*(se completa automáticamente al alcanzar N mínimo)*

| Disciplina | N | Acierto | IC 95% | Brier | Skill s/ base | Peso |
|---|---|---|---|---|---|---|
| — | 0 | — | — | — | — | 1.0 |

[[../Sistema/Metodología]] · [[../Patrones/Detectados]]
