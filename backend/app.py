"""
app.py — Kids Hindi Rhymes v6
==============================
KEY CHANGES from v5:
  - NO TTS voice at all — sirf Suno song bajega
  - Video length = Suno song ki exact length
  - Lyrics auto-spread across song duration
  - Better cat animation (dance moves, not just bounce)
  - Hindi font fixed for Windows (Nirmala.ttf)
  - Lyric timing: lines equally divided across song
"""

import os, json, asyncio, subprocess, shutil, threading, uuid, re, math, random
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import requests as req_lib

_here = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_here, ".env"))

app = Flask(__name__)
CORS(app, origins="*")

W, H   = 1080, 1920
FPS    = 30
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
            f = ImageFont.truetype(p, size)
            _fc[key] = f; return f
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
    # Auto-add any mp3 in songs/ not yet mapped
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
    """Find best matching MP3 for text. Returns full path or None."""
    text = re.sub(r"[^\w\s]"," ",(text or "").lower()).strip()
    try: all_mp3=[f for f in os.listdir(SONGS_DIR) if f.endswith(".mp3")]
    except: all_mp3=[]

    print(f"[Song] search='{text}' | files={all_mp3}")

    # 1. Mapping exact word
    for kw,fname in _MAP.items():
        if kw in text.split():
            fp=os.path.join(SONGS_DIR,fname)
            if os.path.exists(fp): return fp
    # 2. Mapping substring
    for kw,fname in _MAP.items():
        if kw in text:
            fp=os.path.join(SONGS_DIR,fname)
            if os.path.exists(fp): return fp
    # 3. Filename fuzzy
    for fname in all_mp3:
        fw=re.sub(r"[_\-\.]"," ",fname.lower().replace(".mp3",""))
        for w in text.split():
            if len(w)>=4 and w in fw:
                return os.path.join(SONGS_DIR,fname)
    # 4. Any mp3
    if all_mp3:
        return os.path.join(SONGS_DIR,sorted(all_mp3)[0])
    return None

def get_duration(path):
    """Get audio/video duration in seconds."""
    try:
        r=subprocess.run([FFPROBE,"-v","quiet","-print_format","json",
                          "-show_streams",path],capture_output=True,text=True)
        for s in json.loads(r.stdout).get("streams",[]):
            if "duration" in s: return float(s["duration"])
    except: pass
    return 30.0

# ── Story configs ─────────────────────────────────────────────────────────────
CONFIGS = {
    "billi":  {"char":"cat",      "bg":("#ff9a9e","#fecfef"), "accent":"#dc2060"},
    "machli": {"char":"fish",     "bg":("#0096c7","#caf0f8"), "accent":"#0077a8"},
    "hathi":  {"char":"elephant", "bg":("#52b788","#b7e4c7"), "accent":"#2d6a4f"},
    "chanda": {"char":"moon",     "bg":("#03045e","#023e8a"), "accent":"#4895ef"},
    "tara":   {"char":"star",     "bg":("#10002b","#3c096c"), "accent":"#9d4edd"},
    "twinkle":{"char":"star",     "bg":("#10002b","#3c096c"), "accent":"#9d4edd"},
    "lakdi":  {"char":"horse",    "bg":("#ff6b35","#ffd166"), "accent":"#e05000"},
    "johny":  {"char":"kid",      "bg":("#ff99c8","#fcf6bd"), "accent":"#e0006a"},
    "nani":   {"char":"peacock",  "bg":("#2d6a4f","#74c69d"), "accent":"#1b4332"},
    "lori":   {"char":"moon",     "bg":("#1a1a2e","#16213e"), "accent":"#e2b714"},
    "default":{"char":"cat",      "bg":("#f72585","#7209b7"), "accent":"#b5179e"},
}

def get_config(text):
    text=(text or "").lower()
    for k,cfg in CONFIGS.items():
        if k in text and k!="default": return cfg
    return CONFIGS["default"]

# ═══════════════════════════════════════════════════════════════════════════════
#  ANIMATION — better cat with dance moves
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
        r=rng.randint(15,55)
        sx=rng.uniform(0.05,0.95)*W
        sy=rng.uniform(0.05,0.52)*H
        ph=rng.random()*10
        cx2=int((sx+math.sin(t*0.4+ph)*50)%W)
        cy2=int((sy-t*35+ph*180)%(H*0.52))
        d.ellipse([cx2-r,cy2-r,cx2+r,cy2+r],fill=light)

