"""
app.py — Kids Hindi Rhymes v7
==============================
FIXES v7:
  - bg_key and song_key are now SEPARATE (no more conflict)
  - Hindi lyrics → Hinglish transliteration in karaoke
  - 5 new Lofi background themes (lofi_blue, lofi_purple, lofi_pink, lofi_green, lofi_warm)
  - Lofi content type supported
"""

import os, json, asyncio, subprocess, shutil, threading, uuid, re, math, random
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import requests as req_lib

# Import our transliteration module (same folder)
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from hindi_transliterate import hindi_to_hinglish
except ImportError:
    def hindi_to_hinglish(text): return text  # fallback: no-op

_here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_here, ".env"))

app = Flask(__name__)
CORS(app, origins="*")

W, H    = 1080, 1920
FPS     = 30
FFMPEG  = shutil.which("ffmpeg")  or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

SONGS_DIR    = os.path.join(_here, "songs")
MAPPING_FILE = os.path.join(_here, "song_mapping.json")
os.makedirs(SONGS_DIR, exist_ok=True)

jobs = {}
GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Font loader ───────────────────────────────────────────────────────────────
_fc = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _fc: return _fc[key]
    candidates = (
        ["C:/Windows/Fonts/NirmalaB.ttf","C:/Windows/Fonts/mangalb.ttf",
         "C:/Windows/Fonts/arialbd.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
         "/usr/share/fonts/opentype/unifont/unifont.otf"]
        if bold else
        ["C:/Windows/Fonts/Nirmala.ttf","C:/Windows/Fonts/mangal.ttf",
         "C:/Windows/Fonts/arial.ttf",
         "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
         "/usr/share/fonts/opentype/unifont/unifont.otf"]
    )
    for p in candidates:
        try:
            f = ImageFont.truetype(p, size); _fc[key]=f; return f
        except: pass
    _fc[key] = ImageFont.load_default()
    return _fc[key]

# ── Color helpers ─────────────────────────────────────────────────────────────
def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def lerp_col(c1, c2, t):
    if isinstance(c1,str): c1=hex_rgb(c1)
    if isinstance(c2,str): c2=hex_rgb(c2)
    t=max(0.0,min(1.0,t))
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

# ── Song mapping ──────────────────────────────────────────────────────────────
FNAME_KW = {
    "billi":"billi","mausi":"billi","machli":"machli","jal":"machli",
    "chanda":"chanda","mama":"chanda","lakdi":"lakdi","kathi":"lakdi",
    "johny":"johny","twinkle":"twinkle","tare":"twinkle",
    "hathi":"hathi","raja":"hathi","nani":"nani","morni":"nani","lori":"lori",
    "school":"school","chalo":"school","lofi":"lofi",
}

def auto_key(fname):
    s = re.sub(r"[_\-\.]"," ",fname.lower().replace(".mp3",""))
    for kw,key in FNAME_KW.items():
        if kw in s: return key
    return None

def load_mapping():
    m = {}
    try:
        if os.path.exists(MAPPING_FILE):
            with open(MAPPING_FILE) as f: m = json.load(f)
    except: pass
    try:
        for f in os.listdir(SONGS_DIR):
            if not f.endswith(".mp3"): continue
            k = auto_key(f)
            if k and k not in m: m[k]=f; print(f"[Map] Auto: {k}->{f}")
    except: pass
    return m

def save_mapping(m):
    try:
        with open(MAPPING_FILE,"w") as f: json.dump(m,f,indent=2)
    except: pass

_MAP = load_mapping()

def find_song(text):
    text = re.sub(r"[^\w\s]"," ",(text or "").lower()).strip()
    try: all_mp3=[f for f in os.listdir(SONGS_DIR) if f.endswith(".mp3")]
    except: all_mp3=[]
    print(f"[Song] search='{text}' | files={all_mp3}")
    for kw,fname in _MAP.items():
        if kw in text.split():
            fp=os.path.join(SONGS_DIR,fname)
            if os.path.exists(fp): return fp
    for kw,fname in _MAP.items():
        if kw in text:
            fp=os.path.join(SONGS_DIR,fname)
            if os.path.exists(fp): return fp
    for fname in all_mp3:
        fw=re.sub(r"[_\-\.]"," ",fname.lower().replace(".mp3",""))
        for w in text.split():
            if len(w)>=4 and w in fw: return os.path.join(SONGS_DIR,fname)
    if all_mp3: return os.path.join(SONGS_DIR,sorted(all_mp3)[0])
    return None

def get_duration(path):
    try:
        r=subprocess.run([FFPROBE,"-v","quiet","-print_format","json",
                          "-show_streams",path],capture_output=True,text=True)
        for s in json.loads(r.stdout).get("streams",[]):
            if "duration" in s: return float(s["duration"])
    except: pass
    return 30.0

# ── Story / Theme configs ─────────────────────────────────────────────────────
# bg_key now directly maps to visual config — fully independent of song
CONFIGS = {
    # Classic themes
    "billi":       {"char":"cat",      "bg":("#ff9a9e","#fecfef"), "accent":"#dc2060", "style":"bright"},
    "machli":      {"char":"fish",     "bg":("#0096c7","#caf0f8"), "accent":"#0077a8", "style":"bright"},
    "hathi":       {"char":"elephant", "bg":("#52b788","#b7e4c7"), "accent":"#2d6a4f", "style":"bright"},
    "chanda":      {"char":"moon",     "bg":("#03045e","#023e8a"), "accent":"#4895ef", "style":"dark"},
    "tara":        {"char":"star",     "bg":("#10002b","#3c096c"), "accent":"#9d4edd", "style":"dark"},
    "twinkle":     {"char":"star",     "bg":("#10002b","#3c096c"), "accent":"#9d4edd", "style":"dark"},
    "lakdi":       {"char":"horse",    "bg":("#ff6b35","#ffd166"), "accent":"#e05000", "style":"bright"},
    "johny":       {"char":"kid",      "bg":("#ff99c8","#fcf6bd"), "accent":"#e0006a", "style":"bright"},
    "nani":        {"char":"peacock",  "bg":("#2d6a4f","#74c69d"), "accent":"#1b4332", "style":"bright"},
    "lori":        {"char":"moon",     "bg":("#1a1a2e","#16213e"), "accent":"#e2b714", "style":"dark"},
    # Lofi themes — new!
    "lofi_blue":   {"char":"kid",      "bg":("#1a2a4a","#2d4a7a"), "accent":"#4a9eff", "style":"lofi"},
    "lofi_purple": {"char":"kid",      "bg":("#2d1b4e","#4a2d7a"), "accent":"#c084fc", "style":"lofi"},
    "lofi_pink":   {"char":"kid",      "bg":("#3d1a2e","#6b2d5e"), "accent":"#f472b6", "style":"lofi"},
    "lofi_green":  {"char":"kid",      "bg":("#0d2b2b","#1a4a4a"), "accent":"#34d399", "style":"lofi"},
    "lofi_warm":   {"char":"kid",      "bg":("#2b1a0d","#4a3520"), "accent":"#fb923c", "style":"lofi"},
    # Fallback for old "school" key
    "school":      {"char":"kid",      "bg":("#1a2a4a","#2d4a7a"), "accent":"#4a9eff", "style":"lofi"},
    "lofi":        {"char":"kid",      "bg":("#1a2a4a","#2d4a7a"), "accent":"#4a9eff", "style":"lofi"},
    "default":     {"char":"kid",      "bg":("#f72585","#7209b7"), "accent":"#b5179e", "style":"bright"},
}

def get_config_by_bg_key(bg_key):
    """Get visual config from bg_key (theme) — independent of song."""
    if bg_key and bg_key in CONFIGS:
        return CONFIGS[bg_key]
    return CONFIGS["default"]

def get_config(text):
    """Legacy: detect config from text keywords."""
    text=(text or "").lower()
    for k,cfg in CONFIGS.items():
        if k in text and k!="default": return cfg
    return CONFIGS["default"]

# ═══════════════════════════════════════════════════════════════════════════════
#  ANIMATION DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def draw_bg(d, col1, col2, t):
    for y in range(H):
        yf=y/H
        wave=math.sin(yf*math.pi*4+t*0.6)*0.025
        col=lerp_col(col1,col2,max(0,min(1,yf+wave)))
        d.line([(0,y),(W,y)],fill=col)

def draw_bokeh(d, accent_rgb, t):
    rng=random.Random(42)
    light=tuple(min(255,c+90) for c in accent_rgb)
    for i in range(10):
        r=rng.randint(15,55); sx=rng.uniform(0.05,0.95)*W; sy=rng.uniform(0.05,0.52)*H
        ph=rng.random()*10
        cx2=int((sx+math.sin(t*0.4+ph)*50)%W)
        cy2=int((sy-t*35+ph*180)%(H*0.52))
        d.ellipse([cx2-r,cy2-r,cx2+r,cy2+r],fill=light)

