# Kit de anuncios con IA

Kit para crear anuncios UGC y anuncios hiperrealistas verticales con avatares generados, y montarlos
con un editor propio. El usuario es un alumno que no sabe editar vídeo: habla claro, de tú, breve.

- **Primera vez:** si no existe `mi-perfil.md` en la raíz, lo primero, antes de cualquier otra cosa,
  es el **onboarding** (`.claude/skills/crear-anuncio/references/onboarding.md`): unas preguntas para
  conocer su negocio, público, mercado y acento, proveedor, presupuesto y marca, y se guarda el perfil.
  Si existe, se lee antes de cada anuncio.
- **Entrada:** skill `crear-anuncio` (`.claude/skills/crear-anuncio/SKILL.md`). Cuando el usuario
  quiera un anuncio, un UGC, un reel para vender, ángulos, hooks, o traiga un guion, úsala.
- **Comandos** (desde la raíz, con el `.venv` activo): `python -m kit.generar …`,
  `python -m kit.revisar …`, `python -m kit.montar <anuncio.json>`. Detalle en `README.md`.
- **Cada anuncio** en `anuncios/<slug>/` (`img/`, `vid/`, `audio/`, `guion.md`, `guion.json`,
  `anuncio.json`). Referencia completa: `ejemplos/onda-x/`.

## Reglas que no se rompen

1. Preguntar antes de hacer; **una pregunta cada vez**, con opciones.
2. **Estrategia antes que guion**: voz del cliente, menú de ángulos, mecanismo y nivel de consciencia,
   y el usuario elige el ángulo (`references/metodo.md`).
3. **OK al guion (con coste) y OK a la primera imagen** antes de generar nada más.
4. **Escena por escena, nunca de un tirón**: un plano cada vez (imagen → clip → revisión); si falla,
   se repite solo ese.
5. Modelos: `sunburst` en calidad `low` para imágenes; `--modelo omni` para personas que hablan (el
   que mejor hace el español); `seedance` solo para objetos (rechaza caras).
6. Ningún texto generado dentro de la imagen o el vídeo, salvo el nombre en el propio producto.
7. Etiqueta de IA siempre (el editor la pone); ningún avatar da testimonio de cliente.
8. Montaje **dinámico por defecto** (`references/montaje.md`): `apretar` en todo plano que habla,
   un cambio cada 1-2,5 s, insertos sin cara, sonido real (nunca sintético), diálogo natural.
9. Revisar cada clip con `kit.revisar` antes de montar; arreglar en montaje lo que se pueda y
   regenerar solo el clip que no, avisando del coste.
10. No tocar el `.env` ni mostrar la clave.
