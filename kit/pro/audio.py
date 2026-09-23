"""Mezcla del montaje profesional: voz limpia a sonoridad constante, música por tramos (apagada,
abierta, silencio antes del remate), ducking bajo la voz, efectos con paneo y master a −14 LUFS.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt

from kit.ffmpeg import FFMPEG

SR = 48000


def cargar(ruta, mono=False) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(ruta), "-f", "f32le", "-ac", "1" if mono else "2",
                        "-ar", str(SR), "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, np.float32).copy()
    return x if mono else x.reshape(-1, 2)


def estirar(x, vel):
    """Cambia la velocidad sin cambiar el tono (para voz acelerada con su imagen)."""
    if abs(vel - 1) < 1e-3:
        return x
    r = subprocess.run([FFMPEG, "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", f"atempo={vel:.4f}", "-f", "f32le", "-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def pico(x, f0, g_db, q):
    A = 10 ** (g_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return lfilter(b / a[0], a / a[0], x)


def envolvente(x, ms=10):
    n = int(SR * ms / 1000)
    k = len(x) // n
    if k == 0:
        return np.zeros_like(x)
    e = np.repeat(np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-12), n)
    return np.pad(e, (0, len(x) - len(e)), mode="edge")


def _suavizar(v, sube, baja, paso=SR // 1000):
    r = v[::paso]
    s = np.zeros_like(r)
    acc = 0.0
    for i, x in enumerate(r):
        acc += (x - acc) * (sube if x > acc else baja)
        s[i] = acc
    return np.repeat(s, paso)[:len(v)]


def comprimir(x, umbral_db=-22, ratio=3.0):
    db = 20 * np.log10(envolvente(x, 5) + 1e-9)
    red = np.minimum(0, (umbral_db - db) * (1 - 1 / ratio))
    return x * 10 ** (-_suavizar(-red, 0.6, 0.012) / 20)


def tramo_de_voz(x, desde, hasta):
    """Dónde empieza y acaba la voz de verdad dentro de [desde, hasta] (envolvente, no Whisper)."""
    seg = x[int(desde * SR):int(hasta * SR)]
    if not len(seg):
        return desde, hasta
    e = 20 * np.log10(envolvente(seg) + 1e-9)
    suelo = np.percentile(20 * np.log10(envolvente(x) + 1e-9), 10) if len(x) else -80
    umbral = max(e.max() - 30, suelo + 10)
    act = np.nonzero(e > umbral)[0]
    if not len(act):
        return desde, hasta
    return desde + act[0] / SR, desde + act[-1] / SR


def paneo(x, p):
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], -1)


def apagar(x):
    """Cómo suena el mundo sin el producto (o sin los cascos): mono y sin agudos."""
    m = x.mean(1) if x.ndim == 2 else x
    m = sosfilt(butter(4, 420, "lp", fs=SR, output="sos"), m) * 1.25
    return np.stack([m, m], -1)


def remuestrear(x, vel):
    """Más rápido y agudo (vel > 1) o más lento y grave (vel < 1), como una cinta."""
    if abs(vel - 1) < 1e-3:
        return x
    n = int(len(x) / vel)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def voz_limpia(x):
    x = sosfilt(butter(2, 90, "hp", fs=SR, output="sos"), x)
    x = pico(x, 3200, 2.5, 1.0)
    e = envolvente(x)
    act = e > e.max() * 0.1
    rms = np.sqrt((x[act] ** 2).mean()) if act.any() else 0.05
    x = x * (10 ** (-19 / 20) / max(rms, 1e-4))
    fi, fo = int(0.012 * SR), int(0.04 * SR)
    x[:fi] *= np.linspace(0, 1, min(fi, len(x)))[:len(x[:fi])]
    x[-fo:] *= np.linspace(1, 0, min(fo, len(x)))[-len(x[-fo:]):]
    return x


class Mezcla:
    def __init__(self, duracion, raiz: Path):
        self.N = int(duracion * SR)
        self.raiz = raiz
        self.voz = np.zeros(self.N + SR, np.float32)
        self.musica = np.zeros((self.N + SR, 2), np.float32)
        self.sfx = np.zeros((self.N + SR, 2), np.float32)
        self._banco = {}

    def poner_voz(self, x, t):
        i0 = int(t * SR)
        self.voz[i0:i0 + len(x)] += x[:len(self.voz) - i0]

    def tramo_musica(self, pista, t0, t1, desde, apagada=False, fundido=0.03):
        a, b = int(t0 * SR), int(t1 * SR)
        s = pista[int(desde * SR):int(desde * SR) + (b - a)].copy()
        if apagada:
            s = apagar(s)
        f = min(int(fundido * SR), len(s))
        if f:
            s[-f:] *= np.linspace(1, 0, f)[:, None]
        self.musica[a:a + len(s)] += s

    def sonido(self, archivo, t, db=0.0, pan=0.0, apagado=False, pico_en=0.0, rev=False, vel=1.0,
               desde=0.0, dur=None, grave=None):
        if archivo not in self._banco:
            self._banco[archivo] = cargar(self.raiz / archivo, mono=True)
        x = self._banco[archivo][int(desde * SR):]
        if dur:
            x = x[:int(dur * SR)].copy()
            fo = min(len(x), int(0.03 * SR))
            x[-fo:] *= np.linspace(1, 0, fo)
        x = remuestrear(x, vel)
        if grave:
            x = sosfilt(butter(4, grave, "lp", fs=SR, output="sos"), x).astype(np.float32) * 1.4
        if rev:
            x = x[::-1].copy()
        x = x * 10 ** (db / 20)
        if isinstance(pan, (list, tuple)):
            pan = np.linspace(pan[0], pan[1], len(x))
        st = paneo(x, pan)
        if apagado:
            st = apagar(st)
        i0 = int((t - pico_en) * SR)
        if i0 < 0:
            st, i0 = st[-i0:], 0
        self.sfx[i0:i0 + len(st)] += st[:len(self.sfx) - i0]

    def final(self, musica_db=-1.5, ducking_db=8.5, sfx_db=-5.0):
        voz = comprimir(self.voz, -22, 3.0)
        act = np.clip(envolvente(voz, 20) / 0.04, 0, 1)
        duck = _suavizar(act, 0.15, 0.006)
        mus = self.musica * (10 ** ((musica_db - ducking_db * duck) / 20))[:, None]
        total = voz[:, None] + mus + self.sfx * 10 ** (sfx_db / 20)
        return total[:self.N].astype(np.float32)


def masterizar(x, salida: Path, lufs=-14.0, tp=-1.8):
    crudo = salida.with_suffix(".crudo.wav")
    wavfile.write(str(crudo), SR, x)
    pre = "alimiter=limit=0.8:attack=4:release=60:level=disabled"
    r = subprocess.run([FFMPEG, "-v", "info", "-i", str(crudo), "-af",
                        f"{pre},loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    filtro = (f"{pre},loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(crudo), "-af", filtro, "-ar", str(SR),
                    "-c:a", "pcm_s24le", str(salida)], check=True)
    crudo.unlink(missing_ok=True)
    return salida


def compas(t_inicio, t_objetivo, bpm):
    """Primer golpe de la rejilla (que arranca en t_inicio) a partir de t_objetivo."""
    b = 60 / bpm
    return t_inicio + math.ceil((t_objetivo - t_inicio) / b) * b
