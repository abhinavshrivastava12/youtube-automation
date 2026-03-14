"""
music_gen.py — Pure Python background music generator
=======================================================
No API needed. Generates WAV music using numpy sine waves.
- Piano/Xylophone loop for kids rhymes
- Soft guitar/pad feel for lullabies & songs
"""

import numpy as np
import wave, struct, math, os, random

SAMPLE_RATE = 44100

# ── Note frequencies ─────────────────────────────────────────────────────────
NOTES = {
    "C3":130.81,"D3":146.83,"E3":164.81,"F3":174.61,"G3":196.00,"A3":220.00,"B3":246.94,
    "C4":261.63,"D4":293.66,"E4":329.63,"F4":349.23,"G4":392.00,"A4":440.00,"B4":493.88,
    "C5":523.25,"D5":587.33,"E5":659.25,"F5":698.46,"G5":783.99,"A5":880.00,"B5":987.77,
    "C6":1046.50,
}

# ── Kids rhyme melody (C major, happy, xylophone feel) ────────────────────────
KIDS_MELODY = [
    ("C5",0.5),("E5",0.5),("G5",0.5),("E5",0.5),
    ("D5",0.5),("F5",0.5),("A5",0.5),("F5",0.5),
    ("C5",0.5),("G4",0.5),("E5",0.25),("D5",0.25),("C5",1.0),
    ("G4",0.5),("A4",0.5),("B4",0.5),("C5",0.5),
    ("D5",0.5),("C5",0.5),("B4",0.5),("G4",0.5),
    ("C5",0.5),("E5",0.5),("G5",0.5),("C5",1.0),
]

KIDS_BASS = [
    ("C3",1.0),("G3",1.0),("F3",1.0),("C3",1.0),
    ("G3",1.0),("C3",1.0),("F3",1.0),("G3",1.0),
]

# ── Lullaby melody (C major, slow, soft) ──────────────────────────────────────
LULLABY_MELODY = [
    ("E5",1.0),("D5",0.5),("C5",0.5),("D5",1.0),
    ("E5",1.0),("E5",0.5),("E5",1.0),
    ("D5",1.0),("D5",0.5),("D5",1.0),
    ("E5",0.5),("G5",0.5),("G5",1.5),
    ("E5",1.0),("D5",0.5),("C5",0.5),("D5",1.0),
    ("E5",1.0),("E5",0.5),("E5",0.5),
    ("D5",1.0),("D5",0.5),("E5",0.5),("D5",0.5),("C5",2.0),
]

LULLABY_BASS = [
    ("C3",2.0),("G3",2.0),("F3",2.0),("G3",2.0),
    ("C3",2.0),("F3",2.0),("G3",2.0),("C3",2.0),
]

# ── Wave generators ───────────────────────────────────────────────────────────

def sine_wave(freq, duration, sr=SAMPLE_RATE, amplitude=0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)

def piano_wave(freq, duration, sr=SAMPLE_RATE, amplitude=0.4):
    """Piano-like: fundamental + harmonics + fast decay"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (
        amplitude * np.sin(2 * np.pi * freq * t) +
        amplitude * 0.5 * np.sin(2 * np.pi * freq * 2 * t) +
        amplitude * 0.25 * np.sin(2 * np.pi * freq * 3 * t) +
        amplitude * 0.12 * np.sin(2 * np.pi * freq * 4 * t)
    )
    # Exponential decay (piano note dies quickly)
    decay = np.exp(-3.5 * t / duration)
    return wave * decay

def xylophone_wave(freq, duration, sr=SAMPLE_RATE, amplitude=0.45):
    """Xylophone: bright harmonics, very fast decay"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (
        amplitude * np.sin(2 * np.pi * freq * t) +
        amplitude * 0.6 * np.sin(2 * np.pi * freq * 2.756 * t) +
        amplitude * 0.3 * np.sin(2 * np.pi * freq * 5.404 * t)
    )
    decay = np.exp(-6.0 * t / duration)
    return wave * decay

