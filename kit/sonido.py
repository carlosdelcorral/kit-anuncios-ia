"""Sonido del anuncio: efectos y música desde ficheros (generados con `kit.generar sonido/musica` o
tuyos con licencia), colocados en la línea de tiempo con paneo y efecto «apagado», ducking de la
música bajo la voz, silencios, y loudnorm a −14 LUFS.

    python -m kit.sonido --ritmo anuncios/x/audio/musica.wav     # tempo y golpes, para cortar a ritmo

Todo en numpy a 48 kHz estéreo. ffmpeg solo decodifica, codifica y mide (loudnorm en dos pasadas).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

from kit.ffmpeg import FFMPEG

SR = 48000
AQUI = Path(__file__).resolve().parent


# ─── utilidades ───────────────────────────────────────────────────────────────────────────────
def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def _lp(x: np.ndarray, corte) -> np.ndarray:
    """Paso bajo de un polo; `corte` puede ser un número o un array (barrido)."""
    corte = np.broadcast_to(np.asarray(corte, dtype=float), x.shape)
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def _hp(x: np.ndarray, corte: float) -> np.ndarray:
    return x - _lp(x, corte)


def _norm(x: np.ndarray, pico_db: float) -> np.ndarray:
    p = np.max(np.abs(x)) or 1.0
    return x / p * 10 ** (pico_db / 20)


def _estereo(x: np.ndarray) -> np.ndarray:
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


def leer_wav(ruta: Path) -> np.ndarray:
    with wave.open(str(ruta)) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2, f"{ruta}: se espera 48 kHz 16 bits"
        d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return d.reshape(-1, w.getnchannels()) if w.getnchannels() > 1 else _estereo(d)


def escribir_wav(ruta: Path, x: np.ndarray) -> Path:
    x = _estereo(np.clip(x, -1, 1))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return ruta


# ─── la mezcla ────────────────────────────────────────────────────────────────────────────────
def _pan(x: np.ndarray, desde: float, hasta: float) -> np.ndarray:
    """Paneo de potencia constante que va de `desde` a `hasta` (−1 izquierda, +1 derecha)."""
    mono = x.mean(axis=1)
    p = np.linspace(desde, hasta, len(mono))
    th = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(th), mono * np.sin(th)], axis=1)


PANEOS = {None: None, "centro": (0, 0), "izq": (-0.9, -0.9), "der": (0.9, 0.9),
          "izq-der": (-1, 1), "der-izq": (1, -1)}


def cargar(ruta: Path) -> np.ndarray:
    ruta = Path(ruta)
    return leer_wav(ruta) if ruta.suffix == ".wav" and _es_48k(ruta) else leer_wav(_a_wav(ruta))


def _es_48k(ruta: Path) -> bool:
    try:
        with wave.open(str(ruta)) as w:
            return w.getframerate() == SR and w.getsampwidth() == 2
    except Exception:
        return False


def apagar(x: np.ndarray, corte: float = 650.0) -> np.ndarray:
    """Suena «a través de unos cascos malos»: mono, sin agudos y más bajo."""
    mono = x.mean(axis=1)
    f = np.fft.rfft(mono)
    frec = np.fft.rfftfreq(len(mono), 1 / SR)
    f *= 1 / (1 + (frec / corte) ** 4)
    y = np.fft.irfft(f, n=len(mono)) * 0.6
    return np.stack([y, y], axis=1)


def colocar(capa: np.ndarray, evento: dict) -> None:
    """Pone un efecto (`archivo`, ya con ruta absoluta) en la capa, con `db`, `pan`, `apagado` y `dur`."""
    x = cargar(evento["archivo"]).copy()
    if evento.get("dur"):
        n = int(float(evento["dur"]) * SR)
        x = x[:n]
        cola = min(len(x), int(0.05 * SR))
        x[-cola:] *= np.linspace(1, 0, cola)[:, None]
    if evento.get("apagado"):
        x = apagar(x)
    pan = PANEOS.get(evento.get("pan"))
    if pan:
        x = _pan(x, *pan)
    x = x * 10 ** (float(evento.get("db", 0)) / 20)
    i0 = int(evento["t"] * SR)
    if i0 < 0:
        x, i0 = x[-i0:], 0
    fin = min(len(capa), i0 + len(x))
    if fin > i0:
        capa[i0:fin] += x[: fin - i0]


def ducking(musica: np.ndarray, voz: np.ndarray, reduccion_db: float = 10.0) -> np.ndarray:
    """Baja la música cuando hay voz: envolvente RMS de 50 ms con ataque 30 ms y relajación 350 ms."""
    ventana = int(0.05 * SR)
    energia = np.sqrt(np.convolve(voz.mean(axis=1) ** 2, np.ones(ventana) / ventana, mode="same"))
    hay_voz = (energia > 10 ** (-42 / 20)).astype(float)
    g = np.empty_like(hay_voz)
    acc = 0.0
    at, rel = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.35 * SR))
    for i, v in enumerate(hay_voz[::48]):                      # a 1 kHz basta
        k = at if v > acc else rel
        acc = k * acc + (1 - k) * v
        g[i * 48:(i + 1) * 48] = acc
    ganancia = 10 ** (-reduccion_db * g / 20)
    return musica * ganancia[:, None]


def mezclar(voz: np.ndarray, eventos: list[dict], musica: dict | None) -> np.ndarray:
    n = len(voz)
    capa = np.zeros((n, 2))
    for e in eventos:
        colocar(capa, e)
    pico_voz = np.max(np.abs(voz)) or 1e-3
    rms_voz = np.sqrt(np.mean(voz[np.abs(voz.mean(axis=1)) > 10 ** (-45 / 20)] ** 2)) if pico_voz > 1e-3 else 0.05
    # Los efectos se ajustan todos juntos: el más fuerte queda ~3 dB por debajo del pico de la voz;
    # entre ellos manda el `db` de cada uno.
    if np.max(np.abs(capa)) > 0:
        capa = capa / np.max(np.abs(capa)) * pico_voz * 10 ** (-3 / 20)
    mezcla = voz + capa
    if musica and musica.get("archivo"):
        m = cargar(musica["archivo"])
        m = m[int(float(musica.get("desde", 0)) * SR):]
        reps = int(np.ceil(n / len(m)))
        m = np.tile(m, (reps, 1))[:n]
        m = m / (np.sqrt(np.mean(m ** 2)) or 1) * rms_voz * 10 ** (float(musica.get("db", -10)) / 20)
        if musica.get("ducking", True):
            m = ducking(m, voz, float(musica.get("ducking_db", 8)))
        cola = int(1.0 * SR)
        m[-cola:] *= np.linspace(1, 0, cola)[:, None]
        # «apagada»: suena como a través de unos cascos malos y al final del tramo SE ABRE en 0,25 s
        if musica.get("apagada"):
            mp = apagar(m, 520) / 0.6 * 0.8
            env = np.zeros(n)
            abre = int(0.25 * SR)
            for a, b in musica["apagada"]:
                i0, i1 = int(a * SR), min(n, int(b * SR))
                env[i0:i1] = 1
                env[i1:i1 + abre] = np.linspace(1, 0, len(env[i1:i1 + abre]))
            m = mp * env[:, None] + m * (1 - env[:, None])
        rampa = int(0.06 * SR)
        for a, b in musica.get("silencios", []):             # la música se calla (s del montaje)
            env = np.ones(n)
            i0, i1 = int(a * SR), min(n, int(b * SR))
            env[i0:i1] = 0
            env[max(0, i0 - rampa):i0] = np.linspace(1, 0, i0 - max(0, i0 - rampa))
            env[i1:i1 + rampa] = np.linspace(0, 1, len(env[i1:i1 + rampa]))
            m = m * env[:, None]
        mezcla = mezcla + m
    return mezcla


def ritmo(ruta: Path) -> dict:
    """Tempo y golpes de la música (flujo espectral + autocorrelación). Sirve para cortar a ritmo."""
    x = cargar(ruta).mean(axis=1)
    hop = 512
    ventanas = np.lib.stride_tricks.sliding_window_view(x, 2048)[::hop] * np.hanning(2048)
    espectro = np.abs(np.fft.rfft(ventanas, axis=1))
    flujo = np.maximum(0, np.diff(np.log1p(espectro), axis=0)).sum(axis=1)
    flujo = (flujo - flujo.mean()) / (flujo.std() or 1)
    fps = SR / hop
    ac = np.correlate(flujo, flujo, mode="full")[len(flujo) - 1:]
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)
    periodo = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60 * fps / periodo
    picos = [i for i in range(1, len(flujo) - 1) if flujo[i] > 1.5 and flujo[i] >= flujo[i - 1] and flujo[i] >= flujo[i + 1]]
    golpes = [round(i / fps, 3) for i in picos]
    return {"bpm": round(bpm, 1), "golpes": golpes}


def _a_wav(ruta: Path) -> Path:
    destino = ruta.with_suffix(".48k.wav")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(ruta), "-ar", str(SR), "-ac", "2", destino],
                   check=True)
    return destino


def loudnorm(entrada: Path, salida: Path, lufs: float = -14.0, tp: float = -1.5) -> dict:
    """Dos pasadas: se mide y se aplica con los valores medidos (lineal). Devuelve la medida final."""
    def medir(ruta: Path, filtro: str) -> dict:
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(ruta), "-af", filtro, "-f", "null", "-"],
                           capture_output=True, text=True)
        return json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    m = medir(entrada, f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json")
    filtro = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:linear=true,aresample={SR}")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(entrada), "-af", filtro, "-ar", str(SR), str(salida)],
                   check=True)
    final = medir(salida, f"loudnorm=I={lufs}:print_format=json")
    return {"lufs": float(final["input_i"]), "pico_dbtp": float(final["input_tp"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ritmo", type=Path, help="música: imprime el tempo y los golpes fuertes")
    a = ap.parse_args()
    if a.ritmo:
        r = ritmo(a.ritmo)
        print(f"≈ {r['bpm']} BPM · un tiempo cada {60 / r['bpm']:.3f} s")
        print("golpes fuertes (s):", " ".join(f"{g:.2f}" for g in r["golpes"][:60]))
    else:
        ap.print_help()
