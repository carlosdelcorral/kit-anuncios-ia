"""Revisa cada clip generado ANTES de montar: qué dice de verdad, dónde empieza y acaba la voz,
pausas muertas, y palabras que no estaban en el guion (el generador se inventa cosas).

    python -m kit.revisar ejemplos/onda-x/vid/*.mp4 --guion ejemplos/onda-x/guion.json

`guion.json` = {"c0": "texto que debía decir", ...}. Sale una tabla y un `revision.json` al lado de
los clips con `desde`/`hasta` recomendados para `anuncio.json` (entrada 0,10 s antes de la primera
palabra y 0,35 s de aire tras la última: el mismo margen que usa el editor).
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from kit.transcribir import transcribir

PAUSA_MUERTA = 0.8


UNIDADES = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis diecisiete dieciocho diecinueve veinte".split()
DECENAS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
CENTENAS = {1: "cien", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos",
            7: "setecientos", 8: "ochocientos", 9: "novecientos"}
LETRAS = {"x": "equis"}


def _numero(n: int) -> str:
    """Número (0-999) en palabras, para comparar lo que dice el clip con el guion."""
    if n <= 20:
        return UNIDADES[n]
    if n < 30:
        return "veinti" + UNIDADES[n - 20]
    if n < 100:
        d, u = divmod(n, 10)
        return DECENAS[d * 10] + ("" if not u else " y " + UNIDADES[u])
    c, r = divmod(n, 100)
    return ("ciento" if c == 1 and r else CENTENAS[c]) + ("" if not r else " " + _numero(r))


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = re.sub(r"[^a-zñ0-9 ]", " ", "".join(c for c in s if unicodedata.category(c) != "Mn"))
    s = re.sub(r"\b\d{1,3}\b", lambda m: _numero(int(m.group())), s)
    return " ".join(LETRAS.get(w, w) for w in s.split() if w != "y" or True)


def revisar(clip: Path, esperado: str | None) -> dict:
    pal = transcribir(clip)
    if not pal:
        return {"clip": clip.name, "texto": "", "aviso": ["no se oye voz"]}
    avisos = []
    for a, b in zip(pal, pal[1:]):
        if b["inicio"] - a["fin"] > PAUSA_MUERTA:
            avisos.append(f"pausa de {b['inicio'] - a['fin']:.1f} s tras «{a['texto']}» ({a['fin']:.2f} s)")
    texto = " ".join(p["texto"] for p in pal)
    sobran, faltan = [], []
    if esperado:
        e, d = _norm(esperado).split(), _norm(texto).split()
        sobran = [w for w in d if w not in e]
        faltan = [w for w in e if w not in d]
        if sobran:
            avisos.append("dice palabras que no están en el guion: " + ", ".join(sobran))
        if faltan:
            avisos.append("le faltan: " + ", ".join(faltan))
    # tartamudeo: la misma palabra dos veces seguidas
    for a, b in zip(pal, pal[1:]):
        if _norm(a["texto"]) and _norm(a["texto"]) == _norm(b["texto"]):
            avisos.append(f"repite «{a['texto']}» en {a['inicio']:.2f} s")
    return {"clip": clip.name, "texto": texto, "voz_desde": pal[0]["inicio"], "voz_hasta": pal[-1]["fin"],
            "desde": round(max(0.0, pal[0]["inicio"] - 0.10), 2), "hasta": round(pal[-1]["fin"] + 0.35, 2),
            "palabras": pal, "avisos": avisos}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="+", type=Path)
    ap.add_argument("--guion", type=Path, help='JSON {"c0": "lo que debía decir", ...}')
    a = ap.parse_args()
    guion = json.loads(a.guion.read_text()) if a.guion else {}
    res = []
    for c in a.clips:
        r = revisar(c, guion.get(c.stem))
        res.append(r)
        print(f"\n■ {c.name}  voz {r.get('voz_desde', 0):.2f}→{r.get('voz_hasta', 0):.2f} s")
        print(f"  «{r['texto']}»")
        for av in r.get("avisos", []):
            print(f"  ⚠ {av}")
    salida = a.clips[0].parent / "revision.json"
    salida.write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(f"\n→ {salida}")


if __name__ == "__main__":
    main()
