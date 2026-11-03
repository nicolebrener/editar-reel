# Formato de los archivos del proyecto

Todos los tiempos de `captions.json` y `reel.json` están en segundos del reel final (el de `aroll.mp4`).
Los de `edl.json` están en segundos de cada clip original.

## edl.json (lo escribe Claude en el paso 2)
```json
[
  {"id": "gancho", "clip": "c5", "in": 0.57, "out": 1.99, "zoom": 1.0, "cx": 0.5, "cy": 0.45,
   "line": "¿Te diste cuenta que estamos viendo"},
  {"id": "gancho-b", "clip": "c5", "in": 2.83, "out": 7.70, "zoom": 1.35, "cx": 0.5, "cy": 0.38,
   "line": "la muerte de las herramientas..."}
]
```
`zoom` 1.0 = cuadro completo; 1.3-1.8 = punch-in. `cx`/`cy` = centro del recorte (0-1). `line` es solo para leer.

## captions.json (lo genera captions.py; se edita a mano)
```json
[
  {"id": "k1", "start": 0.0, "end": 0.6, "y": null, "emph": null,
   "words": [{"t": "Te", "s": 0.0, "e": 0.2}, {"t": "diste", "s": 0.26, "e": 0.4}, {"t": "cuenta", "s": 0.42, "e": 0.6}]},
  {"id": "k3", "start": 2.84, "end": 3.2, "y": null, "emph": {"color": 0},
   "words": [{"t": "muerte", "s": 2.84, "e": 3.2}]}
]
```
- Cambiar una palabra: editá `t`. Juntar o separar grupos: mové objetos de `words` entre grupos y ajustá
  `start`/`end` (start = `s` de la primera palabra).
- `y`: altura de ese grupo (px desde arriba). `null` = la de `reel.json`.
- `emph`: `null` o `{"color": n}` (índice de `accents`).

## reel.json (lo escribe Claude en el paso 6)
```json
{
  "captions": {"y": 1240, "size": 92, "emphSize": 150},
  "autoZoom": true,
  "zooms":   [{"start": 3.2, "end": 5.0, "scale": 1.18, "ox": 0.5, "oy": 0.35}],
  "flashes": [7.76, 16.44],
  "music":   {"src": "assets/musica.mp3", "volume": 0.08},
  "sfx":     {"gain": 1.0},
  "inserts": [ ... ]
}
```
En `captions.json` un destacado puede llevar su propio color: `"emph": {"color": "#9B7FD8"}` (un color por
sección). `captions.style: "clean"` cambia el look: blanco en Inter ExtraBold y minúscula, destacados en itálica gruesa
de un solo color (`emphColor`, default `#FFE14D`) y entrada suave sin rebote. Va bien con `captions.py --max-words 1`
(una palabra por vez).

### El look de los subtítulos (`captions`)
`style` (`pop` o `clean`) pone la base; cualquiera de estas claves la pisa. Es lo que cambia el estudio
(`scripts/studio.py`), así que un reel tocado ahí puede traer cualquiera:

| Clave | Valores | pop / clean |
|---|---|---|
| `font`, `emphFont` | `cal`, `inter`, `montserrat`, `montserrat-m` (Medium), `poppins`, `grotesk`, `anton`, `bebas`, `dmserif`, `caveat`, `bootzy` (la toma de `~/Library/Fonts/BootzyTM.ttf`: tiene licencia propia y no va en el repo; sin ella, Inter) | `cal` / `inter` |
| `color` | `"#hex"` de los subtítulos (`null` = `config.json` `caption`) | amarillo / `#FFFFFF` |
| `emphColor` | `"#hex"` para todos los destacados, `null` = rotan los `accents` | `null` / `#FFE14D` |
| `case`, `emphCase` | `asis` (como se dijo), `auto` (minúscula al empezar la frase), `upper`, `lower` | `asis`, `upper` / `auto`, `upper` |
| `emphItalic` | `true` / `false` | `false` / `true` |
| `shadow` | `light`, `soft`, `strong`, `box` (caja oscura detrás), `none`. Nunca contorno | `soft` / `light` |
| `anim` | `pop` (rebote e inclinación), `soft` (sube suave), `none` | `pop` / `soft` |
| `emphSfx` | `pop`, `click`, `ding` o `null` | `pop` / `null` |
| `size`, `emphSize`, `y` | px | 92, 150, 1240 / 80, 130, 1240 |
| `curve` | px que bajan las puntas del arco: 0 = recto; 150-250 = el subtítulo en arco sobre la cabeza, como un halo (con `y` ~430) | 0 |
| `tilt` | hasta cuántos grados se inclina cada subtítulo (uno distinto por subtítulo) | 0 |
| `emphBox` | `"pill"`: el destacado sobre una píldora de `emphColor` con letra negra o blanca. No va con `curve` | `null` |
| `sparkles` | `true`: brillitos ✦ (uno blanco chico y uno del color del destacado) a cada lado de los destacados | `false` |
| `emphStickers` | nombre de un pack de `~/reel-stickers` (`"girly"`): en cada destacado aparece con pop un sticker del pack (estrellas, brillos, corazones, bolas de disco), alternando izquierda y derecha | `null` |