def soft_pad_wave(freq, duration, sr=SAMPLE_RATE, amplitude=0.2):
    """Soft pad/guitar feel: slow attack, long sustain"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (
        amplitude * np.sin(2 * np.pi * freq * t) +
        amplitude * 0.3 * np.sin(2 * np.pi * freq * 2 * t) +
        amplitude * 0.15 * np.sin(2 * np.pi * freq * 3 * t)
    )
    # Slow attack + gentle decay
    attack = np.minimum(t / 0.1, 1.0)
    decay = np.exp(-0.8 * t / max(duration, 0.1))
    return wave * attack * decay

def bass_wave(freq, duration, sr=SAMPLE_RATE, amplitude=0.25):
    """Warm bass"""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = (
        amplitude * np.sin(2 * np.pi * freq * t) +
        amplitude * 0.4 * np.sin(2 * np.pi * freq * 2 * t)
    )
    decay = np.exp(-1.5 * t / max(duration, 0.1))
    return wave * decay

def add_reverb(audio, sr=SAMPLE_RATE, delay=0.08, decay=0.3):
    """Simple reverb effect"""
    delay_samples = int(delay * sr)
    result = audio.copy()
    if len(audio) > delay_samples:
        result[delay_samples:] += decay * audio[:-delay_samples]
    return result

# ── Melody renderer ───────────────────────────────────────────────────────────

def render_melody(melody, bass_pattern, style="kids", target_duration=30.0, volume=0.55):
    """
    Render melody + bass into a numpy audio array.
    Loops until target_duration is reached.
    style: "kids" = xylophone, "lullaby" = soft pad
    """
    sr = SAMPLE_RATE

    # Build one loop of melody
    melody_samples = []
    for note_name, duration in melody:
        freq = NOTES.get(note_name, 440)
        if style == "kids":
            s = xylophone_wave(freq, duration, sr)
        else:
            s = soft_pad_wave(freq, duration, sr, amplitude=0.22)
        melody_samples.append(s)

    melody_audio = np.concatenate(melody_samples) if melody_samples else np.zeros(sr)

    # Build one loop of bass
    bass_samples = []
    for note_name, duration in bass_pattern:
        freq = NOTES.get(note_name, 130)
        s = bass_wave(freq, duration, sr)
        bass_samples.append(s)

    bass_audio = np.concatenate(bass_samples) if bass_samples else np.zeros(sr)

    # Build full-length audio by looping
    target_samples = int(target_duration * sr)

    def loop_to(arr, length):
        if len(arr) == 0:
            return np.zeros(length)
        repeats = math.ceil(length / len(arr))
        looped = np.tile(arr, repeats)
        return looped[:length]

    melody_full = loop_to(melody_audio, target_samples)
    bass_full   = loop_to(bass_audio,   target_samples)

    # Mix
    combined = melody_full + bass_full

    # Add light reverb for warmth
    combined = add_reverb(combined, sr)

    # Add gentle fade in / fade out
    fade_in  = int(sr * 1.5)
    fade_out = int(sr * 2.0)
    if fade_in < len(combined):
        combined[:fade_in] *= np.linspace(0, 1, fade_in)
    if fade_out < len(combined):
        combined[-fade_out:] *= np.linspace(1, 0, fade_out)

    # Normalize
    peak = np.max(np.abs(combined))
    if peak > 0:
        combined = combined / peak * volume

    return combined.astype(np.float32)

# ── Public API ────────────────────────────────────────────────────────────────

def generate_music(style: str, duration: float, output_path: str):
    """
    Generate background music WAV file.

    style:
      "kids"    — xylophone piano loop, bright C major
      "lullaby" — soft pad, slow, gentle
      "song"    — alias for lullaby
      "poem"    — alias for lullaby

    duration: seconds
    output_path: .wav file path
    """
    style = style.lower()
    if style in ("lullaby", "song", "poem"):
        melody  = LULLABY_MELODY
        bass    = LULLABY_BASS
        vol     = 0.35
        stype   = "lullaby"
    else:
        melody  = KIDS_MELODY
        bass    = KIDS_BASS
        vol     = 0.45
        stype   = "kids"

    audio = render_melody(melody, bass, style=stype,
                           target_duration=duration + 2.0, volume=vol)

    # Save as WAV
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        pcm = (audio * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())

    return output_path


def mix_voice_and_music(voice_mp3: str, music_wav: str,
                         output_path: str, ffmpeg: str = "ffmpeg",
                         music_volume: float = 0.28):
    """
    Mix TTS voice with background music using ffmpeg.
    music_volume: 0.0 = silent, 1.0 = equal volume
    """
    import subprocess
    cmd = [
        ffmpeg,
        "-i", voice_mp3,
        "-i", music_wav,
        "-filter_complex",
        f"[0:a]volume=1.0[v];[1:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
        output_path, "-y", "-loglevel", "quiet"
    ]
    subprocess.run(cmd, check=True)
    return output_path