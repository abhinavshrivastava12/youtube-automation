"""
app.py — Kids Hindi Rhymes & Songs YouTube Shorts
===================================================
Channel Focus:
  • Kids Hindi Rhymes  (Machli Jal Ki Rani, Lakdi Ki Kathi...)
  • Slow Hindi Songs   (AI voice cover, short clips)
  • Hindi Kavita / Poems
  • Lullabies

Voice: edge-tts hi-IN-SwaraNeural (best free Hindi female voice)
Animation: Karaoke-style — lyrics highlight hote hain line by line
Video: 1080x1920 Shorts format
"""

import os, json, asyncio, subprocess, shutil, threading, uuid, time, math
import random, re, wave
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import requests as req_lib

load_dotenv()
app  = Flask(__name__)
CORS(app)

W      = 1080
H      = 1920
FPS    = 30
FFMPEG  = shutil.which("ffmpeg")  or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

jobs = {}

# ── AI Keys ──────────────────────────────────────────────────────────────────
GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Voice Config ─────────────────────────────────────────────────────────────
# SwaraNeural = best natural Hindi female (kids + songs)
# MadhurNeural = male Hindi
VOICES = {
    "swara":  "hi-IN-SwaraNeural",    # default — sweet female, perfect for rhymes
    "madhur": "hi-IN-MadhurNeural",   # male
    "neerja": "en-IN-NeerjaNeural",   # English Indian female
}

# ── Built-in Rhymes DB ───────────────────────────────────────────────────────
BUILTIN_RHYMES = {
    "machli": {
        "title": "Machli Jal Ki Rani Hai 🐟",
        "type": "rhyme",
        "lines": [
            "मछली जल की रानी है",
            "जीवन उसका पानी है",
            "हाथ लगाओ डर जाएगी",
            "बाहर निकालो मर जाएगी",
        ],
        "emoji": "🐟",
        "bg": "ocean",
    },
    "lakdi": {
        "title": "Lakdi Ki Kathi 🐴",
        "type": "rhyme",
        "lines": [
            "लकड़ी की काठी",
            "काठी पे घोड़ा",
            "घोड़े की दुम पे",
            "जो मारा हथौड़ा",
            "दौड़ा दौड़ा दौड़ा घोड़ा",
            "दुम उठाके दौड़ा",
        ],
        "emoji": "🐴",
        "bg": "rainbow",
    },
    "chanda": {
        "title": "Chanda Mama 🌙",
        "type": "rhyme",
        "lines": [
            "चंदा मामा दूर के",
            "पुए पकाएं बूर के",
            "आप खाएं थाली में",
            "मुन्ने को दें प्याली में",
            "प्याली गई टूट",
            "मुन्ना गया रूठ",
        ],
        "emoji": "🌙",
        "bg": "night_sky",
    },
    "johny": {
        "title": "Johny Johny Yes Papa 👶",
        "type": "rhyme",
        "lines": [
            "जॉनी जॉनी हाँ पापा",
            "चीनी खाना? नहीं पापा",
            "सच बोलना? हाँ पापा",
            "मुँह खोलो? हा हा हा",
        ],
        "emoji": "👶",
        "bg": "pastel",
    },
    "twinkle": {
        "title": "Twinkle Twinkle ⭐",
        "type": "rhyme",
        "lines": [
            "टिमटिम करते तारे हैं",
            "जैसे हीरे प्यारे हैं",
            "ऊँचे नीले आसमान में",
            "चमकते दिन और रात में",
        ],
        "emoji": "⭐",
        "bg": "night_sky",
    },
    "nani": {
        "title": "Nani Teri Morni 🦚",
        "type": "lullaby",
        "lines": [
            "नानी तेरी मोरनी को मोर ले गए",
            "बाकी जो बचा था काले चोर ले गए",
            "सो जा सो जा सो जा मेरे राजा",
            "सो जा नींद आई है",
        ],
        "emoji": "🦚",
        "bg": "dreamy",
    },
    "aayi_diwali": {
        "title": "Aayi Diwali ✨",
        "type": "rhyme",
        "lines": [
            "आई दिवाली आई दिवाली",
            "संग में लाई खुशियाँ निराली",
            "जलाओ दीपक करो उजाला",
            "मीठा खाओ मनाओ मेला",
        ],
        "emoji": "🪔",
        "bg": "festive",
    },
    "billi": {
        "title": "Billi Mausi 🐱",
        "type": "rhyme",
        "lines": [
            "बिल्ली मौसी बिल्ली मौसी",
            "क्या खाओगी खाना",
            "दूध और रोटी लाऊँ",
            "या मछली मँगवाना",
            "म्याऊँ म्याऊँ म्याऊँ",
        ],
        "emoji": "🐱",
        "bg": "pastel",
    },
}