def draw_stars_bg(d, t):
    rng = random.Random(99)
    # Background faint stars
    for _ in range(220):
        sx  = rng.randint(0, W)
        sy  = rng.randint(0, int(H * 0.60))
        fl  = 0.3 + 0.7 * abs(math.sin(t * rng.uniform(0.8, 4.5) + rng.random() * 6.28))
        br  = int(140 * fl + 90)
        sr  = rng.choice([1, 1, 1, 2, 2, 3])
        d.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(br, br, min(255, br+25)))
    # Bright twinkle stars (4 stars with cross-sparkle)
    rng2 = random.Random(42)
    for _ in range(4):
        sx  = rng2.randint(60, W-60)
        sy  = rng2.randint(40, int(H * 0.48))
        spd = rng2.uniform(1.2, 2.6)
        ph  = rng2.random() * 6.28
        fl  = abs(math.sin(t * spd + ph))
        if fl < 0.3: continue
        size = int(4 + fl * 6)
        br2 = min(255, int(180 + fl * 75))
        col = (br2, br2, min(255, br2 + 20))
        d.ellipse([sx-size, sy-size, sx+size, sy+size], fill=col)
        # cross arms
        arm = int(size * 2.5)
        d.line([(sx-arm, sy), (sx+arm, sy)], fill=col, width=max(1, size//3))
        d.line([(sx, sy-arm), (sx, sy+arm)], fill=col, width=max(1, size//3))
    # Occasional shooting star
    ss_cycle = 9.0
    ss_t = t % ss_cycle
    if 0.0 < ss_t < 1.4:
        rng3 = random.Random(int(t / ss_cycle))
        ss_sx = rng3.randint(200, W-100)
        ss_sy = rng3.randint(30, int(H * 0.30))
        prog  = ss_t / 1.4
        trail = 280
        ex  = ss_sx + int(trail * prog)
        ey  = ss_sy + int(trail * prog * 0.45)
        bri = int(255 * (1.0 - prog))
        for seg_i in range(8):
            seg_p = (seg_i / 8.0)
            seg_x = ss_sx + int(trail * seg_p * prog)
            seg_y = ss_sy + int(trail * seg_p * prog * 0.45)
            seg_b = int(bri * (1.0 - seg_p * 0.6))
            d.ellipse([seg_x-2, seg_y-2, seg_x+2, seg_y+2],
                       fill=(seg_b, seg_b, min(255, seg_b+30)))

def draw_lofi_bg(d, col1, col2, accent_rgb, t):
    """Lofi aesthetic: city window + rain streaks + glow dots"""
    draw_bg(d, col1, col2, t)

    # Distant city silhouette
    rng = random.Random(77)
    city_y = int(H * 0.72)
    for i in range(18):
        bw = rng.randint(40, 90)
        bh = rng.randint(80, 240)
        bx = i * 62 - 10
        dark = tuple(max(0, c - 30) for c in hex_rgb(col1 if isinstance(col1,str) else "#1a2a4a"))
        d.rectangle([bx, city_y - bh, bx + bw, city_y], fill=dark)
        # Windows
        for wy in range(city_y - bh + 12, city_y - 10, 22):
            for wx in range(bx + 6, bx + bw - 4, 18):
                if rng.random() > 0.45:
                    win_col = tuple(min(255, c + 60) for c in accent_rgb)
                    d.rectangle([wx, wy, wx+8, wy+10], fill=win_col)

    # Rain streaks (subtle)
    rng2 = random.Random(int(t * 8) % 1000)
    for _ in range(22):
        rx = rng2.randint(0, W)
        ry = rng2.randint(0, H)
        rl = rng2.randint(15, 45)
        rain_col = tuple(min(255, c + 40) for c in accent_rgb) + (60,)
        d.line([(rx, ry), (rx - 4, ry + rl)],
               fill=tuple(min(255, c + 40) for c in accent_rgb), width=1)

    # Soft glow circles (window reflection feel)
    for i in range(4):
        gx = int(W * (0.2 + i * 0.2))
        gy = int(H * 0.35 + math.sin(t * 0.5 + i) * 30)
        gr = 35 + i * 10
        d.ellipse([gx-gr, gy-gr, gx+gr, gy+gr], fill=accent_rgb)

def draw_cat(d, cx, cy, t):
    phase = (t % 8)
    # Smoother motion: blend between phases
    if phase < 2:
        bounce = int(abs(math.sin(t * 3.2)) * 36)
        swing  = int(math.sin(t * 1.6) * 12)
    elif phase < 4:
        bounce = int(abs(math.sin(t * 2.1)) * 22)
        swing  = int(math.sin(t * 2.1) * 38)
    elif phase < 6:
        bounce = int(abs(math.sin(t * 5.8)) * 28)
        swing  = int(math.sin(t * 4.8) * 22)
    else:
        bounce = int(abs(math.sin(t * 3.0)) * 28)
        swing  = int(math.sin(t * 3.0) * 48)
    cy -= bounce; cx += swing

    bc  = (255, 140, 50)
    bel = (255, 200, 150)
    ec  = (220, 90, 25)
    ie  = (255, 170, 185)

    # Shadow ellipse
    d.ellipse([cx-105, cy+165, cx+105, cy+195], fill=(200, 80, 100))

    # Curved tail (Bezier-like approximation with 24 segments)
    px, py = None, None
    for i in range(24):
        ang  = i / 24 * math.pi + t * 1.3
        tx2  = cx + 120 + int(62 * math.sin(ang))
        ty2  = cy + 55  - i * 10
        if px is not None:
            d.line([(px, py), (tx2, ty2)], fill=bc, width=28)
        px, py = tx2, ty2
    if px is not None:
        d.ellipse([px-16, py-16, px+16, py+16], fill=(255, 175, 75))

    # Body
    d.ellipse([cx-112, cy-145, cx+112, cy+75],  fill=bc)
    d.ellipse([cx-60,  cy-95,  cx+60,  cy+52],  fill=bel)

    # Ears
    hr = 118; hx = cx; hy = cy - 145 - hr + 18
    d.polygon([(hx-90, hy+18), (hx-42, hy-hr-82), (hx-10, hy-hr+16)], fill=ec)
    d.polygon([(hx-78, hy+10), (hx-44, hy-hr-58), (hx-15, hy-hr+11)], fill=ie)
    d.polygon([(hx+90, hy+18), (hx+42, hy-hr-82), (hx+10, hy-hr+16)], fill=ec)
    d.polygon([(hx+78, hy+10), (hx+44, hy-hr-58), (hx+15, hy-hr+11)], fill=ie)

    # Head
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=bc)

    # Eyes — blink every ~4s, squint during fast phase
    blink  = abs(math.sin(t * 0.52)) > 0.95
    squint = (4 <= phase < 6)
    for xo in [-38, 38]:
        ex2, ey2 = hx + xo, hy - 11
        if blink:
            d.arc([ex2-22, ey2-6, ex2+22, ey2+6], 195, 345, fill=(40, 25, 8), width=7)
        elif squint:
            d.arc([ex2-22, ey2-8, ex2+22, ey2+12], 200, 340, fill=(40, 25, 8), width=7)
        else:
            d.ellipse([ex2-22, ey2-20, ex2+22, ey2+20], fill=(255, 255, 255))
            d.ellipse([ex2-13, ey2-18, ex2+13, ey2+18], fill=(40, 25, 8))
            d.ellipse([ex2-7,  ey2-16, ex2-2,  ey2-9],  fill=(255, 255, 255))

    # Nose + mouth
    d.polygon([(hx, hy+16), (hx-13, hy+4), (hx+13, hy+4)], fill=(255, 110, 145))
    d.arc([hx-26, hy+22, hx+26, hy+52], 15, 165, fill=(170, 55, 75), width=6)

    # Cheek blush
    for xo in [-68, 68]:
        d.ellipse([hx+xo-28, hy+8, hx+xo+28, hy+36], fill=(255, 155, 155))

    # Whiskers
    wy = hy + 24
    for wx1, wx2, wy1, wy2 in [(-20,-94,2,-10),(-20,-90,11,-2),(-20,-86,20,6)]:
        d.line([(hx+wx1, wy+wy1), (hx+wx2, wy+wy2)], fill=(200,155,115), width=3)
    for wx1, wx2, wy1, wy2 in [(20,94,2,-10),(20,90,11,-2),(20,86,20,6)]:
        d.line([(hx+wx1, wy+wy1), (hx+wx2, wy+wy2)], fill=(200,155,115), width=3)

    # Arms with alternating up/down
    aw = math.sin(t * 3.2) * 55
    d.line([cx-112, cy-35, cx-178, cy-78-int(aw)],  fill=bc, width=40)
    d.ellipse([cx-206, cy-108-int(aw)-28, cx-154, cy-108-int(aw)+28], fill=bc)
    d.line([cx+112, cy-35, cx+178, cy-78+int(aw*0.6)], fill=bc, width=40)
    d.ellipse([cx+154, cy-108+int(aw*0.6)-28, cx+206, cy-108+int(aw*0.6)+28], fill=bc)

    # Feet — alternating tap
    lk = int(math.sin(t * 4.0) * 20)
    for xo in [-44, 44]:
        d.ellipse([cx+xo-40, cy+50+(lk if xo<0 else -lk),
                   cx+xo+40, cy+108+(lk if xo<0 else -lk)], fill=bc)


def draw_fish(d, cx, cy, t):
    sx=int(math.sin(t*1.6)*80); sy=int(math.sin(t*2.4)*30); cx+=sx; cy+=sy
    bc=(50,180,255); sc=(30,140,220)
    d.ellipse([cx-130,cy-72,cx+130,cy+72],fill=bc)
    tw=int(math.sin(t*4)*24)
    d.polygon([(cx+118,cy-12+tw),(cx+118,cy+12+tw),(cx+180,cy-72),(cx+180,cy+72)],fill=sc)
    d.polygon([(cx-26,cy-72),(cx+26,cy-72),(cx,cy-125)],fill=sc)
    for i in range(3):
        for j in range(2): d.arc([cx-78+i*58,cy-28+j*46,cx-22+i*58,cy+18+j*46],0,180,fill=sc,width=4)
    d.ellipse([cx-85,cy-26,cx-46,cy+16],fill=(255,255,255))
    d.ellipse([cx-76,cy-19,cx-55,cy+9],fill=(20,20,20))
    d.arc([cx-72,cy+8,cx-28,cy+40],10,160,fill=(255,255,255),width=5)


def draw_elephant(d, cx, cy, t):
    b=int(abs(math.sin(t*2.8))*26); cy-=b
    col=(180,160,200); dark=(140,120,165)
    d.ellipse([cx-115,cy+160,cx+115,cy+190],fill=(30,30,30))
    d.ellipse([cx-115,cy-138,cx+115,cy+65],fill=col)
    d.ellipse([cx-100,cy-210,cx+100,cy-28],fill=col)
    px,py=None,None
    for i in range(14):
        tx2=cx-int(38*math.sin(i*0.42+t*1.6)); ty2=cy-28+i*24
        if px: d.line([(px,py),(tx2,ty2)],fill=col,width=44)
        px,py=tx2,ty2
    ef=int(math.sin(t*2.2)*12)
    d.ellipse([cx-152-ef,cy-195,cx-40-ef,cy-40],fill=dark)
    d.ellipse([cx+40+ef,cy-195,cx+152+ef,cy-40],fill=dark)
    for xo in [-36,36]:
        ex2,ey2=cx+xo,cy-128
        d.ellipse([ex2-18,ey2-18,ex2+18,ey2+18],fill=(255,255,255))
        d.ellipse([ex2-10,ey2-14,ex2+10,ey2+14],fill=(40,25,15))
    lk=int(math.sin(t*2.8)*16)
    for xo in [-52,52]: d.rounded_rectangle([cx+xo-28,cy+42+lk,cx+xo+28,cy+130+lk],radius=12,fill=col)


def draw_moon(d, cx, cy, t):
    glow=int(abs(math.sin(t*1.5))*28)
    for r in range(158+glow,95,-20): d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(255,240,100))
    d.ellipse([cx-112,cy-112,cx+112,cy+112],fill=(255,230,50))
    d.ellipse([cx+28,cy-100,cx+175,cy+100],fill=(50,30,150))
    fx=cx-20
    for xo in [-26,20]:
        ex2,ey2=fx+xo,cy-20
        d.ellipse([ex2-13,ey2-13,ex2+13,ey2+13],fill=(80,50,10))
    d.arc([fx-24,cy+8,fx+24,cy+38],10,170,fill=(180,100,30),width=6)


def draw_star(d, cx, cy, t):
    pulse=1.0+0.20*math.sin(t*3); r=int(122*pulse)
    for gr in range(r+40,r,-12):
        fc=lerp_col((255,240,100),(50,30,100),(gr-r)/40)
        d.ellipse([cx-gr,cy-gr,cx+gr,cy+gr],fill=fc)
    pts=[]
    for i in range(10):
        ang=i/10*2*math.pi-math.pi/2+t*0.55; dist=r if i%2==0 else r//2
        pts.append((cx+int(dist*math.cos(ang)),cy+int(dist*math.sin(ang))))
    if pts: d.polygon(pts,fill=(255,235,50))
    for xo in [-28,28]:
        d.ellipse([cx+xo-15,cy-25,cx+xo+15,cy+5],fill=(100,70,0))
    d.arc([cx-20,cy+8,cx+20,cy+32],10,170,fill=(180,120,0),width=6)


def draw_horse(d, cx, cy, t):
    trot=int(math.sin(t*5.5)*26); cx+=int(math.sin(t*2.2)*22); cy-=abs(trot)
    col=(160,90,30); dark=(120,60,15)
    d.ellipse([cx-108,cy+172,cx+108,cy+200],fill=(30,20,10))
    d.ellipse([cx-112,cy-112,cx+112,cy+78],fill=col)
    d.polygon([(cx-38,cy-112),(cx+38,cy-112),(cx+58,cy-192),(cx-20,cy-204)],fill=col)
    d.ellipse([cx-64,cy-238,cx+52,cy-144],fill=col)
    for i,(xo,ph) in enumerate([(-50,0),(50,1),(-32,1),(32,0)]):
        lk2=int(math.sin(t*5.5+ph*math.pi)*28)
        d.rounded_rectangle([cx+xo-18,cy+64+lk2,cx+xo+18,cy+168+lk2],radius=10,fill=col)
        d.ellipse([cx+xo-20,cy+154+lk2,cx+xo+20,cy+184+lk2],fill=dark)


def draw_peacock(d, cx, cy, t):
    for i in range(8):
        ang=-math.pi/2+(i-3.5)*0.28+math.sin(t*1.6)*0.07
        fl=220+int(math.sin(t*2.2+i)*14)
        fx2=cx+int(fl*math.cos(ang)); fy2=cy-78+int(fl*math.sin(ang))
        col=[(0,180,100),(0,150,200),(100,50,200),(0,200,150),(50,180,220)][i%5]
        d.line([(cx,cy-78),(fx2,fy2)],fill=col,width=13)
        d.ellipse([fx2-26,fy2-26,fx2+26,fy2+26],fill=col)
        d.ellipse([fx2-13,fy2-13,fx2+13,fy2+13],fill=(0,0,80))
    d.ellipse([cx-58,cy-104,cx+58,cy+66],fill=(0,150,100))
    d.ellipse([cx-36,cy-162,cx+36,cy-84],fill=(0,150,100))


def draw_kid(d, cx, cy, t):
    phase=(t%6)
    bounce=int(abs(math.sin(t*3.5))*30); cy-=bounce
    swing=int(math.sin(t*2)*28) if phase<3 else int(math.sin(t*4)*18)
    cx+=swing
    skin=(255,220,177); shirt=(255,100,100)
    d.ellipse([cx-78,cy+132,cx+78,cy+158],fill=(30,20,10))
    d.rounded_rectangle([cx-92,cy-108,cx+92,cy+15],radius=26,fill=shirt)
    pants=(70,100,180)
    d.rounded_rectangle([cx-78,cy-28,cx+78,cy+140],radius=15,fill=pants)
    d.rectangle([cx-7,cy+15,cx+7,cy+140],fill=tuple(max(0,c-30) for c in pants))
    shoe=(60,40,20); lk=int(math.sin(t*3.5)*12)
    d.ellipse([cx-78,cy+108+lk,cx-14,cy+152+lk],fill=shoe)
    d.ellipse([cx+14,cy+108-lk,cx+78,cy+152-lk],fill=shoe)
    hr=102; hx,hy=cx,cy-108-hr+24
    d.ellipse([hx-hr+8,hy-hr+8,hx+hr+8,hy+hr+8],fill=(20,15,10))
    d.ellipse([hx-hr,hy-hr,hx+hr,hy+hr],fill=skin)
    hair=(80,50,20)
    d.ellipse([hx-hr,hy-hr,hx+hr,hy-14],fill=hair)
    blink=abs(math.sin(t*0.72))>0.93
    for xo in [-36,36]:
        ex2,ey2=hx+xo,hy-14
        if blink: d.arc([ex2-23,ey2-8,ex2+23,ey2+8],185,355,fill=(50,30,20),width=7)
        else:
            d.ellipse([ex2-23,ey2-23,ex2+23,ey2+23],fill=(255,255,255))
            d.ellipse([ex2-14,ey2-16,ex2+14,ey2+16],fill=(80,50,200))
            d.ellipse([ex2-9,ey2-10,ex2+9,ey2+10],fill=(20,15,10))
    d.arc([hx-28,hy+16,hx+28,hy+50],15,165,fill=(180,60,80),width=7)
    for cxo in [-54,54]: d.ellipse([hx+cxo-26,hy+8,hx+cxo+26,hy+38],fill=(255,160,160))
    aw_l=math.sin(t*3.8)*62; aw_r=math.sin(t*3.8+math.pi)*62
    d.line([cx-92,cy-65,cx-168,cy-100-int(aw_l)],fill=shirt,width=38)
    d.ellipse([cx-192,cy-124-int(aw_l)-26,cx-148,cy-124-int(aw_l)+26],fill=skin)
    d.line([cx+92,cy-65,cx+168,cy-100-int(aw_r)],fill=shirt,width=38)
    d.ellipse([cx+148,cy-124-int(aw_r)-26,cx+192,cy-124-int(aw_r)+26],fill=skin)


# Lofi-specific kid: sitting by window with headphones
def draw_lofi_kid(d, cx, cy, t):
    """Lofi girl/boy sitting by window, headphones on, subtle sway."""
    sway = int(math.sin(t * 0.8) * 8)
    cx += sway

    skin = (255, 210, 165)
    hair = (40, 25, 15)
    shirt = (80, 100, 160)
    pants = (50, 55, 80)
    headphone = (30, 30, 50)
    hp_accent = (100, 150, 255)

    # Body (sitting — torso only visible)
    d.rounded_rectangle([cx-70, cy-90, cx+70, cy+60], radius=20, fill=shirt)

    # Legs (sitting, bent)
    d.rounded_rectangle([cx-60, cy+50, cx-10, cy+130], radius=14, fill=pants)
    d.rounded_rectangle([cx+10, cy+50, cx+60, cy+130], radius=14, fill=pants)
    # Shoes
    d.ellipse([cx-72, cy+110, cx-6, cy+145], fill=(40, 35, 60))
    d.ellipse([cx+6, cy+110, cx+72, cy+145], fill=(40, 35, 60))

    # Head
    hr = 85; hx, hy = cx, cy - 90 - hr + 18
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=skin)

    # Hair (long-ish lofi style)
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+10], fill=hair)
    d.ellipse([hx-hr-10, hy-hr+30, hx-hr+25, hy+50], fill=hair)
    d.ellipse([hx+hr-25, hy-hr+30, hx+hr+10, hy+50], fill=hair)

    # Headphones
    # Band over head
    d.arc([hx-78, hy-72, hx+78, hy+20], start=200, end=340, fill=headphone, width=14)
    # Ear cups
    for xo in [-80, 80]:
        d.ellipse([hx+xo-22, hy-22, hx+xo+22, hy+22], fill=headphone)
        d.ellipse([hx+xo-14, hy-14, hx+xo+14, hy+14], fill=hp_accent)

    # Eyes (half-closed, looking down — lofi mood)
    for xo in [-26, 26]:
        ex2, ey2 = hx+xo, hy+2
        d.arc([ex2-18, ey2-8, ex2+18, ey2+8], start=200, end=340, fill=(40, 25, 10), width=5)

    # Subtle smile
    d.arc([hx-16, hy+14, hx+16, hy+32], start=15, end=165, fill=(160, 90, 70), width=4)

    # Arms on desk (folded)
    d.rounded_rectangle([cx-90, cy+20, cx-20, cy+55], radius=16, fill=shirt)
    d.rounded_rectangle([cx+20, cy+20, cx+90, cy+55], radius=16, fill=shirt)

    # Floating music notes (lofi vibe)
    note_alpha = abs(math.sin(t * 1.2))
    for i, (nx, ny_off) in enumerate([(cx+110, -180), (cx+140, -240), (cx+90, -300)]):
        ny = cy + ny_off + int(math.sin(t * 1.5 + i) * 20)
        if ny > 0:
            fnt = get_font(28 + i*4, bold=False)
            try:
                d.text((nx, ny), "♪", fill=tuple(min(255, c+80) for c in hex_rgb("#4a9eff")), font=fnt)
            except: pass


