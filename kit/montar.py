"""El editor de anuncios: un `anuncio.json` entra, un MP4 1080×1920 a −14 LUFS sale.

    python -m kit.montar ejemplos/onda-x/anuncio.json
    python -m kit.montar ejemplos/onda-x/anuncio.json --rapido     # borrador: sin grano, preset rápido

Qué hace, por orden:
  1. Resuelve la línea de tiempo (J-cuts: el audio del plano siguiente entra antes que su imagen).
  2. Renderiza cada plano con sus efectos (kit/efectos.py), siempre re-encode.
  3. Cose la voz de los planos que hablan y la iguala entre clips.
  4. Transcribe la voz YA cosida → subtítulos palabra a palabra (caen exactos en el montaje).
  5. Rótulos, cartel, etiqueta de IA → ASS, y comprueba la zona segura.
  6. Efectos de sonido con paneo + cama con ducking → loudnorm a −14 LUFS.
  7. Render final y un informe.md al lado del MP4.

Los tiempos de `rotulos` y `sonidos` se escriben por plano (`"plano": 3, "t": 1.2` = 1,2 s después de
que empiece el plano 3 en el montaje) o absolutos (`"t": 12.4`).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

from kit import efectos, sonido, zonas
from kit.ffmpeg import FFMPEG, FFPROBE
from kit.subtitulos import FUENTES, Ass
from kit.transcribir import transcribir

W, H, FPS, SR = efectos.W, efectos.H, efectos.FPS, sonido.SR


def _q(t: float) -> float:
    """A la rejilla de fotogramas: mezclar cortes de vídeo y de audio fuera de rejilla acumula desfase."""
    return round(t * FPS) / FPS


def sondear(clip: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                        "-of", "json", str(clip)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return {"w": int(v["width"]), "h": int(v["height"]), "dur": float(d["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


# ─── 0 · apretar: quitar las pausas de dentro de un plano ────────────────────────────────────
PAUSA_APRETAR = 0.22          # s: por encima de esto, la pausa se corta
AIRE_TRAS, AIRE_ANTES = 0.07, 0.05


def _silencios(clip: Path, desde: float, hasta: float) -> list[tuple[float, float]]:
    """Silencios de más de PAUSA_APRETAR s dentro de [desde, hasta], medidos por la envolvente de la
    voz (RMS de 20 ms, umbral 30 dB bajo el pico del tramo). Whisper no vale para esto: estira las
    palabras y esconde pausas de más de un segundo dentro de una sola palabra."""
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(clip), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(float) / 32768
    x = x[int(desde * 16000):int(hasta * 16000)]
    if len(x) < 3200:
        return []
    rms = np.sqrt(np.convolve(x ** 2, np.ones(320) / 320, mode="same"))[::160]      # cada 10 ms
    db = 20 * np.log10(rms + 1e-9)
    habla = db > db.max() - 30
    out, i = [], 0
    while i < len(habla):
        if not habla[i]:
            j = i
            while j < len(habla) and not habla[j]:
                j += 1
            a, b = desde + i / 100, desde + j / 100
            # no se cortan los extremos del tramo (eso ya lo deciden desde/hasta), solo pausas internas
            if i > 0 and j < len(habla) and b - a > PAUSA_APRETAR:
                out.append((a, b))
            i = j
        else:
            i += 1
    return out


def expandir(anuncio: dict, base: Path) -> dict:
    """Parte cada plano con `apretar: true` en sub-planos sin las pausas, alternando el zoom para que el
    corte se lea como un cambio de plano. Reubica efectos, juntas, rótulos, sonidos y silencios."""
    a = json.loads(json.dumps(anuncio))
    nuevos, mapa, juntas = [], [], []
    viejas = list(a.get("juntas", [])) + [{"tipo": "corte"}] * len(a["planos"])
    for i, p in enumerate(a["planos"]):
        rampa = any(e["tipo"] == "rampa" for e in p.get("efectos", []))
        tramos = [(float(p.get("desde", 0)), float(p.get("hasta", 0)))]
        if p.get("apretar") and not rampa and p.get("voz", True):
            cortes = [(a0 + AIRE_TRAS, a1 - AIRE_ANTES)
                      for a0, a1 in _silencios((base / p["clip"]).resolve(), *tramos[0])]
            cortes = [c for c in cortes if c[1] - c[0] > 0.05]
            if cortes:
                ini, tramos = tramos[0][0], []
                for c0, c1 in cortes:
                    tramos.append((ini, c0)); ini = c1
                tramos.append((ini, float(p["hasta"])))
                tramos = [t for t in tramos if t[1] - t[0] > 0.12]
        subs = []
        for k, (d0, d1) in enumerate(tramos):
            q = dict(p)
            q.pop("apretar", None)
            q["desde"], q["hasta"] = d0, d1
            if len(tramos) > 1:
                z = dict(p.get("zoom", {}))
                if k % 2:
                    z["base"] = float(z.get("base", 1.0)) * float(p.get("apretar_zoom", 1.13))
                if k:
                    z["entrada"] = max(float(z.get("entrada", 0)), 0.04)
                q["zoom"] = z
                q["efectos"] = []
            subs.append((len(nuevos), d0, d1))
            nuevos.append(q)
            if k:
                juntas.append({"tipo": "corte"})
        # reubicar efectos del plano original en su sub-plano
        if len(tramos) > 1:
            for e in p.get("efectos", []):
                j, t = _reubicar(subs, float(p["desde"]), float(e.get("t", 0)))
                nuevos[j]["efectos"] = nuevos[j].get("efectos", []) + [dict(e, t=t)]
        mapa.append((subs, float(p.get("desde", 0))))
        if i < len(a["planos"]) - 1:
            juntas.append(viejas[i])

    def mover(ev: dict) -> dict:
        if "plano" not in ev:
            return ev
        subs, d0 = mapa[ev["plano"]]
        j, t = _reubicar(subs, d0, float(ev["t"]))
        return dict(ev, plano=j, t=t)
    a["planos"], a["juntas"] = nuevos, juntas
    a["rotulos"] = [mover(r) for r in a.get("rotulos", [])]
    a["sonidos"] = [mover(x) for x in a.get("sonidos", [])]
    if a.get("musica"):
        for clave in ("silencios", "apagada"):
            a["musica"][clave] = [[mover(x) if isinstance(x, dict) else x for x in par]
                                  for par in a["musica"].get(clave, [])]
    return a


def _reubicar(subs: list[tuple[int, float, float]], desde: float, t: float) -> tuple[int, float]:
    """t (s desde el inicio del plano original) → (sub-plano, t dentro de él). Si cae en una pausa
    quitada, va al principio del siguiente trozo."""
    c = desde + t
    if t < 0:
        return subs[0][0], t
    for j, a0, a1 in subs:
        if c < a1:
            return j, max(0.0, c - a0)
    j, a0, a1 = subs[-1]
    return j, c - a0


# ─── 1 · línea de tiempo ──────────────────────────────────────────────────────────────────────
def resolver(anuncio: dict, base: Path) -> tuple[list[dict], list[str]]:
    avisos = []
    planos = [dict(p) for p in anuncio["planos"]]
    juntas = list(anuncio.get("juntas", []))
    juntas += [{"tipo": "corte"}] * (len(planos) - 1 - len(juntas))
    for i, p in enumerate(planos):
        p["_i"] = i
        p["_clip"] = (base / p["clip"]).resolve()
        p["_info"] = sondear(p["_clip"])
        rampa = next((e for e in p.get("efectos", []) if e["tipo"] == "rampa"), None)
        if rampa:
            p["voz"] = False
            p["_dur"] = _q(sum((b - a) / v for a, b, v in rampa["tramos"]))
            p["desde"], p["hasta"] = rampa["tramos"][0][0], rampa["tramos"][-1][1]
        else:
            p["desde"], p["hasta"] = _q(float(p["desde"])), _q(float(p["hasta"]))
            p["_dur"] = _q(p["hasta"] - p["desde"])
        p.setdefault("voz", True)
        for campo in ("pip", "audio"):
            if p.get(campo):
                p[campo] = dict(p[campo])
                p[campo]["_clip"] = (base / p[campo]["clip"]).resolve()
                p[campo]["_info"] = sondear(p[campo]["_clip"])
                if campo == "audio":
                    p["voz"] = True
    for k, j in enumerate(juntas):
        a, b = planos[k], planos[k + 1]
        tipo = j.get("tipo", "corte")
        if tipo == "barrido":
            a["_barrido_sale"] = b["_barrido_entra"] = True
        elif tipo == "flash":
            a["_flash_sale"] = b["_flash_entra"] = True
        L = _q(float(j.get("jcut", 0)))
        rampa_ab = any(e["tipo"] == "rampa" for e in a.get("efectos", []) + b.get("efectos", []))
        if L and rampa_ab:
            avisos.append(f"junta {k}: el J-cut no se combina con una rampa; se ignora")
            L = 0
        if L and a["hasta"] + L > a["_info"]["dur"] - 0.05:
            L = _q(max(0, a["_info"]["dur"] - 0.05 - a["hasta"]))
            avisos.append(f"junta {k}: el clip {a['clip']} no tiene cola para el J-cut; queda en {L:.2f} s")
        a["_L_sale"], b["_L_entra"] = L, L
    t = 0.0
    for p in planos:
        p["_inicio"] = t
        Lin, Lout = p.get("_L_entra", 0), p.get("_L_sale", 0)
        p["_v_in"], p["_v_out"] = p["desde"] + Lin, p["hasta"] + Lout
        p["_v_dur"] = _q(p["_dur"] - Lin + Lout)
        if p.get("pip"):
            p["pip"]["_v_in"] = float(p["pip"].get("desde", 0)) + Lin
        # tiempos de efectos: del plano en el montaje → del vídeo del plano (que empieza Lin más tarde)
        t += p["_dur"]
    return planos, avisos


def _abs(evento: dict, planos: list[dict]) -> float:
    return float(evento["t"]) + (planos[evento["plano"]]["_inicio"] if "plano" in evento else 0.0)


# ─── 2 · render por plano ─────────────────────────────────────────────────────────────────────
def _franja(ruta: Path) -> Path:
    """Franja diagonal de luz (PNG con alfa) para el barrido sobre el producto."""
    w, h = 1700, H
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.abs((xx - w / 2) - (yy - h / 2) * 0.35)
    alfa = np.clip(1 - d / 150, 0, 1) ** 2 * 120
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., :3] = 255
    img[..., 3] = alfa.astype(np.uint8)
    Image.fromarray(img, "RGBA").save(ruta)
    return ruta


def _mascaras(tmp: Path, acento: str) -> tuple[Path, Path]:
    """Máscara redondeada de la ventana de cámara y su borde en el color de acento."""
    from PIL import ImageDraw
    w, h, b, r = efectos.PIP_W, efectos.PIP_H, efectos.PIP_BORDE, 34
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    m.save(tmp / "pip_mascara.png")
    col = tuple(int(acento.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
    borde = Image.new("RGBA", (w + 2 * b, h + 2 * b), (0, 0, 0, 0))
    d = ImageDraw.Draw(borde)
    d.rounded_rectangle([0, 0, w + 2 * b - 1, h + 2 * b - 1], r + b, fill=col + (255,))
    d.rounded_rectangle([b, b, w + b - 1, h + b - 1], r, fill=(0, 0, 0, 0))
    borde.save(tmp / "pip_borde.png")
    return tmp / "pip_mascara.png", tmp / "pip_borde.png"


def render_plano(p: dict, destino: Path, franja: Path, pip_png: tuple[Path, Path], rapido: bool) -> Path:
    dur = p["_v_dur"]
    q = dict(p)
    Lin = p.get("_L_entra", 0)
    q["efectos"] = [dict(e, t=float(e["t"]) - Lin) if "t" in e else e for e in p.get("efectos", [])]
    if rapido:
        q["grano"] = False
    cmd = [FFMPEG, "-v", "error", "-y", "-i", str(p["_clip"])]
    entradas, n = {}, 1
    fija = ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur + 0.5:.3f}", "-i"]
    if any(e["tipo"] == "barrido_luz" for e in q["efectos"]):
        cmd += fija + [str(franja)]; entradas["franja"] = n; n += 1
    if p.get("pip"):
        cmd += ["-i", str(p["pip"]["_clip"])]; entradas["pip"] = n; n += 1
        cmd += fija + [str(pip_png[0])]; entradas["mascara"] = n; n += 1
        cmd += fija + [str(pip_png[1])]; entradas["borde"] = n; n += 1
    fc = efectos.cadena(q, p["_info"], dur, entradas)
    n = efectos.fotogramas(dur)
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-an", "-r", str(FPS), "-frames:v", str(n), "-c:v", "libx264",
            "-preset", "veryfast" if rapido else "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(destino)]
    subprocess.run(cmd, check=True)
    reales = contar_fotogramas(destino)
    if reales != n:
        raise SystemExit(f"plano {p['_i']}: salen {reales} fotogramas y deberían ser {n} — se desincronizaría")
    return destino


def contar_fotogramas(video: Path) -> int:
    r = subprocess.run([FFPROBE, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


# ─── 3 · voz ──────────────────────────────────────────────────────────────────────────────────
def voz_plano(p: dict, tmp: Path) -> np.ndarray:
    n = int(round(p["_dur"] * SR))
    fuente, a0 = p["_clip"], p["desde"]
    info = p["_info"]
    if p.get("voz_de") == "pip" and p.get("pip"):
        fuente, a0, info = p["pip"]["_clip"], float(p["pip"].get("desde", 0)), p["pip"]["_info"]
    elif p.get("audio"):                     # la voz de otro clip sobre esta imagen
        fuente, a0, info = p["audio"]["_clip"], float(p["audio"].get("desde", 0)), p["audio"]["_info"]
    if not p.get("voz") or not info["audio"]:
        return np.zeros((n, 2))
    wav = tmp / f"voz{p['_i']:02d}.wav"
    d = p["_dur"]
    af = (f"atrim=start={a0:.4f}:end={a0 + d:.4f},asetpts=PTS-STARTPTS,"
          f"afade=t=in:d=0.008,afade=t=out:st={max(0, d - 0.012):.4f}:d=0.012")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(fuente), "-af", af, "-ar", str(SR), "-ac", "2",
                    str(wav)], check=True)
    x = sonido.leer_wav(wav)
    if p.get("audio", {}).get("hasta") is not None:            # solo ese tramo de la otra voz
        util = int((float(p["audio"]["hasta"]) - a0) * SR)
        x = x[:util]
        cola = min(len(x), int(0.03 * SR))
        x[-cola:] *= np.linspace(1, 0, cola)[:, None]
    x = x[:n] if len(x) >= n else np.vstack([x, np.zeros((n - len(x), 2))])
    return x * ganancia_voz(fuente) * 10 ** (float(p.get("voz_db", 0)) / 20)


_GANANCIAS: dict[str, float] = {}


def ganancia_voz(clip: Path) -> float:
    """Una sola ganancia por CLIP (su voz a −20 dBFS RMS): igualar trozo a trozo hacía que cada
    fragmento de la misma frase sonara a un volumen distinto al quitar las pausas."""
    clave = str(clip)
    if clave not in _GANANCIAS:
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", clave, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                             capture_output=True).stdout
        m = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        habla = m[np.abs(m) > 10 ** (-40 / 20)]
        rms = np.sqrt(np.mean(habla ** 2)) if len(habla) > SR * 0.3 else 0.1
        _GANANCIAS[clave] = float(min(4.0, 10 ** (-20 / 20) / rms))
    return _GANANCIAS[clave]


# ─── el montaje entero ────────────────────────────────────────────────────────────────────────
def montar(ruta_json: Path, rapido: bool = False, depurar: bool = False) -> Path:
    t_inicio = time.time()
    anuncio = json.loads(ruta_json.read_text(encoding="utf-8"))
    base = ruta_json.parent
    salida = (base / anuncio.get("salida", "anuncio.mp4")).resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)
    anuncio = expandir(anuncio, base)
    planos, avisos = resolver(anuncio, base)
    total = sum(p["_dur"] for p in planos)
    print(f"▶ {len(planos)} planos · {total:.2f} s")

    tmp = Path(tempfile.mkdtemp(prefix="montaje_"))
    try:
        franja = _franja(tmp / "franja.png")
        pip_png = _mascaras(tmp, anuncio.get("estilo", {}).get("acento", "#A259FF"))
        lista = []
        for p in planos:
            seg = render_plano(p, tmp / f"plano{p['_i']:02d}.mp4", franja, pip_png, rapido)
            lista.append(seg)
            print(f"  ✓ plano {p['_i']} · {Path(p['clip']).name} {p['_v_in']:.2f}→{p['_v_out']:.2f} · {p['_v_dur']:.2f} s")
        (tmp / "lista.txt").write_text("".join(f"file '{s.name}'\n" for s in lista))

        voz = np.vstack([voz_plano(p, tmp) for p in planos])
        sonido.escribir_wav(tmp / "voz.wav", voz)

        # 4 · subtítulos sobre la voz cosida
        print("  · transcribiendo la voz del montaje…")
        palabras = transcribir(tmp / "voz.wav") if anuncio.get("subtitulos", {}).get("activos", True) else []
        ass = Ass(anuncio.get("estilo", {}))
        rotulos = [dict(r, t=_abs(r, planos)) for r in anuncio.get("rotulos", [])]
        silencios = [(r["t"], r["t"] + float(r.get("dur", 1.6))) for r in rotulos
                     if r.get("estilo") in ("cartel", "producto") and r.get("tapa_subtitulos", True)]
        ass.karaoke(palabras, anuncio.get("subtitulos", {}).get("resaltar", []), silencios)
        for r in rotulos:
            ass.rotulo(r)
        if anuncio.get("etiqueta_ia", "Vídeo generado con IA"):
            ass.rotulo({"texto": anuncio.get("etiqueta_ia", "Vídeo generado con IA"), "t": 0, "dur": total,
                        "estilo": "etiqueta"})
        ass.escribir(tmp / "subs.ass")
        avisos += zonas.comprobar(ass.cajas)

        # 6 · sonido
        eventos = [dict(e, t=_abs(e, planos), archivo=str((base / e["archivo"]).resolve()))
                   for e in anuncio.get("sonidos", [])]
        musica = dict(anuncio["musica"]) if anuncio.get("musica") else None
        if musica and musica.get("archivo"):
            musica["archivo"] = str((base / musica["archivo"]).resolve())
            for clave in ("silencios", "apagada"):
                musica[clave] = [[_abs(x, planos) if isinstance(x, dict) else float(x) for x in par]
                                 for par in musica.get(clave, [])]
        mezcla = sonido.mezclar(voz, eventos, musica)
        sonido.escribir_wav(tmp / "mezcla.wav", mezcla * 0.7)
        medida = sonido.loudnorm(tmp / "mezcla.wav", tmp / "final.wav")

        # 7 · render final
        dst = tmp / "fuentes"
        shutil.copytree(FUENTES, dst)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "lista.txt",
                        "-i", "final.wav", "-vf", "ass=subs.ass:fontsdir=fuentes", "-map", "0:v", "-map", "1:a",
                        "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset",
                        "veryfast" if rapido else "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(salida)],
                       check=True, cwd=tmp)
        final = sondear(salida)
        esperados = sum(efectos.fotogramas(p["_v_dur"]) for p in planos)
        final["fotogramas"] = contar_fotogramas(salida)
        final["deriva_ms"] = round((final["fotogramas"] - esperados) * 1000 / FPS)
        if final["deriva_ms"]:
            avisos.append(f"SINCRONÍA · el vídeo tiene {final['fotogramas']} fotogramas y deberían ser {esperados}")
        informe(salida, anuncio, planos, palabras, medida, avisos, final, time.time() - t_inicio)
        shutil.copy(tmp / "subs.ass", salida.with_suffix(".ass"))
    finally:
        if depurar:
            print(f"  (depurar) intermedios en {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    for a in avisos:
        print("  ⚠", a)
    print(f"✓ {salida}  ·  {final['dur']:.2f} s  ·  {medida['lufs']:.1f} LUFS")
    return salida


def informe(salida: Path, anuncio: dict, planos: list[dict], palabras: list[dict], medida: dict,
            avisos: list[str], final: dict, segundos: float) -> None:
    usados = sorted({e["tipo"] for p in planos for e in p.get("efectos", [])}
                    | {j.get("tipo") for j in anuncio.get("juntas", []) if j.get("tipo") != "corte"}
                    | ({"jcut"} if any(j.get("jcut") for j in anuncio.get("juntas", [])) else set())
                    | {"sonido:" + Path(s["archivo"]).stem for s in anuncio.get("sonidos", [])}
                    | ({"pip"} if any(p.get("pip") for p in planos) else set())
                    | ({"apagado"} if (anuncio.get("musica") or {}).get("apagada") else set())
                    | {r.get("estilo", "hook") for r in anuncio.get("rotulos", [])})
    filas = "\n".join(f"| {p['_i']} | `{p['clip']}` | {p['desde']:.2f}→{p['hasta']:.2f} | {p['_inicio']:.2f} | "
                      f"{p['_dur']:.2f} | {'sí' if p.get('voz') else 'no'} | "
                      f"{', '.join(e['tipo'] for e in p.get('efectos', [])) or '—'} |" for p in planos)
    texto = " ".join(w["texto"] for w in palabras)
    md = f"""# Informe de montaje · {salida.name}

