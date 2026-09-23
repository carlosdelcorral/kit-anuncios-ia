# Entradas de cámara · los primeros 1,7 segundos

> El hook visual del anuncio, clip 0. Complementa `planos.md` (desde **dónde** mira la cámara) con
> **cómo entra** el plano: el movimiento, el objeto que tapa el objetivo, el corte que se esconde.
> Investigado en septiembre de 2026 (fuentes al final). Un id por entrada para citarla desde un
> guion: `ENT-*`.

## La regla que decide todo: qué hace el modelo y qué hacemos nosotros

Los modelos de vídeo siguen bien **un movimiento lento y una acción** por plano. Fallan en los
rápidos (la cara se deforma), en dos movimientos seguidos (intenta los dos y no hace ninguno), en
los cortes descritos (salen como un fundido blando) y en el texto. De ahí la columna **Cómo**:

| Código | Quién lo hace | Fiabilidad |
|--------|---------------|------------|
| **M** | El modelo solo, con el primer fotograma | Alta si el movimiento es lento |
| **M+UF** | El modelo con primer **y último** fotograma (`--imagen A --ultimo B`) | Alta: el final no se inventa |
| **2C** | Dos clips y un corte seco en nuestro montaje | Muy alta: la junta se decide en la edición |
| **ED** | El editor del kit (`anuncio.json`): `zoom_seco`, junta `barrido`, `rampa`, `flash`, `sacudida`, `glitch`, reordenar planos | Total. Lo que el editor no trae (croma, interfaz de notificación) se deja para una versión futura |

**Regla práctica:** todo lo que es *velocidad* (crash zoom, whip, rampa) sale mejor en edición; todo
lo que es *acción física* (tapar el objetivo, lanzar algo, entrar en cuadro) sale mejor del modelo.

## El catálogo

| id | Qué es | Por qué para el scroll | Cuándo | Cómo |
|----|--------|------------------------|--------|------|
| `ENT-CRASH-ZOOM` | Zoom seco de plano medio a primerísimo en la primera palabra | Movimiento + cara en el fotograma 1 | Claim fuerte, contrarian | **ED** (100→140 % en 4-6 fotogramas) |
| `ENT-WHIP-IN` | El plano entra a mitad de un barrido y se asienta sobre la persona | «Ya está pasando algo» | Segundo golpe del hook, cambio de sitio | **2C + ED** (desenfoque direccional en la junta) |
| `ENT-TAPA-OBJETIVO` | Una mano, la sudadera o el producto tapa el objetivo y al apartarse revela otro estado | Antes/después instantáneo, con el corte escondido | Antes/después, cambio de sitio o de ropa | **M+UF + 2C** |
| `ENT-PRODUCTO-LENTE` | Empuja el producto contra el objetivo hasta llenar el cuadro y lo retira para enseñar la cara | Cambio de escala y producto en el primer segundo | Demo, unboxing | **M** (producto sencillo) |
| `ENT-LANZA` | Lanza algo a cámara, tapa el objetivo, y corte a otra escena | Sorpresa + transición «de magia» | Cambio de ropa/sitio, día 1 vs día 30 | **M+UF + 2C** |
| `ENT-ENTRA-EN-CUADRO` | Móvil apoyado y quieto; la persona entra en cuadro ya hablando | Te meten en algo que ya ha empezado | Hook de escenario, problema | **M** (fiable: cámara fija) |
| `ENT-COGE-MOVIL` | El móvil está en la mesa mirando al techo; una mano lo coge y el cuadro gira hasta el selfie | Movimiento + intimidad («te lo tengo que contar») | Confesión, secreto | **M+UF** (último = el selfie) |
| `ENT-CAMINA-HABLA` | Selfie a brazo extendido andando | El formato más nativo | Testimonio, «voy de camino a…» | **M** |
| `ENT-ULTRAWIDE` | Selfie con el 0,5× pegado a la cara, distorsión en los bordes | El autorretrato Gen Z de 2026; lo contrario del testimonio de aro de luz | Público joven, humor, detrás de cámaras | **M** (el look sale de la imagen) |
| `ENT-VERTIGO` | Dolly zoom: la cara no cambia de tamaño y el fondo se estira | «El momento en que me di cuenta» | Revelación, error descubierto | **M** (sujeto quieto y centrado; probar antes) |
| `ENT-SNORRI` | Cámara atada al cuerpo: la cara fija y el mundo temblando | Urgencia, agobio | Agitar el problema («mi semana fue un caos») | **M** (riesgo medio) |
| `ENT-ARCO` | Arco corto de 30° alrededor de la persona o el producto | Momento «héroe», da volumen | Enseñar el producto o el resultado | **M** (≤ 30°); **M+UF** si es más |
| `ENT-RAMPA` | Cámara lenta que entra a tiempo real en el golpe | Ritmo, «espera…» | Revelación, antes/después | **ED** (nunca sobre la voz) |
| `ENT-MATCH-CUT` | Misma pose o gesto en dos realidades distintas | Se lee como hecho a propósito | Transformación | **2C** (corte en el gesto, el parpadeo o el giro) |
| `ENT-REACCION-PRIMERO` | Arranca por la reacción o el resultado y luego «tres días antes…» | Curiosity gap + micro-expresión real | Resultados, casos | **ED** (se sube 1-1,5 s del final al principio) |
| `ENT-NOTIFICACION` | Arranca con una notificación, un mensaje o un comentario y corte a la reacción | Así descubre la gente las cosas | «Alguien me preguntó…», objeciones | **M** (la reacción); la notificación, hoy como rótulo `hook` |
| `ENT-PANTALLA-VERDE` | La persona delante de una captura, un artículo o una gráfica | Nativo de TikTok y parece prueba | Noticia, prueba, nosotros vs ellos | Pendiente en el editor (croma) |