BUILTIN_SONGS = {
    "lori": {
        "title": "Lori — Chanda Hai Tu ✨",
        "type": "lullaby",
        "lines": [
            "चंदा है तू मेरा सूरज है तू",
            "ओ मेरी आँखों का तारा है तू",
            "शाम सवेरे तुझे मैं देखूँ",
            "मेरे प्यारे मेरे राजदुलारे",
            "सो जा सो जा सो जा",
        ],
        "emoji": "🌙",
        "bg": "night_sky",
    },
    "hawa": {
        "title": "Hawa Hawa 🌬️",
        "type": "poem",
        "lines": [
            "हवा हवा ए हवा खुशबू लुटा दे",
            "ठंडी ठंडी हवा मन को भा गई",
            "पेड़ों के पत्ते झूमते हैं",
            "बच्चे भी खुशी से गाते हैं",
        ],
        "emoji": "🌬️",
        "bg": "nature",
    },
}

# ── Font loader ───────────────────────────────────────────────────────────────
_font_cache = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache: return _font_cache[key]
    candidates = [
        ("C:/Windows/Fonts/NirmalaB.ttf", True),
        ("C:/Windows/Fonts/Nirmala.ttf",  False),
        ("C:/Windows/Fonts/mangal.ttf",   False),
        ("C:/Windows/Fonts/arialbd.ttf",  True),
        ("C:/Windows/Fonts/arial.ttf",    False),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", True),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      False),
        ("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",  True),
        ("/usr/share/fonts/truetype/freefont/FreeSans.ttf",      False),
    ]
    for path, is_bold in candidates:
        if bold and not is_bold: continue
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except: pass
    for path, _ in candidates:
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except: pass
    return ImageFont.load_default()

# ── Color helpers ─────────────────────────────────────────────────────────────
def lerp_col(c1, c2, t):
    if isinstance(c1, str): c1 = tuple(int(c1.lstrip('#')[i:i+2],16) for i in (0,2,4))
    if isinstance(c2, str): c2 = tuple(int(c2.lstrip('#')[i:i+2],16) for i in (0,2,4))
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

def ease_out_back(t, s=1.70158):
    t = max(0,min(1,t))
    return 1 + (s+1)*(t-1)**3 + s*(t-1)**2

# ══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND THEMES
# ══════════════════════════════════════════════════════════════════════════════

BG_THEMES = {
    "ocean": {
        "top": "#0077b6", "bottom": "#00b4d8",
        "circles": [(100,200,255),(50,150,220),(150,230,255)],
        "emojis": ["🐟","🐠","🌊","🐚","⭐"],
    },
    "rainbow": {
        "top": "#ff6b6b", "bottom": "#ffd93d",
        "circles": [(255,150,100),(255,200,80),(200,255,150)],
        "emojis": ["🌈","⭐","✨","🦋","🌸"],
    },
    "night_sky": {
        "top": "#03045e", "bottom": "#023e8a",
        "circles": [(100,100,200),(150,120,220),(200,180,255)],
        "emojis": ["🌙","⭐","✨","🌟","💫"],
    },
    "pastel": {
        "top": "#ffb3c6", "bottom": "#c8b6ff",
        "circles": [(255,180,200),(200,180,255),(180,230,255)],
        "emojis": ["🌸","💝","🌷","🦋","✨"],
    },
    "dreamy": {
        "top": "#7b2d8b", "bottom": "#c77dff",
        "circles": [(180,100,220),(200,150,255),(255,200,255)],
        "emojis": ["🌙","💫","✨","🌟","🦋"],
    },
    "festive": {
        "top": "#ff4800", "bottom": "#ffd000",
        "circles": [(255,120,50),(255,200,50),(255,150,100)],
        "emojis": ["🪔","✨","🎆","⭐","🌟"],
    },
    "nature": {
        "top": "#2d6a4f", "bottom": "#74c69d",
        "circles": [(80,200,120),(120,220,160),(200,255,200)],
        "emojis": ["🌿","🌸","🦋","🌼","☀️"],
    },
    "default": {
        "top": "#f72585", "bottom": "#7209b7",
        "circles": [(255,150,200),(200,100,255),(255,200,255)],
        "emojis": ["⭐","✨","🌈","💫","🌸"],
    },
}

