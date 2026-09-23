"""Transcripción con marcas de tiempo por palabra, en español.

En un Mac con chip Apple usa mlx-whisper (GPU, ~5× tiempo real); en el resto, faster-whisper.
La primera vez descarga el modelo (~1,5 GB) y lo deja en caché.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from kit.ffmpeg import FFMPEG

MODELO_MLX = "mlx-community/whisper-large-v3-turbo"
MODELO_FW = "large-v3-turbo"


def _a_wav16(ruta: Path) -> Path:
    tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(ruta), "-ac", "1", "-ar", "16000", str(tmp)],
                   check=True)
    return tmp


def _fusionar_cifras(palabras: list[dict]) -> list[dict]:
    """Whisper parte «2.752» en «2» + «.752»: se unen antes de hacer subtítulos."""
    out: list[dict] = []
    for p in palabras:
        if out and re.match(r"^[.,]\d", p["texto"]) and re.search(r"\d$", out[-1]["texto"]):
            out[-1] = {**out[-1], "texto": out[-1]["texto"] + p["texto"], "fin": p["fin"]}
        else:
            out.append(p)
    return out


def transcribir(ruta: Path | str, idioma: str = "es") -> list[dict]:
    """Devuelve [{texto, inicio, fin}] por palabra."""
    wav = _a_wav16(Path(ruta))
    try:
        try:
            import mlx_whisper
            r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=MODELO_MLX, language=idioma,
                                       word_timestamps=True, condition_on_previous_text=False)
            palabras = [{"texto": w["word"].strip(), "inicio": float(w["start"]), "fin": float(w["end"])}
                        for s in r["segments"] for w in s.get("words", [])]
        except ImportError:
            from faster_whisper import WhisperModel
            modelo = WhisperModel(MODELO_FW, compute_type="int8")
            segs, _ = modelo.transcribe(str(wav), language=idioma, word_timestamps=True,
                                        condition_on_previous_text=False, vad_filter=True)
            palabras = [{"texto": w.word.strip(), "inicio": float(w.start), "fin": float(w.end)}
                        for s in segs for w in (s.words or [])]
    finally:
        wav.unlink(missing_ok=True)
    return _fusionar_cifras([p for p in palabras if p["texto"]])
