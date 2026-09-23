"""Etalonaje y acabado de imagen del montaje profesional.

Cinco perfiles de color. La idea es contar con el color: `antes` (el mundo sin el producto:
desaturado, frío, apagado) y `despues` (vivo), más `inserto_antes`/`inserto` para planos de contexto
(gameplay, cocina, calle) y `producto` para el producto sobre fondo negro.
"""
from __future__ import annotations

import numpy as np
import cv2

W, H = 1080, 1920

PERFILES = {  # canales en BGR
    "antes": dict(exp=0.96, c=0.25, lift=(0.05, 0.032, 0.022), gain=(0.96, 0.93, 0.88),
                  gamma=(1.0, 1.03, 1.06), sat=0.48, bloom=0.2, vin=0.45, grano=0.024),
    "inserto_antes": dict(exp=0.88, c=0.3, lift=(0.045, 0.03, 0.025), gain=(0.95, 0.92, 0.9),
                          gamma=(1.0, 1.03, 1.05), sat=0.5, bloom=0.3, vin=0.45, grano=0.024),
    "despues": dict(exp=1.04, c=0.38, lift=(0.028, 0.012, 0.006), gain=(1.0, 1.0, 1.035),
                    gamma=(0.98, 0.98, 0.97), sat=1.16, bloom=0.5, vin=0.3, grano=0.018),
    "inserto": dict(exp=1.0, c=0.42, lift=(0.024, 0.006, 0.014), gain=(1.03, 0.98, 1.03),
                    gamma=(1.0, 1.02, 1.0), sat=1.14, bloom=0.36, vin=0.3, grano=0.018),
    "producto": dict(exp=1.06, c=0.34, lift=(0.0, 0.0, 0.0), gain=(1.02, 1.0, 1.0),
                     gamma=(1.04, 1.04, 1.04), sat=1.22, bloom=0.75, vin=0.15, grano=0.014),
    "natural": dict(exp=1.0, c=0.2, lift=(0.012, 0.008, 0.006), gain=(1.0, 1.0, 1.01),
                    gamma=(1.0, 1.0, 1.0), sat=1.04, bloom=0.15, vin=0.2, grano=0.016),
}
_LUT = {}


def lut(perfil: str) -> np.ndarray:
    if perfil not in _LUT:
        p = PERFILES[perfil]
        x = np.arange(256) / 255.0
        y = np.clip(x * p["exp"], 0, 1)
        k = 7.0
        sg = 1 / (1 + np.exp(-(y - 0.45) * k))
        s0, s1 = 1 / (1 + np.exp(0.45 * k)), 1 / (1 + np.exp(-0.55 * k))
        y = y * (1 - p["c"]) + (sg - s0) / (s1 - s0) * p["c"]
        can = [np.clip(p["lift"][i] + y * (p["gain"][i] - p["lift"][i]), 0, 1) ** p["gamma"][i] for i in range(3)]
        _LUT[perfil] = (np.stack(can, -1) * 255).round().astype(np.uint8).reshape(1, 256, 3)
    return _LUT[perfil]


def saturar(f: np.ndarray, s: float) -> np.ndarray:
    if abs(s - 1) < 1e-3:
        return f
    l = f[..., 0:1] * 0.114 + f[..., 1:2] * 0.587 + f[..., 2:3] * 0.299
    return l + (f - l) * s


def bloom(f: np.ndarray, k: float, umbral: float = 0.72) -> np.ndarray:
    """Las luces brillantes (RGB, pantallas, destellos) sangran un halo suave."""
    if k <= 0:
        return f
    h, w = f.shape[:2]
    small = cv2.resize(f, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    lum = small.max(axis=2, keepdims=True)
    b = small * np.clip((lum - umbral) / (1 - umbral), 0, 1)
    bl = cv2.GaussianBlur(b, (0, 0), 4) * 0.6 + cv2.GaussianBlur(b, (0, 0), 16) * 0.9
    bl = cv2.resize(bl, (w, h), interpolation=cv2.INTER_LINEAR) * k
    return 1 - (1 - f) * (1 - np.clip(bl, 0, 1))


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_R2 = ((XX - W / 2) / (W / 2)) ** 2 * 0.8 + ((YY - H / 2) / (H / 2)) ** 2
VINETA = np.clip(_R2 / 1.8, 0, 1)[..., None] ** 1.1
_rng = np.random.default_rng(7)
GRANOS = [cv2.GaussianBlur(_rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7)[..., None]
          for _ in range(6)]


def grano(f: np.ndarray, k: int, fuerza: float) -> np.ndarray:
    g = GRANOS[k % len(GRANOS)]
    return f + np.roll(g, (k * 37) % 200, axis=1) * fuerza


def borde_suave(sw: int, sh: int, px: int = 120) -> np.ndarray:
    """Máscara que funde los bordes a negro (para encoger un plano de producto sobre fondo negro)."""
    m = np.ones((sh, sw), np.float32)
    for i in range(px):
        v = (i / px) ** 1.5
        m[i, :] *= v; m[-1 - i, :] *= v; m[:, i] *= v; m[:, -1 - i] *= v
    return m


def aberracion(f: np.ndarray, fuerza: float) -> np.ndarray:
    out = f.copy()
    h, w = f.shape[:2]
    for canal, esc in ((2, 1 + 0.009 * fuerza), (0, 1 - 0.009 * fuerza)):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, esc)
        out[..., canal] = cv2.warpAffine(f[..., canal], M, (w, h), borderMode=cv2.BORDER_REFLECT101)
    return out


def glitch(f: np.ndarray, k: int) -> np.ndarray:
    rng = np.random.default_rng(k)
    out = f.copy()
    h = f.shape[0]
    for _ in range(9):
        y0 = rng.integers(0, h - 60)
        hh = rng.integers(12, 90)
        out[y0:y0 + hh] = np.roll(f[y0:y0 + hh], rng.integers(-90, 90), axis=1)
    return out


def barrido(f: np.ndarray, u: float) -> np.ndarray:
    """Un brillo diagonal que cruza el plano (u de 0 a 1), más fuerte donde ya hay luz."""
    banda = np.clip(1 - np.abs((XX + YY * 0.45) / (W + H * 0.45) - (u * 1.4 - 0.2)) / 0.07, 0, 1)
    return f + banda[..., None] * np.sqrt(f.max(axis=2, keepdims=True)) * 0.5