def draw_bg(d, theme_key, t):
    theme = BG_THEMES.get(theme_key, BG_THEMES["default"])
    # Gradient
    for y in range(H):
        yf = y/H
        wave = math.sin(yf*math.pi*3 + t*0.8) * 0.05
        col = lerp_col(theme["top"], theme["bottom"], max(0,min(1,yf+wave)))
        d.line([(0,y),(W,y)], fill=col)
    # Floating bokeh circles
    rng = random.Random(42)
    for i in range(16):
        cr   = rng.randint(50,180)
        sx   = rng.uniform(0,W)
        sy   = rng.uniform(0,H)
        spd  = rng.uniform(30,90)
        ph   = rng.random()*10
        col  = rng.choice(theme["circles"])
        cx   = int((sx + math.sin(t*0.3+ph)*70) % W)
        cy   = int((sy - t*spd + ph*300) % H)
        for r in range(cr,0,-18):
            fc = lerp_col(col,(255,255,255), 1-r/cr)
            fc = tuple(min(255,c) for c in fc)
            d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=fc)

def draw_floating_emojis(d, t, emojis):
    fnt = get_font(88)
    rng = random.Random(77)
    for i in range(7):
        em = emojis[i % len(emojis)]
        sx = rng.uniform(0.05, 0.92)*W
        sy = rng.uniform(0,H)
        sp = rng.uniform(40,110)
        ph = rng.random()*10
        sw = math.sin(t*rng.uniform(0.4,1.2)+ph)*70
        ex = int((sx+sw) % W)
        ey = int((sy - t*sp + ph*280) % H)
        try: d.text((ex,ey), em, font=fnt)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTER — Cute Bunny (kids channel mascot)
# ══════════════════════════════════════════════════════════════════════════════

