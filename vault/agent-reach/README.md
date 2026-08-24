# Vault · Agent Reach

Copia versionada (vendored) de la skill **Agent Reach**: un router de acceso a
internet para agentes. Cubre 15 plataformas (web, YouTube, RSS, GitHub, Exa,
Twitter/X, Reddit, Facebook, Instagram, B站, 小红书, V2EX, LinkedIn, 小宇宙,
雪球) eligiendo por plataforma el backend que hoy funciona.

Vive acá y no en `.claude/skills/` porque ese directorio está en `.gitignore`:
el vault es lo que persiste en el repo, `.claude/skills/` es la copia activa.

```
vault/agent-reach/
├── skills/agent-reach/   SKILL.md (+ SKILL_en.md) y references/ por categoría
├── licenses/             licencia original (MIT)
└── install.sh            copia la skill y, con --cli, instala el CLI
```

## Instalación

```bash
./vault/agent-reach/install.sh --cli            # skill en este proyecto + CLI
./vault/agent-reach/install.sh --global --cli   # ~/.claude/skills, todos los proyectos
./vault/agent-reach/install.sh --cli-only       # solo el CLI
```

La skill sola alcanza como router — sabe qué comando corre para cada
plataforma — pero sin el CLI no hay `agent-reach doctor` ni instalación de
canales. El CLI también sabe registrarse solo:

```bash
agent-reach skill --install   # copia SKILL.md a ~/.claude/skills, ~/.openclaw/skills, etc.
```

## Dos partes, dos ritmos

| | Qué es | Cómo se actualiza |
|---|---|---|
| **Skill** (este vault) | `SKILL.md` + `references/*.md`: tabla de ruteo y comandos | Re-copiar desde upstream (abajo) |
| **CLI** (`agent-reach`) | Instalador, `doctor`, router de backends | `pipx upgrade agent-reach` / reinstalar desde upstream |

Agent Reach nunca envuelve a las herramientas de cada plataforma: instala
`yt-dlp`, `gh`, `mcporter`, `twitter-cli`, `bili-cli`, `opencli`… y después el
agente las llama directo. Por eso `doctor` es el punto de entrada real.

## Uso

```bash
agent-reach doctor --json     # qué canal está activo y con qué backend
agent-reach install --env=auto            # chequeo de solo lectura (default seguro)
agent-reach install --env=auto --system   # instala dependencias (requiere aprobación)
agent-reach install --system --channels=twitter,reddit,xiaohongshu
```

Canales sin configuración: web (Jina Reader), YouTube, RSS, GitHub público,
V2EX, B站 básico. El resto pide cookies o sesión de navegador — Agent Reach no
inicia sesión por el usuario; las cookies quedan en `~/.agent-reach/` y nunca se
suben.

### Regla de workspace

La skill escribe temporales en `/tmp/` y datos persistentes en
`~/.agent-reach/`. Nunca en el directorio del proyecto.

## Origen

| | |
|---|---|
| Upstream | [Panniantong/agent-reach](https://github.com/Panniantong/agent-reach) |
| Fork usado | [rossilucianomarcos-dev/agent-reach](https://github.com/rossilucianomarcos-dev/agent-reach) |
| Commit fijado | `93ae1d1` (2026-08-12), release v1.5.0 |
| Licencia | MIT — `licenses/agent-reach.LICENSE` |

### Actualizar la copia del vault

```bash
git clone --depth 1 https://github.com/Panniantong/agent-reach /tmp/agent-reach
rm -rf vault/agent-reach/skills/agent-reach
cp -R /tmp/agent-reach/agent_reach/skill vault/agent-reach/skills/agent-reach
cp /tmp/agent-reach/LICENSE vault/agent-reach/licenses/agent-reach.LICENSE
./vault/agent-reach/install.sh
```

Anotá el commit nuevo en la tabla de arriba.

## Nota sobre sesiones remotas

En un contenedor de Claude Code en la web la política de egreso bloquea con 403
casi todos los destinos de Agent Reach (`r.jina.ai`, `youtube.com`,
`www.v2ex.com`, `api.bilibili.com`, `xueqiu.com`, `mcp.exa.ai`), y Exa además
pide OAuth por navegador. La instalación es válida igual, pero los canales solo
responden corriendo Claude Code local.