Los estilos base del estudio (`assets/studio/options.json` -> `presets`) son combinaciones de estas claves: Pop,
Clean, Bold, Impacto, Editorial, Caja, Arco (minúscula amarilla pálida en arco y remate en serif itálica, de una
referencia de la persona), Arco blanco, Cine, Girly y Girly serif.

### Color de la imagen (`grade`, `gradeAmount`)
`"grade"`: `cine` (verde salvia en fondos y medios, piel dorada, negros suaves, grano y viñeta), `calido`, `film`
(lavado y desaturado) o `frio`; `null` = natural. `"gradeAmount"` 0.2-1.5 (default 1). Se hornea con ffmpeg en el
video principal, el recorte y el b-roll (una vez por look, en `assets/graded/`; ~1 min en 4K). El grano va aparte, como
capa semitransparente (`assets/grain-*.webm`): dentro del video lo haría pesar gigas. En el estudio (`build.py
--preview`) el color se aplica solo a las copias livianas de la vista previa. Un fondo que no es verde no se vuelve
verde: el look tiñe, no repinta.

Arriba de `captions`, `titleFont` (las mismas fuentes) cambia la de los títulos detrás de la cabeza.

### Tipos de insert
Todos llevan `type`, `start`, `end`. Opcional en todos: `sfx` (nombre del sonido, o `null` para ninguno).

| type | Campos | Notas |
|---|---|---|
| `note` | `text`, `x`, `y`, `w` (640), `rot`, `paper` (`lined`/`pink`), `font` (`caveat`/`dmserif`), `size`, `stickers` (pack para las esquinas, `null` = sin), `color` | tarjeta de cuaderno con renglones, margen, agujeros, clip y cinta; el texto se escribe solo. Va donde hay lugar (arriba de la cabeza o al costado), nunca sobre la cara: mientras está, bajá los subtítulos de ese momento al pecho (`"y": 1240` en `captions.json`) |
| `title` | `text`, `behind`, `color`, `y`, `size`, `font` (`cal`/`hand`), `clipTop` | `behind: true` necesita `cutout.py`. `clipTop` = desde qué altura tapa la cabeza (default: deja ~80 % de la letra) |
| `image` | `src`, `mode` (`card`/`sticker`/`full`), `x`, `y`, `w`, `maxH`, `rot` | `src` relativo al proyecto, en `assets/`, o `"sticker:<pack>/<nombre>"` de `~/reel-stickers` (`scripts/stickers.py list`) |
| `broll` | igual que `image` + `mediaStart` | video sin sonido; `full` cubre todo el cuadro |
| `scribble` | `text`, `x`, `y`, `w`, `rot`, `size`, `color` | Caveat, se escribe palabra por palabra |
| `steps` | `items` (2-4 textos cortos), `times` (uno por item), `title`, `highlight` (índices), `y`, `color` | chips con flechas |
| `profile` | `y`, `followers`, `posts`, `following`, `bio`, `avatar` | nombre y usuario salen de `config.json`; los números solo si la persona los da; `avatar` default `assets/avatar.jpg` (si no hay, iniciales) |
| `webm` | `src`, `x`, `y`, `w`, `h` | animación con transparencia hecha aparte |
| `scene` | `kind` (`chat`/`calendar`/`checklist`/`stat`/`text`) + los campos de cada una, `accent` | escena animada a pantalla completa que explica lo que se dice; detalles en `references/pantalla-completa.md` |
| `light` | `color`, `x`, `y` (centro de la luz, 0-1), `size` (%), `blend` (`soft-light`/`overlay`), `strength` | luz de color sobre la pared de atrás (necesita `cutout.py`): tiñe el fondo, nunca la cara. Varias seguidas que se pisan 0.3 s hacen un fundido |
| `anim` | `icon`, `pos` (`right`/`left`), `x`, `y`, `size`, `style` (`line`/`badge`), `label`, `color`, `accent` | ícono de línea que se dibuja solo y se mueve, para ilustrar lo que se dice; íconos y reglas en `references/animaciones.md` |
| `number` | `text`, `x`, `y`, `size`, `stroke`, `color` | número gigante solo con contorno ("1", "2", "3") para cada punto de una lista; `x` = borde izquierdo de la zona donde se centra. Al costado de la cabeza, nunca sobre la cara |
| `handle` | `spots` (`[{"t", "x", "y"}]`) | ícono de Instagram + @usuario como marca de agua que cambia de lugar; solo si la persona lo quiere |
| `endcard` | | cierre: oscurece el video y muestra el logo de Instagram + @usuario en el centro; solo si la persona lo quiere |

### Capturas de pantalla como tarjeta
Sacá un cuadro de la grabación y recortá solo la parte que se lee:
```bash
ffmpeg -ss 80 -i "grabacion.mov" -frames:v 1 -vf "crop=640:210:290:185,pad=iw+80:ih+60:40:30:white" assets/captura.png
```
Recortá texto que se lea en el celu (letra de al menos ~40 px en el reel). Sin nombres completos, teléfonos ni
chats de terceros.