def draw_bunny(d, cx, cy, t, small=False):
    s = 0.75 if small else 1.0
    bounce = int(abs(math.sin(t*3.5)) * 28)
    cy = cy - bounce

    # Shadow
    d.ellipse([cx-int(85*s), cy+int(115*s), cx+int(85*s), cy+int(135*s)], fill=(0,0,0))

    # Body
    d.ellipse([cx-int(75*s), cy-int(95*s), cx+int(75*s), cy+int(30*s)], fill=(255,235,225))
    d.ellipse([cx-int(38*s), cy-int(60*s), cx+int(38*s), cy+int(18*s)],  fill=(255,210,210))

    # Head
    hr = int(65*s)
    hx,hy = cx, cy-int(95*s)-hr+int(18*s)
    d.ellipse([hx-hr,hy-hr,hx+hr,hy+hr], fill=(255,235,225))

    # Ears
    for xo,tilt in [(-int(24*s),-6),(int(24*s),6)]:
        d.polygon([(hx+xo+tilt,hy-hr),(hx+xo-int(16*s),hy-hr-int(85*s)),(hx+xo+int(16*s),hy-hr-int(85*s))],
                  fill=(255,235,225))
        d.polygon([(hx+xo+tilt,hy-hr-int(4*s)),(hx+xo-int(8*s),hy-hr-int(74*s)),(hx+xo+int(8*s),hy-hr-int(74*s))],
                  fill=(255,170,185))

    # Eyes
    blink = abs(math.sin(t*0.65)) > 0.95
    for xo in [-int(22*s), int(22*s)]:
        ex2,ey2 = hx+xo, hy-int(12*s)
        if blink:
            d.arc([ex2-int(12*s),ey2-int(4*s),ex2+int(12*s),ey2+int(4*s)], 195,345, fill=(60,30,20),width=4)
        else:
            d.ellipse([ex2-int(12*s),ey2-int(12*s),ex2+int(12*s),ey2+int(12*s)], fill=(45,22,12))
            d.ellipse([ex2-int(5*s),ey2-int(10*s),ex2+int(2*s),ey2-int(3*s)], fill=(255,255,255))

    # Nose + smile
    d.ellipse([hx-int(7*s),hy+int(4*s),hx+int(7*s),hy+int(15*s)], fill=(255,120,150))
    sy2 = int(math.sin(t*2)*3)
    d.arc([hx-int(19*s),hy+int(10*s)+sy2,hx+int(19*s),hy+int(36*s)+sy2], 10,170, fill=(200,80,100),width=int(4*s))

    # Cheeks
    for xo in [-int(38*s), int(38*s)]:
        d.ellipse([hx+xo-int(17*s),hy+int(6*s),hx+xo+int(17*s),hy+int(22*s)], fill=(255,160,160))

    # Arms wave
    aw = math.sin(t*3)*28
    d.line([cx-int(68*s),cy-int(32*s), cx-int(110*s),cy-int(52*s)-int(aw)], fill=(255,235,225),width=int(24*s))
    d.line([cx+int(68*s),cy-int(32*s), cx+int(110*s),cy-int(52*s)+int(aw)], fill=(255,235,225),width=int(24*s))

    # Legs
    lk = int(math.sin(t*3.5)*12)
    for xo in [-int(30*s), int(30*s)]:
        d.ellipse([cx+xo-int(22*s),cy+int(12*s)+lk, cx+xo+int(22*s),cy+int(48*s)+lk], fill=(255,235,225))

    # Tail
    d.ellipse([cx+int(60*s),cy-int(18*s), cx+int(95*s),cy+int(17*s)], fill=(255,255,255))

# ══════════════════════════════════════════════════════════════════════════════
#  KARAOKE TEXT RENDERER
# ══════════════════════════════════════════════════════════════════════════════

def wrap_text(text, fnt, d, max_w):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur+[w])
        try:
            bb = d.textbbox((0,0), test, font=fnt)
            tw = bb[2]-bb[0]
        except:
            tw = len(test)*30
        if tw > max_w and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(" ".join(cur))
    return lines

def draw_karaoke_line(d, text, y_center, active, progress, theme_key):
    """
    active=True  → current line being sung → large, bright, highlighted
    active=False → other lines             → smaller, dimmed
    progress     → 0→1 how much of current line has been sung (for word highlight)
    """
    theme = BG_THEMES.get(theme_key, BG_THEMES["default"])

    if active:
        fnt_size = 88
        text_col = (255, 255, 255)
        shadow_col = (0, 0, 0)
        pill_col = lerp_col(theme["top"], (255,255,255), 0.15)
        pill_col = tuple(min(255,c) for c in pill_col)
        glow = True
        scale = ease_out_back(min(1.0, progress*4)) if progress < 0.25 else 1.0
        fnt_size = int(fnt_size * scale)
    else:
        fnt_size = 58
        text_col = (220, 220, 220)
        shadow_col = (0,0,0)
        pill_col = None
        glow = False

    fnt = get_font(fnt_size, bold=True)
    max_w = W - 120
    lines = wrap_text(text, fnt, d, max_w)

    line_h = fnt_size + 20
    total_h = len(lines)*line_h
    base_y = y_center - total_h//2

    for li, line in enumerate(lines):
        try:
            bb = d.textbbox((0,0), line, font=fnt)
            lw = bb[2]-bb[0]
            lh = bb[3]-bb[1]
        except:
            lw = len(line)*fnt_size*0.55
            lh = fnt_size

        bx = (W-lw)//2
        by = base_y + li*line_h

        if pill_col:
            pad = 28
            d.rounded_rectangle([bx-pad, by-10, bx+lw+pad, by+lh+10],
                                 radius=22, fill=pill_col)

        if glow:
            # Glow outline
            for dx,dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
                d.text((bx+dx, by+dy), line, fill=shadow_col, font=fnt)
        else:
            d.text((bx+2, by+2), line, fill=shadow_col, font=fnt)

        d.text((bx, by), line, fill=text_col, font=fnt)


