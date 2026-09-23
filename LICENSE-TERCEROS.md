# Licencias de terceros

| Qué | Dónde | Licencia |
|---|---|---|
| Lato (Łukasz Dziedzic) | `kit/assets/fuentes/Lato-*.ttf` | SIL Open Font License 1.1 — `kit/assets/fuentes/OFL-Lato.txt` |
| DM Serif Display (Colophon Foundry / Google) | `kit/assets/fuentes/DMSerifDisplay-Regular.ttf` | SIL Open Font License 1.1 — `kit/assets/fuentes/OFL-DMSerifDisplay.txt` |
| Anton (Vernon Adams) | `kit/assets/fuentes/Anton-Regular.ttf` | SIL Open Font License 1.1 — `kit/assets/fuentes/OFL-Anton.txt` |
| Chakra Petch (Cadson Demak) | `kit/assets/fuentes/ChakraPetch-Bold.ttf` | SIL Open Font License 1.1 — `kit/assets/fuentes/OFL-ChakraPetch.txt` |
| Montserrat (Julieta Ulanovsky) | `kit/assets/fuentes/Montserrat.ttf` | SIL Open Font License 1.1 — `kit/assets/fuentes/OFL-Montserrat.txt` |
| Real-ESRGAN, red SRVGGNetCompact y pesos `realesr-general-x4v3` (Xintao Wang) | Arquitectura en `kit/pro/preparar.py`; pesos descargados la primera vez | BSD 3-Clause — github.com/xinntao/Real-ESRGAN |
| Robust Video Matting (Peter Lin) | Modelo descargado la primera vez desde su repositorio (no va en el kit) | GPL-3.0 — github.com/PeterL1n/RobustVideoMatting |
| YuNet, detector de caras (Shiqi Yu, OpenCV Zoo) | Modelo descargado la primera vez | MIT — github.com/opencv/opencv_zoo |
| Imágenes y vídeos de la demo | `ejemplos/onda-x/img`, `vid` | Generados con IA (gpt-image-2.5, gemini-omni-1.1, seedance-2.5). Personaje y marca inventados |
| Música de la demo | `ejemplos/onda-x/audio/musica.wav` | Generada con Google Lyria 2 (vía Replicate), bajo sus condiciones |
| Efectos de la demo | `ejemplos/onda-x/audio/sfx-*.wav` | Generados con Stable Audio Open 1.0 (Stability AI Community License). La edición profesional usa derivados de estos mismos (más graves, al revés, recortados) |

El kit no trae sonidos «de fábrica»: cada anuncio genera los suyos con `kit.generar musica/sonido`
o usa los que tú tengas con licencia.

Los modelos de Replicate se usan con **tu** cuenta y bajo **sus** condiciones (Replicate, OpenAI,
Google, ByteDance). Revisa las de cada modelo antes de usar un anuncio comercialmente.

Este kit no incluye material de pago de terceros.
