"""Los efectos de vídeo de cada plano, como cadenas de filtros de ffmpeg.

Un plano se monta así, siempre en este orden (cada paso es opcional salvo el encuadre):

    recorte (y rampa)  →  zoom (entrada + empuje + zoom seco)  →  encuadre 1080×1920 con
    sacudida y barrido  →  desenfoque de barrido  →  glitch  →  flash  →  barrido de luz  →  grano

El zoom se hace escalando por fotograma (`scale` con `eval=frame`) por encima del lienzo y
recortando: así siempre se reduce, nunca se amplía un recorte, y el margen sobrante es el que
usan la sacudida y el barrido para moverse sin enseñar bordes negros.
"""
from __future__ import annotations

W, H, FPS = 1080, 1920, 30

# Márgenes mínimos de escala: una sacudida de 28 px o un barrido de 60 px necesitan sitio.
BASE_SACUDIDA = 1.06
BASE_BARRIDO = 1.10
BARRIDO_DUR = 0.12          # s de desenfoque a cada lado de la junta
BARRIDO_PX = 60


def _f(x: float) -> str:
    return f"{x:.4f}"


def fotogramas(dur: float) -> int:
    return int(round(dur * FPS))


def expr_zoom(p: dict, dur: float) -> str:
    """K(t): factor de zoom sobre el encuadre que cubre el lienzo."""
    z = p.get("zoom", {})
    base = float(z.get("base", 1.0))
    if any(e["tipo"] == "sacudida" for e in p.get("efectos", [])):
        base = max(base, BASE_SACUDIDA)
    if p.get("_barrido_entra") or p.get("_barrido_sale"):
        base = max(base, BASE_BARRIDO)
    if (p.get("movil") or {}).get("mano"):
        base = max(base, 1.06)
    k = f"{_f(base)}*(1+{_f(z.get('entrada', 0.0))}*exp(-t/0.12))*(1+{_f(z.get('empuje', 0.0))}*t/{_f(dur)})"
    for e in p.get("efectos", []):
        if e["tipo"] == "zoom_seco":
            k += f"*(1+{_f(e.get('cantidad', 0.25))}*clip((t-{_f(e['t'])})/0.10,0,1))"
    return k


def expr_desplazamiento(p: dict, dur: float) -> tuple[str, str]:
    """Desplazamiento (dx, dy) en px del recorte: sacudidas amortiguadas + barridos."""
    dx, dy = ["0"], ["0"]
    for e in p.get("efectos", []):
        if e["tipo"] == "sacudida":
            a, t0 = float(e.get("fuerza", 26)), _f(e["t"])
            env = f"{_f(a)}*exp(-(t-{t0})/0.09)*gte(t,{t0})"
            dx.append(f"{env}*sin(2*PI*27*(t-{t0}))")
            dy.append(f"{env}*0.7*cos(2*PI*21*(t-{t0}))")
    movil = p.get("movil") or {}
    if movil.get("mano"):
        # Temblor de mano de móvil: deriva lenta de senos no armónicos (nunca vibración digital ni
        # estabilizado de gimbal). Fases distintas por plano para que no se repita el patrón.
        m, f = float(movil["mano"]), 1.7 * (p.get("_i", 0) + 1)
        dx.append(f"{_f(m)}*(9*sin(2*PI*0.23*t+{_f(f)})+5*sin(2*PI*0.61*t+{_f(f * 1.3)})+2*sin(2*PI*1.7*t+{_f(f * 0.4)}))")
        dy.append(f"{_f(m)}*(12*sin(2*PI*0.19*t+{_f(f * 2.1)})+6*sin(2*PI*0.53*t+{_f(f * 0.7)})+2*sin(2*PI*2.3*t+{_f(f)}))")
    d = BARRIDO_DUR
    if p.get("_barrido_sale"):
        dx.append(f"{BARRIDO_PX}*pow(clip((t-{_f(dur - d)})/{_f(d)},0,1),2)")
    if p.get("_barrido_entra"):
        dx.append(f"-{BARRIDO_PX}*pow(clip(1-t/{_f(d)},0,1),2)")
    return "+".join(dx), "+".join(dy)


# Ventana de cámara del diseño «streamer» (gameplay a pantalla completa + la cara en pequeño).
PIP_W, PIP_H, PIP_X, PIP_Y, PIP_BORDE = 440, 540, 70, 372, 7