def draw_stars_bg(d, t):
    rng=random.Random(99)
    for _ in range(180):
        sx=rng.randint(0,W); sy=rng.randint(0,int(H*0.58))
        fl=0.3+0.7*abs(math.sin(t*rng.uniform(1,5)+rng.random()*6.28))
        br=int(150*fl+80); sr=rng.choice([1,1,2,2,3])
        d.ellipse([sx-sr,sy-sr,sx+sr,sy+sr],fill=(br,br,min(255,br+20)))

# ── CAT — full dance animation ────────────────────────────────────────────────
def draw_cat(d, cx, cy, t):
    # Multiple dance moves cycling
    phase = (t % 8)  # 8 second cycle

    if phase < 2:    # bounce
        bounce = int(abs(math.sin(t*3.5))*42)
        swing  = 0
    elif phase < 4:  # side sway
        bounce = int(abs(math.sin(t*2))*20)
        swing  = int(math.sin(t*2)*35)
    elif phase < 6:  # fast dance
        bounce = int(abs(math.sin(t*6))*30)
        swing  = int(math.sin(t*5)*20)
    else:            # spin feel (head tilt)
        bounce = int(abs(math.sin(t*3))*25)
        swing  = int(math.sin(t*3)*45)

    cy -= bounce
    cx += swing

    bc=(255,140,50); bel=(255,200,150); ec=(220,90,25); ie=(255,170,185)

    # Shadow
    d.ellipse([cx-105,cy+165,cx+105,cy+195],fill=(200,80,100))

    # Tail — more animated
    px,py=None,None
    tail_wave = math.sin(t*2.5)*0.4
    for i in range(22):
        ang=i/22*math.pi+t*1.2+tail_wave
        tx2=cx+118+int(58*math.sin(ang)); ty2=cy+50-i*11
        if px: d.line([(px,py),(tx2,ty2)],fill=bc,width=30)
        px,py=tx2,ty2
    if px: d.ellipse([px-18,py-18,px+18,py+18],fill=(255,175,75))

    # Body
    d.ellipse([cx-112,cy-145,cx+112,cy+75],fill=bc)
    d.ellipse([cx-60,cy-95,cx+60,cy+52],fill=bel)

    # Head
    hr=118; hx=cx; hy=cy-145-hr+18

    # Ears
    d.polygon([(hx-90,hy+18),(hx-42,hy-hr-82),(hx-10,hy-hr+16)],fill=ec)
    d.polygon([(hx-78,hy+10),(hx-44,hy-hr-58),(hx-15,hy-hr+11)],fill=ie)
    d.polygon([(hx+90,hy+18),(hx+42,hy-hr-82),(hx+10,hy-hr+16)],fill=ec)
    d.polygon([(hx+78,hy+10),(hx+44,hy-hr-58),(hx+15,hy-hr+11)],fill=ie)
    d.ellipse([hx-hr,hy-hr,hx+hr,hy+hr],fill=bc)

    # Eyes — blink + happy squint during fast dance
    blink=abs(math.sin(t*0.55))>0.94
    squint = (4 <= phase < 6)
    for xo in [-38,38]:
        ex2,ey2=hx+xo,hy-11
        if blink:
            d.arc([ex2-22,ey2-6,ex2+22,ey2+6],195,345,fill=(40,25,8),width=7)
        elif squint:
            d.arc([ex2-22,ey2-8,ex2+22,ey2+12],200,340,fill=(40,25,8),width=7)
        else:
            d.ellipse([ex2-22,ey2-20,ex2+22,ey2+20],fill=(255,255,255))
            d.ellipse([ex2-13,ey2-18,ex2+13,ey2+18],fill=(40,25,8))
            d.ellipse([ex2-7,ey2-16,ex2-2,ey2-9],fill=(255,255,255))
            d.arc([ex2-21,ey2-19,ex2+21,ey2+19],0,360,fill=(70,170,70),width=3)

    # Nose + mouth
    d.polygon([(hx,hy+16),(hx-13,hy+4),(hx+13,hy+4)],fill=(255,110,145))
    smile = 0.15 if squint else 0
    d.arc([hx-26,hy+22-int(smile*10),hx+26,hy+52],15,165,fill=(170,55,75),width=6)

    # Cheeks
    for xo in [-68,68]:
        d.ellipse([hx+xo-28,hy+8,hx+xo+28,hy+36],fill=(255,155,155))

    # Whiskers
    wy=hy+24
    for wx1,wx2,wy1,wy2 in [(-20,-94,2,-10),(-20,-90,11,-2),(-20,-86,20,6)]:
        d.line([(hx+wx1,wy+wy1),(hx+wx2,wy+wy2)],fill=(200,155,115),width=3)
    for wx1,wx2,wy1,wy2 in [(20,94,2,-10),(20,90,11,-2),(20,86,20,6)]:
        d.line([(hx+wx1,wy+wy1),(hx+wx2,wy+wy2)],fill=(200,155,115),width=3)

    # Arms — different moves per phase
    if phase < 2:   # bounce: arms up-down
        aw=math.sin(t*3.5)*60
        d.line([cx-112,cy-35,cx-180,cy-82-int(aw)],fill=bc,width=40)
        d.ellipse([cx-210,cy-112-int(aw)-30,cx-158,cy-112-int(aw)+30],fill=bc)
        d.line([cx+112,cy-35,cx+180,cy-82+int(aw)],fill=bc,width=40)
        d.ellipse([cx+158,cy-112+int(aw)-30,cx+210,cy-112+int(aw)+30],fill=bc)
    elif phase < 4: # sway: arms to sides
        aw=math.sin(t*2)*30
        d.line([cx-112,cy-35,cx-185,cy-60-int(aw)],fill=bc,width=40)
        d.ellipse([cx-215,cy-88-int(aw)-30,cx-163,cy-88-int(aw)+30],fill=bc)
        d.line([cx+112,cy-35,cx+185,cy-60+int(aw)],fill=bc,width=40)
        d.ellipse([cx+163,cy-88+int(aw)-30,cx+215,cy-88+int(aw)+30],fill=bc)
    elif phase < 6: # fast: both arms up (celebration)
        aw=abs(math.sin(t*6))*50
        d.line([cx-112,cy-35,cx-165,cy-95-int(aw)],fill=bc,width=40)
        d.ellipse([cx-195,cy-125-int(aw)-30,cx-143,cy-125-int(aw)+30],fill=bc)
        d.line([cx+112,cy-35,cx+165,cy-95-int(aw)],fill=bc,width=40)
        d.ellipse([cx+143,cy-125-int(aw)-30,cx+195,cy-125-int(aw)+30],fill=bc)
    else:           # spin: one arm up one down
        aw=math.sin(t*3)*70
        d.line([cx-112,cy-35,cx-172,cy-75-int(aw)],fill=bc,width=40)
        d.ellipse([cx-202,cy-105-int(aw)-30,cx-150,cy-105-int(aw)+30],fill=bc)
        d.line([cx+112,cy-35,cx+172,cy-75+int(aw*0.5)],fill=bc,width=40)
        d.ellipse([cx+150,cy-105+int(aw*0.5)-30,cx+202,cy-105+int(aw*0.5)+30],fill=bc)

    # Legs
    lk=int(math.sin(t*4)*18)
    for xo in [-44,44]:
        d.ellipse([cx+xo-40,cy+50+lk,cx+xo+40,cy+108+lk],fill=bc)


