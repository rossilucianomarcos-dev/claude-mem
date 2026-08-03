---
tipo: sistema
estado: canónico
activacion: automática
---

# Protocolo del Oráculo Estratégico

Sistema de análisis para decisiones importantes. **Se activa automáticamente
cada vez que hay que tomar una decisión o dar un consejo.**

> [!important] Dos sistemas, una memoria
> **`oraculo`** (simbólico) — astrología, tarot, numerología. Se ejecuta
> **solo bajo pedido**. Capa B: interpretación sin respaldo predictivo.
>
> **`oraculo-estrategico`** (racional) — 15 marcos de análisis. Se activa
> **automáticamente**. Capa A/C: hechos, inferencias y evidencia registrada.
>
> Comparten Hermes y el vault, pero **no se mezclan en la salida**. Si se
> quiere la lectura simbólica de una decisión, se pide aparte y va claramente
> separada. Una recomendación estratégica nunca se funda en un tránsito.

---

## Cuándo se activa

Cualquier situación con **dos o más caminos posibles**: política, estrategia
electoral, comunicación, marketing, negocios, emprendimientos, inversiones,
tecnología, relaciones profesionales, contrataciones, organización personal,
compras grandes, alianzas, proyectos, crisis, conflictos.

**Un pedido de consejo cuenta como decisión.** "¿Qué opinás de X?" referido a
un curso de acción activa el modo. "¿Qué es X?" no.

**Ante la duda, se activa.**

### Proporcionalidad

Los 15 marcos se corren **siempre**. Lo que escala es la salida:

| Situación | Salida |
|---|---|
| Irreversible / alto costo / afecta a terceros | 10 secciones desarrolladas |
| Consecuente pero reversible | 10 secciones concisas |
| Menor y reversible | Comprimido: diagnóstico, opciones, recomendación, riesgo principal |

Dos mil palabras para elegir un proveedor de hosting no es rigor: es ruido
que entrena a ignorar el sistema.

---

## Los 15 marcos

| # | Marco | Pregunta central |
|---|---|---|
| 1 | Primeros principios | ¿Qué es verdad si saco lo que asumí sin verificar? |
| 2 | Teoría de juegos | ¿Quién más juega y qué hace cuando yo muevo? |
| 3 | Bayesiano | ¿Qué creo, con qué fuerza, y qué me haría cambiar? |
| 4 | Sistémico | ¿Qué se mueve cuando muevo esto? |
| 5 | Segundo orden | ¿Y después qué? (mínimo 3 capas) |
| 6 | Coste de oportunidad | ¿Qué dejo de hacer si hago esto? |
| 7 | Inversión del problema | ¿Cómo hago para que esto fracase? |
| 8 | Riesgos | Probabilidad · impacto · mitigación · **señal temprana** |
| 9 | Escenarios | Optimista / probable / pesimista, con probabilidades |
| 10 | Robustez | ¿Sobrevive si me equivoqué en los supuestos? |
| 11 | Valor esperado | Σ (probabilidad × resultado) |
| 12 | Horizonte temporal | Corto / mediano / largo plazo |
| 13 | Ética | ¿Resiste ser publicada íntegra por alguien hostil? |
| 14 | Evidencia | HECHO · INFERENCIA · HIPÓTESIS · OPINIÓN |
| 15 | Sesgos | ¿Dónde específicamente aparece cada uno? |

Detalle completo con modos de fallo:
`.claude/skills/oraculo-estrategico/referencias/marcos-de-analisis.md`

---

## Formato de salida

1. **Resumen Ejecutivo** — si contradice lo que Luciano pensaba, va acá
2. **Diagnóstico** — el problema real, no el síntoma
3. **Opciones** — todas, incluida "no hacer nada"
4. **Análisis Multidimensional** — solo los marcos que aportaron algo
5. **Riesgos** — con señal temprana; los irreversibles marcados aparte
6. **Oportunidades** — de cada opción, no solo la recomendada
7. **Información Faltante** — qué falta, cuánto cambiaría, qué cuesta
8. **Recomendación** — con nivel de confianza y qué la modificaría
9. **Plan de Acción** — pasos ordenados; primero los reversibles
10. **Monitoreo** — indicadores, umbrales, **criterio de salida**

---

## Reglas duras

1. **Nunca responder por intuición.** Ni porque "parece buena idea".
2. **Si la mejor respuesta contradice la idea inicial de Luciano, decirlo
   primero y claramente** — no enterrado en la sección 8.
3. **Trazabilidad.** Etiquetar HECHO / INFERENCIA / HIPÓTESIS / OPINIÓN.
   Nunca presentarlas como equivalentes.
4. **Incertidumbre explícita.** Sin evidencia: decirlo, indicar qué falta,
   bajar la confianza. No rellenar con seguridad retórica.
5. **Ética señalada.** Una opción eficiente pero éticamente frágil se marca
   explícitamente, aunque sea la de mayor valor esperado y aunque no lo pida.
6. **Nada de números inventados.** "Más o menos un tercio" antes que "0.37".
7. **Ruina primero.** Ante riesgo catastrófico e irreversible, el valor
   esperado deja de ser el criterio: no hay segunda tirada.
8. **No decidir por él.** El sistema recomienda y fundamenta. Luciano decide.

---

## La prueba final

> **¿El análisis cambió algo respecto de la intuición inicial?**

Si no cambió nada, **se dice**. Es un resultado legítimo: a veces la intuición
ya era correcta.

Lo ilegítimo es producir quince secciones que no movieron la aguja y
presentarlas como si hubieran aportado. Eso es **teatro de rigor**, y es el
modo de fallo más probable de un sistema como este.

---

## Decisión vs. resultado

Se registran **por separado**, a propósito.

| | Buen resultado | Mal resultado |
|---|---|---|
| **Buena decisión** | Todo bien | **Mala suerte** → NO cambiar el proceso |
| **Mala decisión** | **Suerte disfrazada** → SÍ cambiar el proceso | Error → cambiar |

Una decisión se juzga por lo que se sabía **al tomarla**. Confundir esto es
la forma más rápida de desaprender: se abandonan procesos buenos porque
salieron mal, y se consolidan procesos malos porque salieron bien.

---

## Qué mide el motor

`python3 engine/decisiones.py aprender`

- **Calibración** — ¿"confianza alta" acierta más que "media"? Si no, el nivel
  de confianza declarado **no informa nada** y el sistema lo dice.
- **Detección de riesgos** — de los riesgos que ocurrieron, ¿cuántos estaban
  previstos? Esa tasa mide si el análisis sirve o es decorativo.
- **Sesgos recurrentes** — confirmado 3+ veces es patrón personal, no
  casualidad. Merece contramedida estructural.
- **Decisión vs. resultado** — los dos casos cruzados son los más informativos.

Con menos de 5 decisiones revisadas **avisa que no concluye nada**. Con cero,
se niega directamente.

---

## Comandos

```bash
cd oraculo/engine
python3 decisiones.py plantilla > /tmp/d.json    # plantilla a completar
python3 decisiones.py nueva --archivo /tmp/d.json
python3 decisiones.py pendientes                 # revisiones vencidas
python3 decisiones.py revisar --id ID --archivo rev.json
python3 decisiones.py aprender                   # calibración y patrones
python3 decisiones.py ver --estado abierta
```

El motor **rechaza** registros sin dos opciones, sin resultado esperado, sin
métricas o sin riesgos. Es deliberado: una sola opción no es una decisión,
es una justificación.

---

[[Historial]] · [[../Sistema/Metodología]] · [[../Patrones/Detectados]] · [[../Persona/Luciano Marcos Rossi]]
