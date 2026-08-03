# Oráculo Personal — Luciano Marcos Rossi

**Dos sistemas** con memoria compartida y validación empírica de sus propias
recomendaciones.

| Sistema | Qué es | Cuándo corre |
|---|---|---|
| **`oraculo`** | Simbólico: astrología (occidental, helenística, védica), numerología, BaZi, maya, tarot, I Ching, runas, cábala, feng shui, ayurveda | **Solo bajo pedido** |
| **`oraculo-estrategico`** | Racional: 15 marcos de análisis de decisiones | **Automático** ante toda decisión o consejo |

Comparten Hermes y el vault, pero **no se mezclan en la salida**. Una
recomendación estratégica nunca se funda en un tránsito planetario.

---

## La idea

La mayoría de los sistemas de este tipo tienen el mismo defecto: **no pueden
equivocarse**. Producen afirmaciones tan elásticas que siempre parecen
acertar, y nadie lleva registro.

Este está construido al revés. Cada recomendación falsable se sella con marca
de tiempo, confianza declarada y tasa base estimada, **antes** de conocerse el
resultado. Después se evalúa. Con datos suficientes, el sistema calcula qué
disciplinas aportan valor real por encima del azar y ajusta su peso — o
concluye que ninguna lo hace, si eso es lo que dicen los datos.

La disciplina `analisis_racional` está en la lista **como línea de base**. Si
ninguna disciplina simbólica la supera, el sistema debe decirlo.

---

## Instalación

```bash
cd oraculo && ./setup.sh
```

Instala `pyswisseph` y descarga las efemérides Swiss Ephemeris (~2 MB, no
versionadas). Verifica que el Ascendente calculado sea el correcto.

---

## Uso

```bash
cd oraculo/engine

# Simbólico (bajo pedido)
python3 informe.py --markdown          # dossier del día
python3 informe.py --completo          # + carta natal y tradiciones
python3 registro.py validar            # precisión medida hasta ahora
python3 sorteos.py iching --pregunta "..."

# Estratégico (activación automática)
python3 decisiones.py plantilla > /tmp/d.json
python3 decisiones.py nueva --archivo /tmp/d.json
python3 decisiones.py pendientes       # revisiones vencidas
python3 decisiones.py aprender         # calibración y sesgos recurrentes

# Compartido
python3 hermes.py briefing             # memoria ejecutiva
```

**El oráculo simbólico no genera informes diarios automáticos.** El modo
estratégico sí se activa solo, ante cualquier decisión o pedido de consejo.

---

## Arquitectura

```
oraculo/
├── engine/            # motores de cálculo (Python, deterministas)
│   ├── natal.py           carta natal — Swiss Ephemeris
│   ├── transitos.py       tránsitos, progresiones, retornos, ciclos
│   ├── numerologia.py     pitagórico + caldeo, ciclos personales
│   ├── tradiciones.py     BaZi, maya, celta, cábala, feng shui, ayurveda
│   ├── sorteos.py         tarot, I Ching, runas — con registro sellado
│   ├── registro.py        MOTOR DE VALIDACIÓN (predicciones simbólicas)
│   ├── decisiones.py      MOTOR DE DECISIONES (15 marcos, calibración)
│   ├── verificar_hora.py  auditoría de la hora de nacimiento
│   ├── hermes.py          memoria ejecutiva
│   └── informe.py         compositor de dossiers
├── vault/             # Obsidian — conocimiento estable, notas enlazadas
├── hermes/            # memoria ejecutiva (estado vivo)
├── data/              # salidas y registros
└── ephe/              # efemérides (no versionadas)
```

**Dos memorias, a propósito.** Obsidian guarda lo **estable** (carta natal,
perfil, patrones consolidados). Hermes guarda lo que **cambia** (proyectos
activos, decisiones pendientes, problemas abiertos). Confundirlas convierte
el vault en un log y a Hermes en un archivo muerto.

---

## Las tres capas

| Capa | Contenido | Estatus |
|---|---|---|
| **A · Verificable** | Posiciones planetarias, fases, eclipses, calendarios, aritmética | Correcto o es un bug |
| **B · Simbólica** | El significado atribuido a lo anterior | **Sin respaldo empírico predictivo.** Se marca siempre |
| **C · Empírica personal** | Lo registrado y verificado sobre Luciano | La que más pesa |

Los estudios controlados sobre astrología natal (Carlson 1985; Dean & Kelly
2003) no encontraron capacidad predictiva sobre el azar. El sistema no finge
lo contrario. Se usa igual porque **un vocabulario simbólico estructurado es
una herramienta de pensamiento útil**: obliga a mirar ángulos que uno no
miraría solo. Eso no requiere que la astrología sea verdadera.