def draw_fish(d, cx, cy, t):
    sx=int(math.sin(t*1.6)*80); sy=int(math.sin(t*2.4)*30)
    cx+=sx; cy+=sy
    bc=(50,180,255); sc=(30,140,220)
    d.ellipse([cx-130,cy-72,cx+130,cy+72],fill=bc)
    tw=int(math.sin(t*4)*24)
    d.polygon([(cx+118,cy-12+tw),(cx+118,cy+12+tw),(cx+180,cy-72),(cx+180,cy+72)],fill=sc)
    d.polygon([(cx-26,cy-72),(cx+26,cy-72),(cx,cy-125)],fill=sc)
    for i in range(3):
        for j in range(2):
            d.arc([cx-78+i*58,cy-28+j*46,cx-22+i*58,cy+18+j*46],0,180,fill=sc,width=4)
    d.ellipse([cx-85,cy-26,cx-46,cy+16],fill=(255,255,255))
    d.ellipse([cx-76,cy-19,cx-55,cy+9],fill=(20,20,20))
    d.ellipse([cx-73,cy-17,cx-66,cy-10],fill=(255,255,255))
    d.arc([cx-72,cy+8,cx-28,cy+40],10,160,fill=(255,255,255),width=5)
    for i in range(4):
        bx=cx-104+i*12; by=int((cy-65-i*32-t*45+i*20)%(H*0.45)); br=11+i*5
        d.ellipse([bx-br,by-br,bx+br,by+br],fill=(200,235,255))


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
    d.ellipse([cx-138-ef,cy-182,cx-54-ef,cy-58],fill=(220,190,220))
    d.ellipse([cx+40+ef,cy-195,cx+152+ef,cy-40],fill=dark)
    d.ellipse([cx+54+ef,cy-182,cx+138+ef,cy-58],fill=(220,190,220))
    for xo in [-36,36]:
        ex2,ey2=cx+xo,cy-128
        d.ellipse([ex2-18,ey2-18,ex2+18,ey2+18],fill=(255,255,255))
        d.ellipse([ex2-10,ey2-14,ex2+10,ey2+14],fill=(40,25,15))
    lk=int(math.sin(t*2.8)*16)
    for xo in [-52,52]:
        d.rounded_rectangle([cx+xo-28,cy+42+lk,cx+xo+28,cy+130+lk],radius=12,fill=col)


