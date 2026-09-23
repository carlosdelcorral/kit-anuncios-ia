# Prompts · plantillas que funcionan

Todos en inglés salvo el diálogo, que va en el idioma del anuncio. Se rellenan los `<…>`. Ejemplo
completo y real: `ejemplos/onda-x/1_imagenes.py`, `2_imagenes.py` y `3_clips.py`.

## Escena por escena, nunca de un tirón

**No se pide el anuncio entero en un solo prompt** (un «one-shot» de 30 s). Sale una toma que no
controlas: la cara cambia a mitad, el producto se deforma, la voz se acelera y, si falla un detalle,
se repite todo y se paga todo otra vez. Se trabaja **plano a plano**:

1. Una imagen por plano (rama de la base), revisada antes de animarla.
2. Un clip por plano, con **una** acción y **un** movimiento de cámara.
3. Cada clip se revisa suelto (`kit.revisar` + fotogramas) y, si falla, se regenera **solo ese**.
4. El ritmo, los cortes y los efectos se deciden en el montaje, donde cambiar es gratis.

Cuesta lo mismo o menos, y el resultado se controla de principio a fin.

## PERSONA (la imagen base)

```
Photorealistic vertical photo, shot on a real iPhone 15 Pro front camera held at arm's length,
26mm, slight wide-angle. <A Spanish young man, about 22, short messy dark hair, light stubble, a few
faint skin blemishes, wearing a plain charcoal grey hoodie>. <He sits in his small bedroom gaming
setup at night: …, a slightly messy shelf, the corner of an unmade bed>. <What he holds / does>.
He looks straight into the lens, mid-sentence, <relaxed half smile>. <Light: cool screen glow on one
side of his face, warm desk lamp on the other>. Natural skin texture with visible pores, slight
facial asymmetry, flyaway hairs, real fabric texture, nothing airbrushed. The goal is for this to
look like a candid frame from a real creator's TikTok, not an AI render. Do not smooth the skin
artificially. No plastic skin, no beauty filter, no CGI, no 3D render, no doll-like face. No text
anywhere in the frame, no logos, no watermark, no readable screen interface.
```
`python -m kit.generar imagen "<prompt>" --out anuncios/<slug>/img/base.png`

## PRODUCTO (si es inventado; si es real, su foto oficial)

```
Studio product photograph of <the product, materials, colours, details>. Three-quarter view,
floating centred on a pure black background, dramatic rim light, subtle reflections, sharp detail,
realistic materials. A small <embossed wordmark reading exactly "<NOMBRE>"> on <where>, spelled
letter for letter. No other text, no watermark.
```
`python -m kit.generar imagen "<prompt>" --modelo sunburst --aspecto 1:1 --out …/img/producto.png`

## RAMA (un plano nuevo desde la base)

```
Reference Image 1 defines the <person> — exact face, hair, clothes — and the <place> and lighting.
Reference Image 2 defines the exact <product>: do not redesign, simplify or alter it in any way.
Change: <only what changes: action, framing, what he holds>. Preserve: the same person, same face and
identity, same clothes, same skin texture with visible pores and slight asymmetry, same place and
light. Match: same phone-camera look, same colour and direction of light. The result should look
like the next frame of the same TikTok video. Natural skin, nothing airbrushed, no CGI. No text
anywhere except <the product name on the product/box>.
```
`python -m kit.generar imagen "<prompt>" --ref …/img/base.png …/img/producto.png --out …/img/p1.png`

## CLIP QUE HABLA (gemini-omni-1.1)

Las doce reglas: dirección en inglés, diálogo en español **entre comillas**, idioma y acento sin
ambigüedad, negativos dentro del prompt, toma única, ≤ 20-25 palabras, marcas de tiempo, **el
sonido descrito y `No music`** (si no, mete música genérica), un solo movimiento de cámara, nombres
extranjeros escritos como suenan, y la frase de naturalidad de Google.

