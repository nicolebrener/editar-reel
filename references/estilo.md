# El look: dinámico, colorido, animado

Sale de reels de referencia de creadoras en español: subtítulos de pocas palabras, palabras clave gigantes de
color, inserts que entran con "pop", texto escrito a mano, b-roll y capturas reales encima del video.

## Tipografías (todas OFL, incluidas en `assets/fonts`)
| Uso | Fuente |
|---|---|
| Subtítulos, destacados, títulos, chips | **Cal Sans** |
| Texto a mano (`scribble`, `title` con `"font": "hand"`) | **Caveat Bold** |
| Tarjeta de perfil, flechas | **Inter** SemiBold / ExtraBold |

Para elegir otra letra en los subtítulos o los títulos (`captions.font`, `emphFont`, `titleFont`, o el estudio):
Montserrat Black, Poppins ExtraBold, Space Grotesk Bold, Anton, Bebas Neue y DM Serif Display, también OFL.

## Colores (`config.json` -> `colors`)
- `caption` `#FFD60A`: amarillo, el color base de todos los subtítulos.
- `accents`: rosa frambuesa `#E2577F`, terracota `#E07A4F`, lavanda `#9B7FD8`, mostaza `#E8B53E`, salvia `#7FA86A`.
  **Nada flúo ni neón** (ni turquesa `#00E0FF`, ni lima `#7CFF4F`, ni naranja `#FF7A00`, ni rosa chicle `#FF3EA5`):
  se ven hechos con IA. Tonos profundos y apagados, que se lean sobre pared clara y sobre fondo oscuro. Los destacados y los títulos
  van rotando por esta lista (`"color": 0..3` en `reel.json`, o un `"#hex"` directo).
- **Sin contorno.** Todo el texto lleva solo una sombra suave. Si algo no se lee, primero movelo a una zona más
  oscura o lisa del cuadro; después, como mucho, más sombra.

## Subtítulos
- 1 a 3 palabras, sin puntos ni comas ni signos. Cada palabra aparece cuando se dice (pop corto).
- Altura por defecto `y = 1240` (pecho), dentro de la zona segura. Nunca sobre la boca ni los ojos.
- Destacados: solos, en MAYÚSCULA, ~150 px, color de acento, inclinación chica, pop con sonido y un zoom rápido
  de cámara (1.08). Uno cada 4-8 segundos; si todo está destacado, nada lo está.

## Inserts y cuándo usarlos
| Momento del guion | Insert |
|---|---|
| Gancho con una idea fuerte ("la muerte de...") | `title` detrás de la cabeza ("R.I.P.") |
| Cada sección / marca / número ("Shopify", "#1") | `title` detrás de la cabeza, un acento distinto cada vez, + `flash` |
| Muestra algo real (una app, un resultado) | `image` o `broll` en modo `card` arriba de la cabeza, con borde blanco |
| Un objeto o un logo propio | `image` modo `sticker` (PNG transparente), pop + flota |
| Explica algo que se entiende mejor viéndolo (una conversación, una agenda, una lista, un número, un lugar) | corte a pantalla completa: `scene` animada, stock (Pixabay o Pexels) o clip propio (`references/pantalla-completa.md`) |
| Nombra algo concreto (un calendario, un chat, pendientes, un permiso, la IA) | `anim`: ícono de línea que se dibuja y se mueve al costado de la cabeza (`references/animaciones.md`) |
| Una lista de puntos ("lo primero", "la segunda", "y tercero") | `number` con contorno, al costado de la cabeza |
| Remate, chiste, reacción ("¡ojo!", "cero olvidos") | `scribble` |
| Un proceso o un antes/después | `steps` (chips con flechas que aparecen al ritmo de la voz) |
| CTA final | `profile` (tarjeta de Instagram con "Seguir" -> "Siguiendo") |

## Títulos detrás de la cabeza
Van arriba de todo de la zona segura (y 228). La cabeza tapa solo la base de las letras (~20 %): se leen siempre
y dan profundidad. No pongas títulos de más de ~10 letras por línea: el tamaño baja y pierden fuerza.

## Color por sección (cuando la persona pide más color)
Un color para cada parte del guion (cada marca, cada idea), el mismo en todo lo de esa parte: el destacado, el
`number`, el detalle del `anim` y el acento de la `scene`. Al cambiar de tema cambia el color: eso solo ya se
siente como edición. Los mismos tonos de `accents`, nunca flúo (rosa frambuesa `#E2577F`, terracota `#E07A4F`, lavanda `#9B7FD8`,
mostaza `#E8B53E`, salvia `#7FA86A`).

## Luz de fondo
Una sola `light` cálida (naranja `#FF8A3D`, `soft-light`) en todo el video, desde arriba a un costado, como una
lámpara: le da calidez a la pared sin tocar la cara. **No cambies el color de la luz por sección**: un fondo que
pasa de verde a amarillo a violeta se ve como un cambalache.

## Movimiento
- Punch-ins alternados entre segmentos (1.0 / 1.2-1.35, desde el 4K original), aunque el video venga de una sola
  toma: cortá en el comienzo de una frase. Hacé el punch-in en las frases sin nada al costado de la cabeza: con
  zoom la cabeza ocupa más y los números o tarjetas laterales terminan sobre el pelo.
- Zoom rápido en cada destacado (`autoZoom`), zooms lentos a mano en momentos clave (`zooms`).
- Flash blanco corto al cambiar de tema (`flashes`).

## Sonido
Sintetizados por `setup.py` (propios, libres para compartir): `pop`, `click`, `ding`, `rise`, `bass`, `whoosh`.
Por defecto: pop en destacados y tarjetas, whoosh en títulos y b-roll a pantalla completa, click en texto a mano,
rise + click + ding en la tarjeta de perfil. Volumen general en `reel.json` `sfx.gain`.

## Color de cámara
Los iPhone graban en HDR (HLG). `assemble.py` lo pasa a SDR con un LUT propio (`make_lut.py`). Exposición en
`config.json` `hdrExposure`: 0.62 es natural; bajala (0.55) si la piel se quema, subila (0.7) si queda oscuro.

## Girly aesthetic (cuando la persona lo pide)
Sale de reels de creadoras de lifestyle: el texto arriba de la cabeza, blanco bold (Montserrat Bold) con la palabra
clave en rosa bebé `#F9B4D0` o en serif itálica amarilla pálida `#F8EDA8`, brillitos ✦ a los costados, un sticker
(estrella con glitter, corazón cromado, bola de disco, brillo cromado) que aparece con pop en cada destacado, y alguna
nota de cuaderno (`note`) para una lista o un tip. Presets "Girly" y "Girly serif" del estudio. Los stickers salen de
`~/reel-stickers/girly` (recortados de las imágenes que pasó la persona con `scripts/stickers.py cut`); para sumar más,
`cut` con las imágenes nuevas y mirá `sheet.jpg`. Menos es más: 1 sticker por destacado, 1 nota cada 15-20 s.