CHARS = {
    "cat":draw_cat, "fish":draw_fish, "elephant":draw_elephant,
    "moon":draw_moon, "star":draw_star, "horse":draw_horse,
    "peacock":draw_peacock, "kid":draw_kid,
}

# ── Lyrics display — NOW WITH TRANSLITERATION ────────────────────────────────
def _wrap_words(words, fnt, d, max_w):
    """Wrap list of words into lines that fit max_w pixels."""
    lines = []
    cur_words = []
    for w in words:
        test = " ".join(cur_words + [w])
        try:
            bb = d.textbbox((0,0), test, font=fnt)
            tw = bb[2] - bb[0]
        except:
            tw = len(test) * 28
        if tw > max_w and cur_words:
            lines.append(" ".join(cur_words))
            cur_words = [w]
        else:
            cur_words.append(w)
    if cur_words:
        lines.append(" ".join(cur_words))
    return lines


def draw_lyrics(d, lines_data, t, accent_rgb, style="bright"):
    """
    Caption-style lyrics — fixed at bottom, max 2 lines,
    word-by-word highlight, unique per style.
    """
    # ── Find current line ───────────────────────────────────────────────────
    cur = 0
    for i, ld in enumerate(lines_data):
        if t >= ld["start"]: cur = i

    raw_text = lines_data[cur]["text"]
    text     = hindi_to_hinglish(raw_text)
    words    = text.split()
    if not words: return

    # ── Word-by-word progress ───────────────────────────────────────────────
    dur  = max(0.1, lines_data[cur]["end"] - lines_data[cur]["start"])
    prog = max(0.0, min(1.0, (t - lines_data[cur]["start"]) / dur))
    # how many words are "revealed" so far
    n_shown = max(1, int(prog * (len(words) + 0.5)))

    # ── Font & layout constants ─────────────────────────────────────────────
    FONT_SIZE  = 72          # readable but not huge
    MAX_W      = W - 120     # 60px margin each side
    LINE_GAP   = 14
    BOTTOM_PAD = 90          # above progress bar

    fnt_bold = get_font(FONT_SIZE, bold=True)
    fnt_reg  = get_font(FONT_SIZE, bold=False)

    # Wrap full text into lines (max 2)
    all_lines = _wrap_words(words, fnt_bold, d, MAX_W)
    all_lines = all_lines[:2]   # hard cap at 2 lines

    # Measure total block height
    try:
        sample_bb = d.textbbox((0,0), "Ag", font=fnt_bold)
        line_h = sample_bb[3] - sample_bb[1]
    except:
        line_h = FONT_SIZE + 10

    n_lines    = len(all_lines)
    block_h    = n_lines * line_h + (n_lines - 1) * LINE_GAP
    pad_v, pad_h = 28, 44

    # Fixed Y position — bottom of frame above progress bar
    block_y = H - BOTTOM_PAD - block_h - pad_v * 2

    # ── Background box ───────────────────────────────────────────────────────
    box_w = MAX_W + pad_h * 2
    bx1   = (W - box_w) // 2
    bx2   = bx1 + box_w
    by1   = block_y
    by2   = by1 + block_h + pad_v * 2

    if style == "lofi":
        # Frosted glass dark box
        d.rounded_rectangle([bx1+6, by1+6, bx2+6, by2+6], radius=30, fill=(0,0,0))
        d.rounded_rectangle([bx1, by1, bx2, by2], radius=30, fill=(12, 16, 36))
        # Accent border glow
        for bw in [6, 3]:
            alpha = 180 if bw==6 else 255
            d.rounded_rectangle([bx1, by1, bx2, by2], radius=30,
                                  outline=accent_rgb, width=bw)
        # Top accent line
        d.rounded_rectangle([bx1 + 40, by1 - 4, bx1 + 160, by1 + 4],
                              radius=4, fill=accent_rgb)

    elif style == "dark":
        # Deep dark with neon border
        d.rounded_rectangle([bx1+5, by1+5, bx2+5, by2+5], radius=28, fill=(0,0,0))
        d.rounded_rectangle([bx1, by1, bx2, by2], radius=28, fill=(10, 8, 25))
        d.rounded_rectangle([bx1, by1, bx2, by2], radius=28,
                              outline=accent_rgb, width=5)
        # Corner dots
        for cx2, cy2 in [(bx1+16, by1+16),(bx2-16, by1+16)]:
            d.ellipse([cx2-7, cy2-7, cx2+7, cy2+7], fill=accent_rgb)

    else:
        # Bright style: white card with coloured top stripe
        d.rounded_rectangle([bx1+6, by1+6, bx2+6, by2+6],
                              radius=28, fill=(120,120,120))
        d.rounded_rectangle([bx1, by1, bx2, by2],
                              radius=28, fill=(255, 255, 255))
        # Coloured stripe at top of card
        stripe_h = 10
        d.rounded_rectangle([bx1, by1, bx2, by1 + stripe_h + 28],
                              radius=28, fill=accent_rgb)
        d.rectangle([bx1, by1 + 28, bx2, by1 + stripe_h + 28],
                     fill=accent_rgb)

    # ── Draw words line by line with per-word highlight ──────────────────────
    word_idx = 0   # global word counter across lines
    for li, line in enumerate(all_lines):
        line_words = line.split()
        if not line_words: continue

        # Measure total line width for centering
        try:
            bb_full = d.textbbox((0,0), line, font=fnt_bold)
            line_w  = bb_full[2] - bb_full[0]
        except:
            line_w = len(line) * 36

        line_x = (W - line_w) // 2
        line_y = block_y + pad_v + li * (line_h + LINE_GAP)
        cur_x  = line_x

        for wi, word in enumerate(line_words):
            global_wi = word_idx + wi
            revealed  = global_wi < n_shown
            is_active = global_wi == n_shown - 1  # current word

            # Measure this word
            try:
                wb = d.textbbox((0,0), word, font=fnt_bold)
                ww = wb[2] - wb[0]
            except:
                ww = len(word) * 36

            # Space width
            if wi < len(line_words) - 1:
                try:
                    sb = d.textbbox((0,0), " ", font=fnt_bold)
                    sw2 = sb[2] - sb[0]
                except:
                    sw2 = 18
            else:
                sw2 = 0

            if style == "bright":
                if revealed:
                    if is_active:
                        # Active word: bold, accent color, small underline
                        d.text((cur_x, line_y), word,
                               fill=accent_rgb, font=fnt_bold)
                        d.rounded_rectangle(
                            [cur_x, line_y + line_h + 2,
                             cur_x + ww, line_y + line_h + 7],
                            radius=3, fill=accent_rgb)
                    else:
                        # Already said: dark text
                        d.text((cur_x, line_y), word,
                               fill=(30, 30, 30), font=fnt_bold)
                else:
                    # Not yet: grey
                    d.text((cur_x, line_y), word,
                           fill=(180, 180, 180), font=fnt_reg)

            elif style == "lofi":
                if revealed:
                    if is_active:
                        # Active: accent glow behind word
                        glow_pad = 8
                        d.rounded_rectangle(
                            [cur_x - glow_pad, line_y - 4,
                             cur_x + ww + glow_pad, line_y + line_h + 4],
                            radius=10,
                            fill=tuple(max(0, c - 140) for c in accent_rgb))
                        d.text((cur_x, line_y), word,
                               fill=accent_rgb, font=fnt_bold)
                    else:
                        d.text((cur_x, line_y), word,
                               fill=(220, 225, 255), font=fnt_bold)
                else:
                    d.text((cur_x, line_y), word,
                           fill=(80, 85, 110), font=fnt_reg)

            else:  # dark
                if revealed:
                    if is_active:
                        # Active: bright accent + bottom dot
                        d.text((cur_x, line_y), word,
                               fill=(255, 255, 255), font=fnt_bold)
                        dot_x = cur_x + ww // 2
                        d.ellipse([dot_x-5, line_y+line_h+4,
                                   dot_x+5, line_y+line_h+14],
                                  fill=accent_rgb)
                    else:
                        d.text((cur_x, line_y), word,
                               fill=tuple(min(255,c+60) for c in accent_rgb),
                               font=fnt_bold)
                else:
                    d.text((cur_x, line_y), word,
                           fill=(70, 70, 100), font=fnt_reg)

            cur_x += ww + sw2

        word_idx += len(line_words)


