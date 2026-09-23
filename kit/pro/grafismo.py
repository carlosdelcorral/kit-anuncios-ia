"""Grafismo del montaje profesional: texto cinético, texto detrás del sujeto, anillo 360, ondas de
sonido, indicador de dirección, avisos de juego, marca y CTA. Todo se dibuja en píxeles de la salida
(1080×1920) salvo lo que sigue a la cabeza, que se coloca con la cara detectada en cada fotograma.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SH = 2560
FUENTES = Path(__file__).resolve().parents[1] / "assets" / "fuentes"
NOMBRES = {"blanco": (255, 255, 255), "rojo": (255, 59, 78), "cian": (61, 245, 255),
           "violeta": (162, 89, 255), "negro": (8, 8, 16), "amarillo": (255, 214, 0)}


def hex_a_rgb(c) -> tuple:
    if isinstance(c, (list, tuple)):
        return tuple(int(v) for v in c)
    if c in NOMBRES:
        return NOMBRES[c]
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ───────────── curvas ─────────────

def ease_io(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    return 1 - (1 - min(max(x, 0.0), 1.0)) ** 3


def ease_back(x, s=2.2):
    x = min(max(x, 0.0), 1.0) - 1
    return x * x * ((s + 1) * x + s) + 1


def ruido(t, semilla):
    r = np.random.default_rng(semilla).uniform(0, 2 * np.pi, 3)
    return math.sin(t + r[0]) * 0.5 + math.sin(t * 2.3 + r[1]) * 0.3 + math.sin(t * 4.1 + r[2]) * 0.2


# ───────────── tipografía y sprites ─────────────

_F = {}


def fuente(nombre: str, tam: int):
    """«titular» (Anton), «texto» (Montserrat 900), «texto600», «hud» (Chakra Petch Bold)."""
    k = (nombre, tam)
    if k not in _F:
        if nombre.startswith("texto"):
            f = ImageFont.truetype(str(FUENTES / "Montserrat.ttf"), tam)
            f.set_variation_by_axes([int(nombre[5:] or 900)])
        elif nombre == "titular":
            f = ImageFont.truetype(str(FUENTES / "Anton-Regular.ttf"), tam)
        else:
            f = ImageFont.truetype(str(FUENTES / "ChakraPetch-Bold.ttf"), tam)
        _F[k] = f
    return _F[k]


def a_sprite(im: Image.Image) -> np.ndarray:
    """PIL RGBA → float32 BGRA premultiplicado."""
    a = np.asarray(im.convert("RGBA"), np.float32) / 255.0
    return np.dstack([a[..., 2::-1] * a[..., 3:4], a[..., 3]])


def _ancho(t, fnt, tracking=0):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return d.textlength(t, font=fnt) + tracking * max(len(t) - 1, 0)


def sprite_linea(trozos, nombre_fuente, tam, trazo=6, sombra=0.55, tracking=0, ancho_max=None):
    """[(texto, rgb)] en una línea con contorno oscuro y sombra; encoge si no cabe en ancho_max."""
    fnt = fuente(nombre_fuente, tam)
    esp = lambda f: f.size * 0.28  # noqa: E731
    if ancho_max:
        while tam > 36 and sum(_ancho(t, fnt, tracking) for t, _ in trozos) + esp(fnt) * (len(trozos) - 1) > ancho_max:
            tam = int(tam * 0.94)
            fnt = fuente(nombre_fuente, tam)
    anchos = [_ancho(t, fnt, tracking) for t, _ in trozos]
    asc, desc = fnt.getmetrics()
    pad = trazo + 34
    Wc = int(sum(anchos) + esp(fnt) * (len(trozos) - 1) + 2 * pad)
    Hc = int(asc + desc + 2 * pad)
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, rangos = pad, []
    for (t, col), aw in zip(trozos, anchos):
        xx = x
        for ch in (t if tracking else [t]):
            d.text((xx, pad), ch, font=fnt, fill=tuple(col) + (255,), stroke_width=trazo,
                   stroke_fill=(8, 8, 16, 255))
            xx += d.textlength(ch, font=fnt) + tracking
        rangos.append((x - Wc / 2, x + aw - Wc / 2))
        x += aw + esp(fnt)
    if sombra:
        a = im.split()[3].filter(ImageFilter.GaussianBlur(12))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * sombra)))
        base = Image.new("RGBA", im.size, (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 9))
        base.alpha_composite(im)
        im = base
    return a_sprite(im), rangos


def sprite_degradado(texto, tam, arriba, abajo, brillo=None, radio=26, tracking=0, nombre_fuente="titular"):
    """Texto grande con relleno en degradado vertical y halo de color."""
    fnt = fuente(nombre_fuente, tam)
    asc, desc = fnt.getmetrics()
    pad = radio * 3
    Wc, Hc = int(_ancho(texto, fnt, tracking) + 2 * pad), int(asc + desc + 2 * pad)
    m = Image.new("L", (Wc, Hc), 0)
    d = ImageDraw.Draw(m)
    x = pad
    for ch in texto:
        d.text((x, pad), ch, font=fnt, fill=255)
        x += d.textlength(ch, font=fnt) + tracking
    mm = np.asarray(m, np.float32) / 255.0
    ys = np.nonzero(mm.max(1) > 0.1)[0]
    y0, y1 = (ys[0], ys[-1]) if len(ys) else (0, Hc)
    u = np.clip((np.arange(Hc) - y0) / max(y1 - y0, 1), 0, 1)[:, None, None]
    col = (np.array(arriba, np.float32) * (1 - u) + np.array(abajo, np.float32) * u) / 255.0
    col = np.broadcast_to(col, (Hc, Wc, 3))[..., ::-1]
    spr = np.dstack([col * mm[..., None], mm])
    if brillo:
        g = cv2.GaussianBlur(mm, (0, 0), radio)
        gc = np.array(brillo[::-1], np.float32) / 255.0
        spr = spr + np.dstack([gc * g[..., None] * 0.9, g * 0.9]) * (1 - spr[..., 3:4])
    return spr.astype(np.float32)


def pegar(img, spr, cx, cy, esc=1.0, alfa=1.0, rot=0.0):
    """Compone un sprite premultiplicado sobre img (float BGR) con escala y giro en su centro."""
    if alfa <= 0.003 or esc <= 0.01:
        return
    h, w = spr.shape[:2]
    c, s = math.cos(rot) * esc, math.sin(rot) * esc
    M = np.array([[c, -s, 0], [s, c, 0]], np.float64)
    M[:, 2] = np.array([cx, cy]) - M[:, :2] @ np.array([w / 2, h / 2])
    esq = M[:, :2] @ np.array([[0, w, w, 0], [0, 0, h, h]]) + M[:, 2:3]
    x0, y0 = max(int(esq[0].min()) - 1, 0), max(int(esq[1].min()) - 1, 0)
    x1, y1 = min(int(esq[0].max()) + 2, img.shape[1]), min(int(esq[1].max()) + 2, img.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    M[:, 2] -= [x0, y0]
    out = cv2.warpAffine(spr, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderValue=0)
    a = out[..., 3:4] * alfa
    roi = img[y0:y1, x0:x1]
    roi *= (1 - a)
    roi += out[..., :3] * alfa


class Lienzo:
    """Capa uint8 (color premultiplicado + alfa) para dibujar líneas con antialias y halo."""

    def __init__(self):
        self.c = np.zeros((H, W, 3), np.uint8)
        self.a = np.zeros((H, W), np.uint8)

    def linea(self, p0, p1, col, alfa, grosor):
        cv2.line(self.c, p0, p1, tuple(int(v * alfa) for v in col[::-1]), grosor, cv2.LINE_AA)
        cv2.line(self.a, p0, p1, int(255 * alfa), grosor, cv2.LINE_AA)

    def elipse(self, centro, ejes, a0, a1, col, alfa, grosor):
        e = tuple(max(1, int(v)) for v in ejes)
        cv2.ellipse(self.c, centro, e, 0, a0, a1, tuple(int(v * alfa) for v in col[::-1]), grosor, cv2.LINE_AA)
        cv2.ellipse(self.a, centro, e, 0, a0, a1, int(255 * alfa), grosor, cv2.LINE_AA)

    def componer(self, img, halo=10.0):
        c = self.c.astype(np.float32) / 255.0
        a = self.a.astype(np.float32)[..., None] / 255.0
        if halo:
            img += cv2.GaussianBlur(c, (0, 0), halo) * 1.6
        np.multiply(img, 1 - a, out=img)
        img += c


_CACHE = {}


def cache(clave, fn):
    if clave not in _CACHE:
        _CACHE[clave] = fn()
    return _CACHE[clave]


def a_salida(M, x, y):
    return (M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2])


# ───────────── elementos ─────────────
# Cada elemento sabe su ventana [t0, t1) en segundos del montaje, su capa («delante» o «detras»:
# detrás del sujeto, con la máscara de persona) y cómo dibujarse. E resuelve tiempos y colores.

class Elemento:
    capa = "delante"
    necesita_cabeza = False

    def __init__(self, d, E):
        self.d = d
        self.E = E
        self.planos = d["plano"] if isinstance(d.get("plano"), list) else ([d["plano"]] if "plano" in d else [])
        if self.planos:
            self.t0 = E.S[self.planos[0]].t0
            self.t1 = E.S[self.planos[-1]].t0 + E.S[self.planos[-1]].n / E.fps
        else:
            self.t0 = E.t(d.get("desde", 0))
            self.t1 = E.t(d["hasta"]) if "hasta" in d else E.duracion
        if "desde" in d and self.planos:
            self.t0 = E.t(d["desde"])

    def activo(self, T):
        return self.t0 <= T < self.t1


class Titulo(Elemento):
    """Titular del hook en líneas que entran de golpe: {"lineas": [{texto, color, tam, y, t}]}."""

    def dibujar(self, img, T, ctx):
        temb = 0.0
        ls = self.d["lineas"]
        tiempos = [self.E.t(l.get("t", 0), self.planos[0] if self.planos else None) for l in ls]
        for t0 in tiempos:
            if T >= t0:
                temb += 12 * max(0, 1 - (T - t0) / 0.18) ** 2
        dx, dy = temb * ruido(T * 60, 1), temb * ruido(T * 60, 2)
        for l, t0 in zip(ls, tiempos):
            if T < t0:
                continue
            col = self.E.color(l.get("color", "blanco"), t0)
            spr = cache(("tit", l["texto"], col, l.get("tam", 150)), lambda: sprite_linea(
                [(l["texto"], col)], "titular", l.get("tam", 150), trazo=8, ancho_max=920)[0])
            u = (T - t0) / 0.13
            pegar(img, spr, W / 2 + dx, l.get("y", 600) + dy, esc=1.5 - 0.5 * ease_out(u), alfa=min(1, (T - t0) / 0.04))


class Cartel(Elemento):
    """Palabras gigantes que entran una a una; «tachar» cruza una con una raya, «glitch» la hace temblar."""

    def dibujar(self, img, T, ctx):
        tam = self.d.get("tam", 190)
        y = self.d.get("y", self.E.y_sub)
        trozos = self.d["trozos"]
        sprs = []
        for tr in trozos:
            col = self.E.color(tr.get("color", "blanco"), self.t0)
            sprs.append(cache(("cartel", tr["texto"], col, tam), lambda tr=tr, col=col: sprite_linea(
                [(tr["texto"], col)], "titular", tam, trazo=8)[0]))
        anchos = [s.shape[1] - 84 for s in sprs]
        x = W / 2 - (sum(anchos) + 40 * (len(anchos) - 1)) / 2
        pl = self.planos[0] if self.planos else None
        for tr, spr, aw in zip(trozos, sprs, anchos):
            cx = x + aw / 2
            x += aw + 40
            t0 = self.E.t(tr.get("t", 0), pl)
            if T < t0:
                continue
            v = T - t0
            gl = max(0, 1 - v / 0.3) if tr.get("glitch") else 0
            if gl > 0:
                k = gl * 22
                for canales, off in (((0, 1), k), ((1, 2), -k)):
                    s_ = spr.copy()
                    s_[..., list(canales)] = 0
                    pegar(img, s_, cx + off, y + ruido(T * 90, 5) * k * 0.4, alfa=0.9)
            pegar(img, spr, cx + ruido(T * 80, 7) * gl * 10, y, esc=1.45 - 0.45 * ease_out(v / 0.12),
                  alfa=min(1, v / 0.04))
            if tr.get("tachar") and v > 0.2:
                L = aw * 1.25 * ease_out((v - 0.2) / 0.1)
                a0 = (cx - aw * 0.62, y + 26)
                ang = math.radians(-9)
                a1 = (a0[0] + L * math.cos(ang), a0[1] + L * math.sin(ang))
                lz = Lienzo()
                lz.linea(tuple(map(int, a0)), tuple(map(int, a1)), (8, 8, 16), 1.0, 30)
                lz.componer(img, halo=0)
                lz = Lienzo()
                lz.linea(tuple(map(int, a0)), tuple(map(int, a1)), (255, 255, 255), 1.0, 18)
                lz.componer(img, halo=0)


class Detras(Elemento):
    """Texto grande DETRÁS del sujeto: {"piezas": [{texto, x, y, tam, color, color2, t}]}.
    Colócalo a los lados y por encima de la cabeza, nunca en el centro: la cabeza lo taparía."""
    capa = "detras"

    def dibujar(self, img, T, ctx):
        deriva = 1 + 0.03 * max(0, T - self.t0) / max(self.t1 - self.t0, 0.1)
        for pz in self.d["piezas"]:
            t0 = self.E.t(pz.get("t", 0), self.planos[0] if self.planos else None)
            if T < t0 - 0.02:
                continue
            c1 = self.E.color(pz.get("color", "blanco"), t0)
            c2 = self.E.color(pz.get("color2", pz.get("color", "blanco")), t0)
            brillo = self.E.color(pz.get("brillo", "acento"), t0)
            spr = cache(("detras", pz["texto"], pz.get("tam", 400), c1, c2, brillo),
                        lambda: sprite_degradado(pz["texto"], pz.get("tam", 400), c1, c2, brillo=brillo, radio=28))
            v = T - t0 + 0.02
            cx, y = pz.get("x", W / 2), pz.get("y", 470)
            pegar(img, spr, W / 2 + (cx - W / 2) * deriva, y, esc=(1.35 - 0.35 * ease_out(v / 0.16)) * deriva,
                  alfa=min(1, v / 0.05))


class Orbita(Elemento):
    """Anillo que gira alrededor de la cabeza; la mitad de atrás pasa por detrás (máscara)."""
    necesita_cabeza = True

    def dibujar(self, img, T, ctx):
        cab = ctx.get("cabeza")
        if not cab:
            return
        t = T - self.t0
        M = ctx["M"]
        cx, cy = cab["cx"], cab["top"] + 0.72 * (cab["menton"] - cab["top"])
        rx, ry, incl = cab["ancho"] * 1.1, 0.085 * SH, math.radians(-6)
        ap = ease_out(t / 0.35)
        vuelta = self.d.get("vuelta", 1.15)
        theta = -math.pi / 2 + 2 * math.pi * t / vuelta
        c1 = self.E.color(self.d.get("color", "violeta"), T)
        c2 = self.E.color(self.d.get("color2", "acento"), T)
        pts = []
        for i in range(71):
            f = -math.pi + 2 * math.pi * i / 70
            x, y = rx * math.cos(f) * ap, ry * math.sin(f) * ap
            pts.append((f, a_salida(M, cx + x * math.cos(incl) - y * math.sin(incl),
                                    cy + x * math.sin(incl) + y * math.cos(incl))))
        lz = Lienzo()
        for (f0, q0), (f1, q1) in zip(pts, pts[1:]):
            if (math.sin((f0 + f1) / 2) > 0) != (ctx["capa"] == "delante"):
                continue
            dd = (theta - (f0 + f1) / 2) % (2 * math.pi)
            ac = max(0.0, 1 - dd / 2.6) if dd < 2.6 else 0.0
            col = tuple(int(c1[k] * (1 - ac) + c2[k] * ac) for k in range(3))
            lz.linea(tuple(map(int, q0)), tuple(map(int, q1)), col, (0.28 + 0.72 * ac ** 1.5) * ap, int(3 + 7 * ac))
        fc = theta % (2 * math.pi)
        if (math.sin(fc) > 0) == (ctx["capa"] == "delante"):
            x, y = rx * math.cos(fc), ry * math.sin(fc)
            q = a_salida(M, cx + x * math.cos(incl) - y * math.sin(incl), cy + x * math.sin(incl) + y * math.cos(incl))
            cv2.circle(lz.c, tuple(map(int, q)), 11, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(lz.a, tuple(map(int, q)), 11, 255, -1, cv2.LINE_AA)
        lz.componer(img, halo=12)


class Ondas(Elemento):
    """Una onda sale del lado de la cabeza por donde suena cada paso: {"pasos": [t…], "lados": [-1, 1…]}."""
    necesita_cabeza = True

    def dibujar(self, img, T, ctx):
        cab = ctx.get("cabeza")
        if not cab or ctx["capa"] != "delante":
            return
        M = ctx["M"]
        lados = self.d.get("lados") or [(-1) ** (i + 1) for i in range(len(self.d["pasos"]))]
        cy = cab["top"] + 0.45 * (cab["menton"] - cab["top"])
        col = self.E.color(self.d.get("color", "acento"), T)
        lz = Lienzo()
        for tp, lado in zip(self.d["pasos"], lados):
            for eco in (0.0, 0.09):
                e = T - (self.t0 + tp + eco)
                if 0 <= e < 0.5:
                    q = a_salida(M, cab["cx"] + lado * cab["ancho"] * 0.7, cy)
                    r = 30 + 330 * ease_out(e / 0.5)
                    lz.elipse(tuple(map(int, q)), (r * 0.55, r), 0, 360, col, (1 - e / 0.5) ** 1.4 * 0.95,
                              max(2, int(9 * (1 - e / 0.5))))
        lz.componer(img, halo=9)


class Direccion(Elemento):
    """Indicador de por dónde viene el sonido: arco y flechas en un lado, que laten con cada paso."""

    def dibujar(self, img, T, ctx):
        t = T - self.t0
        izq = self.d.get("lado", "izq") == "izq"
        col = self.E.color(self.d.get("color", "acento"), T)
        pulso = max([max(0.0, 1 - (t - tp) / 0.35) for tp in self.d.get("pasos", []) if t >= tp] + [0.0])
        ap = ease_out(t / 0.15)
        lz = Lienzo()
        a0, a1 = (148, 212) if izq else (-32, 32)
        lz.elipse((W // 2, 960), (420, 420), a0, a1, col, (0.45 + 0.55 * pulso) * ap, 12)
        for i in range(3):
            fase = (t * 3.2 - i * 0.28) % 1.0
            a = (0.25 + 0.75 * max(0, 1 - fase * 1.6)) * ap
            if izq:
                x = 250 - i * 52
                lz.linea((x + 26, 920), (x, 960), col, a, 11); lz.linea((x, 960), (x + 26, 1000), col, a, 11)
            else:
                x = W - 250 + i * 52
                lz.linea((x - 26, 920), (x, 960), col, a, 11); lz.linea((x, 960), (x - 26, 1000), col, a, 11)
        lz.componer(img, halo=10)


class Aviso(Elemento):
    """Filas tipo killfeed arriba a la derecha: {"filas": [{t, izq, der}]}. Sirve para cualquier
    notificación con dos textos: «ONDA_X ⌖ ROBOT», «PEDIDO ✓ ENVIADO»…"""

    def dibujar(self, img, T, ctx):
        filas = [f for f in self.d["filas"] if T >= self.E.t(f["t"])]
        for i, f in enumerate(reversed(filas)):
            e = T - self.E.t(f["t"])
            col = self.E.color(f.get("color", "acento"), T)
            spr = cache(("aviso", f["izq"], f["der"], col), lambda f=f, col=col: self._fila(f["izq"], f["der"], col))
            x = 1010 - spr.shape[1] / 2 + 460 * (1 - ease_out(e / 0.16))
            y = 318 + i * 70 * (ease_out(e / 0.16) if i == 0 else 1)
            pegar(img, spr, x, y, alfa=min(1, e / 0.06))

    @staticmethod
    def _fila(izq, der, col):
        fnt = fuente("hud", 34)
        wi, wd = _ancho(izq, fnt), _ancho(der, fnt)
        w = int(22 + wi + 24 + 44 + 24 + wd + 22)
        im = Image.new("RGBA", (w, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, 59), 8, fill=(8, 8, 16, 185))
        d.rectangle((0, 8, 6, 51), fill=col + (255,))
        d.text((22, 10), izq, font=fnt, fill=col + (255,))
        cx, cy = int(22 + wi + 24 + 22), 30
        d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), outline=(255, 255, 255, 255), width=3)
        for a, b in (((cx - 22, cy), (cx - 8, cy)), ((cx + 8, cy), (cx + 22, cy)),
                     ((cx, cy - 22), (cx, cy - 8)), ((cx, cy + 8), (cx, cy + 22))):
            d.line((a, b), fill=(255, 255, 255, 255), width=3)
        d.text((cx + 22 + 24, 10), der, font=fnt, fill=(255, 255, 255, 255))
        return a_sprite(im)


class Impacto(Elemento):
    """Marca de impacto en el centro (hitmarker): {"t": [ref…], "color"}."""

    def __init__(self, d, E):
        super().__init__({**d, "desde": 0}, E)
        self.tiempos = [E.t(x) for x in d["t"]]

    def dibujar(self, img, T, ctx):
        for k in self.tiempos:
            e = T - k
            if 0 <= e < 0.22:
                col = self.E.color(self.d.get("color", "rojo"), T)
                lz = Lienzo()
                s = 1 + 0.5 * (1 - ease_out(e / 0.08))
                for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    lz.linea((int(540 + dx * 26 * s), int(960 + dy * 26 * s)),
                             (int(540 + dx * 62 * s), int(960 + dy * 62 * s)), col, 1 - e / 0.22, 9)
                lz.componer(img, halo=6)


class Marca(Elemento):
    """Nombre de la marca letra a letra con un barrido de luz, y una línea debajo."""

    def dibujar(self, img, T, ctx):
        t0 = self.E.t(self.d.get("t", 0), self.planos[0] if self.planos else None)
        if T < t0:
            return
        e = T - t0
        y = self.d.get("y", 365)
        letras = self.d["texto"]
        tam = self.d.get("tam", 190)
        fnt = fuente("titular", tam)
        trk = int(tam * 0.14)
        anchos = [_ancho(ch, fnt) for ch in letras]
        total = sum(anchos) + trk * (len(letras) - 1)
        x = W / 2 - total / 2
        brillo = self.E.color(self.d.get("brillo", "violeta"), T)
        bar = (e - 0.35) / 0.55
        for i, (ch, aw) in enumerate(zip(letras, anchos)):
            if ch != " ":
                spr = cache(("letra", ch, tam, brillo), lambda ch=ch: sprite_degradado(
                    ch, tam, (255, 255, 255), (190, 200, 255), brillo=brillo, radio=22))
                u = (e - i * 0.04) / 0.22
                if u > 0:
                    pegar(img, spr, x + aw / 2, y + 40 * (1 - ease_out(u)), alfa=min(1, u * 1.5))
                    if 0 < bar < 1.3:
                        k = max(0, 1 - abs(bar - (x + aw / 2 - (W / 2 - total / 2)) / total) / 0.12)
                        if k > 0:
                            pegar(img, spr, x + aw / 2, y, alfa=0.85 * k)
            x += aw + trk
        if self.d.get("sub"):
            col = self.E.color(self.d.get("color_sub", "acento"), T)
            sub = cache(("marca_sub", self.d["sub"], col), lambda: sprite_linea(
                [(self.d["sub"], col)], "hud", 50, trazo=0, sombra=0.5, tracking=12)[0])
            pegar(img, sub, W / 2, y + tam * 0.79, alfa=min(1, max(0, (e - 0.3) / 0.2)))


class CTA(Elemento):
    """Botón de llamada a la acción que entra con rebote y late: {"t", "texto", "y"}."""

    def dibujar(self, img, T, ctx):
        t0 = self.E.t(self.d["t"])
        if T < t0:
            return
        e = T - t0
        col = self.E.color(self.d.get("color", "acento"), T)
        spr = cache(("cta", self.d["texto"], col), lambda: self._boton(self.d["texto"], col))
        esc = (0.6 + 0.4 * ease_back(e / 0.22)) * (1 + 0.025 * math.sin(e * 7))
        pegar(img, spr, W / 2, self.d.get("y", 1150), esc=esc, alfa=min(1, e / 0.08))

    @staticmethod
    def _boton(texto, col):
        fnt = fuente("texto", 44)
        tw = _ancho(texto, fnt)
        w, h, pad = int(max(560, tw + 150)), 108, 36
        m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + w, pad + h), h // 2, fill=255)
        base = Image.new("RGBA", m.size, col + (0,))
        base.putalpha(m.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.8)))
        caja = Image.new("RGBA", m.size, col + (0,))
        caja.putalpha(m)
        base.alpha_composite(caja)
        d = ImageDraw.Draw(base)
        oscuro = (4, 16, 24, 255)
        x0 = pad + (w - tw - 50) / 2
        d.text((x0, pad + 28), texto, font=fnt, fill=oscuro)
        ax, ay = x0 + tw + 22, pad + h / 2
        d.line(((ax, ay), (ax + 28, ay)), fill=oscuro, width=7)
        d.line(((ax + 16, ay - 13), (ax + 29, ay), (ax + 16, ay + 13)), fill=oscuro, width=7)
        return a_sprite(base)


TIPOS = {"titulo": Titulo, "cartel": Cartel, "detras": Detras, "orbita": Orbita, "ondas": Ondas,
         "direccion": Direccion, "aviso": Aviso, "impacto": Impacto, "marca": Marca, "cta": CTA}


# ───────────── piezas fijas ─────────────

def marco_pip(w, h, c1, c2):
    def f():
        pad = 40
        m = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + w, pad + h), 28, outline=255, width=6)
        g = np.linspace(0, 1, m.size[1])[:, None, None]
        col = np.broadcast_to(np.array(c1) * (1 - g) + np.array(c2) * g, (m.size[1], m.size[0], 3)).astype(np.uint8)
        a = Image.fromarray(np.dstack([col, (np.asarray(m.filter(ImageFilter.GaussianBlur(14)), np.float32) * 0.9).astype(np.uint8)]), "RGBA")
        a.alpha_composite(Image.fromarray(np.dstack([col, np.asarray(m)]), "RGBA"))
        return a_sprite(a)
    return cache(("marco", w, h, c1, c2), f)


def etiqueta_pip(texto):
    def f():
        fnt = fuente("hud", 28)
        w = int(_ancho(texto, fnt) + 66)
        im = Image.new("RGBA", (w, 56), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, 55), 10, fill=(10, 10, 18, 190))
        d.ellipse((16, 19, 34, 37), fill=(255, 59, 78, 255))
        d.text((46, 11), texto, font=fnt, fill=(255, 255, 255, 255))
        return a_sprite(im)
    return cache(("etq", texto), f)


def etiqueta_ia(img, texto):
    spr = cache(("ia", texto), lambda: sprite_linea([(texto, (235, 235, 240))], "texto600", 26, trazo=0, sombra=0.8)[0])
    pegar(img, spr, 65 + spr.shape[1] / 2 - 34, 290, alfa=0.82)
