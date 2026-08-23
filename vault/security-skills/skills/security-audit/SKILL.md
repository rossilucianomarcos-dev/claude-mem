---
name: security-audit
description: >
  Auditoría de seguridad de este proyecto usando la librería de skills de
  ciberseguridad vendorizada en vault/security-skills/. Úsala cuando se pida
  una revisión, auditoría o análisis de seguridad del proyecto o de una parte
  de él ("revisá la seguridad de X", "auditá el server", "¿esto es seguro?",
  "buscá vulnerabilidades", "/security-audit"). Cubre superficie completa o un
  área acotada. Para revisar solo el diff pendiente de la branch, usá la skill
  security-review incorporada en su lugar.
version: 1.0.0
license: Apache-2.0
---

# Auditoría de seguridad del proyecto

Orquesta las 24 skills de ciberseguridad vendorizadas en
`vault/security-skills/skills/` contra la superficie real de este repo.

## Cuándo usarla

- "hacé una revisión de seguridad del proyecto" → auditoría completa
- "auditá la seguridad del server" / "de la ingesta" → auditoría acotada
- "¿es seguro exponer X?" → auditoría acotada + modelado de amenazas

**No la uses** para revisar únicamente los cambios sin commitear de la branch:
para eso está la skill `security-review` incorporada, que es más rápida y
específica. Si el pedido es ambiguo, preguntá si quiere *todo el proyecto* o
*el diff*.

## Alcance por defecto

Si no se aclara, auditá estas cinco superficies en este orden. El orden importa:
las primeras dos son específicas de un plugin de memoria para agentes y son
donde vive el riesgo que un SAST genérico no ve.

### 1. Ingesta de contenido no confiable (prioridad máxima)

claude-mem lee transcripts de Claude Code y comprime output de herramientas.
Ese contenido es **no confiable**: viene de archivos leídos, respuestas HTTP,
salidas de comandos. Si termina en memoria y se reinyecta en sesiones futuras,
una prompt injection persiste entre sesiones.

- `detecting-indirect-prompt-injection` — el vector principal
- `testing-prompt-injection-in-rag-pipelines` — recuperación e inyección de contexto
- `detecting-data-and-model-poisoning` — envenenamiento persistente de la memoria
- `implementing-llm-guardrails-for-security` — mitigaciones

Preguntas guía: ¿se distingue el contenido citado del texto de instrucción al
comprimir? ¿Un observation almacenado puede alterar el comportamiento de una
sesión posterior? ¿Hay límites de longitud y saneamiento antes de persistir?

### 2. Superficie MCP y de herramientas

El proyecto expone un server MCP (`src/server/mcp/`, `src/servers/`).

- `auditing-mcp-servers-for-tool-poisoning` — descripciones de tools como vector
- `securing-agentic-ai-tool-invocation` — validación de argumentos, autorización

Preguntas guía: ¿las descripciones de las tools se construyen con datos
almacenados? ¿Se validan los argumentos contra un schema antes de ejecutar?

### 3. Server, API y almacenamiento

`src/server/` (auth, middleware, routes, queue), SQLite en `~/.claude-mem/`,
Chroma en `~/.claude-mem/chroma/`.

- `conducting-api-security-testing` — authz por endpoint, rate limiting
- `exploiting-sql-injection-vulnerabilities` — consultas a SQLite; verificá binding de parámetros
- `assessing-vector-and-embedding-weaknesses` — aislamiento del store de Chroma
- `exploiting-insecure-deserialization` — límites de confianza al parsear
- `exploiting-prototype-pollution-in-javascript` — merges de objetos en TS/Node

Preguntas guía: ¿el server escucha en loopback o en `0.0.0.0`? ¿Hay
autenticación entre el hook y el server? ¿Las queries usan parámetros y no
concatenación?

### 4. Cadena de suministro

Se publica en npm y el instalador baja Bun y uv.

- `detecting-malicious-npm-packages`, `detecting-dependency-confusion`
- `detecting-typosquatting-packages-in-npm-pypi`
- `analyzing-sbom-for-supply-chain-vulnerabilities`
- `performing-sca-dependency-scanning-with-snyk`

Preguntas guía: ¿el instalador verifica checksums o firmas de lo que descarga?
¿Hay lockfile commiteado? ¿Los scripts `postinstall` hacen red?

### 5. CI/CD y secretos

- `securing-github-actions-workflows` — pinning a SHA, permisos del token, injection en expresiones
- `detecting-supply-chain-attacks-in-ci-cd`
- `implementing-secret-scanning-with-gitleaks`, `implementing-secrets-scanning-in-ci-cd`
- `integrating-sast-into-github-actions-pipeline`, `implementing-semgrep-for-custom-sast-rules`

Para modelar amenazas de un diseño nuevo antes de escribir código:
`performing-threat-modeling-with-owasp-threat-dragon`.

## Cómo ejecutarla

1. **Leé la SKILL.md relevante antes de auditar cada superficie.** Traen
   checklists concretos y patrones de código. No audites de memoria.
2. **Verificá contra el código real** con Grep/Read. Cada hallazgo se ancla a
   `archivo:línea`. Sin ancla, no es un hallazgo: es una hipótesis.
3. **Los scripts son opcionales.** Muchas skills traen `scripts/agent.py` o
   `process.py`. Para correrlos:
   `vault/security-skills/run-script.sh <skill> <script.py> [args]`
   Nunca hace falta correrlos para usar la skill; la guía es lo que vale.
4. **No reportes lo que no verificaste.** Antes de escribir un hallazgo,
   intentá refutarlo: ¿hay validación aguas arriba? ¿el input es realmente
   alcanzable por un atacante? Un falso positivo cuesta más que un hueco.

## Formato de salida

Agrupá por superficie, ordená por severidad. Para cada hallazgo:

```
[ALTA] Prompt injection persistente vía output de herramientas
  Dónde:    src/services/compression.ts:142
  Qué:      El output de Bash se concatena al prompt de compresión sin
            delimitadores ni marcado de contenido citado.
  Impacto:  Un archivo leído con instrucciones embebidas puede alterar el
            resumen almacenado y afectar sesiones futuras.
  Skill:    detecting-indirect-prompt-injection
  Arreglo:  Envolver el contenido en delimitadores explícitos e instruir al
            modelo a tratarlo como datos.
```

Cerrá con: superficies revisadas, conteo por severidad, y qué quedó **sin**
revisar. Si no encontrás nada en una superficie, decilo explícitamente —
"sin hallazgos en cadena de suministro" es información; el silencio no.

## Advertencia sobre las skills ofensivas

Varias de las skills vendorizadas describen técnicas ofensivas
(`exploiting-*`). Están para reconocer patrones vulnerables en **este** código.
No las uses para atacar sistemas de terceros.
