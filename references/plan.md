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
`captions.style: "clean"` cambia el look: blanco en Inter ExtraBold y minúscula, destacados en itálica gruesa
de un solo color (`emphColor`, default `#FFE14D`) y entrada suave sin rebote. Va bien con `captions.py --max-words 1`
(una palabra por vez). `emphSfx` le pone un sonido a los destacados (por defecto ninguno).

### Tipos de insert
Todos llevan `type`, `start`, `end`. Opcional en todos: `sfx` (nombre del sonido, o `null` para ninguno).

| type | Campos | Notas |
|---|---|---|
| `title` | `text`, `behind`, `color`, `y`, `size`, `font` (`cal`/`hand`), `clipTop` | `behind: true` necesita `cutout.py`. `clipTop` = desde qué altura tapa la cabeza (default: deja ~80 % de la letra) |
| `image` | `src`, `mode` (`card`/`sticker`/`full`), `x`, `y`, `w`, `maxH`, `rot` | `src` relativo al proyecto, en `assets/` |
| `broll` | igual que `image` + `mediaStart` | video sin sonido; `full` cubre todo el cuadro |
| `scribble` | `text`, `x`, `y`, `w`, `rot`, `size`, `color` | Caveat, se escribe palabra por palabra |
| `steps` | `items` (2-4 textos cortos), `times` (uno por item), `title`, `highlight` (índices), `y`, `color` | chips con flechas |
| `profile` | `y`, `followers`, `posts`, `following`, `bio`, `avatar` | nombre y usuario salen de `config.json`; los números solo si la persona los da; `avatar` default `assets/avatar.jpg` (si no hay, iniciales) |
| `webm` | `src`, `x`, `y`, `w`, `h` | animación con transparencia hecha aparte |
| `scene` | `kind` (`chat`/`calendar`/`checklist`/`stat`/`text`) + los campos de cada una, `accent` | escena animada a pantalla completa que explica lo que se dice; detalles en `references/pantalla-completa.md` |
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
