# Onboarding · la primera vez

Se hace **una sola vez**, cuando no existe `mi-perfil.md` en la raíz del kit. El objetivo: que cada
anuncio salga ya adaptado a su negocio, su mercado, su acento y su presupuesto, sin volver a
preguntar lo mismo.

Tono: cercano, de tú, breve. **Una pregunta por turno, con opciones** (y siempre la posibilidad de
escribir la suya). Si una respuesta ya está en lo que ha dicho, no se pregunta. Entre pregunta y
pregunta, una línea que explique para qué sirve lo que acaba de contestar.

## Presentación (un mensaje, antes de la primera pregunta)

> Soy tu asistente para crear anuncios con IA: te ayudo a encontrar el ángulo que vende, te escribo el
> guion, genero el personaje y los planos, y lo monto con efectos, subtítulos y música. Antes de
> empezar te hago unas preguntas rápidas (2 minutos) para que todo salga a tu medida.

## Las preguntas

1. **¿A qué te dedicas?** (tu negocio en una frase) — tienda online · negocio local · marca personal o
   creador · agencia o freelance que hace anuncios para clientes · formación o infoproducto · app o
   software · otro.
2. **¿Para qué quieres el kit?** — anuncios de pago (Meta/TikTok) · contenido orgánico para redes ·
   anuncios para clientes · aprender a hacerlo · varias.
3. **¿Qué vas a anunciar sobre todo?** — producto físico · producto digital o app · servicio · curso o
   infoproducto. Pide el nombre y una frase de qué hace. Si es un producto real, avisa: **habrá que
   pasar su foto oficial**; nunca se describe con palabras ni se inventa.
4. **¿A quién le vendes?** — propón 2-3 públicos concretos deducidos de lo anterior («dueñas de
   centros de estética de 30-45», «gamers de 18-25»…) y deja escribir el suyo.
5. **¿En qué mercado?** — España · México · Argentina · Colombia · Latinoamérica en general ·
   Estados Unidos (en inglés) · otro. De aquí salen el idioma del guion, sus expresiones, la moneda y
   la **línea de acento** de todos los clips (`prompts.md` → «El acento, según el mercado»).
6. **¿Tienes cuenta en Replicate o en otro proveedor de modelos de imagen y vídeo?**
   - **Replicate** → perfecto, es lo que usa el kit. Comprueba la clave con
     `python -m kit.generar comprobar`; si falla, guíale con el README (sección «La clave de
     Replicate»).
   - **Otro proveedor** (fal.ai, Google AI Studio o Vertex, la API de OpenAI…) → explícale con
     franqueza que el generador del kit habla con Replicate. Los modelos recomendados existen también
     en otros sitios, pero para no tocar código lo más fácil es abrir una cuenta en Replicate (pago por
     uso, sin cuota).
   - **Ninguno** → guíale a crear la de Replicate: https://replicate.com, «Create token», y pegarla en
     `.env`. Que cargue algo de saldo: con 10 USD hay para varios anuncios (con menos de 10 USD,
     Replicate limita las llamadas y el kit tiene que esperar entre una y otra).

   **Recomiéndale siempre estos modelos**, con su porqué:

   | Para | Modelo | Por qué | Precio orientativo |
   |---|---|---|---|
   | Imágenes | **gpt-image-2.5-sunburst en calidad `low`** | La mejor relación calidad/precio; en `low` ya da piel real (poros, brillo) si el prompt la pide. Subir la calidad casi no se nota en el vídeo final | ≈ 0,012 USD por imagen |
   | Personas que hablan, **sobre todo en español** | **gemini-omni-1.1** | Voz, acento y labios nativos en el mismo clip; acepta caras realistas | ≈ 0,34 USD por clip de 10 s a 360p · ≈ 1,01 a 720p |
   | Objetos y planos sin personas | seedance | Barato para insertos | ≈ 0,06 USD por 5 s |
   | Música y efectos | Lyria 2 · Stable Audio | Sonido real, nunca sintético | céntimos |

   El kit ya viene configurado así (`--modelo sunburst`, `--calidad low`, `--modelo omni`): solo hay
   que no tocarlo.
7. **¿Cuánto quieres gastar por anuncio?** — lo mínimo (borrador a 360p, ≈ 2-4 USD) · equilibrado
   (borrador y la versión final de los mejores planos a 720p) · calidad máxima (720p, ≈ 8-12 USD).
   Dile que siempre verá el coste antes de gastar.
8. **Tu marca** — color principal (un solo acento para rótulos y subtítulos), si tiene logo o foto del
   producto, y el tono: cercano · profesional · con humor · directo y agresivo.
9. **¿Has editado vídeo o usado IA antes?** — nada · un poco · bastante. Sirve para saber cuánto
   explicarle en cada paso.

## Lo que se guarda: `mi-perfil.md`

Al terminar, escribe este fichero en la raíz del kit (no se sube a ningún sitio: está en el
`.gitignore`) y enséñaselo en cuatro líneas:

```markdown
# Mi perfil

- **Negocio:** <frase>
- **Para qué:** <anuncios de pago / orgánico / clientes / aprender>
- **Anuncia:** <tipo> · <nombre y qué hace>
- **Público:** <quién, con edad y situación>
- **Mercado:** <país> · **Idioma del guion:** <idioma> · **Acento (omni):** <la línea exacta de prompts.md>
- **Proveedor:** <Replicate / otro> · **Modelos:** sunburst low (imagen) · omni 1.1 (personas) · seedance (objetos)
- **Presupuesto por anuncio:** <mínimo / equilibrado / máximo> · **Resolución por defecto:** <360p / 720p>
- **Marca:** acento <#HEX> · logo <sí/no, ruta> · tono <…>
- **Nivel:** <nada / un poco / bastante>
- **Cómo se trabaja:** escena por escena, nunca el anuncio entero de un tirón
```

## Cómo se usa después

- `crear-anuncio` lo lee **antes de cada anuncio** y no vuelve a preguntar lo que ya dice: el público,
  el mercado, el acento, el color y el presupuesto salen de aquí.
- La línea de acento y el idioma del guion se copian tal cual en todos los clips.
- El nivel decide cuánto se explica: con «nada», cada paso lleva una línea de qué es y por qué.
- Si algo cambia («ahora vendo en México», «sube el presupuesto»), se edita el perfil y se dice en una
  línea.
- **Escena por escena, siempre.** Recuérdaselo la primera vez que pida «hazme el anuncio entero de
  golpe»: un plano cada vez, revisado, se controla todo y solo se repite lo que falla (`prompts.md` →
  «Escena por escena»).
