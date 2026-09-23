"""ONDA X · paso 3: 7 clips de omni (cara y voz), 6 de seedance (juego, manos, producto y el 3D), la
música y los efectos, todo en paralelo (≈2,90 USD a 360p). Python y no shell: el diálogo lleva comillas, tildes y signos de apertura.

    python ejemplos/onda-x/3_clips.py             # desde la raíz del kit
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

I, V, A = "ejemplos/onda-x/img", "ejemplos/onda-x/vid", "ejemplos/onda-x/audio"
G = [sys.executable, "-m", "kit.generar"]
VOZ = ("Voice: a young Spanish male voice, about 22, medium pitch, energetic but relaxed, casual gamer tone, "
       "a smile in the voice.")
AC = ("He speaks in Spanish from Spain, natural Madrid accent (castellano peninsular, not Latin American), "
      "informal and conversational, like a real TikTok creator.")
SALA = "Ambient noise: quiet bedroom room tone, faint computer fan hum. No music."
FIN = ("Consider micro-detail, expression and timing to create a very rich, detailed but entirely natural scene. "
       "No subtitles, no captions, no on-screen text. In a single continuous shot, no scene cuts.")
WEBCAM = "(static camera on top of the monitor, webcam style, locked off) realistic arm movements and subtle micro-movements. "
SELFIE = "(handheld selfie camera, slight natural sway) realistic arm movements and subtle micro-movements. "
OMNI = {
 "o1": ("w0", WEBCAM + '[0-2s] He plays with the controller, focused. [2-3s] He suddenly freezes, eyes wide: he just got '
        'killed in the game. [3-6s] He throws his hands up in disbelief and says: "¿Pero de dónde me han dado?" '
        '[6-10s] He shakes his head, annoyed, and lets out a short laugh.', 
        "Ambient noise: quiet bedroom, faint muffled game gunfire from the monitor speakers. No music."),
 "o2": ("base", SELFIE + '[0-1s] He brings the small microphone up to his chin, half laughing. [1-6s] He looks into the '
        'lens and says: "Tranquilo, no es lag. Es que no les oyes venir." [6-10s] He raises his eyebrows knowingly and nods.', SALA),
 "o3": ("p2", WEBCAM + '[0-3s] He puts the ONDA X headset on with both hands and the RGB rings light up brighter. '
        '[3-8s] He looks into the lens and says: "Sonido trescientos sesenta. Oyes cada paso... y sabes de dónde viene." '
        '[8-10s] He smiles and grabs the controller.', SALA),
 "o4": ("p3", WEBCAM + '[0-1s] He plays, focused. [1-5s] His eyes flick to the left and he whispers, intense: '
        '"Está subiendo por la escalera..." [5-10s] He leans in, jaw tight, thumbs moving fast.', SALA),
 "o5": ("p4", WEBCAM + '[0-2s] Head turned to his left, then he snaps back to the screen. [2-6s] Thumbs hammering the '
        'buttons, he mutters under his breath: "Uno... dos..." [6-10s] Total focus, then a tiny satisfied smile.', SALA),
 "o6": ("p3", WEBCAM + '[0-2s] He leans back in the chair laughing and lifts one ear cup off his ear. [2-6s] He looks at '
        'the lens and says: "Uno contra tres. Ni me han visto." [6-10s] He shrugs with a cocky grin.', SALA),
 "o7": ("p6", SELFIE + '[0-1s] He brings the microphone up to his chin. [1-8s] He looks into the lens and says with a '
        'cocky smile: "Onda Equis. Enlace en el perfil. Y si te vuelven a matar... ya no será por los cascos." '
        '[8-10s] He winks and taps the headset around his neck.', SALA),
}
JUEGO = " Video game footage, fast responsive game camera, no HUD, no text, no user interface."
SEED = {
 "s1": ("g1", 5, False, "First-person view in the video game: the player walks forward down the corridor holding the "
        "rifle, then gets shot from behind: the screen shakes violently, flashes red and the view tilts and drops." + JUEGO),
 "s2": ("g2", 5, False, "First-person view: the player turns left toward the metal stairs, raises the rifle and fires two "
        "quick energy shots with bright purple muzzle flashes; the robot on the stairs is hit, sparks fly and it collapses "
        "down the steps." + JUEGO),
 "s3": ("g1", 4, False, "First-person view: a fast turn to the right, the player fires a burst at a combat robot, bright "
        "muzzle flashes, sparks and metal debris burst, the robot falls." + JUEGO),
 "s4": ("u1", 4, True, "Top-down view: the hands lift the lid off the box and pull the ONDA X headset out of the foam; "
        "the RGB rings flicker on. Smooth natural motion. No text changes."),
 "c5": ("p5", 6, True, "The ONDA X headset slowly rotates in mid-air, then its parts gently separate into a floating "
        "exploded view — ear cups, cushions, drivers and headband drift apart — and smoothly snap back together; the RGB "
        "rings pulse from purple to cyan; tiny glowing particles drift around it; pure black background, studio rim "
        "light, glossy reflection below. One continuous shot, no cuts, smooth natural acceleration. No text."),
 "s5": ("m1", 4, True, "Macro product shot: the RGB light ring slowly powers on, glowing from purple to cyan, and a soft "
        "light sweep crosses the ear cup. Smooth premium product commercial. No text."),
}
MUSICA = ("Dark aggressive phonk trap beat for a gaming ad, 140 BPM, heavy distorted 808 bass, cowbell melody, crisp "
          "hi-hats, punchy kick, tense and energetic, strong drop, instrumental")
SFX = {
 "whoosh": (1, "fast clean cinematic whoosh transition swish, short"),
 "golpe": (2, "deep cinematic sub bass impact boom hit, trailer, powerful and short"),
 "disparo": (1, "sci-fi energy rifle shot, punchy futuristic laser gun blast, video game weapon"),
 "pasos": (4, "heavy metallic robot footsteps walking down metal stairs, clanking steps, video game"),
 "encendido": (2, "futuristic headset power on sound, sleek sci-fi activation, soft rising tone"),
 "impacto": (2, "robot hit by energy blast, electric sparks, metal crunch, small explosion, video game"),
 "rafaga": (2, "sci-fi energy rifle rapid burst fire, three quick laser shots, video game"),
}

def run(cmd, nombre):
    r = subprocess.run(G + cmd, capture_output=True, text=True)
    return f"{nombre}: {'ok' if r.returncode == 0 else r.stderr[-300:]}"

if __name__ == "__main__":
    trabajos = []
    for n, (img, accion, amb) in OMNI.items():
        trabajos.append((["video", f"{accion} {VOZ} {AC} {amb} {FIN}", "--imagen", f"{I}/{img}.png",
                          "--res", "360p", "--out", f"{V}/{n}.mp4"], n))
    for n, (img, dur, fija, prompt) in SEED.items():
        trabajos.append((["video", prompt, "--modelo", "seedance", "--imagen", f"{I}/{img}.png", "--res", "480p",
                          "--dur", str(dur), "--out", f"{V}/{n}.mp4"] + (["--camara-fija"] if fija else []), n))
    trabajos.append((["musica", MUSICA, "--out", f"{A}/musica.wav"], "musica"))
    for n, (dur, prompt) in SFX.items():
        trabajos.append((["sonido", prompt, "--dur", str(dur), "--out", f"{A}/sfx-{n}.wav"], n))
    with ThreadPoolExecutor(len(trabajos)) as ex:
        for linea in ex.map(lambda t: run(*t), trabajos):
            print(linea, flush=True)
