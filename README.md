# Kit de anuncios con IA

Anuncios UGC verticales con **avatares hiperrealistas**, de la idea al MP4 montado, hablando con
Claude Code. Tú dices qué vendes; el kit hace de **estratega de respuesta directa** (voz del cliente,
ángulos, mecanismo, nivel de consciencia), te propone hooks y guion, te enseña el coste, genera el
personaje y los clips **escena por escena**, los revisa y los monta con un editor de nivel
profesional: zoom de entrada, barridos, sacudidas, glitch, rampas de velocidad, sonido que cruza
de un oído a otro, subtítulos palabra a palabra, rótulos y la etiqueta de IA.

La primera vez que lo abres te hace unas preguntas (a qué te dedicas, qué vendes, a quién, en qué
mercado y con qué acento, tu presupuesto y tu marca) y guarda tu perfil: desde ahí, cada anuncio sale
a tu medida.

**Demo:** [`ejemplos/onda-x/`](ejemplos/onda-x/) — un anuncio de 31 s y 24 planos de unos cascos
gaming inventados: creador a cámara, gameplay, diseño streamer, el sonido que se abre al ponerse los
cascos, un despiece 3D. Con todo lo que lo hizo (imágenes, clips, música, efectos, guion,
`anuncio.json`, informe). Coste: ≈3 USD.

**Segunda demo:** [`ejemplos/gelida/`](ejemplos/gelida/) — la más natural: un test de 24 h de una botella
térmica inventada, con la hora en pantalla y el realismo de móvil del editor (temblor de mano,
exposición y enfoque que respiran, grano de sensor). La prueba es un sonido: el hielo 19 horas después.

## Lo que necesitas

- **Claude Code** (el curso lo explica).
- **Python 3.11 o superior.**
- Una cuenta de **Replicate** con saldo (se paga por uso: un anuncio de 7 clips en borrador ≈ 2-3 USD).
  Carga al menos 10 USD: por debajo, Replicate limita las llamadas y todo va más lento.
- Mac (probado) o Windows/Linux (debería funcionar; el transcriptor usa faster-whisper fuera de Mac).

## Los modelos que recomendamos (ya vienen configurados)

| Para | Modelo | Por qué | Precio orientativo |
|---|---|---|---|
| Imágenes | **gpt-image-2.5-sunburst**, calidad **`low`** | La mejor relación calidad/precio; en `low` ya da piel real si el prompt la pide | ≈ 0,012 USD por imagen |
| Personas que hablan, **sobre todo en español** | **gemini-omni-1.1** | Voz, acento y labios en el mismo clip; acepta caras realistas | ≈ 0,34 USD por clip a 360p · ≈ 1,01 a 720p |
| Objetos sin personas | seedance | Barato para planos de producto | ≈ 0,06 USD por 5 s |
| Música y efectos | Lyria 2 · Stable Audio | Sonido real, nunca sintético | céntimos |

El kit habla con **Replicate**. Si usas otro proveedor, estos modelos existen también allí, pero el
generador habría que adaptarlo: lo sencillo es abrir cuenta en Replicate.

## Cómo se trabaja: escena por escena

Nada de pedir el anuncio entero en un solo prompt. Un plano cada vez: su imagen, su clip, su revisión.
Si algo falla, se repite **solo ese plano** (y solo se paga ese). El ritmo, los cortes y los efectos se
deciden en el montaje, donde cambiar es gratis.

## Instalación (una vez)

```bash
git clone https://github.com/carlosdelcorral/kit-anuncios-ia.git
cd kit-anuncios-ia
python3 -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # y pega tu clave de Replicate dentro
python -m kit.generar comprobar      # → «OK — cuenta de Replicate: …»
```

**La clave de Replicate:** https://replicate.com/account/api-tokens → «Create token» → cópiala en
`.env` como `REPLICATE_API_TOKEN=r8_…`. Nunca la subas a ningún sitio (el `.gitignore` ya la protege).

La primera transcripción descarga el modelo de voz (~1,5 GB) y tarda unos minutos; después va solo.

## Uso: habla con Claude Code

```bash
claude
```

y di **«hola»** la primera vez (te hará el onboarding) y **«quiero hacer un anuncio»** después. El
asistente (skill `crear-anuncio`):

1. **La primera vez**, te pregunta a qué te dedicas, para qué quieres el kit, qué vendes, a quién, en
   qué mercado, qué proveedor tienes, cuánto quieres gastar y cómo es tu marca. Lo guarda en
   `mi-perfil.md` (solo en tu ordenador).
2. En cada anuncio, te pregunta lo justo: qué anuncias esta vez, si hay oferta, qué tipo de anuncio y
   si traes guion.
3. Te da la **estrategia**: dolores, deseos y objeciones de tu cliente, un menú de 8-12 ángulos, el
   mecanismo y el nivel de consciencia. **Tú eliges el ángulo.**
4. Te propone hooks y el guion plano a plano **con su coste**, y espera tu OK.
5. Genera **solo** la imagen del personaje y la del producto, y espera tu OK.
6. Genera el resto **escena por escena**, revisa cada clip y monta el anuncio.
7. Te entrega el MP4, un informe (duración, volumen, lo que se oye, avisos) y hooks nuevos para probar.

Cada anuncio queda en `anuncios/<nombre>/`.

## Uso a mano (sin el asistente)

```bash
python -m kit.generar imagen "<prompt>" --out anuncios/x/img/base.png
python -m kit.generar video  "<prompt>" --imagen anuncios/x/img/base.png --out anuncios/x/vid/c0.mp4
python -m kit.generar musica "<estilo, bpm, instrumental>" --out anuncios/x/audio/musica.wav
python -m kit.generar sonido "<efecto>" --dur 2 --out anuncios/x/audio/sfx-golpe.wav
python -m kit.sonido --ritmo anuncios/x/audio/musica.wav    # tempo, para cortar a golpe
python -m kit.revisar anuncios/x/vid/*.mp4 --guion anuncios/x/guion.json
python -m kit.montar  anuncios/x/anuncio.json          # --rapido borrador · --depurar guarda los planos
python -m kit.generar gasto
```

Volver a montar la demo (no genera nada, no gasta): `python -m kit.montar ejemplos/onda-x/anuncio.json`

Las plantillas de prompts, el formato de `anuncio.json` y el método están en
`.claude/skills/crear-anuncio/references/`.

## Reglas del kit

- **Nada se genera sin tu OK** (guion y primera imagen).
- **Ningún texto sale del generador**: rótulos, subtítulos y logos los pone el editor.
- **Etiqueta de IA siempre**, en zona segura. Al subirlo, activa también la de la plataforma.
- **Un avatar no da testimonio de cliente.** Detalle en `references/legal.md`.

## Qué hay dentro

| Carpeta | Qué |
|---|---|
| `.claude/skills/crear-anuncio/` | El asistente y su método |
| `kit/` | `generar` (imagen, vídeo, música y efectos en Replicate), `revisar` (transcribe y avisa), `montar` (el editor), `efectos`, `subtitulos`, `sonido` (mezcla, ritmo), `zonas`, `transcribir` |
| `kit/assets/` | Tipografías (licencia OFL) |
| `ejemplos/onda-x/` | La demo completa |
| `anuncios/` | Tus anuncios |

Licencias de lo que no es nuestro: [`LICENSE-TERCEROS.md`](LICENSE-TERCEROS.md).

---
Executive Lab · 2026