def draw_title(d, title, accent_rgb, style="bright"):
    if not title: return
    # Transliterate title too
    title_display = hindi_to_hinglish(title)
    clean = re.sub(r"[^\w\s\-\.]","",title_display).strip() or title_display[:30]
    fnt = get_font(54,bold=True)
    try:
        bb=d.textbbox((0,0),clean,font=fnt); tw=bb[2]-bb[0]
    except: tw=len(clean)*34
    tw=max(tw,180); tx=(W-tw)//2
    if style == "lofi":
        d.rounded_rectangle([tx-28+4,52+4,tx+tw+28+4,128+4],radius=22,fill=(0,0,0))
        d.rounded_rectangle([tx-28,52,tx+tw+28,128],radius=22,fill=(15,20,40))
        d.rounded_rectangle([tx-28,52,tx+tw+28,128],radius=22,outline=accent_rgb,width=3)
        d.text((tx,60),clean,fill=accent_rgb,font=fnt)
    else:
        d.rounded_rectangle([tx-28+4,52+4,tx+tw+28+4,128+4],radius=22,fill=(100,100,100))
        d.rounded_rectangle([tx-28,52,tx+tw+28,128],radius=22,fill=accent_rgb)
        d.text((tx+2,62),clean,fill=(0,0,0),font=fnt)
        d.text((tx,60),clean,fill=(255,255,255),font=fnt)


