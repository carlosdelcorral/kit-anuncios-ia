# Montaje · el `anuncio.json` (editor sencillo)

> **Para la entrega se usa el editor profesional** (`kit.pro.montar`, `edicion-pro.md`). Este editor
> sirve para borradores rápidos.

El anuncio entero se describe en un JSON y `python -m kit.montar anuncios/<slug>/anuncio.json`
lo convierte en un MP4 1080×1920 a −14 LUFS con su `informe.md`. Cambiar el montaje es cambiar el
JSON y volver a lanzar: no se regenera nada ni se paga nada. Ejemplo completo:
`ejemplos/onda-x/anuncio.json` (24 planos, 31 s).

## El estilo por defecto: dinámico, sin silencios, con muchas tomas

Un anuncio que se queda quieto pierde. Estas son las reglas de partida (salen de una demo que se
puntuó con un 5 y se rehízo):

1. **Cero silencio.** Todo plano que habla lleva `"apretar": true`: el editor corta las pausas de
   dentro (medidas por la envolvente de la voz, no por Whisper) y alterna el zoom en cada corte,
   para que se lea como un cambio de toma. Pim, pam, pam.
2. **Un cambio cada 1-2,5 s.** Más cortes, más cortos: la cara se intercala con **insertos sin
   cara** — el producto en macro, las manos, la pantalla, el contexto (el videojuego, la cocina, el
   ordenador). Los insertos los hace seedance, que es barato.
3. **Varios tamaños y ángulos**: webcam, selfie, cenital, macro, primer plano, diseño streamer. Nunca
   dos planos seguidos iguales.
4. **Los insertos duran múltiplos del tiempo de la música** (`python -m kit.sonido --ritmo
   musica.wav` da el tempo): el corte cae en el golpe.
5. **Sonido real, nunca sintético**: música de Lyria (`kit.generar musica`) y efectos de Stable Audio
   (`kit.generar sonido`). Pocos y clavados a lo que pasa: disparo con disparo, pasos con pasos.
6. **Una idea sonora** si el producto la permite (cascos, altavoces, un coche): el antes y el
   después se oyen, no se cuentan (`musica.apagada` + `"apagado": true` en los efectos).
7. **El remate del final**, mejor sobre el producto que sobre la cara: la última frase con `audio`
   de otro clip encima del plano de producto, y medio segundo más de plano para que aterrice.
8. **Que parezca un móvil, no una cámara de cine**: `"realismo": {"grano": "movil", "voz": "solapa"}`
   en todo el anuncio y `"movil": {"mano": 1, "exposicion": true, "frontal": true}` en los planos que
   «sujeta» una persona (selfies, andando). **Nunca `mano` en un plano que nadie podría sostener** (el
   cenital del techo, el coche fijo): un temblor imposible delata más que ninguno.
9. **Un momento a voz sola**: callar la música justo en la frase fuerte («uno contra tres») y que
   vuelva de golpe en el siguiente plano pesa más que cualquier efecto.

## Cómo se decide cada corte

1. `python -m kit.revisar anuncios/<slug>/vid/*.mp4 --guion anuncios/<slug>/guion.json` da lo que
   dice cada clip de verdad, las pausas, las palabras de más y las repeticiones.
2. **Los bordes** (`desde`/`hasta`) se ponen a mano: entrada ~0,1 s antes de la primera palabra y
   salida ~0,2 s después de la última. Whisper adelanta la primera palabra; en interiores fíate de
   la envolvente (`revision.json` trae ambas pistas).
3. **Las pausas de dentro** las quita `apretar` — en interiores. En exteriores (calle, coche, terraza)
   el ambiente tapa los silencios y la envolvente no los ve: ahí se parte el plano a mano con los tiempos
   de cada palabra de `revision.json` (y se quitan las repeticiones que mete omni, «mediodía, mediodía»).
   Si la hora o el sitio ya salen en pantalla, la frase que lo dice sobra. Si el modelo añadió una frase buena que no estaba
   en el guion (pasa: «vale, le tengo, le tengo»), úsala en un plano propio.
4. **Lo que se estropea al final de un clip** (un logo que aparece en la ropa, una mano rara) se deja
   fuera con `hasta`, y la frase que faltaba se pone con `audio` sobre otro plano.

## Campos

```jsonc
{
  "salida": "mi-anuncio.mp4",
  "estilo": {"fuente": "Lato Black", "texto": "#FFFFFF", "acento": "#A259FF", "mayusculas": true},
  "etiqueta_ia": "Vídeo generado con IA",          // obligatoria con personas generadas
  "subtitulos": {"activos": true, "resaltar": ["lag", "cascos"]},
  "realismo": {"grano": "movil", "voz": "solapa"},  // grano de sensor que sube en sombras; voz de micro de solapa
  "musica": {"archivo": "audio/musica.wav", "desde": 0.19, "db": -7, "ducking": true, "ducking_db": 7,
             "apagada": [[0, {"plano": 6, "t": 0.85}]],
             "silencios": [[{"plano": 13, "t": 0.75}, {"plano": 14, "t": 2.4}]]},
  "planos": [ … ],
  "juntas": [ … ],          // una por hueco entre planos (planos − 1), en los planos que TÚ escribes
  "rotulos": [ … ],
  "sonidos": [ … ]
}
```

- Tiempos: `{"plano": 3, "t": 1.2}` = 1,2 s después de que empiece el plano 3 **tal como lo escribes**
  (el editor lo reubica solo si `apretar` parte el plano) o un número = segundo absoluto del montaje.