def render_karaoke_frame(lines_data, current_line_idx, fi, total_frames,
                          theme_key, t, overall_progress, title=""):
    """
    lines_data = [{"text": "...", "start": 0.0, "end": 2.5}, ...]
    current_line_idx = which line is currently active
    """
    img = Image.new("RGB",(W,H),(20,20,40))
    d   = ImageDraw.Draw(img)

    # 1. Background
    draw_bg(d, theme_key, t)

    # 2. Floating emojis
    theme = BG_THEMES.get(theme_key, BG_THEMES["default"])
    draw_floating_emojis(d, t, theme["emojis"])

    # 3. Title at top
    if title:
        tfnt = get_font(55, bold=True)
        try:
            tbb = d.textbbox((0,0), title, font=tfnt)
            tw  = tbb[2]-tbb[0]
            tx  = (W-tw)//2
        except:
            tx = 60
        ty = 70
        d.rounded_rectangle([tx-20,ty-10,tx+int(tw if isinstance(tw,int) else 400)+20,ty+60],
                             radius=15, fill=(0,0,0))
        d.text((tx,ty), title, fill=(255,220,100), font=tfnt)

    # 4. Bunny character — left side, smaller
    draw_bunny(d, int(W*0.22), int(H*0.42), t, small=True)

    # 5. Karaoke lines
    # Show: previous line (dim), active line (bright big), next line (dim)
    # Layout in middle-bottom area
    slots = []
    if current_line_idx > 0:
        slots.append((current_line_idx-1, False, 0))
    slots.append((current_line_idx, True,
                  (t - lines_data[current_line_idx]["start"]) /
                  max(0.1, lines_data[current_line_idx]["end"] - lines_data[current_line_idx]["start"])))
    if current_line_idx < len(lines_data)-1:
        slots.append((current_line_idx+1, False, 0))

    # Positions
    y_positions = [int(H*0.58), int(H*0.72), int(H*0.85)]
    if len(slots) == 2:
        y_positions = [int(H*0.65), int(H*0.80)]
    if len(slots) == 1:
        y_positions = [int(H*0.72)]

    for (li_idx, is_active, prog), ypos in zip(slots, y_positions):
        if 0 <= li_idx < len(lines_data):
            draw_karaoke_line(d, lines_data[li_idx]["text"], ypos,
                              is_active, prog, theme_key)

    # 6. Progress bar
    bar_h = 14
    d.rectangle([0,H-bar_h,W,H], fill=(30,30,30))
    for x in range(int(W*overall_progress)):
        col = lerp_col((255,120,180),(255,200,80), x/W)
        d.line([(x,H-bar_h),(x,H)], fill=col)

    return img

# ══════════════════════════════════════════════════════════════════════════════
#  TTS — edge-tts with timing
# ══════════════════════════════════════════════════════════════════════════════

import edge_tts

async def tts_with_timing(text, audio_path, voice="hi-IN-SwaraNeural"):
    """Generate speech AND get word-level timing via SSML"""
    comm = edge_tts.Communicate(text, voice)
    await comm.save(audio_path)

async def tts_line(text, path, voice="hi-IN-SwaraNeural", rate="-8%", pitch="+0Hz"):
    """Single line TTS with optional rate/pitch for song feel"""
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await comm.save(path)

