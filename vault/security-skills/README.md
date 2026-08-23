# Security skills (vendorizadas)

24 skills de ciberseguridad seleccionadas de
[mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills),
más una skill orquestadora propia (`security-audit`).

Mismo patrón que `vault/design-skills/`: esta carpeta es la fuente de verdad y
está commiteada; `install.sh` las copia a `.claude/skills/`, que está
gitigorado. Después de un clone fresco hay que correr el script.

```bash
vault/security-skills/install.sh            # solo este proyecto
vault/security-skills/install.sh --global   # todos los proyectos
```

## Procedencia y advertencias

- **No es de Anthropic.** Pese al nombre del repo upstream, es un proyecto
  comunitario de `mukul975`. El propio README upstream lo aclara.
- **Licencia**: Apache-2.0. Copia en `licenses/`.
- **Commit fijado**: ver `licenses/UPSTREAM_COMMIT`.
- **Contiene técnicas ofensivas** (las skills `exploiting-*`). Están acá para
  reconocer patrones vulnerables en este código, no para atacar terceros.

## Revisión previa a vendorizar

Antes de traer nada se revisó el upstream completo (817 skills, 1093 scripts):

| Chequeo | Resultado |
|---|---|
| Ofuscación (`eval`, `exec`) | 0 usos |
| `os.system` | 3, todos como *patrón detectado* o payload de demo |
| `pickle.loads` / `__import__` | solo como strings de regex en detectores |
| URLs hardcodeadas | APIs conocidas (VirusTotal, NVD, MS Graph) + `evil.com`/`localhost` de ejemplo |
| Prompt injection en SKILL.md | 5 coincidencias, todas payloads de test dentro de skills que *detectan* injection |

Los scripts son implementaciones de referencia reales, no stubs.

**Por qué solo 24 y no las 817:** las descripciones de las 817 suman ~325k
caracteres (~80k tokens) que se cargarían en el contexto de *cada* sesión. Y la
mayoría (forense de Windows, ICS/Modbus, C2) no aplica a un plugin TS/Node. El
subset cubre la superficie real de claude-mem.

## Inventario

**Ingesta de contenido no confiable / LLM** — el riesgo propio de un plugin de memoria
`detecting-indirect-prompt-injection` · `testing-prompt-injection-in-rag-pipelines` ·
`detecting-data-and-model-poisoning` · `implementing-llm-guardrails-for-security` ·
`testing-for-system-prompt-leakage` · `assessing-vector-and-embedding-weaknesses`

**MCP y herramientas**
`auditing-mcp-servers-for-tool-poisoning` · `securing-agentic-ai-tool-invocation`

**AppSec / código**
`exploiting-sql-injection-vulnerabilities` · `exploiting-prototype-pollution-in-javascript` ·
`exploiting-insecure-deserialization` · `conducting-api-security-testing` ·
`implementing-semgrep-for-custom-sast-rules`

**Cadena de suministro**
`detecting-malicious-npm-packages` · `detecting-dependency-confusion` ·
`detecting-typosquatting-packages-in-npm-pypi` · `analyzing-sbom-for-supply-chain-vulnerabilities` ·
`performing-sca-dependency-scanning-with-snyk` · `detecting-supply-chain-attacks-in-ci-cd`

**CI/CD y secretos**
`securing-github-actions-workflows` · `implementing-secret-scanning-with-gitleaks` ·
`implementing-secrets-scanning-in-ci-cd` · `integrating-sast-into-github-actions-pipeline`

**Modelado de amenazas**
`performing-threat-modeling-with-owasp-threat-dragon`

**Orquestadora (propia)**
`security-audit` — mapea las superficies de claude-mem a las skills de arriba.

## Scripts

Las skills funcionan solo con su SKILL.md: **no hace falta instalar nada** para
usarlas. Los `scripts/*.py` son opcionales. Para correr uno:

```bash
vault/security-skills/run-script.sh <skill> <script.py> [args]
vault/security-skills/run-script.sh securing-github-actions-workflows \
  process.py --workflows-dir .github/workflows --output audit.json
```

El wrapper usa `uv` (que claude-mem ya requiere) para resolver dependencias al
vuelo: no instala nada global ni deja un venv en el repo. Las dependencias por
skill están en `deps.txt`, generado desde los imports reales.

Cuatro skills necesitan librerías de ML pesadas (`tensorflow`, `transformers`,
`sentence-transformers`, `scikit-learn`, `llm-guard`) — cientos de MB en la
primera corrida. Están marcadas `[pesada]` en `deps.txt`. Su guía en SKILL.md
sirve igual sin correr el script.

## Actualizar

```bash
git clone --depth 1 https://github.com/mukul975/Anthropic-Cybersecurity-Skills /tmp/acs
for s in $(ls vault/security-skills/skills | grep -v '^security-audit$'); do
  rm -rf "vault/security-skills/skills/$s"
  cp -R "/tmp/acs/skills/$s" "vault/security-skills/skills/$s"
done
(cd /tmp/acs && git rev-parse HEAD) > vault/security-skills/licenses/UPSTREAM_COMMIT
```

Revisá el diff antes de commitear, y regenerá `deps.txt` si cambiaron imports.
`security-audit` es propia: no la pises.

### Divergencias con upstream

El bucle de arriba pisa las skills vendorizadas, así que estos parches locales
se pierden al actualizar. Re-aplicalos:

- `securing-github-actions-workflows/scripts/process.py` — la rama que detecta
  `write-all` usaba `all()` sobre el dict de permisos. Como `all()` de un dict
  vacío es `True`, `permissions: {}` (la remediación que el propio script
  recomienda) se reportaba como HIGH write-all. El fix agrega `top_perms and`
  antes del `all()`. Está marcado con `# PATCH LOCAL` en el archivo.