def cadena(p: dict, info: dict, dur: float, entradas: dict) -> str:
    """filter_complex de un plano. Entrada 0 = el clip; `entradas` dice en qué índice están la franja
    de luz, la ventana de cámara (`pip`), su máscara redondeada y su borde, si el plano los usa."""
    partes = []
    cobertura = max(W / info["w"], H / info["h"])

    # 1 · recorte (con rampa de velocidad si la hay: tramos a distinta velocidad, concatenados)
    rampa = next((e for e in p.get("efectos", []) if e["tipo"] == "rampa"), None)
    if rampa:
        tramos = rampa["tramos"]                       # [[desde, hasta, velocidad], ...] en s del clip
        for i, (a, b, v) in enumerate(tramos):
            partes.append(f"[0:v]trim=start={_f(a)}:end={_f(b)},setpts=(PTS-STARTPTS)/{_f(v)}[r{i}]")
        partes.append("".join(f"[r{i}]" for i in range(len(tramos))) + f"concat=n={len(tramos)}:v=1:a=0,fps={FPS}[v0]")
    else:
        partes.append(f"[0:v]trim=start={_f(p['_v_in'])}:end={_f(p['_v_out'])},setpts=PTS-STARTPTS,fps={FPS}[v0]")

    # 2-3 · zoom y encuadre con sacudida/barrido
    k = expr_zoom(p, dur)
    dx, dy = expr_desplazamiento(p, dur)
    c = [
        f"scale=w='floor(iw*{_f(cobertura)}*{k}/2)*2':h='floor(ih*{_f(cobertura)}*{k}/2)*2':eval=frame:flags=lanczos",
        f"crop={W}:{H}:x='clip((iw-{W})/2+{dx},0,iw-{W})':y='clip((ih-{H})/2+{dy},0,ih-{H})'",
        "unsharp=5:5:0.45:5:5:0",
    ]
    # 4 · desenfoque horizontal en la junta de barrido
    if p.get("_barrido_sale"):
        c.append(f"gblur=sigma=34:sigmaV=0.6:enable='gte(t,{_f(dur - BARRIDO_DUR)})'")
    if p.get("_barrido_entra"):
        c.append(f"gblur=sigma=34:sigmaV=0.6:enable='lte(t,{_f(BARRIDO_DUR)})'")
    # 5 · glitch
    for e in p.get("efectos", []):
        if e["tipo"] == "glitch":
            a, b = _f(e["t"]), _f(e["t"] + float(e.get("dur", 0.18)))
            c.append(f"rgbashift=rh=-16:bh=16:rv=4:enable='between(t,{a},{b})'")
            c.append(f"noise=alls=38:allf=t:enable='between(t,{a},{b})'")
    # 6 · flash de junta (a blanco y desde blanco)
    if p.get("_flash_entra"):
        c.append("fade=t=in:st=0:d=0.14:color=white")
    if p.get("_flash_sale"):
        c.append(f"fade=t=out:st={_f(dur - 0.05)}:d=0.05:color=white")
    # 5b · lo que hace que parezca un móvil: exposición y balance que respiran, enfoque que busca,
    # la distorsión del frontal y un píxel de aberración cromática
    movil = p.get("movil") or {}
    if movil.get("exposicion"):
        fz = 1.3 * (p.get("_i", 0) + 1)
        caidas = "".join(f"-0.045*exp(-pow((t-{_f(t0)})/0.35,2))" for t0 in movil.get("caidas", []))
        c.append(f"eq=eval=frame:brightness='0.012*sin(2*PI*t/6.5+{_f(fz)}){caidas}'"
                 f":gamma_r='1+0.012*sin(2*PI*t/9+{_f(fz)})':gamma_b='1-0.012*sin(2*PI*t/9+{_f(fz)})'")
    for t0 in movil.get("enfoque", []):
        c.append(f"gblur=sigma=2.2:enable='between(t,{_f(t0)},{_f(t0 + 0.14)})'")
        c.append(f"gblur=sigma=1.1:enable='between(t,{_f(t0 + 0.14)},{_f(t0 + 0.32)})'")
    if p.get("noche"):
        # Móvil a oscuras: más oscuro, frío y sin saturación, con las sombras cerradas.
        k = float(p["noche"]) if not isinstance(p["noche"], bool) else 1.0
        c.append(f"eq=brightness={_f(-0.12 * k)}:contrast={_f(1 + 0.08 * k)}:saturation={_f(1 - 0.3 * k)}:gamma={_f(1 - 0.1 * k)}")
        c.append(f"colorbalance=rs={_f(-0.05 * k)}:bs={_f(0.10 * k)}:bm={_f(0.05 * k)}")
    if movil.get("frontal"):
        c.append("lenscorrection=k1=0.02:k2=0.005:i=bilinear")
    if movil:
        c.append("rgbashift=rh=-1:bh=1")
    if p.get("abre_negro"):
        c.append(f"fade=t=in:st={_f(float(p['abre_negro']))}:d=0.12:color=black")
    if p.get("_negro_entra"):
        c.append("fade=t=in:st=0:d=0.10:color=black")
    if p.get("_negro_sale"):
        c.append(f"fade=t=out:st={_f(dur - 0.08)}:d=0.08:color=black")
    # 6b · tinte de color (p. ej. rojo cuando te matan)
    for e in p.get("efectos", []):
        if e["tipo"] == "tinte":
            a, b = _f(e["t"]), _f(e["t"] + float(e.get("dur", 0.35)))
            col = e.get("color", "red").lstrip("#")
            col = f"0x{col}" if all(ch in "0123456789abcdefABCDEF" for ch in col) and len(col) == 6 else col
            c.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={col}@{e.get('alfa', 0.38)}:t=fill:enable='between(t,{a},{b})'")
    partes.append("[v0]" + ",".join(c) + "[v1]")

    ultimo = "v1"
    # 6c · diseño streamer: la cara en una ventana redondeada sobre el gameplay
    pip = p.get("pip")
    if pip and "pip" in entradas:
        ip, im, ib = entradas["pip"], entradas["mascara"], entradas["borde"]
        pinfo = pip["_info"]
        esc_w = PIP_W / pinfo["w"]
        alto = int(pinfo["h"] * esc_w / 2) * 2
        y_cara = float(pip.get("y_cara", 0.16))
        oy = max(0, min(alto - PIP_H, int(alto * y_cara)))
        partes.append(f"[{ip}:v]trim=start={_f(pip['_v_in'])}:end={_f(pip['_v_in'] + dur + 0.1)},setpts=PTS-STARTPTS,"
                      f"fps={FPS},scale={PIP_W}:{alto}:flags=lanczos,crop={PIP_W}:{PIP_H}:0:{oy},format=rgba[pc]")
        partes.append(f"[{im}:v]format=gray,scale={PIP_W}:{PIP_H}[pm]")
        partes.append("[pc][pm]alphamerge[pa]")
        partes.append(f"[{ultimo}][pa]overlay=x={PIP_X}:y={PIP_Y}:shortest=1[vp1]")
        partes.append(f"[vp1][{ib}:v]overlay=x={PIP_X - PIP_BORDE}:y={PIP_Y - PIP_BORDE}:shortest=1[vp2]")
        ultimo = "vp2"
    # 7 · barrido de luz sobre el producto
    luz = next((e for e in p.get("efectos", []) if e["tipo"] == "barrido_luz"), None)
    if luz and "franja" in entradas:
        t0, d = _f(luz["t"]), _f(float(luz.get("dur", 0.9)))
        partes.append(f"[{ultimo}][{entradas['franja']}:v]overlay=x='-1700+3400*(t-{t0})/{d}':y=0:"
                      f"enable='between(t,{t0},{t0}+{d})':format=auto[v2]")
        ultimo = "v2"
    # 8 · grano y etalonaje suave (unifica la textura de la IA) y duración exacta
    grano = p.get("grano", True)
    fin = []
    if grano == "movil":
        # Grano de sensor: más en las sombras que en las luces (el de un móvil con poca luz).
        partes.append(f"[{ultimo}]format=yuv420p,split[ga][gb];[gb]noise=alls=16:allf=t[gn];"
                      "[ga][gn]blend=c0_expr='A+(B-A)*(1.15-A/255)*0.7':c1_expr='A+(B-A)*0.35':"
                      "c2_expr='A+(B-A)*0.35'[vg]")
        ultimo = "vg"
        fin += ["eq=contrast=1.02:saturation=1.03", "vignette=PI/6"]
    elif grano:
        fin += ["noise=alls=5:allf=t+u", "eq=contrast=1.03:saturation=1.04", "vignette=PI/5"]
    # Duración EXACTA en fotogramas: `trim=duration` dejaba uno de más por plano y la imagen se iba
    # retrasando respecto al audio (24 planos → ~0,7 s al final).
    fin += ["tpad=stop_mode=clone:stop_duration=0.3", f"trim=end_frame={fotogramas(dur)}", "setpts=PTS-STARTPTS",
            "format=yuv420p"]
    partes.append(f"[{ultimo}]" + ",".join(fin) + "[vout]")
    return ";".join(partes)
