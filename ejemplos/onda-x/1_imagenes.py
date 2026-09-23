"""ONDA X · paso 1: el personaje, el producto y sus ramas (≈0,10 USD, sunburst `low`).

Con las dos puertas de aprobación del kit:
  1. `base` (el chico) y `producto` (los cascos)  → se enseñan y se aprueban
  2. las ramas p0 (con la caja), p2-p4, p6 (planos de webcam y selfie) y p5 (el producto en vertical)

    python ejemplos/onda-x/1_imagenes.py base producto
    python ejemplos/onda-x/1_imagenes.py p0 p2 p3 p4 p5 p6
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

I = "ejemplos/onda-x/img"
G = [sys.executable, "-m", "kit.generar", "imagen"]
CHICO = ("Photorealistic vertical photo, shot on a real iPhone 15 Pro front camera held at arm's length, 26mm, slight wide-angle. "
 "A Spanish young man, about 22, short messy dark hair with a slight fade, light stubble, a few faint skin blemishes, wearing a plain charcoal grey hoodie. "
 "He sits in his small bedroom gaming setup at night: a desk with a gaming monitor seen from the side, a mechanical keyboard and a game controller, "
 "purple and cyan LED strip light along the wall behind him, a slightly messy shelf, the corner of an unmade bed. "
 "In his left hand, raised near his chin like a street reporter, he holds a small square wireless clip-on microphone transmitter, matte black, about 4 cm wide, no logo. "
 "He looks straight into the lens, mid-sentence, relaxed half smile, eyebrows slightly raised. "
 "Mixed light: cool screen glow on one side of his face, warm desk lamp on the other. "
 "Natural skin texture with visible pores, slight facial asymmetry, flyaway hairs, real fabric texture on the hoodie, nothing airbrushed. "
 "The goal is for this to look like a candid frame from a real creator's TikTok, not an AI render. "
 "Do not smooth the skin artificially. No plastic skin, no beauty filter, no CGI, no 3D render, no doll-like face. "
 "No text anywhere in the frame, no logos, no watermark, no readable screen interface.")
PRODUCTO = ("Studio product photograph of an original over-ear gaming headset design: matte black soft-touch ear cups, "
 "a thin glowing RGB light ring around each ear cup, purple fading to cyan, black memory-foam fabric cushions, "
 "a padded headband with subtle brushed dark metal sliders, no boom microphone, no cables. "
 "Three-quarter view, floating centred on a pure black background, dramatic rim light, subtle glossy reflections, sharp detail, realistic materials. "
 "A small embossed wordmark reading exactly \"ONDA X\" on the side of the headband, spelled letter for letter. "
 "No other text, no watermark, no brand other than ONDA X.")
ROLES = ("Reference Image 1 defines the young man — his exact face, hair, stubble, grey hoodie — and his bedroom, "
         "the purple and cyan LED light and the mixed lighting. Reference Image 2 defines the exact ONDA X headset design: "
         "do not redesign, simplify or alter it in any way, keep the purple-to-cyan RGB rings and the ONDA X wordmark. ")
PRESERVE = ("Preserve: the same person, same face and identity, same hoodie, same skin texture with visible pores and slight "
            "asymmetry, same bedroom and LED light. Match: same phone-camera look, same colour and direction of light. "
            "The result should look like the next frame of the same TikTok video. Natural skin, nothing airbrushed, "
            "no plastic skin, no beauty filter, no CGI. No text anywhere except the ONDA X wordmark on the product and box, "
            "no subtitles, no watermark, no readable screen interface. ")
MIC = "a small square matte black wireless microphone transmitter, no logo"
RAMAS = {
 "p0": (f"Change: he now holds a premium matte black retail box of the ONDA X headset in his right hand, raised at chest height "
        f"towards the camera, the box shows a photo of the headset and the wordmark \"ONDA X\" in bold white letters, spelled exactly. "
        f"In his left hand, near his chin, he still holds {MIC}. He looks into the lens with a knowing half smile. ", ["base", "producto"], "9:16"),
 "p2": (f"Change: he is now sitting at his desk facing the camera placed on top of his gaming monitor, webcam style, the screen glow "
        f"lighting his face; he holds the ONDA X headset with both hands just above his head, about to put it on; {MIC} is clipped "
        f"to the collar of his hoodie. ", ["base", "producto"], "9:16"),
 "p3": (f"Change: webcam-style shot from the top of his monitor: he wears the ONDA X headset with its RGB rings glowing purple and cyan, "
        f"holds a black game controller with both hands, leaning slightly forward, focused, his eyes on the screen just below the lens, "
        f"cool flickering screen light on his face; {MIC} clipped to his hoodie collar. ", ["base", "producto"], "9:16"),
 "p4": (f"Change: close-up from the top of the monitor: he wears the ONDA X headset glowing, head turned sharply to his left as if he just "
        f"heard something, eyes wide and intense, gripping the controller, the screen light on his face. ", ["base", "producto"], "9:16"),
 "p6": (f"Change: he is back in the original framing, facing the camera, the ONDA X headset now resting around his neck with the RGB rings "
        f"glowing, holding {MIC} near his chin in his left hand, confident relaxed smile. ", ["base", "producto"], "9:16"),
 "p5": ("Change: vertical 9:16 frame, the same ONDA X headset floating centred in the upper middle of a pure black background, "
        "three-quarter view, RGB rings glowing purple to cyan, dramatic rim light, a faint reflection below. Do not redesign or alter the "
        "headset in any way. No text except the small ONDA X wordmark on the headband. ", ["producto"], "9:16"),
}
SUELTAS = {"base": (CHICO, [], "9:16"), "producto": (PRODUCTO, [], "1:1")}


def run(nombre):
    if nombre in SUELTAS:
        prompt, refs, aspecto = SUELTAS[nombre]
    else:
        prompt, refs, aspecto = RAMAS[nombre]
        if len(refs) == 2:
            prompt = ROLES + prompt + PRESERVE
        else:
            prompt = "Reference Image 1 defines the exact ONDA X headset. " + prompt
    cmd = G + [prompt, "--modelo", "sunburst", "--aspecto", aspecto, "--out", f"{I}/{nombre}.png"]
    if refs:
        cmd += ["--ref"] + [f"{I}/{x}.png" for x in refs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return f"{nombre}: {'ok' if r.returncode == 0 else r.stderr[-400:]}"


if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        for linea in ex.map(run, sys.argv[1:]):
            print(linea, flush=True)