def draw_moon(d, cx, cy, t):
    glow=int(abs(math.sin(t*1.5))*28)
    for r in range(158+glow,95,-20): d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(255,240,100))
    d.ellipse([cx-112,cy-112,cx+112,cy+112],fill=(255,230,50))
    d.ellipse([cx+28,cy-100,cx+175,cy+100],fill=(50,30,150))
    fx=cx-20
    for xo in [-26,20]:
        ex2,ey2=fx+xo,cy-20
        d.ellipse([ex2-13,ey2-13,ex2+13,ey2+13],fill=(80,50,10))
        d.ellipse([ex2-5,ey2-11,ex2+1,ey2-4],fill=(255,255,255))
    d.arc([fx-24,cy+8,fx+24,cy+38],10,170,fill=(180,100,30),width=6)
    for i in range(5):
        ang=i/5*2*math.pi+t*0.55
        sx2=cx+int(162*math.cos(ang)); sy2=cy+int(162*math.sin(ang))
        pts=[]
        for j in range(10):
            a=j/10*2*math.pi-math.pi/2; dist=24 if j%2==0 else 11
            pts.append((sx2+int(dist*math.cos(a)),sy2+int(dist*math.sin(a))))
        d.polygon(pts,fill=(255,230,50))


def draw_star(d, cx, cy, t):
    pulse=1.0+0.20*math.sin(t*3); r=int(122*pulse)
    for gr in range(r+40,r,-12):
        fc=lerp_col((255,240,100),(50,30,100),(gr-r)/40)
        d.ellipse([cx-gr,cy-gr,cx+gr,cy+gr],fill=fc)
    pts=[]
    for i in range(10):
        ang=i/10*2*math.pi-math.pi/2+t*0.55
        dist=r if i%2==0 else r//2
        pts.append((cx+int(dist*math.cos(ang)),cy+int(dist*math.sin(ang))))
    if pts: d.polygon(pts,fill=(255,235,50))
    for xo in [-28,28]:
        ex2,ey2=cx+xo,cy-10
        d.ellipse([ex2-15,ey2-15,ex2+15,ey2+15],fill=(100,70,0))
    d.arc([cx-20,cy+8,cx+20,cy+32],10,170,fill=(180,120,0),width=6)
    for i in range(6):
        ang=i/6*2*math.pi+t*2.2
        sx2=cx+int((r+62)*math.cos(ang)); sy2=cy+int((r+62)*math.sin(ang))
        pts2=[]
        for j in range(8):
            a=j/8*2*math.pi-math.pi/4; dist=18 if j%2==0 else 7
            pts2.append((sx2+int(dist*math.cos(a)),sy2+int(dist*math.sin(a))))
        d.polygon(pts2,fill=(255,255,200))


