# `edicion.json` · el formato del editor profesional

`python -m kit.pro.montar anuncios/<slug>/edicion.json` (`--rapido` borrador sin superresolución,
`--fotos 20,120` fotogramas sueltos). Rutas relativas a la carpeta del anuncio. Ejemplo completo:
`ejemplos/onda-x/edicion.json`. El criterio para rellenarlo: `edicion-pro.md`.

```jsonc
{
  "salida": "mi-anuncio.mp4",
  "etiqueta_ia": "Vídeo generado con IA",
  "estilo": {"acento": "#3DF5FF", "antes": "#FF3B4E"},   // acento de la marca y el de antes del cambio
  "cambio": "S8",                                         // plano donde el producto cambia el mundo
  "musica": {"archivo": "audio/musica.wav", "bpm": 140, "db": -1.5, "ducking_db": 8.5,
             "tramos": [ … ]},
  "planos": [ … ],
  "grafismo": [ … ],
  "sonidos_db": -5,        // todos los efectos juntos respecto a la voz
  "sonidos": [ … ]
}
```

## Tiempos

Donde se pide un tiempo vale:
- un **número**: segundos del montaje (en `grafismo`/`sonidos`) o del plano (dentro de un plano:
  `zoom`, `efectos`, y `t` de títulos y marcas);
- `{"plano": "S4"}` inicio del plano · `{"plano": "S4", "t": 0.3}` 0,3 s después;
- `{"plano": "S15", "src": 1.76}` el segundo 1,76 **del clip** dentro de ese plano (para clavar un
  sonido al fogonazo aunque haya rampa);
- `{"plano": "S4", "palabra": 3}` cuando empieza la palabra 3 (desde 0) de la voz de ese plano;
- `{"plano": "S19", "fin": true}` final del plano · `{"fin_voz": true}` fin de la última voz ·
  `{"fin_musica": true}` donde acaba la música. Todos admiten `"t"` para sumar o restar.

## `planos[]`

| Campo | Qué |
|---|---|
| `id`, `clip` | Nombre del plano y clip (`vid/c3.mp4`) |
| `desde`, `hasta`, `vel` | Trozo del clip y velocidad. `desde` > `hasta` = marcha atrás |
| `tramos` | Rampa: `[[desde, hasta, vel], …]`. `vel` < 0,9 = cámara lenta (el editor interpola a 72 fps) |
| `voz` | `{"sub": "…"}` su propia voz; o `{"clip", "desde", "hasta", "vel", "en", "sub"}` la voz de otro clip sobre esta imagen (corte en L). Sin `sub`, subtítulos automáticos |
| `cara` | `true`: ancla el mentón encima del subtítulo (todo plano con persona) |
| `zoom` | `[[t, zoom], [t, zoom, "paso"|"lin"|"suave"]]`. `paso` = punch-in seco. < 1 encoge (producto sobre negro) |
| `foco` | `[x, y]` 0-1: hacia dónde se encuadra (si no hay `cara`) |
| `dy` | Desplaza la imagen en vertical (px) |
| `grado` | `antes`, `despues`, `inserto_antes`, `inserto`, `producto`, `natural` |
| `entrada` | Transición con el plano anterior: `corte`, `glitch`, `whip`, `zoom`, `flash` |
| `golpe`, `temblor` | Golpe de entrada (0,04-0,06) · cámara en mano (px) |
| `pip` | `{"clip", "desde", "etiqueta": "DIRECTO"}`: la cara del clip en una ventana sobre este plano |
| `efectos` | Lista de `[tipo, t, …]`, abajo |

**Subtítulos (`sub`)**: un token por palabra, `|` parte bloques en pantalla, `*palabras*` en color de
acento, `!palabra!` en rojo, `_` = palabra que se dice pero no se escribe (porque la escribe un cartel).
Si el número de tokens coincide con lo que oye Whisper, los tiempos salen de Whisper encajado en la
envolvente; si no, se reparten por longitud.

**`efectos`**: `["sacudida", t, px, dur]` · `["aberracion", t, dur, fuerza]` · `["destello", t, dur, alfa]`
· `["tinte", t, dur, alfa, "#color"]` · `["bloom", t, dur, extra]` · `["barrido", t, dur]` (brillo que cruza)
· `["zoom_seco", t, cantidad]`.

## `musica.tramos[]`

`{"desde": t, "hasta": t, "en": segundo de la canción, "apagada": true}`. Entre tramos, silencio. En
`hasta`, `"compas": true` redondea al siguiente golpe de la rejilla (con `bpm`). Patrón típico: apagada
hasta un tiempo antes del cambio → abierta desde el cambio → silencio en el remate → vuelve y cierra a
compás.

## `grafismo[]`

| `tipo` | Campos |
|---|---|
| `titulo` | `plano`, `lineas: [{texto, color, tam, y, t}]` |
| `cartel` | `plano`, `y`, `tam`, `trozos: [{texto, color, t, tachar, glitch}]` |
| `detras` | `plano` (o lista), `piezas: [{texto, x, y, tam, color, color2, brillo, t}]` (degradado de `color` a `color2`) |
| `orbita` | `plano`, `color`, `color2`, `vuelta` (s por vuelta) |
| `ondas` | `plano`, `pasos: [t…]`, `lados: [-1, 1…]` |
| `direccion` | `plano`, `lado`: `izq`/`der`, `pasos` |
| `aviso` | `desde`, `hasta`, `filas: [{t, izq, der, color}]` |
| `impacto` | `t: [t…]`, `color` |
| `marca` | `plano`, `t`, `texto`, `sub`, `y`, `tam` |
| `cta` | `t`, `texto`, `y` |

Colores: `#RRGGBB`, `blanco`, `rojo`, `cian`, `violeta`, `amarillo` o `acento`.

## `sonidos[]`

`{"t", "archivo", "db", "pan": -1…1 o [desde, hasta], "apagado", "pico", "rev", "vel", "desde", "dur", "grave"}`

- `pico`: en qué segundo del efecto está el golpe; el golpe cae en `t`.
- `vel` < 1 más grave y lento (0,5 convierte un impacto en un subgrave), > 1 más agudo y corto.
- `grave`: filtro que deja solo por debajo de esa frecuencia (Hz). `rev`: al revés (subida hacia un golpe).
- `apagado`: suena como el resto del mundo antes del cambio.
