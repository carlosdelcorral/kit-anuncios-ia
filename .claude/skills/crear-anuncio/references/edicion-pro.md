# Edición profesional · el criterio

Esto es lo que hace que un anuncio con avatar deje de parecer "vídeo de IA montado" y parezca una
pieza de agencia. Léelo **entero** antes de escribir el `edicion.json` de cualquier anuncio. El
formato del JSON está en `edicion-json.md`; el ejemplo completo, en `ejemplos/onda-x/edicion.json`
(29 s, 27 planos: la v3 de la demo).

El editor profesional es `python -m kit.pro.montar anuncios/<slug>/edicion.json`. El editor sencillo
(`kit.montar` + `anuncio.json`, ver `montaje.md`) sigue ahí para borradores rápidos, pero **la entrega
se monta con este**.

## La idea que lo gobierna todo

**Imagen y sonido cuentan lo mismo a la vez.** Un efecto suelto no impresiona; impresiona que el color,
el sonido, el texto y el corte cambien en el mismo fotograma porque ha pasado algo en la historia. En
ONDA X, cuando se pone los cascos, en un solo instante: el sonido pasa de mono apagado a estéreo, el
color de desaturado a vivo, entra un destello y la música revienta. El espectador entiende el producto
sin que nadie se lo explique.

Antes de tocar el JSON, escribe en una línea **cuál es el momento de cambio** del anuncio (el drop): el
instante en que el producto entra y el mundo cambia. Todo el montaje se organiza alrededor de él.

## La estructura (se adapta a cada guion, pero casi siempre es esta)

| Bloque | Qué pasa | Técnica típica |
|---|---|---|
| **Hook** (0-1,5 s) | Lo más fuerte primero, sin presentación. Titular en el primer fotograma | Titular que entra a golpes, sacudida, rampa de velocidad en el impacto |
| **Reacción / problema** | La cara reacciona; se nombra el enemigo | Transición glitch, punch-in en la palabra clave, cartel gigante (NO ES LAG) |
| **Giro** | El enemigo equivocado → la verdad | Inserto de contexto mientras sigue la voz (corte en L) |
| **Producto** | Aparece, se abre, se enciende | Zoom a través, cámara rápida hasta el gesto clave, corte en acción |
| **El cambio (drop)** | El producto entra en uso | Destello + color que se abre + música que revienta, a la vez |
| **Demostración** | Se ve funcionar (lo que se oye se ve) | Grafismo detrás del sujeto, ondas, indicadores, diseño streamer |
| **Clímax** | La prueba: el resultado | Cámaras lentas en el impacto, HUD, crash zoom, silencio antes del remate |
| **Marca y CTA** | Nombre, remate, acción | Logotipo letra a letra, remate sobre el producto, botón que late |

## Reglas que no se rompen

1. **Algo cambia cada 0,5-1,5 s.** Ningún plano de más de 3 s. Si el clip es largo, se parte con un
   punch-in (cambio de tamaño en seco) o se intercala un inserto.
2. **Cero aire muerto.** Los bordes de cada frase salen de la **envolvente de la voz**, no de Whisper
   (Whisper adelanta hasta 0,4 s la primera palabra). Entrada ~0,08 s antes de la voz, salida ~0,14 s
   después. El editor lo hace solo con `voz`; tú eliges los trozos.
3. **El subtítulo nunca tapa la boca.** Omni encuadra la cara en el centro del 9:16 y la zona segura
   acaba en y 1248, así que el texto caería sobre la boca. Solución: `"cara": true` en todo plano con
   persona. El editor ancla el mentón justo encima del subtítulo y el zoom hace crecer la cara hacia
   arriba. Si el informe avisa de que tapa la barbilla, sube el zoom de ese plano.
4. **Superresolución siempre en la entrega** (la hace el editor; `--rapido` solo para probar).
5. **Nunca dos planos seguidos iguales**: cambia tamaño, ángulo o tipo (cara → inserto → cara cerrada).
6. **Cámara lenta solo en planos sin voz** (el editor interpola a 72 fps). La voz se puede acelerar
   un 5-10 % con su imagen (`vel` 1,05-1,1) si el modelo habla lento.
7. **El texto grande es la voz hecha imagen**: si el cartel dice la palabra, esa palabra se oculta del
   subtítulo (`_`) para no repetirla.
8. **Un solo color de acento** (el de la marca). Si hay antes/después, el acento de "antes" es rojo
   (peligro) y el de después el de la marca (`estilo.antes` / `estilo.acento`, `cambio`).
9. **Etiqueta de IA** siempre (el editor la pone). Nada de texto encima de la etiqueta del producto.
10. **Sonido real, nunca sintético.** Pocos efectos y clavados a lo que se ve. Los derivados de un
    efecto real (más grave, al revés, recortado) valen; los pitidos de sintetizador, no.

## El catálogo de técnicas y cuándo usarlas

**Imagen**
- **Punch-in** (zoom en `"paso"` sobre una palabra): para la palabra que importa. 1-3 por anuncio.
- **Crash zoom** (`zoom_seco`): en frases cortas de tensión ("Uno.", "Dos.").
- **Golpe de entrada** (`golpe` 0,04-0,06): da energía al corte de una cara.
- **Temblor** (`temblor` 4-8 px): cámara en mano en el momento de tensión, no en todo.
- **Rampa de velocidad** (`tramos` con 0,45-0,5 en el impacto y 1,6-2 alrededor): el sello de un
  montaje de acción. En disparos, golpes, el producto que cae o se enciende.
