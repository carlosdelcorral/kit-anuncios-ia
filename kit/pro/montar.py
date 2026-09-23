"""Montaje profesional: `edicion.json` → MP4 1080×1920 a 24 fps, −14 LUFS, con informe.

    python -m kit.pro.montar anuncios/<slug>/edicion.json            # render completo
    python -m kit.pro.montar anuncios/<slug>/edicion.json --rapido   # borrador sin superresolución
    python -m kit.pro.montar anuncios/<slug>/edicion.json --fotos 30,120,300   # fotogramas sueltos

La primera vez prepara el material (superresolución, 72 fps, máscaras, caras, palabras) y lo deja en
`<anuncio>/pro/`; las siguientes solo monta. El criterio con el que se escribe el JSON está en
`.claude/skills/crear-anuncio/references/edicion-pro.md`; el formato, en `edicion-json.md`.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from kit.ffmpeg import FFMPEG, FFPROBE
from kit.pro import audio as A
from kit.pro import grafismo as G
from kit.pro import imagen as I
from kit.pro.preparar import SH, SW, Material, cara

W, H, FPS = 1080, 1920, 24
Y_SUB = 1175       # centro de los subtítulos: la zona segura de Meta acaba en y 1248
Y_MENTON = 1085    # en los planos con cara, el mentón se coloca aquí: el subtítulo nunca tapa la boca


def leer_fotogramas(ruta, fps, i0, i1, gris=False):
    n = i1 - i0 + 1
    ch = 1 if gris else 3
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, (i0 - 0.5) / fps):.4f}", "-i", str(ruta),
                          "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "gray" if gris else "bgr24", "-"],
                         capture_output=True, check=True).stdout
    tam = SW * SH * ch
    k = len(raw) // tam
    arr = np.frombuffer(raw, np.uint8)[:k * tam]
    arr = arr.reshape(k, SH, SW) if gris else arr.reshape(k, SH, SW, 3)
    return {i0 + j: arr[j] for j in range(k)}


def cercano(d, i):
    return d[i] if i in d else d[min(d, key=lambda j: abs(j - i))]


# ───────────── planos y voces ─────────────

class Plano:
    def __init__(self, d: dict):
        self.d = d
        self.id, self.clip = d["id"], d["clip"]
        self.tramos = [tuple(x) for x in d["tramos"]] if "tramos" in d else [(d["desde"], d["hasta"], d.get("vel", 1.0))]
        self.durs = [abs(b - a) / v for a, b, v in self.tramos]
        self.dur = sum(self.durs)
        self.lento = any(v < 0.9 for _, _, v in self.tramos)
        self.fps = 72 if self.lento else 24
        self.foco = tuple(d.get("foco", (0.5, 0.5)))
        self.grado = d.get("grado", "despues")
        self.entrada = d.get("entrada", "corte")
        self.pip = d.get("pip")
        self.ancla = None
        self.voz = None
        zs = [k[1] for k in d.get("zoom", [[0, 1.0]])]
        self.borde_suave = d.get("borde_suave", min(zs) < 1)

    def src(self, t):
        for i, ((a, b, v), d) in enumerate(zip(self.tramos, self.durs)):
            if t <= d or i == len(self.tramos) - 1:
                return a + (1 if b >= a else -1) * min(max(t, 0), d) * v
            t -= d

    def local(self, s):
        acc = 0.0
        for (a, b, v), d in zip(self.tramos, self.durs):
            if min(a, b) - 1e-6 <= s <= max(a, b) + 1e-6:
                return acc + abs(s - a) / v
            acc += d
        raise ValueError(f"{self.id}: el segundo {s} del clip no está en el plano")


class Voz:
    def __init__(self, E, plano, d):
        self.clip = d.get("clip", plano.clip)
        a, b, v = plano.tramos[0]
        self.desde, self.hasta = d.get("desde", a), d.get("hasta", b)
        self.vel = d.get("vel", v if "clip" not in d else 1.0)
        self.t = plano.t0 + d.get("en", 0.0)
        x = E.mat.audio(self.clip)
        va, vb = A.tramo_de_voz(x, self.desde, self.hasta)
        toks = self._tokens(d.get("sub"), E, va, vb)
        ws = [w for w in E.mat.palabras(self.clip) if w["fin"] > va + 0.02 and w["inicio"] < vb - 0.02]
        if len(ws) == len(toks) and toks:
            durs = [min(max(w["fin"] - w["inicio"], 0.08), 0.55) for w in ws]
            huecos = [max(0.0, min(ws[k + 1]["inicio"] - ws[k]["fin"], 0.4)) for k in range(len(ws) - 1)]
        else:   # si no cuadra con Whisper, reparte por longitud de palabra
            durs = [len(t["texto"]) + 2 for t in toks]
            huecos = [0.8] * max(len(toks) - 1, 0)
        esc = (vb - va) / max(sum(durs) + sum(huecos), 1e-6)
        s = va
        for k, tk in enumerate(toks):
            tk["a"], tk["b"] = s, s + durs[k] * esc
            s = tk["b"] + (huecos[k] * esc if k < len(huecos) else 0)
            tk["ta"], tk["tb"] = self.tl(tk["a"]), self.tl(tk["b"])
        self.tokens = toks
        self.fin = self.tl(vb)

    def tl(self, s):
        return self.t + (s - self.desde) / self.vel

    def _tokens(self, sub, E, va, vb):
        out = []
        if sub:
            modo = "blanco"
            for nb, bloque in enumerate(sub.split("|")):
                for tk in bloque.split():
                    oculto = tk == "_"
                    if tk[0] in "*!":
                        modo = "acento" if tk[0] == "*" else "rojo"
                    out.append({"texto": tk.strip("*!"), "modo": modo, "oculto": oculto, "bloque": nb})
                    if tk[-1] in "*!":
                        modo = "blanco"
            return out
        ws = [w for w in E.mat.palabras(self.clip) if w["fin"] > va + 0.02 and w["inicio"] < vb - 0.02]
        nb, chars, n = 0, 0, 0
        for i, w in enumerate(ws):
            txt = w["texto"].upper()
            if n >= 3 or (n and chars + len(txt) > 15):
                nb, chars, n = nb + 1, 0, 0
            out.append({"texto": txt, "modo": "acento" if i == len(ws) - 1 else "blanco", "oculto": False, "bloque": nb})
            chars, n = chars + len(txt), n + 1
            if txt[-1] in ".,?!":
                nb, chars, n = nb + 1, 0, 0
        return out


class Edicion:
    def __init__(self, ruta: Path, rapido=False):
        self.ruta = ruta
        self.raiz = ruta.parent
        self.d = json.loads(ruta.read_text())
        self.fps = FPS
        self.mat = Material(self.raiz, rapido)
        self.rapido = self.mat.rapido
        est = self.d.get("estilo", {})
        self.acento = G.hex_a_rgb(est.get("acento", "#3DF5FF"))
        self.acento_antes = G.hex_a_rgb(est.get("antes", est.get("acento", "#3DF5FF")))
        self.y_sub = est.get("y_sub", Y_SUB)
        self.planos = [Plano(p) for p in self.d["planos"]]
        self.S = {p.id: p for p in self.planos}
        t = 0.0
        f = 0
        for p in self.planos:
            p.f0 = f
            p.f1 = int(round((t + p.dur) * FPS))
            p.n, p.t0 = p.f1 - p.f0, p.f0 / FPS
            t += p.dur
            f = p.f1
        self.nf = self.planos[-1].f1
        self.duracion = self.nf / FPS
        self.t_cambio = self.S[self.d["cambio"]].t0 if self.d.get("cambio") else -1.0
        self.voces = []
        for p in self.planos:
            if p.d.get("voz"):
                p.voz = Voz(self, p, p.d["voz"] if isinstance(p.d["voz"], dict) else {})
                self.voces.append(p.voz)
        self.fin_musica = None
        self._musica_fin()
        self.subs = self._subtitulos()
        self.elementos = [G.TIPOS[g["tipo"]](g, self) for g in self.d.get("grafismo", [])]
        for p in self.planos:
            p.zoom = [(self.local(k[0], p), k[1], k[2] if len(k) > 2 else "lin") for k in p.d.get("zoom", [[0, 1.0]])]
            p.efectos = [[e[0], self.local(e[1], p), *e[2:]] for e in p.d.get("efectos", [])]
            ventana = (p.t0, p.t0 + p.n / FPS)
            dentro = [e for e in self.elementos if e.t0 < ventana[1] - 1e-6 and e.t1 > ventana[0] + 1e-6]
            p.mate = any(e.capa == "detras" or isinstance(e, G.Orbita) for e in dentro)
            p.cabeza = any(e.necesita_cabeza for e in dentro)

    # tiempos: número (segundos; relativo al plano si se da uno) o {plano, t, src, palabra, fin, fin_voz, fin_musica}
    def t(self, ref, plano=None):
        if isinstance(ref, (int, float)):
            return (self.S[plano].t0 if plano else 0.0) + float(ref)
        pid = ref.get("plano", plano)
        off = ref.get("t", 0.0)
        if ref.get("fin_musica"):
            return self.fin_musica + off
        if ref.get("fin_voz"):
            v = self.S[pid].voz if pid else self.voces[-1]
            return v.fin + off
        p = self.S[pid]
        if "src" in ref:
            return p.t0 + p.local(ref["src"]) + off
        if "palabra" in ref:
            return p.voz.tokens[ref["palabra"]]["ta"] + off
        if ref.get("fin"):
            return p.t0 + p.n / FPS + off
        return p.t0 + off

    def local(self, ref, p):
        return self.t(ref, p.id) - p.t0

    def color(self, nombre, t):
        if nombre == "acento":
            return self.acento_antes if t < self.t_cambio else self.acento
        return G.hex_a_rgb(nombre)

    def _musica_fin(self):
        m = self.d.get("musica")
        if not m:
            return
        for tr in m["tramos"]:
            t0 = self.t(tr["desde"])
            t1 = self.t(tr["hasta"])
            if isinstance(tr["hasta"], dict) and tr["hasta"].get("compas"):
                t1 = A.compas(t0, t1, m.get("bpm", 120))
            tr["_t0"], tr["_t1"] = t0, min(t1, self.duracion)
        self.fin_musica = m["tramos"][-1]["_t1"]

    def _subtitulos(self):
        out = []
        for v in self.voces:
            toks = v.tokens
            for nb in sorted({t["bloque"] for t in toks}):
                idx = [i for i, t in enumerate(toks) if t["bloque"] == nb]
                vis = [i for i in idx if not toks[i]["oculto"]]
                if not vis:
                    continue
                fin = toks[vis[-1]]["tb"] + 0.22
                if vis[-1] + 1 < len(toks):
                    fin = min(fin, toks[vis[-1] + 1]["ta"] - 0.02)
                out.append({"t0": toks[vis[0]]["ta"] - 0.04, "fin": fin,
                            "trozo": [(toks[i]["texto"], toks[i]["modo"]) for i in vis]})
        out.sort(key=lambda b: b["t0"])
        for b, nb in zip(out, out[1:]):
            b["t1"] = min(b["fin"], nb["t0"])
        if out:
            out[-1]["t1"] = out[-1]["fin"]
        return out

    # ───────────── imagen ─────────────

    def transformar(self, p, k, t):
        z = I_valor(p.zoom, t)
        g = p.d.get("golpe", 0.0)
        if g and t < 0.14:
            z *= 1 + g * (1 - G.ease_out(t / 0.14))
        dx = dy = rot = 0.0
        T = k / FPS
        for e in p.efectos:
            if e[0] == "zoom_seco" and t >= e[1]:
                z *= 1 + e[2] * G.ease_out((t - e[1]) / 0.05)
            if e[0] == "sacudida" and e[1] <= t < e[1] + e[3]:
                dec = (1 - (t - e[1]) / e[3]) ** 2
                dx += e[2] * dec * G.ruido(T * 55, 11)
                dy += e[2] * dec * G.ruido(T * 55, 12)
                rot += 0.012 * dec * G.ruido(T * 40, 13) * e[2] / 20
        tb = p.d.get("temblor", 0)
        if tb:
            dx += tb * G.ruido(T * 5, 21)
            dy += tb * G.ruido(T * 5, 22)
            rot += 0.004 * G.ruido(T * 3, 23)
        return z, dx, dy + p.d.get("dy", 0.0), rot

    def matriz(self, p, z, dx, dy, rot):
        s = (W / SW) * z
        cx, cy = p.foco[0] * SW, p.foco[1] * SH
        if p.ancla is not None:
            cy = p.ancla - (Y_MENTON - H / 2) / s
        if z >= 1:
            hw, hh = W / (2 * s), H / (2 * s)
            cx = min(max(cx, hw), SW - hw)
            cy = min(max(cy, hh), SH - hh)
        c, si = math.cos(rot), math.sin(rot)
        M = np.array([[s * c, -s * si, 0.0], [s * si, s * c, 0.0]])
        M[:, 2] = np.array([W / 2 + dx, H / 2 + dy]) - M[:, :2] @ np.array([cx, cy])
        return M

    def transicion(self, p, k):
        i = self.planos.index(p)
        if p.entrada != "corte" and k - p.f0 < 3:
            return p.entrada, k - p.f0
        if i + 1 < len(self.planos):
            nx = self.planos[i + 1]
            if nx.entrada != "corte" and p.f1 - k <= 3:
                return nx.entrada, -(p.f1 - k)
        return None, 0

    def componer(self, p, k, fr, mt, pipf, ctx):
        t = (k - p.f0) / FPS
        T = k / FPS
        base = cercano(fr, self.indice(p, k))
        z, dx, dy, rot = self.transformar(p, k, t)
        tipo, fase = self.transicion(p, k)
        if p.borde_suave:
            base = (base.astype(np.float32) * ctx["borde"][..., None]).astype(np.uint8)
        borde = cv2.BORDER_CONSTANT if p.borde_suave else cv2.BORDER_REFLECT101
        muestras, desenf = [(z, dx)], 0
        if tipo == "whip":
            u = (4 + fase) / 4 if fase < 0 else (3 - fase) / 4
            muestras = [(z, dx + (-1 if fase < 0 else 1) * u * u * 900)]
            desenf = int(u * 170)
        elif tipo == "zoom":
            u = (4 + fase) / 4 if fase < 0 else (3 - fase) / 4
            zm = 1 + u * u * (0.9 if fase < 0 else 0.7)
            muestras = [(z * zm * (1 - j * 0.028 * u), dx) for j in range(6)]
        acc = None
        for zz, xx in muestras:
            w_ = cv2.warpAffine(base, self.matriz(p, zz, xx, dy, rot), (W, H), flags=cv2.INTER_CUBIC, borderMode=borde)
            acc = w_.astype(np.float32) if acc is None else acc + w_
        img = (acc / len(muestras)).astype(np.uint8)
        M = self.matriz(p, z, dx, dy, rot)
        if desenf > 1:
            img = cv2.blur(img, (desenf, 1))
        perfil = I.PERFILES[p.grado]
        f = I.saturar(cv2.LUT(img, I.lut(p.grado)).astype(np.float32) / 255.0, perfil["sat"])

        if p.pip and pipf is not None:
            self._pip(f, p, t, pipf)
        if p.cabeza:
            c = cara(base)
            if c:
                prev = ctx.get("cabeza")
                ctx["cabeza"] = c if prev is None else {kk: 0.6 * prev[kk] + 0.4 * c[kk] for kk in c}
        ctx["M"] = M
        activos = [e for e in self.elementos if e.activo(T)]
        if mt is not None:
            m = cv2.warpAffine(cercano(mt, self.indice(p, k, 24)), M, (W, H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE).astype(np.float32) / 255.0
            m = np.clip((m - 0.15) / 0.7, 0, 1)[..., None]
            detras = f.copy()
            ctx["capa"] = "detras"
            for e in activos:
                if e.capa == "detras" or isinstance(e, G.Orbita):
                    e.dibujar(detras, T, ctx)
            f = f * m + detras * (1 - m)
        extra = sum(e[3] * max(0, 1 - abs(t - e[1] - e[2] / 2) / (e[2] / 2)) for e in p.efectos if e[0] == "bloom")
        f = I.bloom(f, perfil["bloom"] + extra)
        for e in p.efectos:
            if e[0] == "barrido" and 0 <= (t - e[1]) / e[2] <= 1:
                f = I.barrido(f, (t - e[1]) / e[2])
        f = f * (1 - I.VINETA * perfil["vin"])
        ctx["capa"] = "delante"
        for e in activos:
            if e.capa == "delante":
                e.dibujar(f, T, ctx)
        if p.pip:
            G.pegar(f, G.etiqueta_pip(p.pip.get("etiqueta", "DIRECTO")),
                    p.pip.get("x", 70) + 20 + G.etiqueta_pip(p.pip.get("etiqueta", "DIRECTO")).shape[1] / 2,
                    p.pip.get("y", 330) + 53, alfa=1.0 if int(t * 2.2) % 2 == 0 else 0.85)
        self._subtitulo(f, T)
        if self.d.get("etiqueta_ia", "Vídeo generado con IA"):
            G.etiqueta_ia(f, self.d.get("etiqueta_ia", "Vídeo generado con IA"))
        for e in p.efectos:
            if e[0] == "destello" and e[1] <= t < e[1] + e[2]:
                f = f + (1 - f) * e[3] * (1 - (t - e[1]) / e[2])
            if e[0] == "tinte" and e[1] <= t < e[1] + e[2]:
                a = e[3] * (1 - (t - e[1]) / e[2])
                col = np.array(G.hex_a_rgb(e[4])[::-1], np.float32) / 255.0
                f = f * (1 - a) + (f * 0.4 + col * 0.6) * a
        if tipo == "flash":
            f = f + (1 - f) * {-1: 0.45, 0: 1.0, 1: 0.6, 2: 0.28}.get(fase, 0)
        ab = max([e[3] * (1 - (t - e[1]) / e[2]) for e in p.efectos
                  if e[0] == "aberracion" and e[1] <= t < e[1] + e[2]] + [1.2 if tipo == "glitch" else 0.0])
        if ab > 0.02:
            f = I.aberracion(f, ab)
        if tipo == "glitch":
            f = I.glitch(f, k)
        f = I.grano(f, k, perfil["grano"])
        return (np.clip(f, 0, 1) * 255).astype(np.uint8)

    def _pip(self, f, p, t, pipf):
        q = p.pip
        caraf = cercano(pipf, int(round((q["desde"] + t) * 24)))
        bw, bh = q.get("ancho", 400), q.get("alto", 520)
        if "_cx" not in q:
            c = cara(caraf) or {"cx": SW / 2, "top": SH * 0.3, "menton": SH * 0.5}
            q["_cx"], q["_cy"] = c["cx"], (c["top"] + c["menton"]) / 2
        cw = 0.64 * SW
        ch = cw * bh / bw
        x0 = int(min(max(q["_cx"] - cw / 2, 0), SW - cw))
        y0 = int(min(max(q["_cy"] - ch / 2, 0), SH - ch))
        rec = cv2.resize(caraf[y0:int(y0 + ch), x0:int(x0 + cw)], (bw, bh), interpolation=cv2.INTER_AREA)
        rec = I.saturar(cv2.LUT(rec, I.lut("despues")).astype(np.float32) / 255.0, 1.12)
        mask = np.zeros((bh, bw), np.uint8)
        cv2.rectangle(mask, (28, 0), (bw - 28, bh), 255, -1)
        cv2.rectangle(mask, (0, 28), (bw, bh - 28), 255, -1)
        for cxy in ((28, 28), (bw - 29, 28), (28, bh - 29), (bw - 29, bh - 29)):
            cv2.circle(mask, cxy, 28, 255, -1, cv2.LINE_AA)
        mk = mask.astype(np.float32)[..., None] / 255.0
        ap = G.ease_out(t / 0.18)
        px, py = q.get("x", 70), q.get("y", 330) - int(60 * (1 - ap))
        f[py:py + bh, px:px + bw] = f[py:py + bh, px:px + bw] * (1 - mk * ap) + rec * mk * ap
        c1 = G.hex_a_rgb("violeta")
        G.pegar(f, G.marco_pip(bw, bh, c1, self.color("acento", p.t0 + t)), px + bw / 2, py + bh / 2, alfa=ap)

    def _subtitulo(self, f, T):
        for i, b in enumerate(self.subs):
            if b["t0"] <= T < b["t1"]:
                trozo = [(tx, G.NOMBRES["rojo"] if m == "rojo" else
                          (self.color("acento", b["t0"] + 0.05) if m == "acento" else G.NOMBRES["blanco"]))
                         for tx, m in b["trozo"]]
                spr = G.cache(("sub", i), lambda: G.sprite_linea(trozo, "texto", 78, trazo=7, ancho_max=840)[0])
                u = (T - b["t0"]) / 0.14
                G.pegar(f, spr, W / 2, self.y_sub, esc=0.8 + 0.2 * G.ease_back(u), alfa=min(1, (T - b["t0"]) / 0.05))

    def indice(self, p, k, fps=None):
        fps = fps or p.fps
        i = int(round(p.src((k - p.f0) / FPS) * fps))
        return min(max(i, 0), self.mat.nfot(p.clip, fps) - 1)

    def render(self, salida: Path, solo=None):
        tmp = salida.with_suffix(".mudo.mp4")
        sal = None
        if solo is None:
            sal = subprocess.Popen([FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                    "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-c:v", "libx264",
                                    "-preset", "slow", "-crf", "17", "-maxrate", "20M", "-bufsize", "40M",
                                    "-tune", "film", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
                                    "-color_primaries", "bt709", "-color_trc", "bt709", str(tmp)], stdin=subprocess.PIPE)
        ctx = {"borde": I.borde_suave(SW, SH)}
        t0 = time.time()
        for p in self.planos:
            ks = [k for k in range(p.f0, p.f1) if solo is None or k in solo]
            if not ks:
                continue
            ruta = self.mat.video(p.clip, p.fps)
            idx = [self.indice(p, k) for k in ks]
            fr = leer_fotogramas(ruta, p.fps, min(idx), max(idx))
            if p.d.get("cara") and p.ancla is None:
                s_mid = p.src(p.dur / 2)
                c = self.mat.cara_en(p.clip, s_mid, cercano(fr, int(round(s_mid * p.fps))))
                if c:
                    p.ancla = c["menton"]
                    p.foco = (c["cx"] / SW, p.foco[1])
            mt = None
            if p.mate:
                rm = self.mat.mate(p.clip)
                if rm:
                    i24 = [self.indice(p, k, 24) for k in ks]
                    mt = leer_fotogramas(rm, 24, min(i24), max(i24), gris=True)
            pipf = None
            if p.pip:
                a = int(p.pip["desde"] * 24)
                pipf = leer_fotogramas(self.mat.video(p.pip["clip"], 24), 24, a, a + int(p.dur * 24) + 2)
            ctx.pop("cabeza", None)
            for k in ks:
                img = self.componer(p, k, fr, mt, pipf, ctx)
                if sal:
                    sal.stdin.write(img.tobytes())
                else:
                    cv2.imwrite(str(salida.parent / f"f{k:04d}.png"), img)
            del fr, mt, pipf
            print(f"  {p.id:5s} {p.n:3d} fotogramas · {time.time() - t0:6.1f} s", flush=True)
        if sal:
            sal.stdin.close()
            sal.wait()
        return tmp

    # ───────────── sonido ─────────────

    def mezcla(self, salida: Path) -> Path:
        mz = A.Mezcla(self.duracion, self.raiz)
        for v in self.voces:
            x = self.mat.audio(v.clip)[int(v.desde * A.SR):int(v.hasta * A.SR)]
            mz.poner_voz(A.voz_limpia(A.estirar(x, v.vel)), v.t)
        m = self.d.get("musica")
        if m:
            pista = A.cargar(self.raiz / m["archivo"])
            for tr in m["tramos"]:
                mz.tramo_musica(pista, tr["_t0"], tr["_t1"], tr.get("en", 0.0), tr.get("apagada", False))
        for s in self.d.get("sonidos", []):
            mz.sonido(s["archivo"], self.t(s["t"]), db=s.get("db", 0.0), pan=s.get("pan", 0.0),
                      apagado=s.get("apagado", False), pico_en=s.get("pico", 0.0), rev=s.get("rev", False),
                      vel=s.get("vel", 1.0), desde=s.get("desde", 0.0), dur=s.get("dur"), grave=s.get("grave"))
        x = mz.final(m.get("db", -1.5) if m else 0, m.get("ducking_db", 8.5) if m else 0, self.d.get("sonidos_db", -5.0))
        return A.masterizar(x, salida)


def I_valor(claves, t):
    if t <= claves[0][0]:
        return claves[0][1]
    for (ta, va, _), (tb, vb, mb) in zip(claves, claves[1:]):
        if t < tb:
            if mb == "paso":
                return va
            u = (t - ta) / max(tb - ta, 1e-6)
            return va + (vb - va) * (u if mb == "lin" else G.ease_io(u))
    return claves[-1][1]


# ───────────── control de calidad ─────────────

def revisar(E: Edicion, mp4: Path) -> list[str]:
    hoja = mp4.with_suffix(".hoja.png")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(mp4), "-vf", "fps=2,scale=180:320,tile=15x4:padding=3",
                    "-frames:v", "1", str(hoja)], check=True)
    nf = int(subprocess.run([FFPROBE, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                             "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout)
    ebu = subprocess.run([FFMPEG, "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    res = ebu[ebu.rfind("Summary"):]
    lufs = float(res.split("I:")[1].split("LUFS")[0])
    tp = float(res.split("Peak:")[1].split("dBFS")[0])
    from kit.pro.preparar import transcribir_aparte
    oido = " ".join(w["texto"] for w in transcribir_aparte(mp4))
    avisos = []
    if nf != E.nf:
        avisos.append(f"El vídeo tiene {nf} fotogramas y deberían ser {E.nf}: hay desfase")
    if abs(lufs + 14) > 1:
        avisos.append(f"Volumen {lufs} LUFS (objetivo −14 ±1)")
    for p in E.planos:
        if p.dur > 3:
            avisos.append(f"{p.id} dura {p.dur:.1f} s: más de 3 s sin corte se hace largo")
        if p.d.get("cara") and p.ancla is not None:
            z = I_valor(p.zoom, 0)
            s = (W / SW) * z
            cy = min(max(p.ancla - (Y_MENTON - H / 2) / s, H / (2 * s)), SH - H / (2 * s))
            y_menton = (p.ancla - cy) * s + H / 2
            if y_menton > E.y_sub - 50:
                avisos.append(f"{p.id}: el subtítulo puede tapar la barbilla (mentón en y {y_menton:.0f}); "
                              f"sube el zoom a {z * 1.1:.2f} o más")
    lineas = [f"# Informe de montaje · {mp4.name}", "",
              f"- **{E.duracion:.2f} s** · 1080×1920 · 24 fps · {len(E.planos)} planos · {nf}/{E.nf} fotogramas",
              f"- **Volumen:** {lufs} LUFS · pico {tp} dBTP (objetivo −14 / −1,5)",
              f"- **Imagen:** {'borrador sin superresolución' if E.rapido else 'superresolución Real-ESRGAN'}",
              f"- **Hoja de contactos:** `{hoja.name}` (2 fotogramas por segundo)", "",
              "## Planos", "", "| # | Clip | Empieza | Dura | Entrada | Voz |", "|---|---|---|---|---|---|"]
    for p in E.planos:
        lineas.append(f"| {p.id} | `{p.clip}` | {p.t0:.2f} | {p.dur:.2f} | {p.entrada} | "
                      f"{' '.join(t['texto'] for t in p.voz.tokens) if p.voz else '—'} |")
    lineas += ["", "## Lo que se oye (transcrito del montaje)", "", f"> {oido}", "", "## Avisos", ""]
    lineas += [f"- {a}" for a in avisos] or ["- Ninguno"]
    mp4.with_suffix(".informe.md").write_text("\n".join(lineas) + "\n")
    return avisos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edicion")
    ap.add_argument("--rapido", action="store_true", help="borrador: sin superresolución")
    ap.add_argument("--fotos", help="solo estos fotogramas, a PNG junto al JSON (f0030.png…)")
    a = ap.parse_args()
    ruta = Path(a.edicion).resolve()
    E = Edicion(ruta, a.rapido)
    salida = ruta.parent / E.d.get("salida", ruta.parent.name + ".mp4")
    print(f"{len(E.planos)} planos · {E.nf} fotogramas · {E.duracion:.2f} s", flush=True)
    if a.fotos:
        E.render(salida, {int(v) for v in a.fotos.split(",")})
        return
    wav = E.mezcla(salida.with_suffix(".wav"))
    mudo = E.render(salida)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(mudo), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                    str(salida)], check=True)
    mudo.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    avisos = revisar(E, salida)
    print(f"→ {salida}")
    print(f"  informe: {salida.with_suffix('.informe.md').name}")
    for av in avisos:
        print("  AVISO:", av)


if __name__ == "__main__":
    sys.exit(main())
