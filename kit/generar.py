"""La puerta a Replicate: imágenes y vídeos para el anuncio, con el gasto apuntado.

    python -m kit.generar comprobar                          # ¿funciona mi clave?
    python -m kit.generar imagen "<prompt>" --out img/base.png [--ref a.png b.png] [--modelo sunburst]
    python -m kit.generar video  "<prompt>" --out vid/c0.mp4 --imagen img/base.png [--ultimo img/fin.png]
    python -m kit.generar video  "<prompt>" --out vid/3d.mp4 --imagen img/producto.png --modelo seedance
    python -m kit.generar musica "<estilo, bpm, sin voz>" --out anuncios/x/musica.wav
    python -m kit.generar sonido "<efecto>" --dur 2 --out anuncios/x/sfx/golpe.wav
    python -m kit.generar gasto

Modelos:
  imagen    openai/gpt-image-2            personas y escenas (hasta 3 referencias con --ref)
  sunburst  openai/gpt-image-2.5-sunburst igual, pero escribe mucho mejor el texto (cajas, rótulos)
  omni      google/gemini-omni-1.1        EL VÍDEO QUE HABLA: guion, voz y acento en el prompt; 10 s fijos
  seedance  bytedance/seedance-2.5        vídeo mudo de objetos (producto en 3D). RECHAZA caras realistas
  musica    google/lyria-2                ~30 s de música instrumental a 48 kHz estéreo
  sonido    stable-audio-open-1.0         efectos de sonido realistas (whoosh, golpe, pasos, disparos…)

Regla de gasto: calidad `low` y resolución baja por defecto; subir exige `--caro`. Antes de cada
llamada se dice lo que va a costar. Replicate no cobra las predicciones que fallan.

La clave va en `.env` (REPLICATE_API_TOKEN=r8_…), en la carpeta del kit. Se saca en
https://replicate.com/account/api-tokens y la cuenta necesita saldo.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from kit.ffmpeg import FFPROBE

RAIZ = Path(__file__).resolve().parents[1]
API = "https://api.replicate.com/v1"
UA = "KitAnunciosIA/1.0"          # el User-Agent por defecto de requests recibe 403 de Cloudflare
LOG = RAIZ / "gasto.jsonl"
MODELOS = {"imagen": "openai/gpt-image-2", "sunburst": "openai/gpt-image-2.5-sunburst",
           "omni": "google/gemini-omni-1.1", "seedance": "bytedance/seedance-2.5",
           "musica": "google/lyria-2", "sonido": "stackadoc/stable-audio-open-1.0"}
PRECIO_AUDIO = {"musica": 0.06, "sonido": 0.02}     # estimados por generación: Replicate no los publica
# Precios de referencia (sep-2026). Replicate no publica todos: estimados desde la tarifa del
# fabricante y comprobados con facturas reales. Revísalos en tu panel de Replicate.
PRECIO_IMAGEN = {"low": 0.012, "medium": 0.047, "high": 0.19}
PRECIO_OMNI = {"360p": 0.34, "720p": 1.01, "1080p": 1.50, "4k": 3.00}      # por clip de 10 s
SEEDANCE_USD_MILLON_TOKENS = 1.20                                        # sin audio


def _clave() -> str:
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text().splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    tok = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not tok:
        sys.exit("Falta la clave de Replicate.\n  1. Sácala en https://replicate.com/account/api-tokens\n"
                 "  2. Copia .env.example a .env y pégala en REPLICATE_API_TOKEN=\n  3. Vuelve a lanzar esto.")
    return tok


def _cabeceras(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "Prefer": "wait=60",
            "User-Agent": UA}


def _data_uri(ruta: str | Path) -> str:
    ruta = Path(ruta)
    if not ruta.exists():
        sys.exit(f"No existe {ruta}")
    mime = mimetypes.guess_type(str(ruta))[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(ruta.read_bytes()).decode()


def _correr(modelo: str, entrada: dict, tok: str, timeout: int, por_version: bool = False) -> dict:
    h = _cabeceras(tok)
    for intento in range(8):
        if por_version:                   # modelos de la comunidad: se llaman por su versión
            info = requests.get(f"{API}/models/{modelo}", headers=h, timeout=30).json()
            r = requests.post(f"{API}/predictions", headers=h, timeout=90,
                              json={"version": info["latest_version"]["id"], "input": entrada})
        else:
            r = requests.post(f"{API}/models/{modelo}/predictions", headers=h, json={"input": entrada}, timeout=90)
        if r.status_code != 429:
            break
        # Demasiadas a la vez (con menos de 10 USD de saldo, Replicate baja el límite): se espera y se repite.
        espera = float(r.json().get("retry_after", 5)) + intento
        print(f"   … Replicate pide esperar {espera:.0f} s (límite de peticiones)", flush=True)
        time.sleep(espera)
    if r.status_code == 402:
        sys.exit("Replicate dice que no hay saldo (402). Añade crédito en https://replicate.com/account/billing")
    if r.status_code >= 400:
        sys.exit(f"Error {r.status_code} al crear la predicción: {r.text[:500]}")
    pred, t0 = r.json(), time.time()
    while pred.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() - t0 > timeout:
            sys.exit(f"La predicción {pred.get('id')} sigue en «{pred.get('status')}» tras {timeout} s")
        time.sleep(3)
        pred = requests.get(pred["urls"]["get"], headers=h, timeout=30).json()
        print(f"   … {pred.get('status')}  ({time.time() - t0:4.0f} s)", end="\r", flush=True)
    print()
    if pred["status"] != "succeeded":
        err = str(pred.get("error"))
        pista = ("\n  Pista: seedance rechaza las caras fotorrealistas (E005). Para una persona, usa --modelo omni."
                 if "E005" in err or "sensitive" in err else "")
        sys.exit(f"La predicción ha fallado (no se cobra): {err}{pista}")
    return pred


def _descargar(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=180, headers={"User-Agent": UA}) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for trozo in r.iter_content(1 << 16):
                f.write(trozo)
    return destino


def _apuntar(fila: dict) -> None:
    fila["cuando"] = datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False) + "\n")


def _coste_seedance(mp4: Path) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(mp4)],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    w, h, dur = d["streams"][0]["width"], d["streams"][0]["height"], float(d["format"]["duration"])
    return round(w * h * dur * 24 / 1024 / 1e6 * SEEDANCE_USD_MILLON_TOKENS, 4)


# ─── comandos ─────────────────────────────────────────────────────────────────────────────────
def comprobar(_: argparse.Namespace) -> None:
    tok = _clave()
    r = requests.get(f"{API}/account", headers=_cabeceras(tok), timeout=30)
    if r.status_code != 200:
        sys.exit(f"La clave no vale ({r.status_code}): {r.text[:300]}")
    print(f"OK — cuenta de Replicate: {r.json().get('username')}")


def imagen(a: argparse.Namespace) -> None:
    if a.calidad != "low" and not a.caro:
        sys.exit("Calidad distinta de `low` requiere --caro.")
    tok = _clave()
    modelo = MODELOS[a.modelo]
    entrada = {"prompt": a.prompt, "quality": a.calidad, "aspect_ratio": a.aspecto, "output_format": "png",
               "number_of_images": 1}
    if a.ref:
        entrada["input_images"] = [_data_uri(p) for p in a.ref]
    coste = PRECIO_IMAGEN[a.calidad]
    print(f"🖼  {modelo} · {a.calidad} · {a.aspecto}" + (f" · {len(a.ref)} ref" if a.ref else "")
          + f" · ≈{coste:.3f} USD")
    pred = _correr(modelo, entrada, tok, a.timeout)
    url = pred["output"][0] if isinstance(pred["output"], list) else pred["output"]
    ruta = _descargar(url, Path(a.out))
    _apuntar({"tipo": "imagen", "modelo": modelo, "calidad": a.calidad, "prompt": a.prompt, "ref": a.ref or [],
              "salida": str(ruta), "coste_usd": coste, "id": pred["id"]})
    print(f"✓ {ruta}")


def video(a: argparse.Namespace) -> None:
    tok = _clave()
    modelo = MODELOS[a.modelo]
    if a.modelo == "omni":
        if a.res not in PRECIO_OMNI:
            sys.exit("omni admite 360p, 720p, 1080p o 4k.")
        if a.res in ("1080p", "4k") and not a.caro:
            sys.exit(f"{a.res} requiere --caro.")
        if a.referencias and (a.imagen or a.ultimo):
            sys.exit("omni no deja combinar --referencias con --imagen/--ultimo: es una cosa o la otra.")
        entrada = {"prompt": a.prompt, "resolution": a.res, "aspect_ratio": a.aspecto}
        if a.imagen:
            entrada["image"] = _data_uri(a.imagen)
        if a.ultimo:
            entrada["last_frame"] = _data_uri(a.ultimo)
        if a.referencias:
            entrada["reference_images"] = [_data_uri(r) for r in a.referencias]
        coste = PRECIO_OMNI[a.res]
        print(f"🎬  {modelo} · {a.res} · 10 s con voz · ≈{coste:.2f} USD")
    else:
        res = a.res if a.res in ("480p", "720p") else "480p"
        if res == "720p" and not a.caro:
            sys.exit("seedance a 720p requiere --caro.")
        entrada = {"prompt": a.prompt, "duration": a.dur, "resolution": res, "generate_audio": False,
                   "camera_fixed": a.camara_fija, "aspect_ratio": a.aspecto}
        if a.imagen:
            entrada["image"] = _data_uri(a.imagen)
        coste = None
        print(f"🎬  {modelo} · {res} · {a.dur} s mudo · ≈{a.dur * (0.012 if res == '480p' else 0.026):.2f} USD")
    pred = _correr(modelo, entrada, tok, a.timeout)
    url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
    ruta = _descargar(url, Path(a.out))
    if coste is None:
        coste = _coste_seedance(ruta)
    _apuntar({"tipo": "video", "modelo": modelo, "res": a.res, "prompt": a.prompt, "imagen": a.imagen,
              "ultimo": a.ultimo, "salida": str(ruta), "coste_usd": coste, "id": pred["id"]})
    print(f"✓ {ruta}   ≈{coste:.3f} USD")


def audio(a: argparse.Namespace) -> None:
    tok = _clave()
    modelo = MODELOS[a.cmd]
    if a.cmd == "musica":
        entrada = {"prompt": a.prompt, "negative_prompt": a.negativo or "vocals, singing, speech"}
    else:
        entrada = {"prompt": a.prompt, "seconds_total": a.dur, "negative_prompt": a.negativo or "music, speech, voice"}
    coste = PRECIO_AUDIO[a.cmd]
    print(f"🔊  {modelo} · ≈{coste:.2f} USD")
    pred = _correr(modelo, entrada, tok, a.timeout, por_version=(a.cmd == "sonido"))
    url = pred["output"] if isinstance(pred["output"], str) else pred["output"][0]
    ruta = _descargar(url, Path(a.out))
    if a.cmd == "sonido":            # Stable Audio devuelve ~47 s rellenos de silencio: se recorta al sonido real
        import numpy as np
        from kit import sonido
        x = sonido.cargar(ruta)
        viva = np.where(np.abs(x).max(axis=1) > 10 ** (-60 / 20))[0]
        if len(viva):
            sonido.escribir_wav(ruta.with_suffix(".wav"), x[:min(len(x), viva[-1] + int(0.1 * sonido.SR))])
            ruta.with_suffix(".48k.wav").unlink(missing_ok=True)
    _apuntar({"tipo": a.cmd, "modelo": modelo, "prompt": a.prompt, "salida": str(ruta), "coste_usd": coste,
              "id": pred["id"]})
    print(f"✓ {ruta}")


def gasto(_: argparse.Namespace) -> None:
    if not LOG.exists():
        print("Todavía no has generado nada."); return
    filas = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = 0.0
    for f in filas:
        total += f.get("coste_usd") or 0
        print(f"{f['cuando'][:16]}  {f['modelo'][:30]:30}  {f.get('coste_usd', 0):7.3f}  {Path(f['salida']).name}")
    print(f"\nTOTAL: {total:.2f} USD en {len(filas)} generaciones")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("comprobar", help="prueba la clave de Replicate").set_defaults(fn=comprobar)
    i = sub.add_parser("imagen", help="una imagen (persona, escena, producto)")
    i.add_argument("prompt"); i.add_argument("--out", required=True)
    i.add_argument("--modelo", default="sunburst", choices=["imagen", "sunburst"])
    i.add_argument("--aspecto", default="9:16", help="9:16 (defecto), 1:1, 16:9…")
    i.add_argument("--calidad", default="low", choices=["low", "medium", "high"])
    i.add_argument("--ref", nargs="*", help="imágenes de referencia: persona, producto, fotograma anterior")
    i.add_argument("--caro", action="store_true"); i.add_argument("--timeout", type=int, default=300)
    i.set_defaults(fn=imagen)
    v = sub.add_parser("video", help="un clip (omni habla; seedance, producto mudo)")
    v.add_argument("prompt"); v.add_argument("--out", required=True)
    v.add_argument("--modelo", default="omni", choices=["omni", "seedance"])
    v.add_argument("--imagen", help="primer fotograma"); v.add_argument("--ultimo", help="último fotograma (bucle, junta)")
    v.add_argument("--referencias", nargs="*", help="omni: guían al sujeto (no se combinan con --imagen)")
    v.add_argument("--res", default="360p", help="omni: 360p (borrador) / 720p · seedance: 480p / 720p")
    v.add_argument("--dur", type=int, default=5, help="seedance: segundos (4-12)")
    v.add_argument("--aspecto", default="9:16"); v.add_argument("--camara-fija", action="store_true")
    v.add_argument("--caro", action="store_true"); v.add_argument("--timeout", type=int, default=900)
    v.set_defaults(fn=video)
    for nombre, ayuda in (("musica", "música instrumental (~30 s)"), ("sonido", "un efecto de sonido")):
        s_ = sub.add_parser(nombre, help=ayuda)
        s_.add_argument("prompt"); s_.add_argument("--out", required=True)
        s_.add_argument("--dur", type=int, default=3, help="sonido: segundos (1-47)")
        s_.add_argument("--negativo", default="", help="lo que NO debe sonar")
        s_.add_argument("--timeout", type=int, default=600)
        s_.set_defaults(fn=audio)
    sub.add_parser("gasto", help="lo gastado hasta ahora").set_defaults(fn=gasto)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