def get_audio_duration(path):
    try:
        r = subprocess.run(
            [FFPROBE,"-v","quiet","-print_format","json","-show_streams",path],
            capture_output=True, text=True)
        data = json.loads(r.stdout)
        for s in data.get("streams",[]):
            if "duration" in s:
                return float(s["duration"])
    except: pass
    return 3.0

# ══════════════════════════════════════════════════════════════════════════════
#  AI SCRIPT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def call_groq(prompt, system=""):
    if not GROQ_KEY: return None
    try:
        r = req_lib.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[
                {"role":"system","content":system},
                {"role":"user","content":prompt}
            ],"temperature":0.8,"max_tokens":1000},
            timeout=30
        )
        return r.json()["choices"][0]["message"]["content"]
    except: return None

def call_gemini(prompt):
    if not GEMINI_KEY: return None
    try:
        r = req_lib.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents":[{"parts":[{"text":prompt}]}]},
            timeout=30
        )
        cands = r.json().get("candidates",[])
        if cands: return cands[0]["content"]["parts"][0]["text"]
    except: pass
    return None

def generate_rhyme_script(topic, content_type="rhyme"):
    """Generate a new Hindi rhyme/song/poem using AI"""
    type_map = {
        "rhyme":   "बच्चों की मज़ेदार हिंदी कविता/राइम (4-8 lines, simple, catchy, rhyming)",
        "lullaby": "एक सुंदर हिंदी लोरी (6-10 lines, slow, soothing, for babies)",
        "poem":    "एक भावपूर्ण हिंदी कविता (6-10 lines, poetic, beautiful)",
        "song":    "एक slow Hindi song के lyrics (6-10 lines, melodious, emotional)",
    }
    style = type_map.get(content_type, type_map["rhyme"])

    system = f"""तुम एक प्रसिद्ध हिंदी बाल-साहित्यकार हो।
तुम्हें {style} लिखनी है।
Rules:
- हर line अलग रखो
- Simple Hindi words use करो
- Rhyming होनी चाहिए
- JSON format में return करो:
{{"title": "...", "lines": ["line1", "line2", ...], "emoji": "🌟", "bg": "pastel"}}
bg options: ocean, rainbow, night_sky, pastel, dreamy, festive, nature
JSON के अलावा कुछ मत लिखो।"""

    prompt = f"Topic: {topic}\nType: {style}\n\nJSON likhو:"

    raw = call_groq(prompt, system) or call_gemini(prompt)
    if not raw:
        return None

    # Parse JSON
    try:
        raw = raw.strip()
        if "```" in raw:
            raw = re.sub(r"```[a-z]*", "", raw).replace("```","").strip()
        data = json.loads(raw)
        if "lines" in data and isinstance(data["lines"], list):
            return data
    except:
        # Try to extract lines manually
        lines = [l.strip() for l in raw.split("\n") if l.strip() and not l.strip().startswith("{")]
        if lines:
            return {"title": topic, "lines": lines[:10], "emoji":"⭐","bg":"pastel"}
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO BUILDER — LINE BY LINE KARAOKE
# ══════════════════════════════════════════════════════════════════════════════