```
(<camera: handheld selfie camera, slight natural sway | static camera on top of the monitor, webcam
style, locked off>) realistic arm movements and subtle micro-movements.
[0-2s] <a physical action with a visible consequence>.
[2-7s] He looks into the lens and says: "<la frase en español>"
[7-10s] <a silent reaction: a nod, a laugh, a glance>.
Voice: <a young Spanish male voice, about 22, medium pitch, energetic but relaxed, casual tone>.
He speaks in Spanish from Spain, natural Madrid accent (castellano peninsular, not Latin American),
informal and conversational, like a real TikTok creator.
Ambient noise: <quiet bedroom room tone, faint computer fan hum>. No music.
Consider micro-detail, expression and timing to create a very rich, detailed but entirely natural
scene. No subtitles, no captions, no on-screen text. In a single continuous shot, no scene cuts.
```
`python -m kit.generar video "<prompt>" --imagen …/img/p1.png --out …/vid/c1.mp4` (360p por defecto;
`--res 720p` para el final). **La línea `Voice:` y la del acento, idénticas en todos los clips.**

**Dos personajes en el mismo clip**: se nombran las dos voces (`Voice for the man: … Voice for the
woman: …`) y la que no sale en cuadro se describe como `off-screen` o `from the laptop speaker`.
Con 4 o más personajes, omni se pierde.

**Bucle**: el último clip con `--ultimo` = la imagen base del primero.

## INSERTOS SIN CARA (imagen + seedance)

Dan el ritmo. Primero una imagen (`--modelo sunburst`), luego 4-5 s de seedance desde ella.

```
CONTEXTO (p. ej. el videojuego): A vertical frame from a first-person sci-fi shooter video game: <what
the player sees>, rendered like a modern AAA video game (Unreal Engine 5 look), cinematic volumetric
light, <brand colours> neon accents. No HUD, no crosshair, no health bar, no numbers, no letters, no
user interface, no watermark.
  → seedance: First-person view in the video game: <one action: turns left, fires two shots, the enemy
    collapses>. Video game footage, fast responsive game camera, no HUD, no text, no user interface.

MANOS EN CENITAL: Reference Image 1 defines the exact <product>. Top-down overhead photo looking straight
down at <surface>: <person>'s two hands <opening the box / using the product>, <light>, real
phone-camera look, natural skin on the hands. No text except <the product name>.
  → seedance (--camara-fija): Top-down view: the hands <action with a visible result>. Smooth natural motion.

MACRO DEL PRODUCTO: Reference Image 1 defines the exact <product>: do not redesign it. Extreme macro
close-up of <detail>, very shallow depth of field, dark background, premium product commercial look. No text.
  → seedance (--camara-fija): Macro product shot: <the light powers on / a light sweep crosses it>.
```

Para un mundo inventado (un juego, una app), mejor **robots o criaturas** que personas: seedance
rechaza caras fotorrealistas.

## SONIDO (música y efectos)

```
python -m kit.generar musica "Dark aggressive phonk trap beat for a gaming ad, 140 BPM, heavy distorted
  808 bass, crisp hi-hats, punchy kick, tense and energetic, strong drop, instrumental" --out …/audio/musica.wav
python -m kit.generar sonido "fast clean cinematic whoosh transition swish, short" --dur 1 --out …/audio/sfx-whoosh.wav
python -m kit.generar sonido "deep cinematic sub bass impact boom hit, trailer" --dur 2 --out …/audio/sfx-golpe.wav
```

La música: género + BPM + 3-4 instrumentos + energía + «instrumental». Los efectos: **qué suena, sobre
qué, y el contexto** («heavy metallic robot footsteps walking down metal stairs, video game»). Pide 1-4 s;
el fichero sale más largo, relleno de silencio, y no molesta.

## PRODUCTO EN 3D (seedance, sin personas)

