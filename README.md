# /editar-reel

### Una skill de Claude Code por [@nicolebrener_digital](https://www.instagram.com/nicolebrener_digital)

Grabás tus clips con el celu, los dejás en una carpeta, escribís `/editar-reel` y Claude te devuelve el reel
terminado: elige la mejor toma de cada frase, corta los silencios y las trabadas, pone los subtítulos con tu
estilo, títulos detrás de tu cabeza, capturas, stickers y efectos de sonido. No abrís ningún editor: mirás el
resultado en el celu, decís qué cambiar y vuelve a renderizar.

Pensada para reels en **español**.

---

## Qué hace

1. **Transcribe todas tus tomas** con tiempos por palabra (Whisper, en tu compu, sin mandar nada a ningún lado).
2. **Arma el guion con tu mejor toma** de cada frase (podés repetir cada línea las veces que quieras) y saca las
   pausas y las trabadas, aunque estén en el medio de una frase.
3. **Corta desde el original en 4K**, con punch-ins para dar ritmo, y pasa el HDR del iPhone a color normal para
   que no quede lavado en Instagram.
4. **Subtítulos dinámicos**: Cal Sans amarilla, de 1 a 3 palabras, cada palabra aparece cuando la decís; las
   palabras clave salen solas, gigantes y de color, con un zoom de cámara.
5. **Te recorta del fondo** para poner títulos detrás de tu cabeza.
6. **Inserts animados**: tarjetas con capturas reales, b-roll, stickers, texto escrito a mano, pasos con flechas
   ("antes: tu app → ChatGPT → tu app") y tu perfil de Instagram con el botón "Seguir" en el cierre.
7. **Efectos de sonido** sutiles (pop, whoosh, click, ding), siempre por debajo de tu voz.
8. **Control de calidad**: todo dentro de la zona segura de Reels, revisa cada corte cuadro por cuadro y te da
   una copia liviana para el celu.

---

## Qué necesitás

- Mac, Windows o Linux. En Mac con Apple Silicon el recorte de fondo es mucho más rápido.
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [ffmpeg](https://ffmpeg.org), [Node.js 22+](https://nodejs.org), Python 3.10 a 3.13

No hace falta instalarlos a mano antes: la primera vez la skill revisa tu compu y te dice exactamente qué
comando pegar si falta algo.

| | Mac | Windows (PowerShell) | Linux |
|---|---|---|---|
| ffmpeg | `brew install ffmpeg` | `winget install --id Gyan.FFmpeg -e` | `sudo apt install ffmpeg` |
| Node.js | `brew install node` | `winget install --id OpenJS.NodeJS.LTS -e` | [nodejs.org](https://nodejs.org) |
| Python | `brew install python@3.12` | `winget install --id Python.Python.3.12 -e` | `sudo apt install python3.12 python3.12-venv` |

---

## Instalación

Pegale esto a Claude Code:

```
Instalá la skill de https://github.com/<tu-usuario>/editar-reel en ~/.claude/skills/editar-reel
```

O en la terminal:

```bash
git clone https://github.com/<tu-usuario>/editar-reel ~/.claude/skills/editar-reel
```

Después abrí Claude Code y escribí `/editar-reel`. La primera vez te pregunta tu nombre, tu usuario de
Instagram y dónde guardás los clips (tarda unos 2 minutos y no se repite).

---

## Cómo se usa

```
/editar-reel los clips de la carpeta "apps con ia" en el escritorio
```

Claude te muestra qué toma eligió para cada frase y sigue. Cuando termina te pasa el video. Pedile cambios
como se los pedirías a una editora:

- "en el segundo 12 dice Zapia, no sapia"
- "sacá la parte de Meta"
- "el subtítulo me tapa la boca al final"
- "menos efectos de sonido"
- "usá la otra toma del gancho"

Cada vuelta es un nuevo render (`v2`, `v3`...). Nunca se pisan las versiones anteriores y tus archivos
originales no se tocan.

---

## Personalizar el estilo

Todo el look está en `config.json` (colores) y `references/estilo.md` (las reglas que sigue Claude). Para usar
otros colores, cambiá `caption` (el color de los subtítulos) y `accents` (los de los destacados y títulos).

---

## Créditos y licencias

- Render: [HyperFrames](https://github.com/heygen-com/hyperframes) (Apache-2.0), HTML a video y recorte de fondo.
- Transcripción: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT).
- Animaciones: [GSAP](https://gsap.com) (se descarga al instalar, no viene en el repo).
- Tipografías: Cal Sans, Caveat e Inter, con [SIL Open Font License](assets/fonts/).
- Efectos de sonido: sintetizados por `scripts/setup.py`, propios.
- El código de esta skill: licencia MIT (ver [LICENSE](LICENSE)).

---

Hecho por [@nicolebrener_digital](https://www.instagram.com/nicolebrener_digital), IA y marketing.