def build_karaoke_video(content, job_id,
                        voice="swara", content_type="rhyme", channel_name=""):
    """
    content = {title, lines, emoji, bg}
    Builds a Shorts video with karaoke-style line highlights.
    """
    work = f"C:/tmp/kids_{job_id}" if os.name=='nt' else f"/tmp/kids_{job_id}"
    os.makedirs(f"{work}/audio", exist_ok=True)
    os.makedirs(f"{work}/frames", exist_ok=True)

    voice_name = VOICES.get(voice, VOICES["swara"])
    theme_key  = content.get("bg", "pastel")
    lines_text = content.get("lines", [])
    title      = content.get("title", "")

    # ── Rate/pitch per content type ──────────────────────────────────────────
    tts_rate  = "-12%" if content_type in ("lullaby","song") else "-5%"
    tts_pitch = "+2Hz" if content_type == "rhyme" else "-2Hz"

    # ── Step 1: Generate audio for each line ─────────────────────────────────
    jobs[job_id]["message"] = "Voice generate ho rahi hai... 🎵"
    line_audio_paths = []
    line_durations   = []

    for i, line in enumerate(lines_text):
        jobs[job_id]["progress"] = 10 + i*30//max(len(lines_text),1)
        ap = f"{work}/audio/line_{i:02d}.mp3"
        asyncio.run(tts_line(line, ap, voice=voice_name, rate=tts_rate, pitch=tts_pitch))
        dur = get_audio_duration(ap) + 0.4   # 0.4s pause between lines
        line_audio_paths.append(ap)
        line_durations.append(dur)

    # ── Step 2: Build timing data ─────────────────────────────────────────────
    lines_data = []
    cursor = 0.5   # 0.5s intro before first line
    for i, (txt, dur) in enumerate(zip(lines_text, line_durations)):
        lines_data.append({"text": txt, "start": cursor, "end": cursor+dur-0.2})
        cursor += dur
    total_duration = cursor + 0.5   # 0.5s outro

    # ── Step 3: Concatenate audio ─────────────────────────────────────────────
    jobs[job_id]["message"] = "Audio combine ho raha hai... 🎧"
    combined_audio = f"{work}/audio/combined.mp3"

    # Build silence clips + concat
    silence_path = f"{work}/audio/silence.mp3"
    subprocess.run([
        FFMPEG, "-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
        "-t","0.5","-q:a","9","-acodec","libmp3lame",
        silence_path,"-y","-loglevel","quiet"
    ])

    concat_list = f"{work}/audio/concat.txt"
    with open(concat_list,"w") as f:
        f.write(f"file '{os.path.abspath(silence_path)}'\n")
        for ap in line_audio_paths:
            f.write(f"file '{os.path.abspath(ap)}'\n")
        f.write(f"file '{os.path.abspath(silence_path)}'\n")

    subprocess.run([
        FFMPEG,"-f","concat","-safe","0","-i",concat_list,
        "-acodec","libmp3lame","-q:a","2",
        combined_audio,"-y","-loglevel","quiet"
    ])

    # ── Step 4: Render frames ─────────────────────────────────────────────────
    jobs[job_id]["message"] = "Frames render ho rahe hain... 🎨"
    total_frames = int(total_duration * FPS)
    frame_dir    = f"{work}/frames"

    for fi in range(total_frames):
        jobs[job_id]["progress"] = 40 + fi*45//max(total_frames,1)
        t        = fi / FPS
        overall  = fi / max(total_frames,1)

        # Find current active line
        current_idx = 0
        for li, ld in enumerate(lines_data):
            if t >= ld["start"]:
                current_idx = li

        img = render_karaoke_frame(
            lines_data, current_idx, fi, total_frames,
            theme_key, t, overall, title
        )
        img.save(f"{frame_dir}/f{fi:05d}.png")

    # ── Step 5: Combine video + audio ─────────────────────────────────────────
    jobs[job_id]["message"] = "Video ban raha hai... 🎬"
    out_dir  = ("C:/tmp/kids_outputs" if os.name=='nt' else "/tmp/kids_outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/{job_id}.mp4"

    subprocess.run([
        FFMPEG,
        "-framerate", str(FPS),
        "-i", f"{frame_dir}/f%05d.png",
        "-i", combined_audio,
        "-c:v","libx264","-preset","fast","-crf","20",
        "-vf","scale=1080:1920",
        "-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k",
        "-shortest",
        out_path,"-y","-loglevel","quiet"
    ], check=True)

    shutil.rmtree(work)
    return out_path

# ══════════════════════════════════════════════════════════════════════════════
#  JOB WORKER
# ══════════════════════════════════════════════════════════════════════════════

def run_job(job_id, params):
    job = jobs[job_id]
    job["status"]   = "running"
    job["progress"] = 5
    try:
        content_type = params.get("content_type","rhyme")
        topic        = params.get("topic","")
        builtin_key  = params.get("builtin_key","")
        voice        = params.get("voice","swara")
        channel_name = params.get("channel_name","@KidsHindiRhymes")
        custom_lines = params.get("custom_lines",[])

        # Get content
        if builtin_key and builtin_key in BUILTIN_RHYMES:
            content = BUILTIN_RHYMES[builtin_key]
        elif builtin_key and builtin_key in BUILTIN_SONGS:
            content = BUILTIN_SONGS[builtin_key]
        elif custom_lines:
            content = {
                "title": topic or "Meri Kavita",
                "lines": custom_lines,
                "emoji": "⭐",
                "bg":    params.get("bg","pastel"),
            }
        elif topic:
            job["message"] = "AI se rhyme likh raha hoon... ✍️"
            content = generate_rhyme_script(topic, content_type)
            if not content:
                job["status"]  = "failed"
                job["message"] = "AI script generate nahi ho pai. Dobara try karo."
                return
        else:
            job["status"]  = "failed"
            job["message"] = "Topic ya builtin_key dena zaroori hai."
            return

        job["content"] = content
        video_path = build_karaoke_video(
            content, job_id, voice=voice,
            content_type=content_type, channel_name=channel_name
        )

        job["status"]     = "done"
        job["progress"]   = 100
        job["message"]    = "Video ready hai! 🎉"
        job["video_path"] = video_path

    except Exception as e:
        import traceback
        job["status"]  = "failed"
        job["message"] = f"Error: {str(e)}"
        job["error"]   = traceback.format_exc()

# ══════════════════════════════════════════════════════════════════════════════
#  FLASK API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "voices": list(VOICES.keys()),
        "builtin_rhymes": list(BUILTIN_RHYMES.keys()),
        "builtin_songs": list(BUILTIN_SONGS.keys()),
        "ai": {"groq": bool(GROQ_KEY), "gemini": bool(GEMINI_KEY)},
    })