def draw_progress(d, progress, accent_rgb):
    bh=20
    d.rectangle([0,H-bh,W,H],fill=(25,25,25))
    fw=int(W*progress)
    if fw>2:
        for x in range(fw):
            col=lerp_col(accent_rgb,(255,200,80),x/W)
            d.line([(x,H-bh),(x,H)],fill=col)



# ═══════════════════════════════════════════════════════════════════════════════
#  SONG VIDEO ENGINE — Ken Burns + Synced Captions (no characters)
# ═══════════════════════════════════════════════════════════════════════════════

BG_IMAGES_DIR = os.path.join(_here, "bg_images")
os.makedirs(BG_IMAGES_DIR, exist_ok=True)

_img_cache = {}  # filename → (PIL.Image at 15% overscan)

# Pan directions for Ken Burns: (start_x_frac, start_y_frac, end_x_frac, end_y_frac)
_KB_MOVES = [
    (0.0, 0.0, 1.0, 0.0),   # pan right
    (1.0, 0.0, 0.0, 0.0),   # pan left
    (0.0, 0.0, 0.0, 1.0),   # pan down
    (0.0, 1.0, 0.0, 0.0),   # pan up
    (0.0, 0.0, 1.0, 1.0),   # diagonal TL→BR
    (1.0, 1.0, 0.0, 0.0),   # diagonal BR→TL
    (0.5, 0.0, 0.5, 1.0),   # centre pan down
    (0.0, 0.5, 1.0, 0.5),   # centre pan right
]

def _preload_bg(filename):
    """Load, scale to 115% overscan, cache."""
    if filename in _img_cache:
        return _img_cache[filename]
    path = os.path.join(BG_IMAGES_DIR, filename)
    if not os.path.exists(path):
        _img_cache[filename] = None
        return None
    try:
        img = Image.open(path).convert("RGB")
        bw, bh = img.size
        # scale so it covers 1080×1920 with 15% room to pan
        scale = max(W * 1.15 / bw, H * 1.15 / bh)
        nw, nh = max(W+2, int(bw*scale)), max(H+2, int(bh*scale))
        img = img.resize((nw, nh), Image.LANCZOS)
        _img_cache[filename] = img
        print(f"[BG] cached {filename} → {nw}×{nh}")
        return img
    except Exception as e:
        print(f"[BG] load error {filename}: {e}")
        _img_cache[filename] = None
        return None


