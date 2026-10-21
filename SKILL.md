---
name: editar-reel
description: Edita reels verticales de Instagram/TikTok de punta a punta a partir de clips crudos de celular, en español. Elige la mejor toma de cada frase, corta silencios y trabadas, hace punch-ins desde 4K, convierte el HDR del iPhone, pone subtítulos Cal Sans amarillos de 1 a 3 palabras con las palabras clave grandes y de color, títulos detrás de la cabeza, tarjetas de b-roll, stickers, texto a mano, pasos animados, la tarjeta de perfil para el CTA y efectos de sonido, todo dentro de la zona segura de Reels. Usar con /editar-reel o frases como "editame estos clips", "armá el reel", "editá el video de la carpeta X", "cortá esto en un reel".
---

# /editar-reel

Clips crudos adentro, reel terminado afuera. La persona nunca abre un editor: mira una copia en el celu, da notas,
y cada vuelta es un rebuild + render.

`SK` = la carpeta de esta skill (la que tiene este SKILL.md), con ruta completa.
`PY` = `SK/.venv/bin/python` (Windows: `SK/.venv/Scripts/python.exe`). Todos los scripts corren con `PY`.
`HF` = `npx --yes hyperframes@0.8.34` (HyperFrames: HTML a video, Apache-2.0).

Antes de armar el primer reel de la sesión leé `references/estilo.md` (el look), `references/animaciones.md`
(qué ícono animado va con qué palabras), `references/pantalla-completa.md` (cortes que explican) y
`references/errores.md`
(cada trampa en la que ya caímos). `references/plan.md` tiene el formato completo de `edl.json`, `captions.json`
y `reel.json`.

## Paso 0: setup (la primera vez, y si algo falla)

1. Si no existe `SK/config.json`, preguntá en un solo mensaje: nombre (va en la tarjeta de perfil; formato
   `Nombre Apellido | bajada`), usuario de Instagram, carpeta donde caen los clips, carpeta para los proyectos
   (default `~/reel-edits`). Los colores tienen default (`references/estilo.md`); preguntá solo si quiere otros.
2. Corré `python3 "SK/scripts/setup.py"` (en Windows `py -3`). Imprime una línea STATUS por cosa y READY al final.
   Si algo dice FALTA, la línea trae el comando exacto para instalarlo: dáselo y esperá.
   faster-whisper necesita Python 3.10 a 3.13; si la única Python es 3.14+, la línea lo dice.
3. Guardá `SK/config.json` (nunca secretos):
   ```json
   {"name": "Nombre Apellido | bajada", "instagram": "usuario", "clipsDir": "~/Desktop/videos",
    "projectsDir": "~/reel-edits", "colors": {"caption": "#FFD60A",
    "accents": ["#FF3EA5", "#00E0FF", "#7CFF4F", "#FF7A00"]}, "hdrExposure": 0.62,
    "whisperModel": "small", "language": "es"}
   ```

## Reglas que no se negocian
1. Todo adentro de la zona segura de Reels: arriba 220, abajo 1470, costados 35, derecha 100 desde y 1155.
   `build.py --safe` la dibuja en rojo para las capturas.
2. Los subtítulos dicen lo que se dijo. Corregí lo que Whisper escucha mal (marcas, nombres, voseo: "usas" ->
   "usás", "comenta" -> "comentá"). Nunca cambies el sentido. Si una palabra es dudosa y cambia el sentido,
   preguntá antes de publicar.
3. Sin contorno en la tipografía: solo sombra suave (ya viene así en `build.py`).
4. Los efectos de sonido van por debajo de la voz, nunca más fuerte.
5. Nada de personas reales ajenas en pantalla sin que la persona lo apruebe: si una grabación de pantalla muestra
   nombres completos, teléfonos, mails o chats de terceros, recortá o tapá esa parte y avisá.
6. Los números de la tarjeta de perfil (seguidores, publicaciones) solo si la persona los da. Nunca inventados.
7. Nunca borres ni modifiques los originales. Cada render es una versión nueva en `renders/`.
8. Los cortes se verifican en el render final (`check.py`), no en capturas.

## Flujo

### 1. Ingesta
Clips: los que nombra la persona, o la carpeta que dice dentro de `clipsDir`. Proyecto: `<projectsDir>/<slug>/`.
```bash
PY SK/scripts/ingest.py <proyecto> "<carpeta o clips>" --prompt "marcas, nombres, palabras raras"
```
Mirá `work/sheets.jpg` (encuadres, ángulos, cuáles son grabaciones de pantalla) y leé `transcript.txt`.

### 2. Elegir tomas -> `edl.json`
- Reconstruí el guion: la gente repite cada frase hasta que sale. Usá la ÚLTIMA toma completa y limpia, salvo
  que la persona diga otra cosa.
- Puntos exactos: el primer `s` de Whisper suele ser 0.00 aunque haya silencio; confirmá con
  `ffmpeg -i clip -af silencedetect=n=-35dB:d=0.25 -f null -` y entrá ~0.06 s antes de que termine el silencio.
  Salí donde empieza el silencio después de la última palabra.
