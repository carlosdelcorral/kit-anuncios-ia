# Realismo · que no parezca IA

Un avatar perfecto se lee como IA y deja de vender. El objetivo es que parezca **un vídeo de un
creador grabado con el móvil**, no un render.

## En la imagen (gpt-image-2 / sunburst)

- **«Photorealistic» ya casi no hace nada.** Lo que funciona es hablar como un fotógrafo: `shot on
  a real iPhone 15 Pro front camera`, `26mm` (selfie), `35mm` (plano de cámara), `50mm` (retrato),
  `shallow depth of field`, una luz concreta (`cool screen glow on one side, warm desk lamp on the
  other`).
- **Pide la textura con palabras**: `natural skin texture with visible pores, slight facial
  asymmetry, flyaway hairs, a few faint blemishes, real fabric texture, nothing airbrushed`.
- **Negativos como instrucción**, en la misma frase: `Do not smooth the skin artificially. No
  plastic skin, no beauty filter, no CGI, no 3D render, no doll-like face.`
- **Declara la intención al final**: `The goal is for this to look like a candid frame from a real
  creator's TikTok, not an AI render.`
- **Un sitio real y un poco desordenado** (la cama sin hacer, una estantería con cosas): lo
  ordenado y vacío se lee falso.
- **Varias referencias → di qué define cada una**: `Reference Image 1 defines the young man — his
  exact face, hair, hoodie — and his bedroom. Reference Image 2 defines the exact headset: do not
  redesign it.`
- **Ningún texto generado** salvo el que forma parte del producto (el logo del producto, el nombre
  en la caja) — y para eso, `--modelo sunburst`, con el texto entre comillas y «spelled exactly».

## De una imagen a muchas: ramificar, no encadenar

Todos los planos salen **de la misma imagen base**, cada uno como una rama con tres bloques:

```
Change: <solo lo que cambia: la acción, el encuadre, el sitio>
Preserve: the same person, same face and identity, same hoodie, same skin texture with visible
pores, same bedroom and light.
Match: same phone-camera look, same colour and direction of light.
The result should look like the next frame of the same TikTok video.
```

Editar la edición de la edición degrada: la cara deriva. Si la escena cambia de sitio en cada
plano (calle → tienda → calle), se usa el **último fotograma real** del clip anterior como base de
la rama siguiente (`ffmpeg -sseof -0.25 -i clip.mp4 -frames:v 1 fin.png`).

## En el vídeo (gemini-omni-1.1)

- **Nunca quieto**: `realistic arm movements and subtle micro-movements.` va siempre.
- **La naturalidad se nombra**: `blinks naturally`, `breathes`, `small head tilts while talking`,
  `pauses before reacting`, `looks away before smiling`.
- **Una acción física con consecuencia visible por clip**: se pone los cascos y se encienden las
  luces; bebe y deja el vaso; empuja la caja hacia la cámara. La acción da el movimiento y la boca
  acompaña. Sin acción, parece un maniquí que habla.
- **La expresión se ordena en el tiempo**, no con adjetivos: `[0-2s] freezes and listens.
  [2-4s] snaps back to the screen. [4-7s] says, excited: "…"`.
- **Un solo movimiento de cámara, y lento**: `handheld selfie camera, slight natural sway` o
  `static camera on top of the monitor, webcam style, locked off`. Los rápidos se hacen en montaje.
- **La misma línea `Voice:` y el mismo acento en todos los clips** del personaje, palabra por
  palabra. Si cambian, cambia la voz a mitad de anuncio.
- **Nunca «cinematic»**: empuja hacia el anuncio pulido, justo lo que no queremos.

## Lo que dice la investigación de 2026 (y ya aplica el kit)

- **La sincronía de labios de omni aguanta ~6-7 s**: la frase acaba en el segundo 7 y los 3 s finales
  son una reacción callada (`[7-10s] No dialogue; …`). También da aire para cortar.
- **La mirada va a la pantalla, no a la lente**: `Her eyes stay mostly on the phone screen just below
  the lens, flicking up to the lens on key words; understated, not presenter-like.` Así mira alguien
  que se graba.
- **Encuadre imperfecto**: descentrado, la coronilla algo cortada, el antebrazo en el borde, «23mm»,
  «iPhone HDR look». El encuadre perfecto se lee como producido.
- **Vida detrás**: `at 5s a scooter passes behind her, out of focus`; un sitio real con trastos (llaves,
  un plátano, correo).
- **Sonido del sitio en el prompt**, siempre al final: cafetera, calle, coche cerrado, terraza con
  murmullo que no se entiende. Lo que más delata la IA es una voz **demasiado limpia**, en el vacío.
- **Lo que delata al espectador**: manos que mutan, espejos, extras deformes, texto raro, cámara sin
  temblor, **un vaso que no baja al beber** (por eso nadie bebe en cámara), dos personas hablando a la vez.
- **Producto opaco y prueba sonora**: una botella que no deja ver el nivel, un sonido (hielo, clic) que
  diseñas tú. Lo que cambia de estado (llenar, derretir, batir) se cuenta con un **corte**, nunca dentro
  de un clip.
- **SynthID** va en todo lo que sale de omni: se conserva, y la etiqueta de IA también.

## Checklist anti-robot (antes de dar un clip por bueno)

1. ¿Hay una acción física con consecuencia visible?
2. ¿Hay al menos dos micro-conductas nombradas?
3. ¿La cámara hace algo (o la acción lo justifica)?
4. ¿El plano cambia de tamaño o de ángulo respecto al anterior?
5. ¿Cierra con `In a single continuous shot, no scene cuts.`?
6. ¿Misma `Voice:` y mismo acento que el resto?
7. ¿La cara sigue siendo la de la imagen base?
8. ¿El guion cabe (≤ 20-25 palabras en 10 s)?
9. ¿Lo revisó `kit.revisar` y no dice palabras que no estaban?
10. ¿El anuncio lleva la etiqueta de IA y ningún testimonio falso?

Si falla el 1 o el 2, el clip va a parecer IA aunque todo lo demás esté bien.

## Lo que el montaje arregla (y lo que no)

El editor unifica la textura (grano fino, un punto de contraste, viñeta), esconde las juntas
(barrido, flash, audio que se adelanta) y quita lo que sobra (pausas, repeticiones). Lo que no
arregla: una cara que ha derivado, manos deformes o una voz distinta. Eso se regenera.
