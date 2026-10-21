# Animaciones de lo que se dice

Íconos de línea que se dibujan solos al lado de la cabeza cuando la persona nombra algo concreto: dice
"calendario" y aparece un calendario que tilda un día; dice "pendientes" y aparece una lista que se va tildando.
Son el insert `anim` de `reel.json` (los íconos están en `scripts/anims.py`).

```json
{"type": "anim", "icon": "calendar", "start": 8.45, "end": 10.3, "pos": "right"}
```
| Campo | Default | Para qué |
|---|---|---|
| `icon` | (obligatorio) | uno de la tabla de abajo |
| `pos` | `"right"` | `"right"` o `"left"`: al costado de la cabeza (x 35-1045, y 780) |
| `x`, `y`, `size` | según `pos`, 780, 260 | a mano, si hace falta esquivar algo |
| `style` | `"line"` | `"badge"`: ícono oscuro sobre un cuadrado blanco redondeado (se lee sobre fondos claros o con mucho ruido) |
| `label` | ninguno | texto corto abajo del ícono ("3 días", "24/7"); solo si suma un dato que no está en el subtítulo |
| `color`, `accent` | blanco, el `emphColor` de los subtítulos | color de la línea y del detalle (el tilde, la flecha) |
| `sfx` | `"pop"` (bajito) | `null` para que no suene |

## Qué ícono para qué palabras
| icon | Se dibuja | Cuando se dice... |
|---|---|---|
| `calendar` | calendario que tilda un día | calendario, reunión, agenda, turno, fecha, coordinar, semana |
| `clock` | reloj con la aguja girando | tiempo, horas, minutos, días, "a los 3 días", rápido, ahorrar tiempo, recordatorio |
| `chat` | globo con los tres puntitos escribiendo | WhatsApp, chat, mensaje, responder, conversación, DM |
| `send` | avión de papel que flota | enviar, mandar, se envía, automáticamente, propuesta |
| `bell` | campana que se mueve + punto de aviso | notificación, aviso, recordatorio, seguimiento, "no me olvido" |
| `list` | lista que se va tildando | pendientes, tareas, organiza, prioridad, to-do, pasos |
| `check` | círculo con tilde | listo, aprobar, confirmar, hecho, resuelto, "la apruebo" |
| `shield` | escudo con tilde | permiso, autorización, seguro, privacidad, control |
| `lock` | candado que se abre | contraseña, acceso, desbloquear, privado |
| `bulb` | lamparita con rayos | idea, tip, truco, "lo que nadie te dice", aprender |
| `sparkle` | destellos | IA, inteligencia artificial, magia, automático, nuevo |
| `robot` | robot que parpadea | agente, asistente, bot, IA que hace cosas |
| `chart` | gráfico que sube | crecer, ventas, resultados, más clientes, métricas |
| `money` | moneda con $ | plata, precio, cobrar, gratis, ahorrar, facturar |
| `search` | lupa que se mueve | buscar, encontrar, revisar, investigar, "encuentra huecos" |
| `mail` | sobre con punto de aviso | mail, correo, newsletter, bandeja |
| `heart` | corazón que late | me encanta, favorito, clientes felices, comunidad |
| `phone` | celular con aviso que late | celular, app, llamada, "desde el teléfono" |
| `user` | persona | cliente, persona, equipo, perfil |

## Cuándo sí y cuándo no
- **Sí** cuando la frase nombra algo que se puede dibujar (un objeto, una acción concreta) y es parte de la idea.
  Empezá ~0.1 s antes de la palabra; duración 1.5-2.5 s (que la animación alcance a hacer su movimiento).
- **Una cada 4-8 segundos como mucho.** Si cada frase tiene un ícono, ninguno se nota. Elegí los momentos en que
  el video no tiene otra cosa pasando.
- **No** si en ese momento ya hay en pantalla una captura, una tarjeta o una grabación que muestra eso mismo,
  ni en el mismo momento que un `title`, un `number` o una tarjeta del mismo lado.
- **Nunca sobre la cara.** Siempre al costado de la cabeza (`pos`), y alterná los lados si hay dos seguidas.
  Mirá `snaps.jpg`: si el ícono toca la cara, el pelo de adelante o la mano, movelo.
- Mismo ícono, misma idea: si "WhatsApp" ya tuvo su `chat`, no lo repitas cada vez que se dice.
- Si dudás entre dos íconos, elegí el que muestra la acción ("encuentra huecos" -> `search`, no `calendar`).