def _ease_inout(t):
    """Smooth ease-in-out curve (0→1)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _render_kenburns_frame(bg_imgs_list, fi, total_frames):
    """
    Ken Burns with zoom-in/out alternation, longer crossfade (15%), subtle vignette.
    """
    n      = len(bg_imgs_list)
    seg    = total_frames / n
    i_cur  = min(int(fi / seg), n - 1)
    i_nxt  = (i_cur + 1) % n
    seg_t  = (fi - i_cur * seg) / max(seg, 1)   # 0.0 → 1.0

    def _get_frame(img_obj, move_idx, t_ease, zoom_in=True):
        if img_obj is None:
            return Image.new("RGB", (W, H), (10, 8, 20))
        bw, bh = img_obj.size
        sx0, sy0, sx1, sy1 = _KB_MOVES[move_idx % len(_KB_MOVES)]

        # Alternating zoom-in / zoom-out (13% travel instead of 8%)
        ZOOM_AMT = 0.13
        if zoom_in:
            zoom = 1.0 + ZOOM_AMT * t_ease          # 1.00 → 1.13
        else:
            zoom = 1.0 + ZOOM_AMT * (1.0 - t_ease)  # 1.13 → 1.00

        # Crop zoomed region from center
        crop_w = int(W / zoom)
        crop_h = int(H / zoom)
        # pan offset on top of zoom crop
        extra_x = bw - crop_w
        extra_y = bh - crop_h
        cx = int(sx0 * extra_x + (sx1 - sx0) * extra_x * t_ease)
        cy = int(sy0 * extra_y + (sy1 - sy0) * extra_y * t_ease)
        cx = max(0, min(max(0, extra_x), cx))
        cy = max(0, min(max(0, extra_y), cy))
        frame = img_obj.crop((cx, cy, cx + crop_w, cy + crop_h)).resize((W, H), Image.LANCZOS)

        # Dark vignette overlay: 30% uniform + soft edge
        dark = Image.new("RGB", (W, H), (0, 0, 0))
        frame = Image.blend(frame, dark, 0.30)

        # Add soft radial vignette (dark corners)
        vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dv  = ImageDraw.Draw(vig)
        for r, alpha in [(540, 80), (440, 50), (360, 25)]:
            dv.ellipse([W//2-r, H//2-r, W//2+r, H//2+r],
                       fill=(0, 0, 0, 0), outline=(0, 0, 0, alpha), width=r//2)
        frame_rgba = frame.convert("RGBA")
        frame_rgba = Image.alpha_composite(frame_rgba, vig)
        return frame_rgba.convert("RGB")

    t_smooth  = _ease_inout(seg_t)
    zoom_in   = (i_cur % 2 == 0)   # alternate zoom direction each image
    cur_frame = _get_frame(bg_imgs_list[i_cur], i_cur, t_smooth, zoom_in)

    # crossfade in last 15% of segment (was 10%)
    if seg_t > 0.85 and n > 1:
        blend_t   = (seg_t - 0.85) / 0.15
        nxt_frame = _get_frame(bg_imgs_list[i_nxt], i_nxt, 0.0, not zoom_in)
        # ease the blend curve for smooth dissolve
        alpha = _ease_inout(blend_t)
        cur_frame = Image.blend(cur_frame, nxt_frame, alpha)

    return cur_frame


def _draw_ambient_particles(d, accent_rgb, t):
    """
    Layered ambient bokeh — 3 depth layers: far (tiny dim), mid (medium), near (large faint).
    Adds life without distracting from lyrics.
    """
    rng = random.Random(99)
    # Layer config: (count, size_range, speed_mult, alpha_max, drift_scale)
    layers = [
        (14, (2, 5),   0.18, 0.30, 28),   # far — tiny, slow, very dim
        (7,  (7, 14),  0.28, 0.20, 45),   # mid
        (4,  (18, 32), 0.12, 0.10, 60),   # near — large, blurry-looking, very faint
    ]
    for count, (smin, smax), spd, amax, drift in layers:
        for i in range(count):
            sx   = rng.uniform(0.04, 0.96) * W
            sy   = rng.uniform(0.04, 0.92) * H
            ph   = rng.random() * math.pi * 2
            size = rng.randint(smin, smax)
            blink = 0.4 + 0.6 * abs(math.sin(t * spd + ph))
            cx2  = int((sx + math.sin(t * 0.22 + ph) * drift) % W)
            cy2  = int((sy + math.cos(t * 0.18 + ph) * (drift * 0.7)) % H)
            alpha = amax * blink
            col  = tuple(min(255, int(c * alpha)) for c in accent_rgb)
            if not any(v > 3 for v in col): continue
            d.ellipse([cx2-size, cy2-size, cx2+size, cy2+size], fill=col)
            # ring outline for larger bokeh
            if size >= 14:
                ring_col = tuple(min(255, int(c * alpha * 0.4)) for c in accent_rgb)
                d.ellipse([cx2-size-4, cy2-size-4, cx2+size+4, cy2+size+4],
                           outline=ring_col, width=2)


def _draw_floating_notes(d, accent_rgb, t):
    """Music notes float up with wobble + fade — 4 notes at staggered positions."""
    fnt_s = get_font(34, bold=False)
    fnt_l = get_font(52, bold=False)
    fnt_xl= get_font(66, bold=False)
    notes = ["♪", "♫", "♩", "♬"]
    sizes = [fnt_l, fnt_s, fnt_xl, fnt_s]
    rng   = random.Random(55)
    for i, note in enumerate(notes):
        ph   = rng.random() * 10
        sx   = int(W * rng.uniform(0.07, 0.93))
        spd  = rng.uniform(48, 80)
        raw_y = (H * 0.85) - ((t * spd + ph * 80) % (H * 0.82))
        cy2   = int(raw_y)
        if cy2 < 20: continue
        fade  = max(0.0, min(1.0, raw_y / (H * 0.5)))
        wobble = int(math.sin(t * 1.4 + ph) * 18)
        # slight rotation effect via x offset
        col = tuple(min(255, int(c * 0.55 * fade)) for c in accent_rgb)
        if all(v < 5 for v in col): continue
        try:
            d.text((sx + wobble, cy2), note, fill=col, font=sizes[i])
        except: pass


def _draw_caption_song(d, lines_data, t, accent_rgb):
    """
    Song caption — cinematic subtitle style.
    - Pill slides up when new line starts
    - Word-by-word: upcoming=dim, active=white+glow, said=accent
    - Glow underline (3-layer) under active word
    - Accent border on pill, faint glow shadow
    """
    if not lines_data: return

    cur = 0
    for i, ld in enumerate(lines_data):
        if t >= ld["start"]: cur = i

    raw   = lines_data[cur]["text"]
    text  = hindi_to_hinglish(raw)
    words = text.split()
    if not words: return

    line_start = lines_data[cur]["start"]
    dur     = max(0.1, lines_data[cur]["end"] - line_start)
    prog    = max(0.0, min(1.0, (t - line_start) / dur))
    n_shown = max(1, int(prog * (len(words) + 0.5)))

    # ── Slide-up entrance (first 0.25s of each line) ─────────────────────────
    ENTER_DUR = 0.25
    enter_prog = min(1.0, (t - line_start) / ENTER_DUR)
    enter_ease = _ease_inout(enter_prog)
    slide_offset = int((1.0 - enter_ease) * 48)   # slides up 48px

    # ── Auto font size ─────────────────────────────────────────────────────────
    MAX_TEXT_W = W - 80
    chosen_fnt = None
    for fs in (72, 62, 52, 44, 38, 32):
        f = get_font(fs, bold=True)
        try:
            bb = d.textbbox((0, 0), text, font=f)
            if (bb[2] - bb[0]) <= MAX_TEXT_W:
                chosen_fnt = f; break
        except:
            chosen_fnt = f; break
    if chosen_fnt is None:
        chosen_fnt = get_font(32, bold=True)
    fnt_dim = get_font(chosen_fnt.size if hasattr(chosen_fnt,'size') else 44, bold=False)

    try:
        sb = d.textbbox((0,0), "Ag", font=chosen_fnt)
        line_h = sb[3] - sb[1]
    except:
        line_h = 56

    try:
        bb_full = d.textbbox((0, 0), text, font=chosen_fnt)
        text_w  = min(bb_full[2] - bb_full[0], MAX_TEXT_W)
    except:
        text_w = MAX_TEXT_W

    PAD_H  = 44
    PAD_V  = 22
    pill_w  = text_w + PAD_H * 2
    pill_x1 = (W - pill_w) // 2
    pill_x2 = pill_x1 + pill_w
    BASE_Y2 = H - 100
    pill_y2 = BASE_Y2 + slide_offset
    pill_y1 = pill_y2 - line_h - PAD_V * 2

    # Glow shadow (3 layers, increasingly faint)
    glow_col  = tuple(min(255, int(c * 0.22)) for c in accent_rgb)
    for spread in (22, 14, 7):
        d.rounded_rectangle([pill_x1-spread, pill_y1-spread//2,
                              pill_x2+spread, pill_y2+spread//2],
                             radius=32, fill=glow_col)

    # Main pill
    d.rounded_rectangle([pill_x1+4, pill_y1+4, pill_x2+4, pill_y2+4],
                          radius=28, fill=(0, 0, 0))
    d.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                          radius=28, fill=(6, 4, 18))
    d.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                          radius=28, outline=accent_rgb, width=3)

    # Word-by-word rendering
    text_y = pill_y1 + PAD_V
    cur_x  = (W - text_w) // 2

    word_widths = []
    sp_w = 14
    for wi, word in enumerate(words):
        try:
            wb = d.textbbox((0,0), word, font=chosen_fnt)
            word_widths.append(wb[2]-wb[0])
            if wi == 0:
                sb2 = d.textbbox((0,0), " ", font=chosen_fnt)
                sp_w = sb2[2] - sb2[0]
        except:
            word_widths.append(len(word) * 28)

    for wi, word in enumerate(words):
        revealed  = wi < n_shown
        is_active = wi == n_shown - 1
        ww        = word_widths[wi]

        if is_active:
            # Active word: bright white
            d.text((cur_x, text_y), word, fill=(255, 255, 255), font=chosen_fnt)
            # 3-layer glow underline
            for lw, la in [(10, 0.18), (6, 0.38), (3, 0.85)]:
                uc = tuple(min(255, int(c * la)) for c in accent_rgb)
                d.rectangle([cur_x - 2, text_y + line_h + 3,
                              cur_x + ww + 2, text_y + line_h + 3 + lw],
                             fill=uc)
        elif revealed:
            # Said: tinted accent, slightly softer
            col = tuple(min(255, int(c * 0.72 + 55)) for c in accent_rgb)
            d.text((cur_x, text_y), word, fill=col, font=chosen_fnt)
        else:
            # Upcoming: dark dim grey
            d.text((cur_x, text_y), word, fill=(55, 50, 80), font=fnt_dim)

        cur_x += ww + (sp_w if wi < len(words)-1 else 0)


def render_frame(lines_data, fi, total_frames, cfg, title, bg_imgs=None):
    """
    Render one frame.
    - bg_imgs (list of filenames) → song mode: Ken Burns + particles + captions only
    - no bg_imgs → kids mode: generated bg + character + captions
    """
    t        = fi / FPS
    progress = fi / max(total_frames, 1)
    col1, col2 = cfg["bg"]
    accent   = hex_rgb(cfg["accent"])
    style    = cfg.get("style", "bright")

    img = Image.new("RGB", (W, H), (8, 6, 20))

    if bg_imgs:
        # ── SONG MODE: Ken Burns background ──────────────────────────────────
        # Pre-load all images
        loaded = [_preload_bg(fn) for fn in bg_imgs]
        loaded = [x for x in loaded if x is not None]
        if not loaded:
            loaded = [None]   # fallback: black bg

        kb = _render_kenburns_frame(loaded, fi, total_frames)
        img.paste(kb, (0, 0))
        d = ImageDraw.Draw(img)

        # Subtle ambient effects only — no characters
        _draw_ambient_particles(d, accent, t)
        _draw_floating_notes(d, accent, t)

        # Song title — small, top, semi-transparent
        _draw_song_title(d, title, accent)

        # Synced captions
        if lines_data:
            _draw_caption_song(d, lines_data, t, accent)

    else:
        # ── KIDS MODE: generated background + character ───────────────────────
        d = ImageDraw.Draw(img)
        if style == "lofi":
            draw_lofi_bg(d, col1, col2, accent, t)
        else:
            draw_bg(d, col1, col2, t)
            if hex_rgb(col1)[0] < 80: draw_stars_bg(d, t)
            else: draw_bokeh(d, accent, t)

        draw_title(d, title, accent, style)

        if style == "lofi":
            draw_lofi_kid(d, W//2, int(H*0.76), t)
        else:
            CHARS.get(cfg["char"], draw_kid)(d, W//2, int(H*0.76), t)

        if lines_data:
            draw_lyrics(d, lines_data, t, accent, style)

    # Progress bar — always
    d = ImageDraw.Draw(img)
    draw_progress(d, progress, accent)
    return img


def _draw_song_title(d, title, accent_rgb):
    """Minimal title tag — top center, small, semi-transparent."""
    if not title: return
    title_display = hindi_to_hinglish(title)
    clean = re.sub(r"[^\w\s\-\.]", "", title_display).strip()[:35]
    fnt = get_font(38, bold=True)
    try:
        bb = d.textbbox((0, 0), clean, font=fnt)
        tw = bb[2] - bb[0]
    except:
        tw = len(clean) * 22
    tx = (W - tw) // 2
    # dark pill
    pad = 20
    d.rounded_rectangle([tx-pad+3, 42+3, tx+tw+pad+3, 100+3], radius=16, fill=(0,0,0))
    d.rounded_rectangle([tx-pad, 42, tx+tw+pad, 100], radius=16, fill=(12, 10, 28))
    d.rounded_rectangle([tx-pad, 42, tx+tw+pad, 100], radius=16,
                          outline=accent_rgb, width=2)
    d.text((tx, 50), clean, fill=accent_rgb, font=fnt)


# ═══════════════════════════════════════════════════════════════════════════════
#  VIDEO BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_video(content, job_id, song_key="", bg_key="", char_override="",
                bg_image_keys=None):
    tmp = os.path.join("C:/tmp" if os.name=="nt" else "/tmp", f"kh7_{job_id}")
    os.makedirs(f"{tmp}/frames", exist_ok=True)

    lines_text = content.get("lines", [])
    title      = content.get("title", "")
    bg_imgs    = [fn for fn in (bg_image_keys or [])
                  if os.path.exists(os.path.join(BG_IMAGES_DIR, fn))]

    # ── Find song ─────────────────────────────────────────────────────────────
    search_key = song_key or bg_key or title
    jobs[job_id]["message"] = "🎵 Step 1/3: Song dhundh raha hai..."
    song_path = find_song(search_key)
    if not song_path:
        raise Exception(
            f"Koi MP3 nahi mila! backend/songs/ mein Suno .mp3 daalo.\n"
            f"Song key: '{search_key}' | Folder: {SONGS_DIR}")

    song_dur     = get_duration(song_path)
    total_frames = int(song_dur * FPS)
    mode_label   = f"song-image({len(bg_imgs)}imgs)" if bg_imgs else "kids-anim"
    jobs[job_id]["message"] = (
        f"🎵 {os.path.basename(song_path)} ({song_dur:.1f}s) | mode: {mode_label}")
    print(f"[Build] Song: {song_path} | {song_dur:.1f}s | {total_frames}f | {mode_label}")

    # ── Visual config (used for accent colour even in song mode) ──────────────
    cfg = get_config_by_bg_key(bg_key) if bg_key else get_config(search_key)
    if char_override and char_override in CHARS:
        cfg = dict(cfg); cfg["char"] = char_override

    # Pre-load bg images into cache now (avoids lag during frame render)
    if bg_imgs:
        jobs[job_id]["message"] = "🖼️ Background images load ho rahi hain..."
        for fn in bg_imgs:
            _preload_bg(fn)

    # ── Lyrics timing ─────────────────────────────────────────────────────────
    n = len(lines_text)
    pre_timestamps = content.get("timestamps", [])   # whisper/manual timestamps
    lines_data = []
    if n > 0:
        if pre_timestamps and len(pre_timestamps) == n:
            # Use provided timestamps (whisper or manual)
            lines_data = [
                {"text": t.get("text", lines_text[i]),
                 "start": float(t.get("start", 0)),
                 "end":   float(t.get("end", song_dur))}
                for i, t in enumerate(pre_timestamps)
            ]
            print(f"[Build] Using {'whisper' if content.get('sync_method')=='whisper' else 'manual'} timestamps")
        else:
            # Equal division fallback
            gap = song_dur / n
            for i, txt in enumerate(lines_text):
                lines_data.append({
                    "text":  txt,
                    "start": i * gap + 0.4,
                    "end":   (i + 1) * gap - 0.25
                })
            print(f"[Build] Using equal-division timing ({n} lines, {song_dur:.1f}s)")

    # ── Render frames ──────────────────────────────────────────────────────────
    jobs[job_id]["message"] = "🎨 Step 2/3: Frames render ho rahi hain..."
    print(f"[Build] Rendering {total_frames} frames...")

    for fi in range(total_frames):
        if fi % 30 == 0:
            jobs[job_id]["progress"] = 10 + fi * 75 // max(total_frames, 1)
        img = render_frame(lines_data, fi, total_frames, cfg, title,
                           bg_imgs=bg_imgs if bg_imgs else None)
        img.save(f"{tmp}/frames/f{fi:05d}.png")

    # ── Encode ─────────────────────────────────────────────────────────────────
    jobs[job_id]["message"] = "🎬 Step 3/3: Video encode ho rahi hai..."
    out_dir = "C:/tmp/kh7_out" if os.name=="nt" else "/tmp/kh7_out"
    os.makedirs(out_dir, exist_ok=True)
    out = f"{out_dir}/{job_id}.mp4"

    r = subprocess.run([
        FFMPEG,
        "-framerate", str(FPS),
        "-i", f"{tmp}/frames/f%05d.png",
        "-i", song_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-vf", "scale=1080:1920", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", out, "-y", "-loglevel", "error"
    ], capture_output=True, text=True)

    if r.returncode != 0:
        raise Exception(f"FFmpeg failed: {r.stderr[:400]}")
    shutil.rmtree(tmp, ignore_errors=True)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
#  JOB RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

BUILTIN = {
    "billi":  {"title":"Billi Mausi","lines":["बिल्ली मौसी बिल्ली मौसी","क्या खाओगी खाना","दूध और रोटी लाऊँ","या मछली मँगवाना","म्याऊँ म्याऊँ म्याऊँ"]},
    "machli": {"title":"Machli Jal Ki Rani","lines":["मछली जल की रानी है","जीवन उसका पानी है","हाथ लगाओ डर जाएगी","बाहर निकालो मर जाएगी"]},
    "chanda": {"title":"Chanda Mama Dur Ke","lines":["चंदा मामा दूर के","पुए पकाएं बूर के","आप खाएं थाली में","मुन्ने को दें प्याली में","प्याली गई टूट","मुन्ना गया रूठ"]},
    "lakdi":  {"title":"Lakdi Ki Kathi","lines":["लकड़ी की काठी काठी पे घोड़ा","घोड़े की दुम पे जो मारा हथौड़ा","दौड़ा दौड़ा दौड़ा घोड़ा","दुम उठाके दौड़ा"]},
    "johny":  {"title":"Johny Johny Yes Papa","lines":["जॉनी जॉनी हाँ पापा","चीनी खाना नहीं पापा","सच बोलना हाँ पापा","मुँह खोलो हा हा हा"]},
    "twinkle":{"title":"Twinkle Twinkle Tare","lines":["टिमटिम करते तारे हैं","जैसे हीरे प्यारे हैं","ऊँचे नीले आसमान में","चमकते दिन और रात में"]},
    "hathi":  {"title":"Hathi Raja","lines":["हाथी राजा कहाँ चले","पेट में है दर्द बड़ा","दवाई लेने जाते हैं","डॉक्टर से मिलने जाते हैं","हाथी राजा वापस आए","सबको मिठाई खिलाए"]},
    "nani":   {"title":"Nani Teri Morni","lines":["नानी तेरी मोरनी को मोर ले गए","बाकी जो बचा था काले चोर ले गए","सो जा सो जा सो जा मेरे राजा","सो जा नींद आई है"]},
    "lori":   {"title":"Soja Mere Lal","lines":["सो जा मेरे लाल","सो जा चंद्रमा","माँ की गोद में","चैन से सो जा","मीठे सपने आएंगे","सुबह खुशियाँ लाएंगे"]},
    "school": {"title":"School Chalo","lines":["स्कूल चलो स्कूल चलो","पढ़ने जाना है","नए दोस्त बनाना है","ज्ञान की रोशनी लाना है","आओ मिलकर पढ़ें","भविष्य उज्जवल करें"]},
}

def call_groq(prompt,system=""):
    if not GROQ_KEY: return None
    try:
        r=req_lib.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile",
                  "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
                  "temperature":0.8,"max_tokens":600},timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except: return None

def generate_ai(topic,ct):
    system=f"हिंदी बाल-साहित्यकार हो। {ct} likho. JSON ONLY: {{\"title\":\"...\",\"lines\":[...]}}"
    raw=call_groq(f"Topic: {topic}",system)
    if not raw: return None
    try:
        raw=re.sub(r"```[a-z]*","",raw).replace("```","").strip()
        d=json.loads(raw)
        if "lines" in d: return d
    except: pass
    lines=[l.strip() for l in raw.split("\n") if l.strip() and len(l.strip())>3]
    return {"title":topic,"lines":lines[:10]} if lines else None

def run_job(job_id, params):
    job=jobs[job_id]; job["status"]="running"; job["progress"]=3
    try:
        ct        = params.get("content_type","rhyme")
        bk        = params.get("builtin_key","")
        cl        = params.get("custom_lines",[])
        top       = params.get("topic","")
        cha       = params.get("char_override","")
        bg_key    = params.get("bg_key","")

        # song_key_override = explicit song picked by user in UI
        # builtin_key = rhyme key (content), may or may not match a song
        song_key_override = params.get("song_key_override","").strip()

        if bk and bk in BUILTIN:
            content  = BUILTIN[bk]
            # Use override if given, else use builtin_key as song lookup
            song_key = song_key_override or bk
        elif cl:
            content  = {"title":top or "Meri Kavita","lines":cl}
            song_key = song_key_override or bk or top
        elif top:
            job["message"]="✍️ AI se likh raha hoon..."
            content = generate_ai(top,ct)
            if not content:
                job["status"]="failed"; job["message"]="AI fail. GROQ_API_KEY check karo."; return
            song_key = song_key_override or top
        else:
            job["status"]="failed"; job["message"]="Content chahiye."; return

        job["content"] = content
        # Attach pre-computed timestamps if provided
        if params.get("timestamps"):
            content = dict(content)
            content["timestamps"]  = params["timestamps"]
            content["sync_method"] = params.get("sync_method", "manual")
        vp = build_video(content, job_id,
                         song_key=song_key,
                         bg_key=bg_key or bk,
                         char_override=cha,
                         bg_image_keys=params.get("bg_image_keys", []))
        job["status"]="done"; job["progress"]=100
        job["message"]="🎉 Video taiyaar hai!"; job["video_path"]=vp

    except Exception as e:
        import traceback; tb=traceback.format_exc()
        job["status"]="failed"; job["message"]=str(e)[:200]
        job["error_detail"]=tb; print(f"[Job {job_id}] FAILED:\n{tb}")

# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health")
def health():
    mp3s=[]
    try: mp3s=[f for f in os.listdir(SONGS_DIR) if f.endswith(".mp3")]
    except: pass
    bg_imgs=[]
    try: bg_imgs=[f for f in os.listdir(BG_IMAGES_DIR)
                  if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
    except: pass
    return jsonify({"ok":True,"voices":["swara","madhur"],
        "builtins":list(BUILTIN.keys()),"suno_songs":mp3s,
        "songs_dir":SONGS_DIR,"mapping":_MAP,
        "bg_images":bg_imgs,"bg_images_dir":BG_IMAGES_DIR,
        "ai":{"groq":bool(GROQ_KEY),"gemini":bool(GEMINI_KEY)}})

@app.route("/api/builtins")
def builtins_api():
    return jsonify({k:{"title":v["title"],"type":"rhyme"} for k,v in BUILTIN.items()})

# ── Background Image Routes ───────────────────────────────────────────────────

@app.route("/api/upload-bg-image", methods=["POST"])
def upload_bg_image():
    if "file" not in request.files: return jsonify({"error":"No file"}),400
    f = request.files["file"]
    fname_lower = f.filename.lower()

    # ── IMAGE upload ──────────────────────────────────────────────────────────
    if any(fname_lower.endswith(e) for e in ('.jpg','.jpeg','.png','.webp')):
        safe = re.sub(r"[^\w\-.]","_",f.filename).lower()
        fp   = os.path.join(BG_IMAGES_DIR, safe)
        f.save(fp)
        _img_cache.pop(safe, None)
        return jsonify({"ok":True,"filename":safe,
                        "size_kb":os.path.getsize(fp)//1024,
                        "type":"image"})

    # ── VIDEO CLIP upload (.mp4 / .mov) ───────────────────────────────────────
    elif any(fname_lower.endswith(e) for e in ('.mp4','.mov','.webm')):
        safe_vid = re.sub(r"[^\w\-.]","_",f.filename).lower()
        tmp_vid  = os.path.join(BG_IMAGES_DIR, "tmp_" + safe_vid)
        f.save(tmp_vid)

        try:
            dur = get_duration(tmp_vid)
            base_name = safe_vid.rsplit('.',1)[0]

            # Smart frame count: 1 frame per second, min 1, max 8
            # For a 3s clip → 3 frames (0s, 1.5s, 3s)
            n_frames = max(1, min(8, int(dur)))

            # Spread timestamps evenly, never duplicate
            if n_frames == 1:
                ts_list = [dur / 2]  # just the middle frame
            else:
                # space them out with 0.5s gap from edges
                margin = min(0.4, dur * 0.1)
                span   = dur - 2 * margin
                ts_list = [margin + span * i / (n_frames - 1) for i in range(n_frames)]

            # Deduplicate: round to 2 decimal places, keep unique
            seen = set()
            ts_unique = []
            for ts in ts_list:
                key = round(ts, 2)
                if key not in seen:
                    seen.add(key); ts_unique.append(ts)

            extracted = []
            for idx, ts in enumerate(ts_unique):
                out_jpg = os.path.join(BG_IMAGES_DIR, f"{base_name}_f{idx:02d}.jpg")
                r = subprocess.run([
                    FFMPEG,
                    "-ss", f"{ts:.3f}",
                    "-i", tmp_vid,
                    "-vframes", "1",
                    "-q:v", "2",
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    out_jpg, "-y", "-loglevel", "error"
                ], capture_output=True)
                if r.returncode == 0 and os.path.exists(out_jpg):
                    extracted.append(f"{base_name}_f{idx:02d}.jpg")
                    _img_cache.pop(f"{base_name}_f{idx:02d}.jpg", None)

            os.remove(tmp_vid)

            if not extracted:
                return jsonify({"error": "Video se frames extract nahi hue — ffmpeg check karo"}), 400

            return jsonify({
                "ok": True,
                "type": "video",
                "frames": extracted,
                "frame_count": len(extracted),
                "duration_sec": round(dur, 1),
                "source": safe_vid
            })
        except Exception as e:
            if os.path.exists(tmp_vid): os.remove(tmp_vid)
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error":"Only jpg/png/webp/mp4/mov/webm allowed"}),400

@app.route("/api/bg-images")
def list_bg_images():
    imgs=[]
    try:
        for fname in sorted(os.listdir(BG_IMAGES_DIR)):
            if fname.lower().endswith(('.jpg','.jpeg','.png','.webp')):
                fp = os.path.join(BG_IMAGES_DIR,fname)
                # detect if it's a video-extracted frame
                is_vid_frame = bool(re.search(r'_f\d{2}\.jpg$', fname))
                imgs.append({
                    "filename": fname,
                    "size_kb":  os.path.getsize(fp)//1024,
                    "from_video": is_vid_frame,
                })
    except: pass
    return jsonify(imgs)

@app.route("/api/delete-bg-image/<fname>", methods=["DELETE"])
def delete_bg_image(fname):
    safe = re.sub(r"[^\w\-.]","_",fname)
    fp   = os.path.join(BG_IMAGES_DIR,safe)
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    os.remove(fp); _img_cache.pop(safe,None)
    return jsonify({"ok":True})

@app.route("/api/bg-image/<fname>")
def serve_bg_image(fname):
    safe = re.sub(r"[^\w\-.]","_",fname)
    fp   = os.path.join(BG_IMAGES_DIR,safe)
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    return send_file(fp)

@app.route("/api/whisper-sync", methods=["POST"])
def whisper_sync():
    """
    Auto-sync lyrics to song using Whisper.
    POST { "song_key": "...", "lines": ["line1","line2",...] }
    Returns { "ok": True, "timestamps": [{"text":..,"start":..,"end":..}, ...] }

    Requires: pip install openai-whisper torch
    """
    try:
        import whisper as _whisper
    except ImportError:
        return jsonify({
            "ok": False,
            "error": "Whisper install nahi hai",
            "install": "pip install openai-whisper torch",
            "note": "Ek baar install karo, phir auto-sync kaam karega"
        }), 400

    data = request.json or {}
    song_key = data.get("song_key", "")
    lines    = data.get("lines", [])
    if not lines:
        return jsonify({"ok": False, "error": "lines required"}), 400

    song_path = find_song(song_key)
    if not song_path:
        return jsonify({"ok": False, "error": f"Song not found: {song_key}"}), 404

    song_dur = get_duration(song_path)

    try:
        # Load smallest model for speed (tiny = ~70MB, fast)
        model_name = data.get("model", "tiny")
        model = _whisper.load_model(model_name)
        result = model.transcribe(song_path, word_timestamps=True,
                                   language="hi", task="transcribe")

        # Match Whisper words/segments to our lines
        # Strategy: use Whisper segments as timing anchors, snap our lines to nearest
        segments = result.get("segments", [])
        if not segments:
            return jsonify({"ok": False, "error": "Whisper ne koi segment nahi diya"}), 400

        # Build word timestamps from all segments
        all_words = []
        for seg in segments:
            ws = seg.get("words", [])
            if ws:
                all_words.extend(ws)
            else:
                # no word-level — use segment
                all_words.append({
                    "word": seg.get("text","").strip(),
                    "start": seg["start"],
                    "end":   seg["end"]
                })

        if not all_words:
            # Fallback: use segment times, divide among lines
            n = len(lines)
            gap = song_dur / max(n, 1)
            ts = [{"text": lines[i], "start": i*gap+0.3, "end":(i+1)*gap-0.2}
                  for i in range(n)]
            return jsonify({"ok": True, "timestamps": ts,
                             "method": "segment_fallback", "duration": song_dur})

        # Total whisper duration
        w_start = all_words[0]["start"]
        w_end   = all_words[-1]["end"]
        w_span  = max(w_end - w_start, 1)

        # Divide words proportionally among lines (by character count)
        total_chars = max(1, sum(len(l) for l in lines))
        timestamps = []
        word_idx = 0

        for li, line in enumerate(lines):
            # Expected fraction of words for this line
            frac = len(line) / total_chars
            n_words_for_line = max(1, round(frac * len(all_words)))
            i_start = word_idx
            i_end   = min(word_idx + n_words_for_line - 1, len(all_words)-1)
            word_idx += n_words_for_line

            t_start = all_words[i_start]["start"]
            t_end   = all_words[min(i_end, len(all_words)-1)].get("end", t_start + 2)
            timestamps.append({
                "text":  line,
                "start": round(t_start, 3),
                "end":   round(t_end, 3)
            })

        # Clamp last line to song duration
        if timestamps:
            timestamps[-1]["end"] = min(song_dur - 0.1, timestamps[-1]["end"])

        return jsonify({
            "ok": True,
            "timestamps": timestamps,
            "method": "whisper",
            "model": model_name,
            "duration": song_dur,
            "word_count": len(all_words)
        })

    except Exception as e:
        # Graceful fallback: equal division
        n   = len(lines)
        gap = song_dur / max(n, 1)
        ts  = [{"text": lines[i], "start": i*gap+0.3, "end":(i+1)*gap-0.2}
               for i in range(n)]
        return jsonify({
            "ok": True,
            "timestamps": ts,
            "method": "equal_fallback",
            "error": str(e),
            "duration": song_dur
        })


@app.route("/api/whisper-status")
def whisper_status():
    """Check if whisper is installed."""
    try:
        import whisper as _whisper
        return jsonify({"available": True, "models": ["tiny","base","small"]})
    except ImportError:
        return jsonify({
            "available": False,
            "install": "pip install openai-whisper torch",
            "note": "Ek baar install karo — tiny model ~70MB download hoga"
        })


@app.route("/api/stream-song/<fname>")
def stream_song(fname):
    safe = re.sub(r"[^\w\-.]","_", fname)
    fp   = os.path.join(SONGS_DIR, safe)
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    return send_file(fp, mimetype="audio/mpeg")


@app.route("/api/generate",methods=["POST"])
def generate():
    data=request.json or {}
    jid=str(uuid.uuid4())[:8]
    jobs[jid]={"id":jid,"status":"queued","progress":0,
               "message":"Queue mein hai...","created":datetime.now().isoformat()}
    threading.Thread(target=run_job,args=(jid,data),daemon=True).start()
    return jsonify({"job_id":jid})

@app.route("/api/status/<jid>")
def status(jid):
    job=jobs.get(jid)
    if not job: return jsonify({"error":"Not found"}),404
    resp={k:v for k,v in job.items() if k not in ("video_path",)}
    if job.get("status")=="done": resp["download_url"]=f"/api/download/{jid}"
    return jsonify(resp)

@app.route("/api/download/<jid>")
def download(jid):
    job=jobs.get(jid)
    if not job or job.get("status")!="done": return jsonify({"error":"Not ready"}),404
    vp=job.get("video_path")
    if not vp or not os.path.exists(vp): return jsonify({"error":"File missing"}),404
    t=re.sub(r"[^\w\s-]","",job.get("content",{}).get("title","video")).strip()[:35].replace(" ","_")
    return send_file(vp,as_attachment=True,download_name=f"{t}.mp4")

@app.route("/api/history")
def history():
    return jsonify(sorted(jobs.values(),key=lambda j:j.get("created",""),reverse=True)[:20])

@app.route("/api/songs")
def list_songs():
    songs=[]
    try:
        for fname in sorted(os.listdir(SONGS_DIR)):
            if not fname.endswith(".mp3"): continue
            fp=os.path.join(SONGS_DIR,fname)
            songs.append({"filename":fname,
                "name":fname.replace("_"," ").replace(".mp3","").title(),
                "size_kb":os.path.getsize(fp)//1024,
                "duration_sec":round(get_duration(fp),1),
                "mapped_keys":[k for k,v in _MAP.items() if v==fname]})
    except: pass
    return jsonify(songs)

@app.route("/api/upload-song",methods=["POST"])
def upload_song():
    if "file" not in request.files: return jsonify({"error":"No file"}),400
    f=request.files["file"]
    if not f.filename.lower().endswith(".mp3"): return jsonify({"error":"Only .mp3"}),400
    safe=re.sub(r"[^\w\-.]","_",f.filename).lower()
    fp=os.path.join(SONGS_DIR,safe); f.save(fp)
    key=request.form.get("rhyme_key","").strip().lower() or auto_key(safe) or ""
    if key: _MAP[key]=safe; save_mapping(_MAP)
    return jsonify({"ok":True,"filename":safe,
                    "duration_sec":round(get_duration(fp),1),"mapped_to":key or None})

@app.route("/api/delete-song/<fname>",methods=["DELETE"])
def delete_song(fname):
    safe=re.sub(r"[^\w\-.]","_",fname)
    fp=os.path.join(SONGS_DIR,safe)
    if not os.path.exists(fp): return jsonify({"error":"Not found"}),404
    os.remove(fp)
    for k,v in list(_MAP.items()):
        if v==safe: del _MAP[k]
    save_mapping(_MAP)
    return jsonify({"ok":True})

@app.route("/api/map-song",methods=["POST"])
def map_song():
    data=request.json or {}
    key=data.get("rhyme_key","").strip().lower(); fname=data.get("filename","").strip()
    if not key or not fname: return jsonify({"error":"rhyme_key and filename required"}),400
    if not os.path.exists(os.path.join(SONGS_DIR,fname)): return jsonify({"error":"File not found"}),404
    _MAP[key]=fname; save_mapping(_MAP)
    return jsonify({"ok":True,"mapped":f"{key}->{fname}"})

if __name__=="__main__":
    print("="*55)
    print("  Kids Hindi Rhymes v7 — Lofi + Hinglish Karaoke")
    print(f"  Songs: {SONGS_DIR}")
    try:
        mp3s=[f for f in os.listdir(SONGS_DIR) if f.endswith(".mp3")]
        print(f"  MP3s : {mp3s or 'NONE! backend/songs/ mein MP3 daalo'}")
    except: pass
    print(f"  Mapping: {dict(list(_MAP.items())[:4])}")
    print("  http://127.0.0.1:5000")
    print("="*55)
    app.run(debug=True,host="0.0.0.0",port=5000)