def draw_horse(d, cx, cy, t):
    trot=int(math.sin(t*5.5)*26); cx+=int(math.sin(t*2.2)*22); cy-=abs(trot)
    col=(160,90,30); dark=(120,60,15)
    d.ellipse([cx-108,cy+172,cx+108,cy+200],fill=(30,20,10))
    d.ellipse([cx-112,cy-112,cx+112,cy+78],fill=col)
    d.polygon([(cx-38,cy-112),(cx+38,cy-112),(cx+58,cy-192),(cx-20,cy-204)],fill=col)
    d.ellipse([cx-64,cy-238,cx+52,cy-144],fill=col)
    d.ellipse([cx-46,cy-208,cx-14,cy-178],fill=(255,255,255))
    d.ellipse([cx-40,cy-203,cx-20,cy-183],fill=(30,20,10))
    d.polygon([(cx-10,cy-242),(cx-34,cy-282),(cx+2,cy-276)],fill=col)
    d.polygon([(cx-9,cy-246),(cx-26,cy-268),(cx+1,cy-264)],fill=(255,180,180))
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
        d.ellipse([fx2-6,fy2-6,fx2+6,fy2+6],fill=(100,200,255))
    d.ellipse([cx-58,cy-104,cx+58,cy+66],fill=(0,150,100))
    d.ellipse([cx-36,cy-162,cx+36,cy-84],fill=(0,150,100))
    for i in range(3):
        d.line([(cx-10+i*10,cy-162),(cx-14+i*10,cy-198)],fill=(0,200,150),width=7)
        d.ellipse([cx-20+i*10,cy-212,cx-6+i*10,cy-195],fill=(0,200,150))


def draw_kid(d, cx, cy, t):
    phase=(t%6)
    bounce=int(abs(math.sin(t*3.5))*30); cy-=bounce
    if phase<3: swing=int(math.sin(t*2)*28)
    else: swing=int(math.sin(t*4)*18)
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
            d.ellipse([ex2-6,ey2-14,ex2+1,ey2-7],fill=(255,255,255))
    sy2=int(math.sin(t*2.2)*3)
    d.arc([hx-28,hy+16+sy2,hx+28,hy+50+sy2],15,165,fill=(180,60,80),width=7)
    for cxo in [-54,54]: d.ellipse([hx+cxo-26,hy+8,hx+cxo+26,hy+38],fill=(255,160,160))
    aw_l=math.sin(t*3.8)*62; aw_r=math.sin(t*3.8+math.pi)*62
    d.line([cx-92,cy-65,cx-168,cy-100-int(aw_l)],fill=shirt,width=38)
    d.ellipse([cx-192,cy-124-int(aw_l)-26,cx-148,cy-124-int(aw_l)+26],fill=skin)
    d.line([cx+92,cy-65,cx+168,cy-100-int(aw_r)],fill=shirt,width=38)
    d.ellipse([cx+148,cy-124-int(aw_r)-26,cx+192,cy-124-int(aw_r)+26],fill=skin)


CHARS = {
    "cat":draw_cat,"fish":draw_fish,"elephant":draw_elephant,
    "moon":draw_moon,"star":draw_star,"horse":draw_horse,
    "peacock":draw_peacock,"kid":draw_kid,
}

