"""Zona segura: lo que tiene que leerse no puede caer debajo de la interfaz de la red.

Meta (Reels y Stories, unificadas en marzo de 2026): se tapa el 14 % de arriba, el 35 % de abajo y
el 6 % de los lados. En 1080×1920: x 65-1015, y 270-1248. TikTok tapa además una columna de
iconos a la derecha (~120 px) a media altura; se avisa aparte, sin bloquear.
"""
from __future__ import annotations

ZONA = {"x0": 65, "x1": 1015, "y0": 270, "y1": 1248}
TIKTOK_ICONOS = {"x0": 960, "y0": 700, "y1": 1500}


def comprobar(cajas: list[dict]) -> list[str]:
    avisos = []
    for c in cajas:
        fuera = []
        if c["x0"] < ZONA["x0"] or c["x1"] > ZONA["x1"]:
            fuera.append(f"x {c['x0']:.0f}-{c['x1']:.0f} (zona {ZONA['x0']}-{ZONA['x1']})")
        if c["y0"] < ZONA["y0"] or c["y1"] > ZONA["y1"]:
            fuera.append(f"y {c['y0']:.0f}-{c['y1']:.0f} (zona {ZONA['y0']}-{ZONA['y1']})")
        if fuera:
            avisos.append(f"FUERA DE ZONA · {c['nombre']} en t={c['t']} s: " + "; ".join(fuera))
        elif c["x1"] > TIKTOK_ICONOS["x0"] and c["y1"] > TIKTOK_ICONOS["y0"] and c["y0"] < TIKTOK_ICONOS["y1"]:
            avisos.append(f"En TikTok los iconos pueden tapar el borde derecho de {c['nombre']} (t={c['t']} s)")
    return avisos