---

## Tres correcciones técnicas que cambian el resultado

Errores frecuentes en calculadoras online, ya corregidos acá:

**1. Horario de verano argentino.** Argentina observó DST del 15-oct-1989 al
4-mar-1990. El 9-ene-1990 el offset real fue **UTC−2**, no UTC−3.

Usar UTC−3 desplazaría el Ascendente **12°34′**, movería el **Medio Cielo de
Libra a Escorpio** (cambiando el regente de la carrera de Venus a Marte/Plutón),
cambiaría de casa a **4 de 10 planetas** y eliminaría la conjunción
Venus–Ascendente, que es de apenas 11 minutos de arco.

Verificado contra tzdata IANA: `isdst=1`, `gmtoff=-7200` en esa fecha.

**2. Año BaZi.** Nacido antes de Lì Chūn (4-feb-1990), el año chino es
**1989 己巳 Serpiente de Tierra**, no 1990 Caballo de Metal.

**3. Hora solar.** BaZi y feng shui usan hora solar, no de reloj. En Santa Fe
(60.7° O) la diferencia es de **2h10m**: 08:24 de reloj = **06:14** solar. El
pilar de hora cambia de Dragón a Conejo.

---

## Motor de validación

```bash
python3 registro.py agregar --disciplina astrologia_transitos \
    --claim "afirmación específica y falsable" \
    --confianza 0.6 --horizonte 7 --falsable --tasa-base 0.4

python3 registro.py evaluar --id abc123 --resultado acierto
python3 registro.py validar
```

Reglas:

| Regla | Umbral |
|---|---|
| Mínimo para repesar disciplinas | 20 predicciones cerradas |
| Mínimo por disciplina | 10 cerradas |
| Subir peso | IC 95% de Wilson enteramente > 0.5 |
| Bajar peso | IC 95% enteramente < 0.5 |
| Ajuste por vez | ×1.15 / ×0.85 |
| Rango | 0.2 – 2.0 |

Usa **intervalo de Wilson** (un porcentaje con N pequeño engaña: 4 de 4
parece 100% pero su IC real va de 51% a 100%) y **Brier score** (mide
calibración: penaliza estar muy seguro y equivocarse).

Alerta automáticamente sobre: N insuficiente, sesgo de supervivencia
(predicciones descartadas como "no evaluables"), exceso de vaguedad
(demasiadas afirmaciones no falsables) y descalibración de confianza.

**Con cero datos, se niega a concluir nada.** Es el comportamiento correcto.

---

## Motor de decisiones

El modo estratégico registra cada decisión **antes** de conocerse el resultado
y la compara después. Sin eso, el sesgo retrospectivo hace que meses más tarde
uno crea que "ya sabía" lo que iba a pasar.

```bash
python3 decisiones.py aprender
```

Mide cuatro cosas que sin registro son imposibles de saber:

- **Calibración** — ¿"confianza alta" acierta más que "media"? Si no, el nivel
  de confianza declarado no informa nada, y el sistema lo dice.
- **Detección de riesgos** — de los riesgos que ocurrieron, ¿cuántos estaban
  en la lista previa? Esa tasa mide si el análisis sirve o es decorativo.
- **Sesgos recurrentes** — confirmado 3+ veces es patrón personal, no azar.
- **Decisión vs. resultado** — una buena decisión con mal resultado es mala
  suerte (no cambiar el proceso); una mala con buen resultado es suerte
  disfrazada (sí cambiarlo).

El motor **rechaza** registros con una sola opción, sin resultado esperado,
sin métricas o sin riesgos. Con menos de 5 decisiones revisadas avisa que no
concluye nada; con cero, se niega.

---

## Límites

No predice el futuro. No sustituye médico, abogado, contador ni terapeuta.
No diagnostica — ni por quiromancia, reflexología, MTC, ayurveda,
morfopsicología ni biomagnetismo.

El objetivo declarado es **pensar mejor**, no saber qué va a pasar.

---

## Documentación

- `vault/Sistema/Metodología.md` — reglas epistémicas completas
- `vault/Sistema/Índice.md` — mapa del vault
- `vault/Astrología/Carta Natal.md` — análisis natal completo
- `vault/Decisiones/Protocolo Estratégico.md` — los 15 marcos y el formato
- `skill/SKILL.md` · `skill/SKILL-estrategico.md` — protocolos del agente
- `skill/referencias/marcos-de-analisis.md` — marcos en detalle, con modos de fallo