```
The <product> slowly rotates in mid-air, then its parts gently separate into a floating exploded
view — <parts> drift apart — and smoothly snap back together; <lights pulse …>; tiny glowing
particles drift around it; pure black background, studio rim light, glossy reflection below. One
continuous shot, no cuts, smooth natural acceleration. No text.
```
Primer fotograma: el producto en vertical (una rama de `producto.png` a 9:16 sobre negro).
`python -m kit.generar video "<prompt>" --modelo seedance --imagen …/img/p5.png --dur 6 --camara-fija --out …/vid/c5.mp4`

Seedance **rechaza caras fotorrealistas** (error E005): úsalo solo sin personas.

---

# Técnicas que hay que saber

## El orden del prompt de vídeo

Omni obedece mejor si cada clip dice las cosas **siempre en el mismo orden**:

```
1 cámara (un movimiento)  →  2 acción (una, con consecuencia visible)  →  3 lo que dice
→  4 Voice:  →  5 idioma y acento  →  6 sonido de la sala + No music  →  7 negativos y toma única
```

**El gesto va delante o detrás de la frase según cuándo ocurre:**

```
Antes de hablar:  She <gesture>, then looks at the lens and says: "…"
Mientras habla:   She says: "…" while <gesture>.
Las dos cosas:    She <gesture>, then says: "…" and <closing gesture>.
```

Un gesto por frase. Dos gestos en la misma frase salen mal (hace uno a medias y el otro no).

## Cámaras que obedece

| Quieres | Escribe | Cuándo |
|---|---|---|
| Quieta | `static camera, locked off` | Móvil apoyado, webcam, la acción ya da el movimiento |
| En mano | `handheld, very slight natural sway` | Selfie: el temblor mínimo dice «lo grabó una persona» |
| Acercarse | `slow push-in toward her face` | Frase clave, cierre |
| Alejarse | `slow pull-back revealing the room` | Enseñar el sitio |
| Rodear | `slow shallow arc of about 30 degrees` | Producto o momento «héroe» |
| Seguir | `tracking shot alongside her as she walks` | Caminar y hablar |
| Cambio de foco | `rack focus from the <object> to her face` | Producto delante de la cara |

Nunca dos movimientos en un clip, nunca rápido (la cara se deforma), nunca «then cut to…». Lo que es
velocidad (zoom seco, barrido, cámara lenta) lo hace el editor (`montaje.md`).

## La voz del personaje

Se inventa con cinco piezas y **se copia idéntica en todos los clips** del personaje:

`Voice:` + género y edad + grave/aguda + textura + cómo habla.

```
Voice: a young woman's voice, about 25, bright and clear, warm and friendly, relaxed natural pace.
Voice: a woman's voice, about 35, medium-low and slightly husky, calm and confident.
Voice: a young man's voice, about 22, medium pitch, energetic but relaxed, a smile in the voice.
Voice: a man's voice, about 50, deep and warm, unhurried and reassuring.
```

Si cambia una palabra de la línea `Voice:` entre clips, cambia la voz a mitad del anuncio.

## El acento, según el mercado (`mi-perfil.md`)

| Mercado | Línea de acento |
|---|---|
| España | `She speaks in Spanish from Spain, natural Madrid accent (castellano peninsular, not Latin American), informal and conversational.` |
| México | `She speaks in Mexican Spanish, natural Mexico City accent, informal and conversational.` |
| Argentina | `She speaks in Argentine Spanish, natural Buenos Aires accent with the typical "sh" sound for "ll" and "y", informal and conversational.` |
| Colombia | `She speaks in Colombian Spanish, clear and neutral Bogotá accent, informal and conversational.` |
| Latinoamérica | `She speaks in neutral Latin American Spanish, informal and conversational.` |
| EE. UU. | `She speaks in American English, natural casual tone.` (y el guion, en inglés) |