- **Marcha atrás** (`desde` > `hasta`): cuando un gesto natural sirve al revés (girar la cabeza hacia
  un sonido). Solo en planos sin voz.
- **Sacudida + aberración cromática**: el impacto. Nunca de adorno.
- **Tinte** de color en un fogonazo (rojo cuando te dan).
- **Etalonaje en dos estados**: `antes`/`inserto_antes` (desaturado, frío) hasta el cambio y
  `despues`/`inserto` después. `producto` para el producto sobre negro; `natural` si no hay antes/después.
- **Producto encogido sobre negro** (zoom < 1 y `dy`): el fondo negro se funde solo y deja sitio al
  logotipo encima.

**Transiciones** (la mayoría de cortes son secos; estas son el condimento)
- `glitch`: cambio de mundo (juego ↔ persona, a la vista del directo). 2-3 por anuncio.
- `whip` (latigazo): cambio de sitio o de idea con energía.
- `zoom` (zoom a través): entrar al producto.
- `flash`: el momento de cambio y el cierre. Máximo 2.

**Grafismo**
- `titulo`: el hook escrito, 5-8 palabras en 2-3 líneas que entran a golpes. Solo en el hook.
- `cartel`: 1-3 palabras gigantes que resumen la idea (NO ES LAG, 1 VS 3). Con `tachar` para
  desmontar una creencia. 1-2 por anuncio.
- `detras`: texto grande **detrás** del sujeto (máscara de persona). El efecto que más impresiona.
  Colócalo **encima y a los lados de la cabeza**, nunca en el centro: la cabeza lo taparía entero.
- `orbita`: anillo que rodea la cabeza (360°, protección, "todo alrededor").
- `ondas`: lo que se oye sale del lado de la cabeza por donde suena.
- `direccion`: indicador de por dónde viene algo.
- `aviso`: notificación de dos textos arriba a la derecha (killfeed, pedido, mensaje).
- `impacto`: marca en el centro en cada golpe o acierto.
- `pip` (en el plano): diseño streamer, la cara en una ventana sobre el contexto.
- `marca` + `cta`: el cierre.

**Sonido**
- **La idea sonora**: si el producto se oye (cascos, altavoz, coche, cocina), el antes suena
  `apagada` (mono, sin agudos) y el después abierto. Si no, el cambio se marca con un golpe y la música
  entrando de lleno.
- **Stop antes del drop**: un tiempo de música (`60/bpm` s) en silencio justo antes del cambio, con
  un impacto al revés que sube hacia él.
- **Silencio antes del remate**: la música se calla en la frase fuerte ("Uno contra tres") y vuelve de
  golpe en la siguiente. Pesa más que cualquier efecto.
- **Paneo**: los pasos o lo que se mueva, del lado que se ve (con auriculares se nota).
- **Cierre en seco**: la música acaba en un golpe de la rejilla (`compas`) con un impacto largo; el
  cartel final respira sobre la cola.
- **Mezcla**: la voz manda. Los golpes 3-8 dB por debajo de la voz; el editor hace el ducking.

## El proceso (en este orden)

1. **Mira todo el material**: una hoja de contactos por clip, 2 fotogramas por segundo en los que
   hablan y 4 en los insertos. Apunta qué hay en cada segundo, qué toma de cada frase es la mejor
   (la cara más expresiva, no la primera) y qué hay que evitar (un logo raro que aparece, una mano mal).
2. **Transcribe y mide la voz** (`kit.revisar`): qué dice cada clip de verdad y dónde. Los modelos a
   veces repiten la frase varias veces en el mismo clip: son tomas, elige.
3. **Localiza los eventos al fotograma** en los insertos (el fogonazo, el golpe, el encendido):
   brillo o diferencia entre fotogramas. Los sonidos y las rampas se clavan ahí (`{"src": …}`).
4. **Tempo de la música** (`python -m kit.sonido --ritmo audio/musica.wav`): el drop va en un golpe de
   compás, y los insertos duran múltiplos de un tiempo cuando se pueda.
5. **Escribe la escaleta** en una tabla (tiempo · plano · qué se ve · qué se oye · técnica) con el
   momento de cambio marcado. Que cada bloque tenga su idea visual.
6. **Escribe `edicion.json`** y prueba **fotogramas sueltos** de los momentos clave
   (`--fotos 20,120,260…`). Míralos: ¿el texto tapa la cara?, ¿se lee lo de detrás?, ¿algo quemado?
7. **Render completo.** El editor hace el control de calidad y escribe el informe: fotogramas (sin
   desfase), −14 LUFS, pico, lo que se oye y avisos. Mira la **hoja de contactos** que deja al lado.
8. **Corrige y vuelve a montar.** Montar es gratis; regenerar un clip cuesta: dilo antes.

## Antes de entregar

- Hoja de contactos: ¿cambia algo cada medio segundo?, ¿algún plano quieto de más de 3 s?
- Ningún subtítulo sobre la boca; nada fuera de la zona segura (y 270-1248, x 65-1015).
- El informe dice −14 ±1 LUFS, fotogramas iguales a los esperados y la transcripción coincide con el
  guion.
- Escúchalo con auriculares: paneos, el cambio, el silencio antes del remate.
- Si la marca es inventada o el avatar no existe, que no se venda como testimonio (`legal.md`).