- `musica.desde`: dónde empieza la canción (para que el primer golpe caiga en el 0). `db`: nivel
  respecto a la voz (−6 a −12 en anuncios con energía). `apagada`: tramos en que suena como con unos
  cascos malos y al final **se abre**. `silencios`: la música se calla (antes de un remate).

### `planos[]`

| Campo | Qué |
|---|---|
| `clip`, `desde`, `hasta` | El trozo del clip, en segundos del clip |
| `apretar` | `true`: quita las pausas de dentro y alterna el zoom en cada corte |
| `voz` | `false` si el plano no aporta audio (insertos, producto) |
| `audio` | `{"clip", "desde", "hasta"}`: la voz de **otro** clip sobre esta imagen. Pon siempre `hasta`: sin él suena todo lo que venga detrás (y una frase se oye dos veces) |
| `voz_db` | Sube o baja la voz de este plano (±3 dB) si el modelo la dijo más floja |
| `pip` | `{"clip", "desde", "y_cara"}`: diseño streamer — este plano a pantalla completa y la cara del otro clip en una ventana. Con `"voz_de": "pip"` se oye la voz de la ventana |
| `zoom.base` | Tamaño del plano (1 = completo; 1,1-1,2 = más cerca) |
| `zoom.entrada` | Golpe de entrada: arranca un 5-14 % más grande y se asienta en 0,1 s |
| `zoom.empuje` | Acercamiento lento a lo largo del plano (0,03-0,08) |
| `efectos[]` | Ver abajo; `t` en segundos desde que empieza el plano |
| `movil` | `{"mano": 0.5-1.2, "exposicion": true, "caidas": [t], "enfoque": [t], "frontal": true}`: temblor de mano (deriva lenta, no vibración), exposición y balance que respiran (con una caída en `t` cuando algo tapa la luz), el enfoque que busca en `t` (el producto se acerca a la lente), la distorsión del frontal del iPhone |
| `abre_negro` | s en negro al principio del plano (el hook que empieza por el sonido) |
| `noche` | 0-1: etalonaje de móvil a oscuras (más oscuro, frío, menos color). Los modelos iluminan de más las escenas de noche |

### `efectos[]`

| `tipo` | Campos | Para qué |
|---|---|---|
| `zoom_seco` | `t`, `cantidad` (0,12-0,3) | Crash zoom en un golpe o una palabra |
| `sacudida` | `t`, `fuerza` (14-30 px) | El impacto: un cartel, un disparo, una revelación |
| `glitch` | `t`, `dur` | Corte de señal de 0,1-0,2 s |
| `tinte` | `t`, `dur`, `color`, `alfa` | Fogonazo de color (rojo cuando te dan) |
| `rampa` | `tramos: [[desde, hasta, velocidad], …]` | Cámara lenta / rápida. Solo planos **sin voz** |
| `barrido_luz` | `t`, `dur` | Brillo que cruza el producto |

### `juntas[]`

| `tipo` | Qué | Cuándo |
|---|---|---|
| `corte` | Corte seco | Por defecto: casi todo |
| `barrido` | Desenfoque horizontal (pon un whoosh en `t: -0.38` del plano siguiente) | Cambio de sitio, entrada al producto. 1-3 por anuncio |
| `flash` | Fundido a blanco | El momento clave (se pone los cascos) |
| `negro` | Fundido rápido a negro y desde negro | Saltos de hora o de noche |
| `jcut` (s) | El audio del plano siguiente entra antes que su imagen | 0,15-0,3 s: esconde el primer fotograma quieto de un clip generado |

### `rotulos[]`

| `estilo` | Qué |
|---|---|
| `hook` | La frase del gancho, con caja. 5-8 palabras, en el primer segundo |
| `cartel` | 1-3 palabras gigantes en el color de acento, con golpe («NO ES LAG», «1 VS 3»). 1-2 por anuncio; tapa los subtítulos mientras dura |
| `producto` | Claim sobre el plano de producto |
| `cta` | La acción, sobre una caja de acento |
| `hora` | La hora grande en la parte alta («03:12», «15:40 · 34 °C»), para los formatos de 24 h |

El editor ajusta el tamaño a la zona segura y **avisa** de lo que quede fuera.

### `sonidos[]`

`{"plano": 7, "t": 0.0, "archivo": "audio/sfx-pasos.wav", "pan": "izq-der", "db": -2, "dur": 1.9, "apagado": false}`

`pan`: `izq`, `der`, `izq-der`, `der-izq` (con auriculares se oye moverse). `dur` recorta el efecto.
`apagado`: suena mono y sin agudos. Los efectos se ajustan todos juntos por debajo de la voz; `db`
los equilibra entre sí.

## Qué comprobar antes de entregar

- **Sincronía: deriva 0 ms** en el informe. El editor cuenta los fotogramas de cada plano y se para si
  sobra uno: un fotograma de más por plano retrasaba la imagen ~0,7 s al final de un anuncio de 24.
- El volumen de la voz es uno por **clip** (no por trozo): al quitar pausas, los trozos de una misma
  frase suenan igual. Si una frase concreta quedó floja, `voz_db`.
- Ningún aviso **FUERA DE ZONA**.
- `informe.md`: −14 LUFS (±1), la transcripción coincide con el guion, los efectos que esperabas.
- Una tira de fotogramas (un fotograma por segundo): ¿cambia algo cada 1-2 s? ¿Hay algún plano quieto
  de más de 3 s? Si lo hay, se parte o se intercala un inserto.
