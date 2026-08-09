# Vault · Skills de diseño y animación

Copia versionada (vendored) de 5 colecciones de skills de diseño, motion y 3D.
Vive acá y no en `.claude/skills/` porque ese directorio está en `.gitignore`:
el vault es lo que persiste en el repo, `.claude/skills/` es la copia activa.

```
vault/design-skills/
├── skills/       21 skills de nivel superior (+15 sub-skills de genjutsu)
├── licenses/     licencias originales de cada fuente
└── install.sh    copia skills/ a .claude/skills/ o ~/.claude/skills/
```

## Instalación

```bash
./vault/design-skills/install.sh            # solo este proyecto
./vault/design-skills/install.sh --global   # ~/.claude/skills, todos los proyectos
```

Se copia en vez de enlazar a propósito: `genjutsu` resuelve sus sub-skills con
`find` sin seguir symlinks, así que un enlace simbólico en el nivel superior
rompe la carga de `_jutsu/`.

Alternativa oficial para las dos que se publican como plugin, si preferís que
Claude Code las actualice solo:

```
/plugin marketplace add greensock/gsap-skills   &&  /plugin install gsap-skills
/plugin marketplace add AThevon/genjutsu        &&  /plugin install genjutsu
```

## Qué hay adentro

| Colección | Skills | Fuente | Commit fijado | Licencia |
|---|---|---|---|---|
| **Three.js** | 10 | [CloudAI-X/threejs-skills](https://github.com/CloudAI-X/threejs-skills) | `b1c6230` (2026-01-20) | sin archivo de licencia en origen |
| **GSAP** (oficial GreenSock) | 8 | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | `aed9cfd` (2026-04-21) | MIT |
| **Design DNA** | 1 | [zanwei/design-dna](https://github.com/zanwei/design-dna) | `9d9d795` (2026-04-13) | MIT |
| **Motion Design** (oficial LottieFiles) | 1 | [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | `f9a8a04` (2026-05-18) | MIT |
| **Genjutsu** | 1 router + 2 pipelines + 15 sub-skills | [AThevon/genjutsu](https://github.com/AThevon/genjutsu) v3.3.0 | `08a792f` (2026-07-31) | MIT |

### Three.js — 3D en tiempo real

`threejs-fundamentals` (escena, cámaras, renderer, jerarquía Object3D) ·
`threejs-geometry` (BufferGeometry, instancing) · `threejs-materials` (PBR,
ShaderMaterial) · `threejs-lighting` (tipos de luz, sombras, IBL) ·
`threejs-textures` (UV, cubemaps, HDR) · `threejs-animation` (keyframes,
skeletal, mixing) · `threejs-loaders` (GLTF/GLB, HDR, progreso de carga) ·
`threejs-shaders` (GLSL, uniforms) · `threejs-postprocessing` (EffectComposer,
bloom, DOF) · `threejs-interaction` (raycasting, controles de cámara, selección).

### GSAP — la librería de animación de GreenSock

`gsap-core` (`to/from/fromTo`, easing, stagger, `matchMedia`) · `gsap-timeline`
(secuencias sincronizadas, parámetro de posición, anidado) · `gsap-scrolltrigger`
(scroll-linked, pinning, scrub, parallax) · `gsap-plugins` (Flip, Draggable,
SplitText, ScrollSmoother, MorphSVG, CustomEase) · `gsap-utils` (`clamp`,
`mapRange`, `snap`, `wrap`) · `gsap-react` (hook `useGSAP`, cleanup) ·
`gsap-frameworks` (Vue, Nuxt, Svelte) · `gsap-performance` (transforms,
`will-change`, 60fps sin jank).

### Design DNA — ingeniería inversa del sistema de diseño

Flujo de tres fases: extrae de una URL o un screenshot los **design tokens**
(paleta completa, escala tipográfica, pares de fuentes, espaciado, radios,
sombras), el **estilo cualitativo** (mood, estrategia de composición) y los
**efectos visuales** (Canvas, WebGL, partículas, shaders, scroll), los vuelca a
JSON y genera diseños nuevos que respetan ese ADN. Copia el gusto visual, no el
código.

### Motion Design — principios de movimiento

Timing, easing, coreografía y los principios de animación de Disney adaptados a
UI. Agnóstica del sistema: sirve igual para CSS, Framer Motion, GSAP, Lottie o
Spring, y cubre el flujo hasta exportar Lottie JSON / `.dotLottie`.

### Genjutsu — dirección creativa anti-AI-slop

Se instala como **una sola skill** (`genjutsu`) con un router que decide el
pipeline; los sub-skills de `_jutsu/` se cargan solos según el stack detectado.

- **cast** — sobre UI que ya existe: escanea el stack, propone una tesis de
  interacción, implementa, audita (reduced-motion, exit animations, hitches).
- **paint** — desde cero: brainstorm de dirección de arte, tesis visual, sistema
  de diseño persistente (`MASTER.md`, Tailwind/CSS, `Theme.kt`, `Color+App.swift`),
  implementación y auditoría completa.
- **`_jutsu/`** (15 módulos internos) — `motion-principles`, `mobile-principles`,
  `desktop-principles`, `design-audit`, `ui-ux-pro-max` (84 estilos, 192 paletas,
  74 pares tipográficos, 99 guidelines), `gsap`, `framer-motion`, `css-native`,
  `threejs-r3f`, `canvas-generative`, `compose-motion`, `compose-graphics`,
  `compose-multiplatform`, `swiftui-motion`, `swiftui-graphics`.

Cubre Web, Android (Jetpack Compose) y Apple (SwiftUI).

> El layout de `skills/genjutsu/` es el bundle oficial generado con
> `package-for-claude-ai.sh`: un `SKILL.md` router en la raíz y los `SKILL.md`
> internos renombrados a `GUIDE.md`, para que Claude Code vea una sola skill y
> no dos genéricas llamadas `cast` y `paint`.

## Actualizar

Volvé a clonar la fuente y sobrescribí la carpeta correspondiente en `skills/`.
Para genjutsu hay que regenerar el bundle:

```bash
git clone --depth 1 https://github.com/AThevon/genjutsu && cd genjutsu
./package-for-claude-ai.sh && unzip -o dist/genjutsu.zip -d <vault>/skills/genjutsu
```

Después actualizá el commit fijado en la tabla de arriba y volvé a correr
`install.sh`.

## Licencias

GSAP Skills, Motion Design Skill, Genjutsu y Design DNA son MIT; los textos
originales están en `licenses/`. El repo de Three.js Skills no publica archivo
de licencia — si lo vas a usar en un producto comercial, conviene consultarle
al autor antes.
