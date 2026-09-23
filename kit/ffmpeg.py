"""Dónde está ffmpeg. Primero el del sistema; si no hay, el de `static-ffmpeg` (pip), que trae
libass para los subtítulos. Así el alumno no tiene que compilar nada."""
from __future__ import annotations

import shutil
import subprocess


def _tiene_libass(ffmpeg: str) -> bool:
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20)
        return " ass " in r.stdout
    except Exception:
        return False


def _localizar() -> tuple[str, str]:
    sistema = shutil.which("ffmpeg")
    if sistema and _tiene_libass(sistema):
        return sistema, shutil.which("ffprobe") or sistema.replace("ffmpeg", "ffprobe")
    try:
        import static_ffmpeg.run as sf
        ffmpeg, ffprobe = sf.get_or_fetch_platform_executables_else_raise()
        return ffmpeg, ffprobe
    except Exception as e:
        raise SystemExit("No encuentro ffmpeg con libass. Instala las dependencias: "
                         "pip install -r requirements.txt") from e


FFMPEG, FFPROBE = _localizar()
