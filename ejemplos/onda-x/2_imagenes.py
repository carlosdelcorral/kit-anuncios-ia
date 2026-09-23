"""ONDA X · paso 2: los planos nuevos (webcam sin cascos, dos fotogramas del juego, unboxing cenital y
macro del aro de luz), ≈0,06 USD. Necesitan `base`, `producto` y `p0` del paso 1.

    python ejemplos/onda-x/2_imagenes.py
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

I = "ejemplos/onda-x/img"
G = [sys.executable, "-m", "kit.generar", "imagen"]
PRESERVE = ("Preserve: the same person, same face and identity, same grey hoodie, same skin texture with visible "
            "pores and slight asymmetry, same bedroom and purple and cyan LED light. Match: same phone-camera look, "
            "same colour and direction of light. The result should look like the next frame of the same TikTok video. "
            "Natural skin, nothing airbrushed, no CGI. No text anywhere, no watermark, no readable screen interface.")
JUEGO = ("rendered like a modern AAA video game (Unreal Engine 5 look), cinematic volumetric light, purple and cyan "
         "neon accents. No HUD, no crosshair, no health bar, no numbers, no letters, no user interface, no watermark.")
IMGS = {
 "w0": ("Reference Image 1 defines the young man — his exact face, hair, stubble, grey hoodie — and his bedroom and "
        "lighting. Change: webcam-style shot from the top of his gaming monitor: he sits at his desk playing with a black "
        "game controller, NOT wearing any headphones, focused, his face lit by the cool flickering screen light; a small "
        "square matte black wireless microphone transmitter is clipped to his hoodie collar. " + PRESERVE,
        ["base"], "9:16", "imagen"),
 "g1": ("A vertical frame from a first-person sci-fi shooter video game: the player's futuristic matte-black energy "
        "rifle with glowing purple and cyan details in the lower right of the frame, a dark industrial corridor with "
        "metal walkways, steam and neon strip lights, a hostile bipedal combat robot with a single glowing red eye at "
        "the far end. " + JUEGO, [], "9:16", "sunburst"),
 "g2": ("A vertical frame from the same first-person sci-fi shooter video game: the player's futuristic matte-black "
        "energy rifle in the lower right, a steep metal staircase on the left leading up to a dark upper level, a "
        "combat robot with a glowing red eye coming down the stairs, sparks falling, haze. " + JUEGO, [], "9:16", "sunburst"),
 "u1": ("Reference Image 1 defines the exact ONDA X headset. Reference Image 2 defines the exact ONDA X retail box. "
        "Do not redesign either. Top-down overhead photo looking straight down at a wooden desk at night: a young man's "
        "two hands in grey hoodie sleeves lifting the lid off the matte black ONDA X box, the ONDA X headset nestled "
        "in black foam inside, purple and cyan LED light spilling on the desk, a game controller at the edge, "
        "real phone-camera look, natural skin on the hands. No text except the ONDA X wordmark on the box.",
        ["producto", "p0"], "9:16", "sunburst"),
 "m1": ("Reference Image 1 defines the exact ONDA X headset: do not redesign it. Extreme macro close-up of one ONDA X "
        "ear cup: the thin RGB light ring glowing purple fading to cyan, the black fabric cushion texture, the matte "
        "soft-touch finish, very shallow depth of field, dark background, premium product commercial look. No text.",
        ["producto"], "9:16", "sunburst"),
}

def run(nombre):
    prompt, refs, aspecto, modelo = IMGS[nombre]
    cmd = G + [prompt, "--modelo", modelo, "--aspecto", aspecto, "--out", f"{I}/{nombre}.png"]
    if refs:
        cmd += ["--ref"] + [f"{I}/{r}.png" for r in refs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return f"{nombre}: {'ok' if r.returncode == 0 else r.stderr[-400:]}"

if __name__ == "__main__":
    with ThreadPoolExecutor(5) as ex:
        for l in ex.map(run, sys.argv[1:] or list(IMGS)):
            print(l, flush=True)
