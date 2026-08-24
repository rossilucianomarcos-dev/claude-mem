# mi-video — editor de vídeo con Claude Code + Remotion

Proyecto de Remotion listo para editar vídeos escribiendo prompts en vez de usar
un programa de edición. Incluye TailwindCSS, las Skills oficiales de Remotion y
una composición de ejemplo (`Intro`) de 10 segundos.

## Puesta en marcha

```bash
cd mi-video
npm install
npm run dev        # abre Remotion Studio en http://localhost:3000
```

Remotion Studio es el editor visual: se ejecuta en el navegador, permite
recorrer la línea de tiempo fotograma a fotograma y se recarga solo cada vez
que Claude modifica el código. Déjalo abierto en una pestaña y pide los cambios
desde otra pestaña de Claude Code.

## Qué hay dentro

| Ruta                 | Qué es                                                                            |
| -------------------- | --------------------------------------------------------------------------------- |
| `src/index.ts`       | Punto de entrada; registra el root de Remotion.                                   |
| `src/Root.tsx`       | Registra las composiciones (id, duración, fps, tamaño, `defaultProps`).           |
| `src/Intro.tsx`      | Escena de ejemplo: nombre de empresa con fundido y eslogan que entra desde abajo. |
| `src/index.css`      | Importa TailwindCSS (`@import "tailwindcss"`).                                    |
| `remotion.config.ts` | Config del renderizado; activa Tailwind con `enableTailwind`.                     |
| `public/`            | Tus vídeos, imágenes y audios. Se referencian con `staticFile("clip.mp4")`.       |
| `.agents/skills/`    | Skills oficiales de Remotion (instaladas con `npx remotion skills add`).          |
| `out/`               | Vídeos renderizados. Está ignorado por Git.                                       |

La composición `Intro` mide 1920×1080, 30 fps y 300 fotogramas (10 s). El nombre
y el eslogan son `defaultProps`, así que se pueden cambiar desde el panel de
props del Studio o directamente en `src/Root.tsx`.

## Skills de Remotion

Las Skills son instrucciones escritas por el equipo de Remotion para que Claude
escriba mejor código de animaciones, transiciones, subtítulos o renderizado.
Viven en `.agents/skills/`, y `.claude/skills/` contiene enlaces simbólicos a
esa carpeta. Ambas cosas están versionadas, así que tras clonar el repositorio
ya funcionan. Para actualizarlas a la versión de Remotion instalada:

```bash
npx remotion skills add
```

## Pedir cambios a Claude

Basta con describir lo que quieres ver en pantalla. Ejemplos:

- «Haz el texto más grande y cambia el fondo a azul oscuro.»
- «Acelera la primera transición.»
- «Añade un efecto de rebote cuando aparezca el logotipo.»
- «Usa el vídeo de `./public/clip.mp4` y añade subtítulos animados, resaltando
  cada palabra en amarillo a medida que se pronuncia.»

Para usar material propio, copia los archivos a `public/` e indica la ruta.

## Exportar el vídeo

```bash
npx remotion render Intro out/intro.mp4
```

Sin argumentos (`npx remotion render`) el CLI pregunta qué composición
renderizar. También puedes pedirle a Claude que «renderice el vídeo».

Remotion descarga su propio Chrome la primera vez que renderiza. Si estás en un
entorno sin acceso a `remotion.media`, apunta a un Chrome headless ya instalado:

```bash
npx remotion render Intro out/intro.mp4 --browser-executable=/ruta/a/headless_shell
```

## Comprobaciones

```bash
npm run lint                  # eslint + tsc
npx remotion compositions     # lista las composiciones registradas
npx remotion still Intro out/frame.png --frame=150 --scale=0.5
```

## Convenciones al animar

- Anima siempre con `useCurrentFrame()` e `interpolate()`. Las clases
  `transition-*` y `animate-*` de Tailwind, y las animaciones CSS, no se
  renderizan correctamente.
- Deja las llamadas a `interpolate()` en línea dentro de `style` y usa
  `scale`, `translate` y `rotate` en lugar de `transform`: así el Studio las
  puede editar de forma visual.
- Nombra los elementos (`<Interactive.Div name="Eslogan">`) para reconocerlos en
  la línea de tiempo.

Documentación de Remotion: https://www.remotion.dev/docs