# ── Lyrics display ────────────────────────────────────────────────────────────
def draw_lyrics(d, lines_data, t, accent_rgb):
    """Show current lyric line with word-by-word highlight + prev/next dimmed."""
    cur = 0
    for i,ld in enumerate(lines_data):
        if t >= ld["start"]: cur = i

    slots = []
    if cur > 0:                    slots.append((cur-1, False))
    slots.append((cur, True))
    if cur < len(lines_data)-1:    slots.append((cur+1, False))

    spacing = 200
    center_y = int(H * 0.38)
    base_y = center_y - spacing*(len(slots)-1)//2

    for i,(li,active) in enumerate(slots):
        if li<0 or li>=len(lines_data): continue
        text = lines_data[li]["text"]
        y = base_y + i*spacing

        if active:
            fnt = get_font(90, bold=True)
            dur = max(0.1, lines_data[li]["end"]-lines_data[li]["start"])
            prog = max(0,min(1,(t-lines_data[li]["start"])/dur))
            words = text.split()
            shown = " ".join(words[:max(1,int(prog*(len(words)+0.5)))])

            try:
                bb=d.textbbox((0,0),text,font=fnt); fw=min(bb[2]-bb[0],W-100); lh=bb[3]-bb[1]
                bb2=d.textbbox((0,0),shown,font=fnt); sw=bb2[2]-bb2[0]
            except: fw=680; sw=340; lh=90

            pad=46; x1=(W-fw)//2-pad; x2=(W+fw)//2+pad
            # shadow
            d.rounded_rectangle([x1+6,y-22+6,x2+6,y+lh+22+6],radius=34,fill=(140,140,140))
            # pill
            d.rounded_rectangle([x1,y-22,x2,y+lh+22],radius=34,fill=(255,255,255))
            d.rounded_rectangle([x1,y-22,x2,y+lh+22],radius=34,outline=accent_rgb,width=6)
            tx=(W-sw)//2
            d.text((tx,y),shown,fill=tuple(max(0,c-30) for c in accent_rgb),font=fnt)
        else:
            fnt=get_font(58,bold=False)
            try:
                bb=d.textbbox((0,0),text,font=fnt); lw=min(bb[2]-bb[0],W-80); lh=bb[3]-bb[1]
            except: lw=480; lh=58
            tx=(W-lw)//2
            d.rounded_rectangle([tx-20,y-14,tx+lw+20,y+lh+14],radius=18,fill=(0,0,0))
            d.text((tx,y),text,fill=(215,205,240),font=fnt)


def draw_title(d, title, accent_rgb):
    if not title: return
    clean = re.sub(r"[^\u0000-\u007F\u0900-\u097F\s\-\.]","",title).strip() or title[:30]
    fnt = get_font(54,bold=True)
    try:
        bb=d.textbbox((0,0),clean,font=fnt); tw=bb[2]-bb[0]
    except: tw=len(clean)*34
    tw=max(tw,180); tx=(W-tw)//2
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


