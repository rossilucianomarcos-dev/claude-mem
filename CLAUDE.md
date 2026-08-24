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

## Internet Access Skill

`agent-reach` is vendored in `vault/agent-reach/` (source of truth, committed) and
installed into `.claude/skills/` by `vault/agent-reach/install.sh --cli`. Same
deal as the design skills: the install directory is gitignored, so re-run the
script after a fresh clone.

Reach for it automatically, without being asked, whenever the work needs
content from the internet: researching a topic across the web, reading a URL,
YouTube transcripts, RSS feeds, GitHub code search, or anything on Twitter/X,
Reddit, Facebook, Instagram, LinkedIn, V2EX, Bilibili, XiaoHongShu, Xueqiu, or
XiaoYuZhou. Start with `agent-reach doctor --json` to see which backend is live
for the platform you need, and say which platform and backend you're using
before you start.

Not for content processing (writing, analysis, translation) or write actions
(posting, commenting) — it only fetches. Temporary files go in `/tmp/`,
persistent data in `~/.agent-reach/`, never in the project directory.

See `vault/agent-reach/README.md` for channel setup, the pinned upstream commit,
and how to update.

## Important

No need to edit the changelog ever, it's generated automatically.