- **Duración:** {final['dur']:.2f} s · **{W}×{H}** · {FPS} fps
- **Volumen:** {medida['lufs']:.1f} LUFS integrados · pico {medida['pico_dbtp']:.1f} dBTP (objetivo −14 / −1,5)
- **Sincronía:** {final.get('fotogramas', '?')} fotogramas · deriva {final.get('deriva_ms', '?')} ms (debe ser 0)
- **Etiqueta de IA:** «{anuncio.get('etiqueta_ia', 'Vídeo generado con IA')}» desde el fotograma 1, dentro de zona segura
- **Efectos usados:** {', '.join(usados)}
- **Tiempo de render:** {segundos:.0f} s

## Planos

| # | Clip | Del clip (s) | Empieza en | Dura | Voz | Efectos |
|---|---|---|---|---|---|---|
{filas}

## Lo que se oye (transcrito del montaje)

> {texto}

## Avisos

{chr(10).join('- ' + a for a in avisos) if avisos else '- Ninguno: todo lo que debe leerse está en zona segura.'}
"""
    salida.with_name(salida.stem + ".informe.md").write_text(md, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("anuncio", type=Path, help="ruta al anuncio.json")
    ap.add_argument("--rapido", action="store_true", help="borrador: sin grano y con preset rápido")
    ap.add_argument("--depurar", action="store_true", help="conserva los planos intermedios para revisarlos")
    a = ap.parse_args()
    if not a.anuncio.exists():
        sys.exit(f"No existe {a.anuncio}")
    montar(a.anuncio, a.rapido, a.depurar)


if __name__ == "__main__":
    main()
