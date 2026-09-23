"""GÉLIDA · paso 1: la chica, la botella y las ramas de cada plano (sunburst `low`).

    python ejemplos/gelida/1_imagenes.py base producto      # primero estas dos
    python ejemplos/gelida/1_imagenes.py                     # después, todas las ramas
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

I = "ejemplos/gelida/img"
G = [sys.executable, "-m", "kit.generar", "imagen"]

PIEL = ("Natural skin texture with visible pores, light freckles, slight facial asymmetry, flyaway hairs, real knit "
        "texture, nothing airbrushed. The goal is for this to look like a candid frame from a real creator's phone, "
        "not an AI render. Do not smooth the skin artificially. No plastic skin, no beauty filter, no CGI, no 3D render. "
        "No text anywhere except the GÉLIDA wordmark on the bottle, no watermark, no readable signs or screens.")
MOVIL = ("Shot on an iPhone front camera at arm's length, 23mm wide, iPhone HDR look, slightly off-center framing, "
         "top of her head slightly cropped, her forearm visible at the frame edge; her eyes on the phone screen just "
         "below the lens.")
ELLA = ("a Spanish woman about 30, shoulder-length wavy chestnut hair held up in a claw clip with loose strands, light "
        "freckles, no makeup, a small silver hoop in her left ear only, wearing a cream chunky knit sweater")
ROLES = ("Reference Image 1 defines the woman — her exact face, freckles, hair, claw clip, left-ear hoop, cream knit "
         "sweater. Reference Image 2 defines the exact GÉLIDA bottle: do not redesign, recolour or alter it in any way. "
         "Same bone structure, same eye spacing; do not beautify into a different person. Ignore the white bottle in "
         "Reference Image 1: the only bottle in the scene is the sage-green GÉLIDA from Reference Image 2. "
         "Change only what is described. ")
BOTELLA_REF = "Reference Image 1 defines the exact GÉLIDA bottle: do not redesign, recolour or alter it in any way. "
PRODUCTO_TXT = ("Studio product photo of an original insulated stainless steel water bottle, 750 ml, matte sage green "
                "powder-coat finish, brushed steel rim, a flip lid with a carry loop, and a small debossed wordmark reading "
                "exactly \"GÉLIDA\" on the body, spelled letter for letter with the accent. Three-quarter view, soft "
                "daylight, plain light grey background, realistic materials, sharp detail. No other text, no watermark.")

IMGS = {
 "base": (f"Photorealistic vertical photo. {MOVIL} {ELLA}. She is in a small Spanish shared-flat kitchen in the "
          "morning: white wall tiles, a gotelé wall, a window with a half-raised slatted blind, a moka pot on the "
          "stove, keys, a banana and some mail on the counter. Soft window light, relaxed half smile, mid-sentence. " + PIEL,
          [], "imagen"),
 "producto": (PRODUCTO_TXT, [], "sunburst"),
 # — planos con cara (omni) —
 "b01": (ROLES + "Change: 3 a.m., a dark bedroom; she sits up in bed under a duvet, her face lit only by the cold "
         "glow of her phone screen from below, holding the GÉLIDA bottle close to the lens; sleepy amused expression; "
         "high-ISO phone grain, deep shadows. " + MOVIL + " " + PIEL, ["base", "producto"], "sunburst"),
 "b03": (ROLES + "Change: same kitchen, morning window light; she holds the GÉLIDA bottle up near her face with one "
         "hand, the lid open, looking at the phone screen. " + MOVIL + " " + PIEL, ["base", "producto"], "sunburst"),
 "b04": (ROLES + "Change: she walks along a narrow Madrid street with wrought-iron balconies and hanging plants at "
         "midday, bright sun and hard shadows, holding the GÉLIDA bottle up next to her ear. " + MOVIL + " " + PIEL,
         ["base", "producto"], "sunburst"),
 "b06": (ROLES + "Change: she sits in the driver's seat of a small parked car in strong afternoon sun, sunlight "
         "flaring through the windscreen, slightly sweaty forehead, fanning herself with her free hand, the GÉLIDA "
         "bottle in her lap. " + MOVIL + " " + PIEL, ["base", "producto"], "sunburst"),
 "b08": (ROLES + "Change: a Spanish bar terrace at golden hour: an aluminium table with a paper-napkin holder, the "
         "GÉLIDA bottle on the table and a glass of water full of whole ice cubes in her hand, the street blurred behind "
         "her. " + MOVIL + " " + PIEL, ["base", "producto"], "sunburst"),
 "b11": (ROLES + "Change: overhead shot from directly above, as if the phone were fixed to the ceiling: at night she "
         "lies on her back in bed on white rumpled sheets, the GÉLIDA bottle resting on her chest in both hands, a warm "
         "dim bedside lamp, she looks up at the camera with a sleepy smile; no handheld tilt. " + PIEL,
         ["base", "producto"], "sunburst"),
 # — insertos sin cara (seedance) —
 "f02": (BOTELLA_REF + "Top-down overhead phone photo looking straight down at a white-tiled kitchen counter in morning "
         "light: the GÉLIDA bottle open, and two hands in cream knit sleeves holding a plastic ice-cube tray just above "
         "its mouth, the first big ice cube about to fall. Real, slightly messy counter. No text except GÉLIDA.",
         ["producto"], "sunburst"),
 "f05": (BOTELLA_REF + "Phone photo of the GÉLIDA bottle standing in the cupholder of a small parked car, harsh afternoon "
         "sun pouring through the windscreen, dusty dashboard, heat haze, lens flare. No text except GÉLIDA, no readable "
         "car display.", ["producto"], "sunburst"),
 "f07": (BOTELLA_REF + "Over-the-shoulder phone photo at a Spanish bar terrace at golden hour: a hand in a cream knit "
         "sleeve tilts the GÉLIDA bottle over an empty glass on an aluminium table, a paper-napkin holder beside it, the "
         "first whole ice cube sliding out of the bottle mouth. No text except GÉLIDA.", ["producto"], "sunburst"),
 "f09": (BOTELLA_REF + "Low phone shot at waist height from behind on an empty Madrid metro platform at night, white "
         "tiled walls, the GÉLIDA bottle clipped by its loop to the strap of a canvas backpack, the person out of frame "
         "above. No readable signs, no text except GÉLIDA.", ["producto"], "sunburst"),
 "f10": (BOTELLA_REF + "Macro phone photo on a terrazo floor next to a bed at night, warm lamp light: the GÉLIDA bottle, "
         "completely dry on the outside, beside a glass of iced water covered in condensation droplets. Shallow depth of "
         "field. No text except GÉLIDA.", ["producto"], "sunburst"),
}

def run(nombre):
    prompt, refs, modelo = IMGS[nombre]
    cmd = G + [prompt, "--modelo", modelo, "--aspecto", "9:16", "--out", f"{I}/{nombre}.png"]
    if refs:
        cmd += ["--ref"] + [f"{I}/{r}.png" for r in refs]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return f"{nombre}: {'ok' if r.returncode == 0 else r.stderr[-300:]}"

if __name__ == "__main__":
    nombres = sys.argv[1:] or [n for n in IMGS if n not in ("base", "producto")]
    with ThreadPoolExecutor(6) as ex:
        for l in ex.map(run, nombres):
            print(l, flush=True)