@app.route("/api/builtins")
def builtins():
    rhymes = {k:{"title":v["title"],"type":v["type"],"emoji":v["emoji"]}
              for k,v in BUILTIN_RHYMES.items()}
    songs  = {k:{"title":v["title"],"type":v["type"],"emoji":v["emoji"]}
              for k,v in BUILTIN_SONGS.items()}
    return jsonify({"rhymes": rhymes, "songs": songs})

@app.route("/api/generate", methods=["POST"])
def generate():
    """
    POST body:
    {
      "content_type": "rhyme" | "lullaby" | "poem" | "song",
      "topic":        "Hathi raja kahan chale",   ← AI se banwao
      "builtin_key":  "machli",                    ← ya builtin use karo
      "custom_lines": ["line1","line2",...],        ← ya apni lines do
      "bg":           "ocean",
      "voice":        "swara",
      "channel_name": "@MyChannel"
    }
    """
    data = request.json or {}
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id, "status":"queued",
        "progress":0, "message":"Queue mein hai...",
        "created": datetime.now().isoformat()
    }
    threading.Thread(target=run_job, args=(job_id, data), daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({"error":"Not found"}),404
    resp = {k:v for k,v in job.items() if k not in ("video_path","error")}
    if job.get("status")=="done":
        resp["download_url"] = f"/api/download/{job_id}"
    if job.get("content"):
        resp["content"] = job["content"]
    return jsonify(resp)

@app.route("/api/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status")!="done":
        return jsonify({"error":"Not ready"}),404
    vp = job.get("video_path")
    if not vp or not os.path.exists(vp):
        return jsonify({"error":"File missing"}),404
    title = (job.get("content",{}).get("title","video") or "video")
    title = re.sub(r"[^\w\s-]","",title).strip().replace(" ","_")[:40]
    return send_file(vp, as_attachment=True, download_name=f"{title}.mp4")

@app.route("/api/history")
def history():
    all_jobs = sorted(jobs.values(), key=lambda j: j.get("created",""), reverse=True)
    return jsonify(all_jobs[:30])

if __name__ == "__main__":
    print("=" * 55)
    print("  🐰 Kids Hindi Rhymes & Songs Channel Backend")
    print("  Voice: hi-IN-SwaraNeural (best free Hindi)")
    print("  Animation: Karaoke-style line highlight")
    print("  Server: http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)