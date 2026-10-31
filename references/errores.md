# Trampas en las que ya caímos (no repetir)

## Audio y transcripción
- **Whisper pone la primera palabra en 0.00** aunque haya medio segundo de silencio. Los puntos de entrada salen
  de `silencedetect`, no del transcript.
- **Una palabra que "dura" 2-8 segundos** (`herramientas[5.24-13.50]`) es una pausa, una trabada o una toma repetida
  escondida. Re-transcribí esa toma con medium y mirá qué hay adentro:
  ```bash
  PY - <<'EOF'
  from faster_whisper import WhisperModel
  import subprocess, numpy as np
  raw = subprocess.run(['ffmpeg','-v','error','-ss','3.5','-t','6','-i','CLIP.MOV','-ac','1','-ar','16000',
                        '-f','s16le','-'], capture_output=True).stdout
  a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
  m = WhisperModel('medium', device='cpu', compute_type='int8')
  s, _ = m.transcribe(a, language='es', word_timestamps=True)
  print(' '.join(f"{w.word}[{w.start+3.5:.2f}]" for x in s for w in x.words))
  EOF
  ```
  Si hay una trabada ("con tus ser... Meta por su lado lanzó..."), muchas veces la persona repite TODA la frase
  más adelante en la misma toma: usá esa repetición entera en vez de remendar.
- **Una palabra dudosa que cambia el sentido** ("las herramientas DE IA" cuando el video dice que mueren las que
  NO tienen IA): no la inventes ni la arregles en silencio. Usá otra toma o preguntá.
- `words.json` sale de transcribir el corte final (no de los clips), así un corte en medio de una palabra nunca
  corre los subtítulos. Leelo entero después de `assemble.py`: es el control de que el corte se entiende.
- faster-whisper rompe con PyAV nuevo (`metadata_errors`): por eso decodificamos el audio con ffmpeg nosotros.
- faster-whisper no instala en Python 3.14+. `setup.py` busca una 3.10-3.13.

## Imagen
- **iPhone = HDR (HLG, BT.2020, 10 bits).** Sin conversión queda gris y lavado. `assemble.py` usa un LUT propio
  porque muchos ffmpeg no traen `zscale`. Exposición 0.62; con 1.0 la piel se quema.
- ffmpeg 8+ ya no acepta `-vsync`: usar `-fps_mode passthrough`.

## Recorte de fondo y títulos detrás de la cabeza
- La máscara incluye lo que está "pegado" a la cabeza: una lámpara de techo, un estante. Si el cutout tapa todo,
  la lámpara tapa el título.
- **HyperFrames ignora `clip-path` (CSS o GSAP) en el video del cutout**: compone los cuadros del video por su
  cuenta. Por eso `build.py` hornea la línea de corte en una copia del webm con ffmpeg (`drawbox ... replace=1`).
- Medir la cabeza desde la máscara no sirve (la lámpara la arruina). Los títulos van arriba de la zona segura
  (y 228) y la línea de corte deja ~80 % de la letra a la vista.
- En planos con zoom la cabeza llega casi al borde de arriba: no hay lugar para títulos "muy" detrás. No bajes
  la línea de corte por debajo de lo que permite leer el 70 % de cada letra.

## HyperFrames / lint
- Cada `<audio>` necesita `id`, `data-duration` y su propio `data-track-index` (si no: pistas superpuestas).
- Toda animación de salida que termina justo cuando termina el clip necesita un `tl.set(..., {opacity:0}, fin)`
  (`gsap_exit_missing_hard_kill`).
- Varios `fromTo` sobre el mismo elemento (el flash): `immediateRender:false` y un `tl.set` inicial en 0.
- Las letras de un título van dentro de un `span` por palabra (`.tw`): si no, el título parte palabras al medio.
- `nth-of-type` cuenta etiquetas, no clases: los chips llevan clase con índice (`.c0`, `.a1`).
- El render tarda bastante más que el video (varios minutos para 1 min con cutout, más en 4K): siempre en segundo plano.
- Un render sin `--resolution portrait-4k` sale en 1080 aunque `aroll.mp4` sea 4K: `check.py` lo avisa.
- Proyectos armados antes del 4K tienen `aroll.mp4` en 1080: para un render 4K de verdad, correr `assemble.py` otra
  vez (y `cutout.py` si hay títulos detrás). Con el `aroll` viejo el render sale 4K pero el video es 1080 escalado.

## Contenido
- Las grabaciones de pantalla suelen mostrar nombres completos, teléfonos y chats de otras personas. Recortá.
- Los números de seguidores no se inventan.

## Escenas y b-roll
- **Sin emojis** en textos de escenas, tarjetas o subtítulos: el render no tiene fuente de emojis (salen cuadraditos).
- Los nombres de clase CSS de cada insert son globales: una clase repetida entre dos inserts (`.num` del número
  con contorno y el contador de `stat`) vuelve invisible a uno de los dos. Prefijá las clases nuevas.
- Un contador con `onUpdate` no se ve en el render (HyperFrames salta de cuadro en cuadro): `stat` usa un
  `tl.set` de texto por cuadro.
- Las grabaciones de pantalla de macOS tienen un espacio raro (U+202F) antes de "PM" en el nombre: usá un glob
  (`Screen*7.32*`) en vez de escribir el nombre a mano.
- **`mix-blend-mode` (CSS) sobre el video se ve en `snap.py` pero NO en el render**: HyperFrames compone los cuadros
  del video por su cuenta. Por eso la `light` se hornea en el a-roll con ffmpeg (`lit_aroll` en `build.py`): luz
  con `blend=overlay` sobre la pared y el recorte encima. Revisá la luz en un cuadro del render, no en las capturas.
- En zsh, `$m[b]` dentro de un filtro de ffmpeg es un subíndice de array: escribí `${m}[b]`.
- Con punch-in la cabeza ocupa casi todo el ancho: los íconos van a una esquina de arriba (y ~235), no al costado.
