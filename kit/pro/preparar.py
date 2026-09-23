"""Preparación del material para el montaje profesional. Todo queda en caché en `<anuncio>/pro/`.

- **Superresolución** (Real-ESRGAN compact ×4): los clips de omni salen a 360p y ampliados ×3 se ven
  blandos. Se guardan a 1440×2560 para que los punch-ins (hasta ×1,33) sigan teniendo detalle.
- **72 fps interpolados** (minterpolate) para los clips que llevan cámara lenta: fluida, sin saltos.
- **Máscara de persona** (Robust Video Matting) para los planos con grafismo DETRÁS del sujeto.
- **Caras** (YuNet de OpenCV) para anclar el mentón encima de los subtítulos.
- **Palabras** (kit.transcribir) y la envolvente de la voz, que marca los bordes de verdad.

Los modelos se descargan solos la primera vez en ~/.cache/kit-anuncios (licencias en
LICENSE-TERCEROS.md). Si no hay torch, se amplía con lanczos y el grafismo «detrás» va delante.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import cv2
import numpy as np

from kit.ffmpeg import FFMPEG, FFPROBE

SW, SH = 1440, 2560
CACHE = Path(os.environ.get("KIT_MODELOS", Path.home() / ".cache" / "kit-anuncios"))
URLS = {
    "realesr-general-x4v3.pth":
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
    "rvm_mobilenetv3_fp32.torchscript":
        "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.torchscript",
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
}


def modelo(nombre: str) -> Path:
    ruta = CACHE / nombre
    if not ruta.exists():
        import requests
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"  descargando {nombre} (una sola vez)…", flush=True)
        r = requests.get(URLS[nombre], timeout=300)
        r.raise_for_status()
        tmp = ruta.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.rename(ruta)
    return ruta


def hay_torch() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _dispositivo():
    import torch
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ───────────── superresolución (arquitectura SRVGGNetCompact de Real-ESRGAN, BSD-3) ─────────────

_RED = {}


def _red_sr():
    if "sr" in _RED:
        return _RED["sr"]
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class SRVGGNetCompact(nn.Module):
        def __init__(self, nf=64, nconv=32, esc=4):
            super().__init__()
            self.esc = esc
            capas = [nn.Conv2d(3, nf, 3, 1, 1), nn.PReLU(num_parameters=nf)]
            for _ in range(nconv):
                capas += [nn.Conv2d(nf, nf, 3, 1, 1), nn.PReLU(num_parameters=nf)]
            capas.append(nn.Conv2d(nf, 3 * esc * esc, 3, 1, 1))
            self.body = nn.ModuleList(capas)
            self.upsampler = nn.PixelShuffle(esc)

        def forward(self, x):
            y = x
            for c in self.body:
                y = c(y)
            return self.upsampler(y) + F.interpolate(x, scale_factor=self.esc, mode="nearest")

    net = SRVGGNetCompact()
    sd = torch.load(modelo("realesr-general-x4v3.pth"), map_location="cpu", weights_only=True)
    net.load_state_dict(sd.get("params_ema") or sd.get("params") or sd, strict=True)
    net.eval().to(_dispositivo())
    _RED["sr"] = net
    return net


def ampliar(bgr: np.ndarray) -> np.ndarray:
    import torch
    net = _red_sr()
    x = torch.from_numpy(bgr[:, :, ::-1].astype(np.float32) / 255.0).permute(2, 0, 1)[None]
    with torch.no_grad():
        y = net(x.to(_dispositivo())).clamp_(0, 1)[0].permute(1, 2, 0).cpu().numpy()
    return (y[:, :, ::-1] * 255.0).round().astype(np.uint8)


def _tam(ruta: Path) -> tuple[int, int, float]:
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "json", str(ruta)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d)


def normalizar(entrada: Path, salida: Path, fps: int, sr: bool) -> int:
    """Clip → 1440×2560 a `fps` (24, o 72 interpolado), recortado a 9:16, con o sin superresolución."""
    w, h, _ = _tam(entrada)
    cw, ch = (w, int(w * 16 / 9)) if h * 9 >= w * 16 else (int(h * 9 / 16), h)
    cw -= cw % 2
    ch -= ch % 2
    vf = f"crop={cw}:{ch},"
    vf += ("minterpolate=fps=72:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" if fps == 72 else f"fps={fps}")
    lector = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(entrada), "-vf", vf, "-f", "rawvideo",
                               "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix(".tmp.mp4")
    escritor = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                 "-s", f"{SW}x{SH}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                                 "-preset", "medium", "-crf", "11", "-pix_fmt", "yuv420p", str(tmp)],
                                stdin=subprocess.PIPE)
    n, tam = 0, cw * ch * 3
    while True:
        raw = lector.stdout.read(tam)
        if len(raw) < tam:
            break
        f = np.frombuffer(raw, np.uint8).reshape(ch, cw, 3)
        l = cv2.resize(f, (SW, SH), interpolation=cv2.INTER_LANCZOS4)
        if sr:
            g = cv2.resize(ampliar(f), (SW, SH), interpolation=cv2.INTER_AREA)
            l = cv2.addWeighted(g, 0.8, l, 0.2, 0)   # un 20 % de lanczos: la piel no queda plástica
        escritor.stdin.write(l.tobytes())
        n += 1
    lector.stdout.close(); escritor.stdin.close(); escritor.wait(); lector.wait()
    tmp.rename(salida)
    return n


# ───────────── máscara de persona (Robust Video Matting) ─────────────

def mate(entrada_sr: Path, salida: Path) -> None:
    """Alfa de la persona a 1440×2560 (se calcula a 720×1280 y se amplía: 4× más rápido)."""
    import torch
    dev = _dispositivo()
    try:
        red = torch.jit.load(str(modelo("rvm_mobilenetv3_fp32.torchscript")), map_location=dev).eval()
    except Exception:
        dev = torch.device("cpu")
        red = torch.jit.load(str(modelo("rvm_mobilenetv3_fp32.torchscript")), map_location=dev).eval()
    w, h = 720, 1280
    lector = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(entrada_sr), "-vf", f"scale={w}:{h}",
                               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix(".tmp.mp4")
    escritor = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                                 "-s", f"{w}x{h}", "-r", "24", "-i", "-", "-vf", f"scale={SW}:{SH}",
                                 "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", str(tmp)],
                                stdin=subprocess.PIPE)
    rec = [None] * 4
    with torch.no_grad():
        while True:
            raw = lector.stdout.read(w * h * 3)
            if len(raw) < w * h * 3:
                break
            x = torch.from_numpy(np.frombuffer(raw, np.uint8).reshape(h, w, 3).copy())
            x = (x.permute(2, 0, 1)[None].float() / 255.0).to(dev)
            _, pha, *rec = red(x, *rec, downsample_ratio=0.4)
            escritor.stdin.write((pha[0, 0].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8).tobytes())
    lector.stdout.close(); escritor.stdin.close(); escritor.wait(); lector.wait()
    tmp.rename(salida)


# ───────────── caras (YuNet) ─────────────

_DET = {}


def cara(bgr: np.ndarray) -> dict | None:
    """Cara más grande de un fotograma 1440×2560 → {cx, top, menton, ancho} en px de ese fotograma."""
    if "yunet" not in _DET:
        _DET["yunet"] = cv2.FaceDetectorYN.create(str(modelo("face_detection_yunet_2023mar.onnx")), "",
                                                  (360, 640), 0.6)
    peq = cv2.resize(bgr, (360, 640), interpolation=cv2.INTER_AREA)
    _, caras = _DET["yunet"].detect(peq)
    if caras is None or not len(caras):
        return None
    x, y, w, h = max(caras, key=lambda c: c[2] * c[3])[:4]
    k = SW / 360
    return {"cx": float((x + w / 2) * k), "top": float(y * k), "menton": float((y + h) * k), "ancho": float(w * k)}


def transcribir_aparte(ruta: Path) -> list[dict]:
    """kit.transcribir en otro proceso: Whisper de Apple (MLX) y OpenCV/torch en el mismo proceso
    pueden romperse con un fallo de segmento."""
    import sys
    r = subprocess.run([sys.executable, "-c", "import json, sys; from kit.transcribir import transcribir; "
                        "print(json.dumps(transcribir(sys.argv[1])))", str(ruta)],
                       capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[2])
    return json.loads(r.stdout.strip().splitlines()[-1])


# ───────────── caché por anuncio ─────────────

class Material:
    """Lo preparado de cada clip de un anuncio, calculado una vez y guardado en <anuncio>/pro/."""

    def __init__(self, raiz: Path, rapido: bool = False):
        self.raiz = raiz
        self.rapido = rapido or not hay_torch()
        self.dir = raiz / "pro"
        self.dir.mkdir(exist_ok=True)
        self._caras = self._leer("caras.json")
        self._pal = self._leer("palabras.json")
        self._nfot = {}
        self._audio = {}

    def _leer(self, nombre):
        p = self.dir / nombre
        return json.loads(p.read_text()) if p.exists() else {}

    def _guardar(self, nombre, datos):
        (self.dir / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=1))

    def video(self, clip: str, fps: int = 24) -> Path:
        tipo = "lq" if self.rapido else "sr"
        destino = self.dir / f"{tipo}{'' if fps == 24 else fps}" / (Path(clip).stem + ".mp4")
        if not destino.exists():
            print(f"  preparando {clip} ({'rápido' if self.rapido else 'superresolución'}"
                  f"{', 72 fps' if fps == 72 else ''})…", flush=True)
            normalizar(self.raiz / clip, destino, fps, sr=not self.rapido)
        return destino

    def nfot(self, clip: str, fps: int) -> int:
        k = (clip, fps)
        if k not in self._nfot:
            r = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-select_streams", "v:0",
                                "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0",
                                str(self.video(clip, fps))], capture_output=True, text=True, check=True)
            self._nfot[k] = int(r.stdout.strip())
        return self._nfot[k]

    def mate(self, clip: str) -> Path | None:
        if not hay_torch():
            return None
        destino = self.dir / "mate" / (Path(clip).stem + ".mp4")
        if not destino.exists():
            print(f"  máscara de persona de {clip}…", flush=True)
            mate(self.video(clip, 24), destino)
        return destino

    def cara_en(self, clip: str, t: float, fotograma: np.ndarray) -> dict | None:
        k = f"{clip}@{t:.2f}"
        if k not in self._caras:
            self._caras[k] = cara(fotograma)
            self._guardar("caras.json", self._caras)
        return self._caras[k]

    def palabras(self, clip: str) -> list[dict]:
        if clip not in self._pal:
            print(f"  transcribiendo {clip}…", flush=True)
            self._pal[clip] = transcribir_aparte(self.raiz / clip)
            self._guardar("palabras.json", self._pal)
        return self._pal[clip]

    def audio(self, clip: str) -> np.ndarray:
        """Audio mono a 48 kHz del clip (vacío si no tiene)."""
        if clip not in self._audio:
            r = subprocess.run([FFMPEG, "-v", "error", "-i", str(self.raiz / clip), "-vn", "-f", "f32le",
                                "-ac", "1", "-ar", "48000", "-"], capture_output=True)
            self._audio[clip] = np.frombuffer(r.stdout, np.float32).copy()
        return self._audio[clip]
