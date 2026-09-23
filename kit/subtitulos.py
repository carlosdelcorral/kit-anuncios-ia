"""Subtítulos palabra a palabra y rótulos, en ASS (coordenadas 1080×1920; libass escala solo).

Estilos de rótulo:
  hook      frase del gancho, caja oscura detrás, entra con un pequeño salto
  cartel    UNA palabra gigante en el color de acento, con golpe de escala y giro (1-2 por anuncio)
  producto  nombre o claim del producto con resplandor, para el plano de producto
  cta       la llamada a la acción sobre una caja del color de acento
  etiqueta  «Vídeo generado con IA»: pequeña, fija, DENTRO de la zona segura, desde el fotograma 1

Cada elemento devuelve su caja (x0, y0, x1, y1) para que `zonas.py` compruebe que se lee.
"""
from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

W, H = 1080, 1920
FUENTES = Path(__file__).resolve().parent / "assets" / "fuentes"
ARCHIVO = {"Lato Black": "Lato-Black.ttf", "Lato Bold": "Lato-Bold.ttf", "Lato": "Lato-Regular.ttf",
           "DM Serif Display": "DMSerifDisplay-Regular.ttf"}

# y del centro de cada cosa: todo dentro de la zona segura de Meta 2026 (270-1248).
Y_SUBTITULOS = 1130
Y_HOOK = 600
Y_CARTEL = 880
Y_PRODUCTO = 1120
Y_CTA = 1000
POS_ETIQUETA = (84, 292)
ANCHO_UTIL = 880          # lo más ancho que puede ser un rótulo (zona segura: 950 px menos aire)


def _color(hexa: str, alfa: int = 0) -> str:
    h = hexa.lstrip("#")
    return f"&H{alfa:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ancho(texto: str, fuente: str, px: int) -> int:
    f = ImageFont.truetype(str(FUENTES / ARCHIVO[fuente]), px)
    return int(f.getlength(texto))


def partir(texto: str, fuente: str, px: int, maximo: int) -> list[str]:
    lineas, actual = [], ""
    for w in texto.split():
        prueba = f"{actual} {w}".strip()
        if actual and ancho(prueba, fuente, px) > maximo:
            lineas.append(actual)
            actual = w
        else:
            actual = prueba
    return lineas + ([actual] if actual else [])


def encajar(texto: str, fuente: str, px: int, maximo: int = ANCHO_UTIL, escala: float = 1.0) -> int:
    """Baja el cuerpo hasta que el texto (con su escala máxima de animación) cabe en `maximo`."""
    while px > 40 and ancho(texto, fuente, px) * escala > maximo:
        px -= 4
    return px


def _t(s: float) -> str:
    s = max(0.0, s)
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{r:05.2f}"


def _esc(s: str) -> str:
    return s.replace("{", "(").replace("}", ")")


