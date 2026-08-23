# Claude-Mem: AI Development Instructions

Claude-mem is a Claude Code plugin providing persistent memory across sessions. It captures tool usage, compresses observations using the Claude Agent SDK, and injects relevant context into future sessions.

## Build

```bash
npm run build-and-sync        # Build, sync to marketplace, restart worker
```

## File Locations

- **Source**: `<project-root>/src/`
- **Built Plugin**: `<project-root>/plugin/`
- **Installed Plugin**: `~/.claude/plugins/marketplaces/thedotmack/`
- **Database**: `~/.claude-mem/claude-mem.db`
- **Chroma**: `~/.claude-mem/chroma/`

## Requirements

- **Bun** (all platforms - auto-installed if missing)
- **uv** (all platforms - auto-installed if missing, provides Python for Chroma)
- Node.js

## Documentation

**Public Docs**: https://docs.claude-mem.ai (Mintlify)
**Source**: `docs/public/` - MDX files, edit `docs.json` for navigation
**Deploy**: Auto-deploys from GitHub on push to main

## Design & Animation Skills

21 vendored skills live in `vault/design-skills/` (source of truth, committed) and
are installed into `.claude/skills/` by `vault/design-skills/install.sh`. That
install directory is gitignored — re-run the script after a fresh clone.

Reach for them automatically, without being asked, whenever the work matches:

| Work | Skill |
|---|---|
| 3D on the web, WebGL, GLTF models, shaders, particles, post-processing | `threejs-*` (10 skills) |
| JS animation, timelines, scroll-driven reveals, text reveal, animating in React/Vue/Svelte | `gsap-*` (8 skills) |
| Cloning a reference site's visual identity — palette, type scale, layout, mood | `design-dna` |
| Timing, easing, choreography for any animation; Lottie / `.dotLottie` output | `motion-design` |
| Making an existing UI feel exceptional, or building a visual identity from scratch (web, Compose, SwiftUI) | `genjutsu` |

`motion-design` sets the timing and easing intent; `gsap-*` / `threejs-*` /
`css-native` implement it. On anything non-trivial, run `genjutsu` first — it
scans the stack and pulls in the right sub-skills itself.

See `vault/design-skills/README.md` for the full inventory, pinned upstream
commits, and how to update.

## Security Skills

24 skills de ciberseguridad vendorizadas en `vault/security-skills/` (fuente de
verdad, commiteada) más la orquestadora propia `security-audit`. Se instalan en
`.claude/skills/` con `vault/security-skills/install.sh` — ese directorio está
gitignorado, así que hay que re-correr el script tras un clone fresco.

Para una revisión de seguridad del proyecto: **`/security-audit`**. Cubre
ingesta de contenido no confiable (transcripts y output de herramientas),
superficie MCP, server/SQLite/Chroma, cadena de suministro npm, y CI/CD.

Para revisar solo el diff pendiente de la branch está la skill incorporada
`/security-review`, que es más rápida y acotada.

Los `scripts/*.py` de las skills son opcionales; se corren con
`vault/security-skills/run-script.sh <skill> <script.py>`, que resuelve deps con
`uv` sin instalar nada global.

Ver `vault/security-skills/README.md` para procedencia, la revisión de seguridad
del upstream y cómo actualizar.

## Important

No need to edit the changelog ever, it's generated automatically.