- Una palabra que dura más de ~1 s en el transcript esconde una pausa o una trabada adentro. Re-transcribí esa toma
  con el modelo medium (`references/errores.md` tiene el snippet) y cortá la trabada en dos segmentos.
- Dos segmentos seguidos del mismo encuadre: alterná zoom 1.0 / 1.35 (cx 0.5, cy 0.38 en el zoom).
- Mostrale a la persona la tabla del EDL (id, frase, clip, zoom) y seguí sin esperar.

### 3. Armar y transcribir el corte
```bash
PY SK/scripts/assemble.py <proyecto>     # aroll.mp4 + segments.json + words.json (Whisper medium del corte final)
```
Leé `words.json` de corrido: es la prueba de que el corte dice bien la frase. Si una frase quedó cortada o
repetida, ajustá el EDL y volvé a correr (los segmentos que no cambiaron se reusan).

### 4. Recorte de fondo (solo si va a haber títulos detrás de la cabeza)
```bash
PY SK/scripts/cutout.py <proyecto>       # en segundo plano: ~3 min por minuto de video en Apple Silicon
```

### 5. Subtítulos -> `captions.json`
```bash
PY SK/scripts/captions.py <proyecto> --force --emph "palabra clave,frase clave" --fix "usas=usás;una agente=un agente"
```
- Destacados: 1 cada 4-8 segundos, las palabras que llevan la idea (la marca, el número, el remate). Salen solas,
  grandes, en mayúscula y en un color de acento, con zoom de cámara.
- Después editá `captions.json` a mano si hace falta (juntar "día a día", mover un destacado).

### 6. Plan creativo -> `reel.json`, build y capturas
Escribí `reel.json` con los inserts (ver `references/plan.md` y las ideas de `references/estilo.md`):
títulos detrás de la cabeza para cada sección, tarjetas con capturas reales, stickers, texto a mano, pasos,
la tarjeta de perfil en el CTA, flashes en los cambios de tema.

**Animá lo que se dice.** Leé `words.json` buscando cosas que se puedan dibujar (un calendario, un chat, una
lista de pendientes, un permiso, la IA) y poné un `anim` al costado de la cabeza justo cuando se nombran: el ícono
se dibuja solo y se mueve. La tabla de qué ícono va con qué palabras y las reglas (una cada 4-8 s, nunca sobre la
cara, nunca encima de una captura que ya muestra eso) están en `references/animaciones.md`. Aunque el video ya
venga editado y la persona pida "solo subtítulos", proponé las que sumen: es lo que más lo hace dinámico.

**Cortes a pantalla completa que explican.** Cada 8-15 s, cuando una frase se entiende mejor viéndola, cortá 1.5-3 s
a una escena animada (`scene`: un chat que se escribe, una agenda con huecos libres, pendientes que se tildan, un
número que cuenta, una frase clave), a un clip de stock de Pexels o a un clip de la persona
(`scripts/broll.py`). Cómo elegir, cómo bajarlos y las reglas: `references/pantalla-completa.md`.
```bash
PY SK/scripts/build.py <proyecto> --safe
cd <proyecto> && HF lint                 # 0 errores
PY SK/scripts/snap.py <proyecto> auto    # o tiempos: 3.3,8.4,17.2
```
Mirá `work/snaps.jpg`: nada tapa la cara, todo se lee, nada sale de la zona roja, los títulos detrás de la
cabeza se ven al menos 70 %. Corregí y repetí.

### 7. Render y control
```bash
PY SK/scripts/build.py <proyecto>        # sin --safe
cd <proyecto> && HF render -o renders/<slug>-vN.mp4 --quality high     # en segundo plano: tarda varios minutos
PY SK/scripts/check.py <proyecto> renders/<slug>-vN.mp4
```
Mirá `work/cut_check.jpg` (cada par antes|después muestra el plano nuevo limpio) y el audio (pico entre -1 y -3 dB).

### 8. Entregar
Pasale la copia `-celu.mp4` y el render completo. Contale en criollo qué hiciste y qué decisiones son suyas
(tomas dudosas, palabras que no se entienden, datos que faltan). En cada vuelta de notas: cambiá JSON, build,
render como `vN+1`. Nunca pises versiones.

## Notas comunes y cómo resolverlas
| Nota | Qué tocar |
|---|---|
| "esta palabra está mal" | `captions.json` (o `--fix` y `captions.py --force`) |
| "el subtítulo me tapa" | `"y"` de ese grupo en `captions.json`, o `reel.json` `captions.y` |
| "sacá esta toma / usá la otra" | `edl.json` -> `assemble.py` -> (cutout si hay títulos detrás) -> captions |
| "más/menos efectos de sonido" | `reel.json` `sfx.gain` (0 apaga todo) |
| "muy oscuro / muy claro" | `config.json` `hdrExposure` (0.5 a 0.75) -> `assemble.py` |
| "sin zoom en las palabras" | `reel.json` `"autoZoom": false` |