Omni solo garantiza oficialmente el inglés: el español funciona muy bien, pero **cada clip se
transcribe** (`kit.revisar`) para pillar palabras cambiadas. Si el acento se cuela de otro sitio, se
regenera ese clip. Cambiar de mercado no es cambiar el acento: **se reescribe el guion** con sus
expresiones y su moneda.

## Una app o una web en una pantalla (dos pasos)

La IA escribe mal las pantallas. Se hace así, en este orden:

1. **La pantalla en negro**: rama de la base donde sostiene el móvil o el portátil hacia la cámara con la
   pantalla apagada (`the screen is completely off, solid black, no reflections, no UI, no text`).
2. **Se mete la captura real**: con esa imagen y la captura como segunda referencia, `place the
   screenshot from Reference Image 2 onto the black screen, matching its perspective, tilt and rounded
   corners, with realistic brightness and a subtle glare; do not crop or stretch it; keep everything
   else identical`.

Así la captura encaja con la perspectiva del aparato en vez de flotar. En el vídeo, se encuadra para que
la pantalla no tenga que leerse durante el movimiento, o se pone la captura encima en el montaje.

## Antes y después

Las dos imágenes salen **de la misma imagen de referencia**, nunca una de la otra: «antes» con el
problema visible, «después» con el resultado. Una editada sobre la otra deriva la cara. Y recuerda
`legal.md`: un avatar no presenta su propio antes/después como cliente; se usa como escena o como
demostración.

## La identidad del personaje en campañas largas

Si el mismo personaje va a salir en muchos anuncios, genera una vez una **hoja de identidad**: una sola
imagen con 9 retratos del mismo personaje (frente, perfiles, tres cuartos, mirando arriba y abajo, dos
expresiones) sobre fondo gris neutro, misma luz y misma distancia, pidiendo que no embellezca ni cambie
ningún rasgo. Se guarda y se usa como referencia para comprobar que la cara no ha derivado.

## El producto en la mano

El producto **entra siempre como imagen de referencia** (su foto oficial si existe), con la frase de no
tocarlo: `do not redesign, simplify or alter the product in any way; keep its shape, colours, label and
proportions`. Describirlo con palabras produce un producto falso.

## Cremas, líquidos y tapas

- Crema o gel que se extiende: **di que la cantidad visible baja** hasta desaparecer (`the amount of
  visible cream continuously decreases until fully absorbed, no residue or streaks`). Si no, el modelo
  la deja flotando en la piel.
- Beber: el vaso **tiene que vaciarse**. Un vaso que no baja al beber delata la IA.
- Tapas con bisagra, bombas, cierres raros: la interacción fina **se resuelve en la imagen** (la tapa ya
  abierta, con una foto de referencia del mecanismo si hace falta) y el vídeo solo la continúa.

## Fija el final cuando la prueba depende de él

Si lo que demuestra el anuncio es **cómo acaba** un plano (el pañuelo sale limpio, el vaso vacío, la
pantalla con el resultado), no te fíes del texto: genera una imagen con ese estado final y pásala como
último fotograma (`--ultimo final.png`). **El último fotograma manda sobre el prompt.** Caso real: un
clip pedido con «a completely clean tissue» salió con una mancha de grasa; con el último fotograma
fijado, salió limpio.

## Dos personajes

- **En el mismo plano**: se dice quién habla y qué hace el otro (`The woman on the left is speaking…
  The man on the right only listens, nodding slightly, reacting naturally`). Un clip por turno de
  palabra, y se nombran las dos voces (`Voice for the woman: … Voice for the man: …`).
- **Estilo podcast**: cada persona se genera **por separado**, cámara fija, mirando hacia donde estaría
  el otro, y se corta entre las dos en el montaje. Para el segundo asiento se genera la otra mitad de la
  habitación, no la imagen en espejo (se nota).
- Quien no sale en cuadro se describe como `off-screen` o `from the laptop speaker`.
- Con 4 personajes o más, omni se pierde.
