"""GÉLIDA · paso 2: 6 clips de omni (cara y voz), 5 insertos de seedance, la música y los efectos.
Frases que acaban en el segundo 7 (la sincronía de labios de omni aguanta ~6-7 s) y 3 s de reacción callada.

    python ejemplos/gelida/2_clips.py
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

I, V, A = "ejemplos/gelida/img", "ejemplos/gelida/vid", "ejemplos/gelida/audio"
G = [sys.executable, "-m", "kit.generar"]
VOZ = ("Voice: a Spanish woman about 30, warm medium-low voice, relaxed and wry, natural and unpolished, "
       "slightly husky.")
AC = ("She speaks in Spanish from Spain, natural Madrid accent (castellano peninsular, not Latin American), "
      "informal and conversational, like a real creator talking to her phone.")
MIRADA = "Her eyes stay mostly on the phone screen just below the lens, flicking up to the lens on key words; understated, not presenter-like."
FIN = ("Consider micro-detail, expression and timing to create a very rich, detailed but entirely natural scene. "
       "No subtitles, no captions, no on-screen text. In a single continuous shot, no scene cuts.")
SELFIE = "(handheld selfie at arm's length, slight natural sway) realistic arm movements and subtle micro-movements. "
OMNI = {
 "o01": ("b01", SELFIE + '[0-1s] She shakes the bottle twice right next to the lens; the ice rattles loudly inside. '
         '[1-6s] She whispers, sleepy and amused: "Son las tres de la mañana... y esto sigue sonando a hielo." '
         '[6-10s] No dialogue; she shakes it once more near her ear and smiles.',
         "Ambient noise: a silent bedroom at night, a faint fridge hum from the hallway, the ice rattling inside the steel bottle. No music."),
 "o03": ("b03", SELFIE + '[0-1s] She snaps the flip lid shut with a click. [1-6s] She says: "Ocho de la mañana. '
         'Hielo hasta arriba. A ver cuánto aguanta." [6-10s] No dialogue; she glances off-camera toward the window and '
         'back, small smile.',
         "Ambient noise: a small kitchen in the morning, a moka pot gurgling faintly, a fridge hum, the street outside the window. No music."),
 "o04": ("b04", "(walking selfie, phone at arm's length, natural walking bounce) realistic arm movements and subtle "
         'micro-movements. [0-1s] Walking, she lifts the bottle to her ear. [1-4s] She shakes it and says: "Mediodía. '
         'Escuchad." [4-10s] No dialogue; she keeps walking, shakes it again near the lens so the ice rattles, and raises '
         'her eyebrows.',
         "Ambient noise: a narrow Madrid street at midday, a scooter in the distance, her footsteps, a far-away neighbour's voice, the ice rattling. No music."),
 "o06": ("b06", SELFIE + '[0-2s] She fans her face with her hand; the parked car is baking hot. [2-6s] She says: "Esto es '
         'un horno... y mira." and shakes the bottle next to the lens; the ice rattles. [6-10s] No dialogue; she laughs softly.',
         "Ambient noise: inside a closed parked car in the sun, the muffled street outside, the ice rattling. No music."),
 "o08": ("b08", SELFIE + '[0-1s] She lifts the glass full of whole ice cubes toward the lens and swirls it so the cubes '
         'clink. [1-5s] She says: "Siete de la tarde. Cubitos enteros." [5-10s] No dialogue; she sets the glass down on '
         'the table without drinking and smiles.',
         "Ambient noise: a Spanish bar terrace at dusk, murmured conversations that cannot be understood, cutlery, a scooter passing, ice clinking. No music."),
 "o11": ("b11", "(static camera fixed on the ceiling looking straight down, locked off) realistic arm movements and "
         'subtle micro-movements. [0-1s] She shakes the bottle on her chest; the ice rattles. [1-7s] She says softly, '
         'smiling up at the camera: "Diecinueve horas. Se llama Gélida. Enlace en el perfil." [7-10s] No dialogue; she '
         'hugs the bottle and closes her eyes, smiling.',
         "Ambient noise: a quiet bedroom at night, the ice rattling. No music."),
}
SEED = {
 "s02": ("f02", 4, True, "Top-down: the hands tip the ice-cube tray and several big ice cubes drop one after another into "
         "the bottle's mouth. Smooth natural motion."),
 "s05": ("f05", 4, True, "Locked-off phone shot: harsh afternoon sun on the bottle in the cupholder, heat shimmer rising "
         "from the dashboard, a slow lens flare drifts across the windscreen; nothing else moves."),
 "s07": ("f07", 4, True, "Over-the-shoulder: the hand tilts the bottle and whole ice cubes with cold water tumble out into "
         "the glass, the cubes clinking and bobbing; the pour lasts two seconds and the hand sets the bottle upright."),
 "s09": ("f09", 4, False, "Low tracking shot from behind at waist height: the person walks along the empty metro platform, "
         "the bottle swinging gently on the backpack strap; a train's headlights glow at the far end of the tunnel."),
 "s10": ("f10", 4, True, "Macro, locked off: a single condensation droplet runs down the glass while the bottle beside it "
         "stays completely dry; the warm lamp light flickers softly; very slow push-in."),
}
MUSICA = ("Warm lo-fi house, 112 BPM, soft four-on-the-floor kick, mellow Rhodes chords, subtle vinyl crackle, relaxed "
          "daytime city vibe, instrumental")
SFX = {
 "hielo": (2, "ice cubes rattling inside an insulated stainless steel bottle being shaken, close-up, crisp"),
 "hielo2": (2, "shaking a metal water bottle full of ice, two quick shakes, rattling"),
 "tapa": (1, "a plastic flip lid snapping shut on a water bottle, single click"),
 "cubitos": (3, "big ice cubes dropping one by one into a stainless steel bottle, clunk"),
 "servir": (3, "pouring cold water with ice cubes into a glass, ice clinking"),
 "metro": (4, "metro train arriving in a tiled underground station, distant rumble and brakes, echo"),
 "aire": (1, "soft short air swish transition, subtle"),
}

def run(cmd, nombre):
    r = subprocess.run(G + cmd, capture_output=True, text=True)
    return f"{nombre}: {'ok' if r.returncode == 0 else r.stderr[-300:]}"

if __name__ == "__main__":
    t = []
    for n, (img, accion, amb) in OMNI.items():
        t.append((["video", f"{accion} {MIRADA} {VOZ} {AC} {amb} {FIN}", "--imagen", f"{I}/{img}.png",
                   "--res", "360p", "--out", f"{V}/{n}.mp4"], n))
    for n, (img, dur, fija, prompt) in SEED.items():
        t.append((["video", prompt, "--modelo", "seedance", "--imagen", f"{I}/{img}.png", "--res", "480p",
                   "--dur", str(dur), "--out", f"{V}/{n}.mp4"] + (["--camara-fija"] if fija else []), n))
    t.append((["musica", MUSICA, "--out", f"{A}/musica.wav"], "musica"))
    for n, (dur, prompt) in SFX.items():
        t.append((["sonido", prompt, "--dur", str(dur), "--out", f"{A}/sfx-{n}.wav"], n))
    with ThreadPoolExecutor(5) as ex:        # de 5 en 5: con poco saldo Replicate limita la ráfaga
        for linea in ex.map(lambda x: run(*x), t):
            print(linea, flush=True)