`ENT-FPV` (dron que se tira a la escena) existe pero **no se recomienda** para un avatar que habla:
alto riesgo a velocidad y no aporta a un anuncio de cara.

## Los prompts (inglés, literales; el primer fotograma ya va con `--imagen`)

Van **después** de la gramática de siempre (cámara → acción → guion → `Voice:` → acento) y
**antes** del cierre `single continuous take, no cuts or scene changes.` El verbo de cámara va
**en las primeras 8-10 palabras** y con palabra de velocidad (*slow, smooth, sudden*).

```
ENT-ENTRA-EN-CUADRO
Static phone propped on a kitchen counter, locked off. She walks into frame from the left
mid-sentence, leans toward the phone and says: "…"

ENT-TAPA-OBJETIVO (clip A, último fotograma = la palma)
She reaches toward the camera and covers the lens with her open palm; the frame fills with
blurred skin and goes dark.
ENT-TAPA-OBJETIVO (clip B, primer fotograma = la palma desenfocada)
Her palm pulls away from the lens revealing her in [new setting], already talking: "…"

ENT-PRODUCTO-LENTE
She pushes the [product] toward the lens until it fills the frame and softly blurs, then pulls it
back to reveal her face and starts talking: "…"

ENT-LANZA (A / B)
A: She tosses the hoodie straight at the camera; the fabric fills the lens.
B: The fabric falls away from the lens revealing [new scene].

ENT-COGE-MOVIL
The phone lies face-up on the table looking at the ceiling; her hand grabs it and lifts it, the
frame swings up and settles into a handheld selfie as she starts talking: "…"

ENT-CAMINA-HABLA
A selfie video of her walking down the street, phone at arm's length, her arm visible in frame;
slight natural shake, occasional small re-framing, subtle push-in to her face.

ENT-ULTRAWIDE (sobre todo en la IMAGEN)
Shot on the phone's 0.5x ultra-wide lens held close, strong wide-angle edge distortion, her face
large in frame, the whole messy room visible behind.

ENT-VERTIGO
Slow dolly zoom on her face as she realizes: her face holds the same size while the background
stretches away behind her; she stays still and centred.

ENT-SNORRI
SnorriCam rig locked to her torso; her face stays centred and sharp while the street rushes and
shakes behind her as she walks fast, talking.

ENT-ARCO
The camera makes a slow, shallow arc of about 30 degrees around her as she holds up the [product].

ENT-REACCION-PRIMERO (el clip del resultado)
She looks at her laptop, freezes, then covers her mouth in genuine disbelief, a small incredulous
laugh; restrained, not exaggerated.

ENT-NOTIFICACION (la reacción)
She glances down at her phone, reads, raises her eyebrows and looks back up at camera.
```

Para `ENT-CRASH-ZOOM`, `ENT-WHIP-IN` y `ENT-RAMPA` **no se le pide velocidad al modelo**: se genera
el plano normal («one continuous fluid motion, natural acceleration») y la velocidad la pone la
edición. Truco del crash zoom con más recorrido: generar la imagen base **más abierta** (outpaint
con gpt-image-2) y hacer el zoom desde ahí.

## Cómo se combinan en un reel

- **Un solo golpe de cámara en el hook.** Dos entradas seguidas se anulan.
- **Hook visual + rótulo + primera frase** a la vez (ver `hooks.md`): la entrada es
  la capa visual; el rótulo lo pone nuestro motor; la frase va en el prompt.
- **Cambio cada 2,5-4 s** después: el resto de clips con `planos.md`, sin repetir `PLN-`.
- **Para un producto de software o un servicio**: `ENT-NOTIFICACION` (el correo del cliente enfadado),
  `ENT-REACCION-PRIMERO` (el informe hecho solo), `ENT-ENTRA-EN-CUADRO` en el despacho y
  `ENT-PANTALLA-VERDE` sobre una captura real. Las acrobáticas (`ENT-SNORRI`, `ENT-VERTIGO`) para
  campañas de marca, no de captación.

## Vocabulario: lo que el modelo obedece y lo que no

| Obedece | No obedece (o sale mal) |
|---------|-------------------------|
| `static` / `locked off` · `slow push-in` / `pull-back` · `slow dolly`, `pan`, `tilt`, `tracking` · arco ≤ 30-45° · `handheld` con límite (`subtle sway`) | Dos movimientos en un prompt · push-in rápido (deforma la cara) · órbita rápida (derrite las manos) · barrido rápido sobre detalle · atravesar objetos · cortes descritos («then cuts to…») · tomas de más de 10 s |

**Handheld creíble:** empezar por «A selfie video of…» con el brazo en cuadro; nombrar los fallos
(`autofocus micro-pulses`, `slight overexposure`, `~26mm`, `edge distortion`); una sola fuente de luz
y un sitio real y desordenado; habla imperfecta (arranca, se corta, ríe); **nunca «cinematic»**;
describir peso y aceleración (la velocidad constante se lee falsa).

## Fuentes

Guía oficial de Gemini Omni (ai.google.dev/gemini-api/docs/omni · deepmind.google/models/gemini-omni/prompt-guide) ·
Higgsfield camera controls y guía de UGC (higgsfield.ai) · Kling camera prompts (kling.ai/blog) ·
TikTok Creative Best Practices (ads.tiktok.com) · Pixis «UGC in 2026» · lzyprompt, prompt-architects,
atlabs, screenweaver (vocabulario de cámara) · sabrina.dev y godofprompt (selfie con Veo) ·
polaroidcam (0,5×) · morphic (match cut). 
