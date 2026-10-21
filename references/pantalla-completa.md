# Videos a pantalla completa que explican lo que se dice

Cortes de 1.5-3 s donde la persona desaparece y la pantalla entera muestra aquello de lo que habla, con los
subtítulos encima. Hay tres fuentes; usá la que mejor explique cada momento.

| Fuente | Cuándo | Cómo |
|---|---|---|
| **Escena animada** (`scene`) | Un proceso, una app, un dato: un chat, una agenda, una lista, un número, una frase clave | se arma en HTML, no hace falta bajar nada |
| **Stock** (Pexels) | Algo del mundo real: una ciudad, gente trabajando, una oficina, un celular en la mano, un estadio | `broll.py search` + `get` |
| **Clips propios** | Grabaciones de pantalla de la app de la que se habla, b-roll que grabó la persona | `broll.py prep` |

## Escenas animadas: insert `scene`
Fondo oscuro con un brillo del color de acento; el contenido va de y 270 a y 1280 (abajo quedan los subtítulos).
Todos los `times` / `t` son segundos del reel: hacé coincidir cada aparición con la palabra que la nombra.
```json
{"type": "scene", "kind": "calendar", "start": 8.45, "end": 10.95, "title": "Tu semana",
 "busy": [[0,0],[1,2]], "free": [[2,0],[3,2]], "times": [9.55, 9.85]}
```
| kind | Campos | Para |
|---|---|---|
| `chat` | `title` (nombre del contacto), `subtitle`, `messages`: `[{"from": "me"/"them", "text", "time", "t"}]` | "le responde al cliente", "me escribe", una conversación |
| `calendar` | `title`, `days` (default Lun-Vie), `slots` (default 4), `busy`, `free` (`[día, franja]`), `times` | reuniones, agenda, huecos libres, turnos |
| `checklist` | `title`, `items`, `tags` (uno por item, opcional: "Alta"), `times` (cuándo se tilda cada uno) | pendientes, tareas, pasos, "me los organiza" |
| `stat` | `value`, `prefix`, `suffix`, `label`, `countFor` (s, default 1) | un número que pega: "258 mensajes", "3x más", "$0" |
| `text` | `lines` (2-4 líneas cortas; `*palabra*` va en el color de acento), `times` | una idea fuerte que conviene leer, el remate |

Los textos de una escena salen de lo que dice el video o de lo que se ve en sus capturas: nunca inventes datos,
nombres de clientes ni números. Si hace falta un ejemplo ("Martina pregunta por una reunión"), que sea genérico y
sin personas reales. Sin emojis: el render no tiene fuente de emojis y salen como cuadraditos.

## Stock de Pexels
```bash
PY SK/scripts/broll.py search <proyecto> "woman texting phone" --n 8     # hoja: work/broll-<busqueda>.jpg
PY SK/scripts/broll.py get <proyecto> <id> --name celu --start 1 --dur 3  # -> assets/broll/celu.mp4
```
- Buscá en inglés y concreto ("calendar planner desk", no "organización"). Mirá la hoja y elegí el que se ve
  natural, con luz parecida al video, sin texto ni logos de otras marcas y sin caras en primer plano que
  distraigan.
- Necesita la clave gratis de Pexels en `SK/.pexels_key` (una línea; está en `.gitignore`) o en la variable
  `PEXELS_API_KEY`. Si falta, el script lo dice: pedile a la persona que la saque en https://www.pexels.com/api/
  y que la pegue ella en ese archivo. Los clips de Pexels se usan gratis y sin atribución.

## Clips propios
```bash
PY SK/scripts/broll.py prep <proyecto> "<archivo>" --name pantalla --start 12 --dur 3 --fit --crop 1200:900:400:150
```
- `--fit` para lo horizontal (una grabación de pantalla): entra entero sobre una copia desenfocada.
- `--crop w:h:x:y` primero recorta la parte que se lee (en píxeles del original); sin eso el texto de una
  pantalla de compu queda chico en el celu.
- Tapá o recortá nombres, teléfonos y chats de terceros antes de usarlo.

En `reel.json` el clip va como `{"type": "broll", "src": "assets/broll/pantalla.mp4", "start": 20.5,
"end": 23.0, "mode": "full"}`.

## Cuándo sí y cuándo no
- **Uno cada 8-15 s**, de 1.5 a 3 s cada uno. Más que eso y la persona deja de estar en su propio video.
- Nunca en el gancho (los primeros 2-3 s son de la cara) ni en el CTA final.
- Cortá en una pausa o al empezar la frase que explica, y volvé a la persona antes de la frase siguiente.
- Si el video ya trae una captura o grabación mostrando eso mismo, no lo tapes con otra cosa.
- Un `anim` (ícono) que caiga dentro de un corte a pantalla completa queda tapado: sacalo o movelo.