def render_frame(lines_data, fi, total_frames, cfg, title):
    t = fi/FPS
    progress = fi/max(total_frames,1)
    col1,col2 = cfg["bg"]
    accent = hex_rgb(cfg["accent"])

    img = Image.new("RGB",(W,H),(20,20,40))
    d   = ImageDraw.Draw(img)

    draw_bg(d,col1,col2,t)

    # dark theme → stars, light → bokeh
    is_dark = hex_rgb(col1)[0]<80
    if is_dark: draw_stars_bg(d,t)
    else: draw_bokeh(d,accent,t)

    draw_title(d,title,accent)

    char_fn = CHARS.get(cfg["char"],draw_cat)
    char_fn(d, W//2, int(H*0.76), t)

    if lines_data: draw_lyrics(d,lines_data,t,accent)
    draw_progress(d,progress,accent)

    return img

# ═══════════════════════════════════════════════════════════════════════════════
#  VIDEO BUILDER — NO TTS, Suno song length
# ═══════════════════════════════════════════════════════════════════════════════

def build_video(content, job_id, builtin_key="", char_override=""):
    tmp = os.path.join("C:/tmp" if os.name=="nt" else "/tmp", f"kh6_{job_id}")
    os.makedirs(f"{tmp}/frames", exist_ok=True)

    lines_text = content.get("lines",[])
    title      = content.get("title","")
    search_key = f"{builtin_key} {title}".strip()

    # ── Find Suno song ────────────────────────────────────────────────────────
    jobs[job_id]["message"] = "🎵 Step 1/3: Suno song dhundh raha hai..."
    song_path = find_song(search_key)

    if not song_path:
        raise Exception(
            f"Koi MP3 nahi mila! backend/songs/ mein Suno .mp3 daalo.\n"
            f"Search key: '{search_key}'\n"
            f"Songs folder: {SONGS_DIR}"
        )

    song_dur = get_duration(song_path)
    total_frames = int(song_dur * FPS)
    jobs[job_id]["message"] = f"🎵 Song mila: {os.path.basename(song_path)} ({song_dur:.1f}s)"
    print(f"[Build] Song: {song_path} | Duration: {song_dur:.1f}s | Frames: {total_frames}")

    # ── Story config ──────────────────────────────────────────────────────────
    cfg = get_config(search_key)
    if char_override and char_override in CHARS:
        cfg = dict(cfg); cfg["char"] = char_override

    # ── Lyrics timing: equally spaced across song ─────────────────────────────
    n = len(lines_text)
    if n == 0:
        lines_data = []
    else:
        gap = song_dur / n
        lines_data = []
        for i,txt in enumerate(lines_text):
            start = i*gap + 0.3
            end   = (i+1)*gap - 0.2
            lines_data.append({"text":txt,"start":start,"end":end})

    # ── Render frames ─────────────────────────────────────────────────────────
    jobs[job_id]["message"] = "🎨 Step 2/3: Animation frames render ho rahi hain..."
    print(f"[Build] Rendering {total_frames} frames...")

    for fi in range(total_frames):
        if fi % 30 == 0:
            pct = 10 + fi*75//max(total_frames,1)
            jobs[job_id]["progress"] = pct

        img = render_frame(lines_data, fi, total_frames, cfg, title)
        img.save(f"{tmp}/frames/f{fi:05d}.png")

    # ── Encode: frames + Suno audio ──────────────────────────────────────────
    jobs[job_id]["message"] = "🎬 Step 3/3: Video encode ho rahi hai..."
    out_dir = "C:/tmp/kh6_out" if os.name=="nt" else "/tmp/kh6_out"
    os.makedirs(out_dir,exist_ok=True)
    out = f"{out_dir}/{job_id}.mp4"

    r = subprocess.run([
        FFMPEG,
        "-framerate",str(FPS),
        "-i",f"{tmp}/frames/f%05d.png",
        "-i",song_path,                    # Suno song directly as audio
        "-c:v","libx264","-preset","fast","-crf","20",
        "-vf","scale=1080:1920","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k",
        "-shortest",                        # video = song length
        out,"-y","-loglevel","error"
    ], capture_output=True, text=True)

    if r.returncode != 0:
        raise Exception(f"FFmpeg encode failed: {r.stderr[:300]}")

    shutil.rmtree(tmp,ignore_errors=True)
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
        ct  = params.get("content_type","rhyme")
        bk  = params.get("builtin_key","")
        cl  = params.get("custom_lines",[])
        top = params.get("topic","")
        cha = params.get("char_override","")

        if bk and bk in BUILTIN:      content=BUILTIN[bk]
        elif cl:                       content={"title":top or "Meri Kavita","lines":cl}
        elif top:
            job["message"]="✍️ AI se likh raha hoon..."
            content=generate_ai(top,ct)
            if not content:
                job["status"]="failed"; job["message"]="AI fail. GROQ_API_KEY check karo."; return
        else:
            job["status"]="failed"; job["message"]="Content chahiye (builtin/custom/AI)."; return

        job["content"]=content
        vp=build_video(content,job_id,builtin_key=bk or top,char_override=cha)
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
    return jsonify({"ok":True,"voices":["swara","madhur"],
        "builtins":list(BUILTIN.keys()),"suno_songs":mp3s,
        "songs_dir":SONGS_DIR,"mapping":_MAP,
        "ai":{"groq":bool(GROQ_KEY),"gemini":bool(GEMINI_KEY)}})

@app.route("/api/builtins")
def builtins_api():
    return jsonify({k:{"title":v["title"],"type":"rhyme"} for k,v in BUILTIN.items()})

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
    print("  Kids Hindi Rhymes v6 — NO TTS, Suno Only")
    print(f"  Songs: {SONGS_DIR}")
    try:
        mp3s=[f for f in os.listdir(SONGS_DIR) if f.endswith(".mp3")]
        print(f"  MP3s : {mp3s or 'NONE! backend/songs/ mein MP3 daalo'}")
    except: pass
    print(f"  Mapping: {dict(list(_MAP.items())[:4])}")
    print("  http://127.0.0.1:5000")
    print("="*55)
    app.run(debug=True,host="0.0.0.0",port=5000)