class Ass:
    def __init__(self, estilo: dict):
        self.e = estilo
        self.fuente = estilo.get("fuente", "Lato Black")
        self.texto = estilo.get("texto", "#FFFFFF")
        self.acento = estilo.get("acento", "#A259FF")
        self.mayus = estilo.get("mayusculas", True)
        self.eventos: list[str] = []
        self.cajas: list[dict] = []

    def _dialogo(self, capa: int, ini: float, fin: float, estilo: str, texto: str) -> None:
        self.eventos.append(f"Dialogue: {capa},{_t(ini)},{_t(fin)},{estilo},,0,0,0,,{texto}")

    def _caja(self, nombre: str, cx: float, cy: float, w: float, h: float, ini: float) -> None:
        self.cajas.append({"nombre": nombre, "t": round(ini, 2), "x0": cx - w / 2, "y0": cy - h / 2,
                           "x1": cx + w / 2, "y1": cy + h / 2})

    def cabecera(self) -> str:
        blanco, negro, acento = _color(self.texto), _color("#000000"), _color(self.acento)
        f = self.fuente
        estilos = [
            f"Style: Sub,{f},92,{blanco},{acento},{negro},{_color('#000000', 0x50)},0,0,0,0,100,100,0,0,1,9,4,5,40,40,40,1",
            f"Style: Hook,{f},82,{blanco},{acento},{_color('#0B0B0B', 0x30)},{negro},0,0,0,0,100,100,0,0,3,22,0,5,40,40,40,1",
            f"Style: Cartel,{f},190,{acento},{acento},{negro},{negro},0,0,0,0,100,100,0,0,1,10,0,5,40,40,40,1",
            f"Style: Resplandor,{f},190,{acento},{acento},{acento},{acento},0,0,0,0,100,100,0,0,1,16,0,5,40,40,40,1",
            f"Style: Producto,{f},118,{blanco},{acento},{negro},{negro},0,0,0,0,100,100,0,0,1,6,0,5,40,40,40,1",
            f"Style: Cta,{f},64,{blanco},{acento},{acento},{negro},0,0,0,0,100,100,0,0,3,26,0,5,40,40,40,1",
            f"Style: Hora,{f},104,{blanco},{acento},{_color('#000000', 0x40)},{_color('#000000', 0x70)},0,0,0,0,100,100,0,0,1,4,6,5,40,40,40,1",
            f"Style: Etiqueta,Lato Bold,34,{_color('#FFFFFF', 0x10)},{blanco},{_color('#000000', 0x70)},{negro},0,0,0,0,100,100,0,0,3,10,0,7,40,40,40,1",
        ]
        return ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\n"
                "WrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                + "\n".join(estilos) + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
                "MarginV, Effect, Text\n")

    # ── subtítulos palabra a palabra ─────────────────────────────────────────────────────────
    def karaoke(self, palabras: list[dict], resaltar: list[str], silencios: list[tuple[float, float]]) -> None:
        px, maxw = 92, 860
        norm = lambda s: "".join(c for c in s.lower() if c.isalnum())
        resaltar = {norm(r) for r in resaltar}
        grupos, g = [], []
        for i, p in enumerate(palabras):
            corte = False
            if g:
                prev = g[-1]
                texto = " ".join(x["texto"] for x in g + [p])
                corte = (len(g) >= 3 or p["inicio"] - prev["fin"] > 0.35
                         or prev["texto"][-1:] in ".?!…," or ancho(texto.upper(), self.fuente, px) > maxw)
            if corte:
                grupos.append(g); g = []
            g.append(p)
        if g:
            grupos.append(g)
        for gi, g in enumerate(grupos):
            ini = g[0]["inicio"]
            sig = grupos[gi + 1][0]["inicio"] if gi + 1 < len(grupos) else None
            fin = sig if sig is not None and sig - g[-1]["fin"] < 0.6 else g[-1]["fin"] + 0.25
            if any(ini < b and fin > a for a, b in silencios):
                continue                                    # hay un cartel que ya lo dice
            textos = [(w["texto"].upper() if self.mayus else w["texto"]) for w in g]
            for k, w in enumerate(g):
                a = ini if k == 0 else w["inicio"]
                b = g[k + 1]["inicio"] if k + 1 < len(g) else fin
                trozos = []
                for j, t in enumerate(textos):
                    if j == k:
                        esc = 124 if norm(t) in resaltar else 112
                        trozos.append(f"{{\\c{_color(self.acento)}\\fscx{esc}\\fscy{esc}}}{_esc(t)}{{\\r}}")
                    else:
                        trozos.append(_esc(t))
                pop = "{\\fscx86\\fscy86\\t(0,90,\\fscx100\\fscy100)}" if k == 0 else ""
                self._dialogo(1, a, b, "Sub", f"{{\\an5\\pos(540,{Y_SUBTITULOS})}}{pop}" + " ".join(trozos))
            w_px = ancho(" ".join(textos), self.fuente, px) * 1.12
            self._caja("subtítulos «" + " ".join(textos) + "»", 540, Y_SUBTITULOS, w_px, px * 1.3, ini)

    # ── rótulos ──────────────────────────────────────────────────────────────────────────────
    def rotulo(self, r: dict) -> None:
        estilo = r.get("estilo", "hook")
        texto = r["texto"].upper() if self.mayus and estilo != "etiqueta" else r["texto"]
        ini, fin = float(r["t"]), float(r["t"]) + float(r.get("dur", 1.6))
        if estilo == "hook":
            y = r.get("y", Y_HOOK)
            lineas = partir(texto, self.fuente, 82, 860)
            anim = "{\\fad(60,120)\\fscx80\\fscy80\\t(0,120,\\fscx104\\fscy104)\\t(120,200,\\fscx100\\fscy100)}"
            self._dialogo(3, ini, fin, "Hook", f"{{\\an5\\pos(540,{y})}}{anim}" + "\\N".join(map(_esc, lineas)))
            w = max(ancho(l, self.fuente, 82) for l in lineas) + 44
            self._caja(f"hook «{texto}»", 540, y, w, 82 * 1.2 * len(lineas) + 44, ini)
        elif estilo == "cartel":
            y = r.get("y", Y_CARTEL)
            anim = ("{\\fscx55\\fscy55\\frz-4\\t(0,110,\\fscx118\\fscy118\\frz-2)"
                    "\\t(110,210,\\fscx100\\fscy100)\\fad(0,160)}")
            px = encajar(texto, self.fuente, 190, escala=1.18)
            self._dialogo(2, ini, fin, "Resplandor", f"{{\\an5\\pos(540,{y})\\fs{px}\\blur14\\alpha&H70&}}{anim}{_esc(texto)}")
            self._dialogo(3, ini, fin, "Cartel", f"{{\\an5\\pos(540,{y})\\fs{px}}}{anim}{_esc(texto)}")
            self._caja(f"cartel «{texto}»", 540, y, ancho(texto, self.fuente, px) * 1.18, px * 1.25, ini)
        elif estilo == "producto":
            y = r.get("y", Y_PRODUCTO)
            anim = "{\\fad(180,220)\\fscx92\\fscy92\\t(0,400,\\fscx100\\fscy100)}"
            px = encajar(texto, self.fuente, 118)
            self._dialogo(2, ini, fin, "Resplandor", f"{{\\an5\\pos(540,{y})\\fs{px}\\blur18\\alpha&H60&}}{anim}{_esc(texto)}")
            self._dialogo(3, ini, fin, "Producto", f"{{\\an5\\pos(540,{y})\\fs{px}}}{anim}{_esc(texto)}")
            self._caja(f"producto «{texto}»", 540, y, ancho(texto, self.fuente, px), px * 1.25, ini)
        elif estilo == "cta":
            y = r.get("y", Y_CTA)
            anim = "{\\fad(80,150)\\fscx85\\fscy85\\t(0,140,\\fscx100\\fscy100)}"
            px = encajar(texto, self.fuente, 64, ANCHO_UTIL - 60)
            self._dialogo(3, ini, fin, "Cta", f"{{\\an5\\pos(540,{y})\\fs{px}}}{anim}{_esc(texto)}")
            self._caja(f"cta «{texto}»", 540, y, ancho(texto, self.fuente, px) + 52, px * 1.2 + 52, ini)
        elif estilo == "hora":
            y = r.get("y", 470)
            px = encajar(texto, self.fuente, 104)
            anim = "{\\fad(90,160)\\fscx90\\fscy90\\t(0,140,\\fscx100\\fscy100)}"
            self._dialogo(3, ini, fin, "Hora", f"{{\\an5\\pos(540,{y})\\fs{px}}}{anim}{_esc(texto)}")
            self._caja(f"hora «{texto}»", 540, y, ancho(texto, self.fuente, px), px * 1.25, ini)
        elif estilo == "etiqueta":
            x, y = POS_ETIQUETA
            self._dialogo(4, ini, fin, "Etiqueta", f"{{\\an7\\pos({x},{y})}}{_esc(texto)}")
            w = ancho(texto, "Lato Bold", 34) + 20
            self._caja(f"etiqueta «{texto}»", x + w / 2 - 10, y + 20, w, 60, ini)
        else:
            raise ValueError(f"estilo de rótulo desconocido: {estilo}")

    def escribir(self, ruta: Path) -> Path:
        ruta.write_text(self.cabecera() + "\n".join(self.eventos) + "\n", encoding="utf-8")
        return ruta
