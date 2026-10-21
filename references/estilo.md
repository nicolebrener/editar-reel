# El look: dinámico, colorido, animado

Sale de reels de referencia de creadoras en español: subtítulos de pocas palabras, palabras clave gigantes de
color, inserts que entran con "pop", texto escrito a mano, b-roll y capturas reales encima del video.

## Tipografías (todas OFL, incluidas en `assets/fonts`)
| Uso | Fuente |
|---|---|
| Subtítulos, destacados, títulos, chips | **Cal Sans** |
| Texto a mano (`scribble`, `title` con `"font": "hand"`) | **Caveat Bold** |
| Tarjeta de perfil, flechas | **Inter** SemiBold / ExtraBold |

## Colores (`config.json` -> `colors`)
- `caption` `#FFD60A`: amarillo, el color base de todos los subtítulos.
- `accents`: rosa `#FF3EA5`, celeste `#00E0FF`, lima `#7CFF4F`, naranja `#FF7A00`. Los destacados y los títulos
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
| Nombra algo concreto (un calendario, un chat, pendientes, un permiso, la IA) | `anim`: ícono de línea que se dibuja y se mueve al costado de la cabeza (`references/animaciones.md`) |
| Una lista de puntos ("lo primero", "la segunda", "y tercero") | `number` con contorno, al costado de la cabeza |
| Remate, chiste, reacción ("¡ojo!", "cero olvidos") | `scribble` |
| Un proceso o un antes/después | `steps` (chips con flechas que aparecen al ritmo de la voz) |
| CTA final | `profile` (tarjeta de Instagram con "Seguir" -> "Siguiendo") |

## Títulos detrás de la cabeza
Van arriba de todo de la zona segura (y 228). La cabeza tapa solo la base de las letras (~20 %): se leen siempre
y dan profundidad. No pongas títulos de más de ~10 letras por línea: el tamaño baja y pierden fuerza.

## Movimiento
- Punch-ins alternados entre segmentos (1.0 / 1.35, desde el 4K original).
- Zoom rápido en cada destacado (`autoZoom`), zooms lentos a mano en momentos clave (`zooms`).
- Flash blanco corto al cambiar de tema (`flashes`).

## Sonido
Sintetizados por `setup.py` (propios, libres para compartir): `pop`, `click`, `ding`, `rise`, `bass`, `whoosh`.
Por defecto: pop en destacados y tarjetas, whoosh en títulos y b-roll a pantalla completa, click en texto a mano,
rise + click + ding en la tarjeta de perfil. Volumen general en `reel.json` `sfx.gain`.

## Color de cámara
Los iPhone graban en HDR (HLG). `assemble.py` lo pasa a SDR con un LUT propio (`make_lut.py`). Exposición en
`config.json` `hdrExposure`: 0.62 es natural; bajala (0.55) si la piel se quema, subila (0.7) si queda oscuro.
