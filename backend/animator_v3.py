"""
animator_v3.py
==============
• Story-matched characters: billi→cat, machli→fish, hathi→elephant etc.
• Word-by-word karaoke typing animation
• Suno MP3 as background music (mixed with TTS voice)
• Story-matched emojis float across screen
• Animated gradient backgrounds per rhyme theme
• Big bouncing character matched to story
"""

import math, random, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS  = 30

# ── Font loader ───────────────────────────────────────────────────────────────
_fc = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _fc: return _fc[key]
    # Priority order: Windows fonts first (for user's PC), then Linux fallbacks
    # FreeSerifBold/FreeSerif support Devanagari (Hindi) — verified working
    candidates_bold = [
        "C:/Windows/Fonts/NirmalaB.ttf",
        "C:/Windows/Fonts/mangalb.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/opentype/unifont/unifont.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    candidates_regular = [
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/mangal.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/opentype/unifont/unifont.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    pool = candidates_bold if bold else candidates_regular
    # Also try the other pool as fallback
    for path in pool + (candidates_regular if bold else candidates_bold):
        try:
            f = ImageFont.truetype(path, size)
            _fc[key] = f
            return f
        except: pass
    return ImageFont.load_default()

def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t

def lerp_col(c1, c2, t):
    if isinstance(c1, str): c1 = tuple(int(c1.lstrip('#')[i:i+2],16) for i in (0,2,4))
    if isinstance(c2, str): c2 = tuple(int(c2.lstrip('#')[i:i+2],16) for i in (0,2,4))
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def ease_out(t):
    return 1 - (1-min(1,t))**3

# ══════════════════════════════════════════════════════════════════════════════
#  STORY → CHARACTER + THEME MAPPING
# ══════════════════════════════════════════════════════════════════════════════

STORY_CONFIG = {
    # keyword → config
    "billi":   {"char":"cat",      "bg":("🌸 Pastel","#ff9a9e","#fecfef"), "emojis":["🐱","🥛","🐟","🌸","🍼","🌙"]},
    "cat":     {"char":"cat",      "bg":("🌸 Pastel","#ff9a9e","#fecfef"), "emojis":["🐱","🥛","🐟","🌸","🍼","🌙"]},
    "machli":  {"char":"fish",     "bg":("🌊 Ocean", "#0096c7","#caf0f8"), "emojis":["🐟","🐠","🌊","🐬","🐚","💧"]},
    "fish":    {"char":"fish",     "bg":("🌊 Ocean", "#0096c7","#caf0f8"), "emojis":["🐟","🐠","🌊","🐬","🐚","💧"]},
    "hathi":   {"char":"elephant", "bg":("🌿 Forest","#52b788","#b7e4c7"), "emojis":["🐘","🌿","🍃","🌳","🍎","🌺"]},
    "elephant":{"char":"elephant", "bg":("🌿 Forest","#52b788","#b7e4c7"), "emojis":["🐘","🌿","🍃","🌳","🍎","🌺"]},
    "chanda":  {"char":"moon",     "bg":("🌙 Night", "#03045e","#023e8a"), "emojis":["🌙","⭐","✨","💫","🌟","🌛"]},
    "mama":    {"char":"moon",     "bg":("🌙 Night", "#03045e","#023e8a"), "emojis":["🌙","⭐","✨","💫","🌟","🌛"]},
    "tara":    {"char":"star",     "bg":("🌌 Space", "#10002b","#3c096c"), "emojis":["⭐","🌟","💫","✨","🚀","🌙"]},
    "twinkle": {"char":"star",     "bg":("🌌 Space", "#10002b","#3c096c"), "emojis":["⭐","🌟","💫","✨","🚀","🌙"]},
    "lakdi":   {"char":"horse",    "bg":("🌅 Sunset","#ff6b35","#ffd166"), "emojis":["🐴","🌅","🌾","🏇","💨","🌻"]},
    "ghoda":   {"char":"horse",    "bg":("🌅 Sunset","#ff6b35","#ffd166"), "emojis":["🐴","🌅","🌾","🏇","💨","🌻"]},
    "johny":   {"char":"kid",      "bg":("🍭 Candy", "#ff99c8","#fcf6bd"), "emojis":["👶","🍭","🍬","🎈","🍰","🌈"]},
    "nani":    {"char":"peacock",  "bg":("🌿 Garden","#2d6a4f","#74c69d"), "emojis":["🦚","🌸","🌺","🌻","🍃","🦋"]},
    "morni":   {"char":"peacock",  "bg":("🌿 Garden","#2d6a4f","#74c69d"), "emojis":["🦚","🌸","🌺","🌻","🍃","🦋"]},
    "titli":   {"char":"butterfly","bg":("🌸 Meadow","#56cfe1","#e0fbfc"), "emojis":["🦋","🌸","🌼","🌿","☀️","🌈"]},
    "default": {"char":"kid",      "bg":("🌈 Rainbow","#f72585","#7209b7"),"emojis":["⭐","🌈","✨","🎵","💫","🌸"]},
}

def get_story_config(title_or_lines):
    """Auto-detect story type from title/lines text"""
    text = title_or_lines.lower() if title_or_lines else ""
    for keyword, cfg in STORY_CONFIG.items():
        if keyword in text and keyword != "default":
            return cfg
    return STORY_CONFIG["default"]

# ══════════════════════════════════════════════════════════════════════════════
#  BACKGROUNDS
# ══════════════════════════════════════════════════════════════════════════════

def draw_bg(d, col1, col2, t):
    for y in range(H):
        yf = y / H
        wave = math.sin(yf * math.pi * 3 + t * 0.7) * 0.04
        col = lerp_col(col1, col2, max(0, min(1, yf + wave)))
        d.line([(0, y), (W, y)], fill=col)

def draw_bokeh(d, accents, t):
    rng = random.Random(42)
    for i in range(18):
        cr  = rng.randint(40, 160)
        sx  = rng.uniform(0, W)
        sy  = rng.uniform(0, H)
        spd = rng.uniform(25, 80)
        ph  = rng.random() * 10
        col = rng.choice(accents)
        cx  = int((sx + math.sin(t*0.4+ph)*80) % W)
        cy  = int((sy - t*spd + ph*300) % H)
        for r in range(cr, 0, -20):
            fc = lerp_col(col, (255,255,255), 1-r/cr)
            fc = tuple(min(255,c) for c in fc)
            d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=fc)

def draw_stars(d, t):
    rng = random.Random(99)
    for _ in range(200):
        sx = rng.randint(0, W)
        sy = rng.randint(0, int(H*0.85))
        fl = 0.3 + 0.7*abs(math.sin(t*rng.uniform(1,5)+rng.random()*6.28))
        br = int(150*fl+80)
        sr = rng.choice([1,1,2,2,3])
        d.ellipse([sx-sr,sy-sr,sx+sr,sy+sr], fill=(br,br,min(255,br+20)))

# Emoji → shape/color mapping for story types
EMOJI_SHAPES = {
    # cat/billi
    "🐱": ("circle",  (255,140,50)),
    "🥛": ("circle",  (240,240,255)),
    "🌸": ("star4",   (255,150,180)),
    "🍼": ("circle",  (200,230,255)),
    # fish/machli
    "🐟": ("diamond", (50,180,255)),
    "🌊": ("wave",    (0,150,220)),
    "🐠": ("diamond", (255,120,50)),
    "🐚": ("circle",  (255,210,150)),
    # elephant
    "🐘": ("circle",  (180,160,200)),
    "🌿": ("star4",   (80,180,80)),
    "🍃": ("star4",   (100,200,100)),
    # moon/stars
    "🌙": ("crescent",(255,230,50)),
    "⭐": ("star5",   (255,230,50)),
    "✨": ("star4",   (255,255,200)),
    "💫": ("star4",   (220,200,255)),
    "🌟": ("star5",   (255,220,50)),
    # horse
    "🐴": ("circle",  (160,90,30)),
    "🌅": ("circle",  (255,150,50)),
    "🌾": ("star4",   (220,180,50)),
    # peacock
    "🦚": ("star5",   (0,180,100)),
    # butterfly
    "🦋": ("diamond", (255,100,200)),
    # kid/default
    "🎈": ("circle",  (255,80,80)),
    "🍭": ("star4",   (255,100,200)),
    "🌈": ("star5",   (255,180,50)),
    "🎵": ("note",    (180,100,255)),
}

def draw_shape(d, shape, cx, cy, size, color):
    r = size
    if shape == "circle":
        d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=color)
        # shine
        sr = r//3
        shine = tuple(min(255,c+80) for c in color)
        d.ellipse([cx-r+4,cy-r+4,cx-r+4+sr,cy-r+4+sr], fill=shine)
    elif shape == "star5":
        pts = []
        for i in range(10):
            angle = i/10*2*math.pi - math.pi/2
            dist = r if i%2==0 else r//2
            pts.append((cx+int(dist*math.cos(angle)), cy+int(dist*math.sin(angle))))
        d.polygon(pts, fill=color)
    elif shape == "star4":
        pts = []
        for i in range(8):
            angle = i/8*2*math.pi - math.pi/4
            dist = r if i%2==0 else r//3
            pts.append((cx+int(dist*math.cos(angle)), cy+int(dist*math.sin(angle))))
        d.polygon(pts, fill=color)
    elif shape == "diamond":
        d.polygon([(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)], fill=color)
    elif shape == "crescent":
        d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=color)
        # cutout using a lighter version to simulate crescent
        lighter = tuple(min(255,c+90) for c in color)
        d.ellipse([cx+r//3,cy-r+r//4,cx+r//3+r,cy+r-r//4], fill=(255,200,220))
    elif shape == "note":
        d.ellipse([cx-r//2,cy,cx+r//2,cy+r], fill=color)
        d.line([(cx+r//2,cy),(cx+r//2,cy-r)], fill=color, width=r//5)
    elif shape == "wave":
        # Draw as concentric rings
        for i in range(3):
            ri = r - i*(r//3)
            if ri > 4:
                d.ellipse([cx-ri,cy-ri//3,cx+ri,cy+ri//3], outline=color, width=max(2,r//8))

def draw_floating_emojis(d, emojis, t):
    rng = random.Random(77)
    for i in range(6):
        em = emojis[i % len(emojis)]
        sx = rng.uniform(0.05, 0.88)*W
        sy = rng.uniform(0.05, 0.82)*H
        sp = rng.uniform(30, 85)
        ph = rng.random()*10
        sw = math.sin(t*rng.uniform(0.4,1.1)+ph)*65
        ex = int((sx+sw) % W)
        ey = int((sy - t*sp + ph*260) % (H*0.60))  # keep in upper 60% only
        size = rng.randint(22, 48)
        pulse = 1.0 + 0.15*math.sin(t*2+i)
        sz = int(size*pulse)
        # Get shape config
        shape_info = EMOJI_SHAPES.get(em, ("circle", (200,200,255)))
        shape, color = shape_info
        # Add transparency feel via lighter color
        lighter = tuple(min(255, c+60) for c in color)
        try:
            draw_shape(d, shape, ex, ey, sz, lighter)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTERS  — story-matched
# ══════════════════════════════════════════════════════════════════════════════

def draw_cat(d, cx, cy, t):
    """Cute cartoon cat — for Billi Mausi"""
    bounce = int(abs(math.sin(t*3.5))*28)
    cy -= bounce

    body_col  = (255,140,50)
    belly_col = (255,200,150)
    ear_col   = (220,90,25)
    inner_ear = (255,170,185)

    # Shadow
    d.ellipse([cx-70,cy+125,cx+70,cy+145], fill=(30,15,10))

    # Tail
    tail_pts = []
    for i in range(18):
        angle = i/18*math.pi + t*0.9
        tx2 = cx + 75 + int(35*math.sin(angle))
        ty2 = cy + 35 - i*7
        tail_pts.append((tx2,ty2))
    if len(tail_pts)>1:
        for pi in range(len(tail_pts)-1):
            d.line([tail_pts[pi],tail_pts[pi+1]], fill=body_col, width=20)
    if tail_pts:
        d.ellipse([tail_pts[-1][0]-12,tail_pts[-1][1]-12,
                   tail_pts[-1][0]+12,tail_pts[-1][1]+12], fill=(255,175,75))

    # Body
    d.ellipse([cx-68,cy-90,cx+68,cy+42], fill=body_col)
    d.ellipse([cx-36,cy-58,cx+36,cy+28], fill=belly_col)

    # --- HEAD (separate coords, always relative to body top) ---
    hr = 68              # head radius
    hx = cx
    hy = cy - 90 - hr + 10   # head center Y = body top minus head radius + small overlap

    # Ears FIRST (drawn behind head)
    # Left ear: base at (-35, hy-10), tip at (-30, hy-hr-52)
    d.polygon([
        (hx-55, hy+10),
        (hx-25, hy-hr-48),
        (hx-5,  hy-hr+8),
    ], fill=ear_col)
    d.polygon([
        (hx-48, hy+5),
        (hx-27, hy-hr-32),
        (hx-8,  hy-hr+5),
    ], fill=inner_ear)
    # Right ear
    d.polygon([
        (hx+55, hy+10),
        (hx+25, hy-hr-48),
        (hx+5,  hy-hr+8),
    ], fill=ear_col)
    d.polygon([
        (hx+48, hy+5),
        (hx+27, hy-hr-32),
        (hx+8,  hy-hr+5),
    ], fill=inner_ear)

    # Head circle (drawn OVER ears base)
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=body_col)

    # Eyes
    blink = abs(math.sin(t*0.6)) > 0.93
    for xo in [-22,22]:
        ex2,ey2 = hx+xo, hy-6
        if blink:
            d.arc([ex2-15,ey2-4,ex2+15,ey2+4], 195,345, fill=(40,25,8), width=5)
        else:
            d.ellipse([ex2-15,ey2-13,ex2+15,ey2+13], fill=(255,255,255))
            d.ellipse([ex2-7, ey2-12,ex2+7, ey2+12], fill=(40,25,8))
            d.ellipse([ex2-4, ey2-10,ex2,   ey2-5],  fill=(255,255,255))
            d.arc([ex2-14,ey2-12,ex2+14,ey2+12], 0,360, fill=(70,170,70), width=3)

    # Nose
    d.polygon([(hx,hy+10),(hx-7,hy+1),(hx+7,hy+1)], fill=(255,110,145))
    # Mouth
    d.arc([hx-14,hy+12,hx+14,hy+28], 15,165, fill=(170,55,75), width=4)
    # Cheeks
    for xo in [-40,40]:
        d.ellipse([hx+xo-15,hy+4,hx+xo+15,hy+20], fill=(255,155,155))
    # Whiskers
    wy = hy+14
    for wx1,wx2,wy1,wy2 in [(-12,-58,2,-6),(-12,-55,6,-2),(-12,-52,10,2)]:
        d.line([(hx+wx1,wy+wy1),(hx+wx2,wy+wy2)], fill=(200,155,115), width=2)
    for wx1,wx2,wy1,wy2 in [(12,58,2,-6),(12,55,6,-2),(12,52,10,2)]:
        d.line([(hx+wx1,wy+wy1),(hx+wx2,wy+wy2)], fill=(200,155,115), width=2)

    # Paws waving
    aw = math.sin(t*3.5)*32
    d.line([cx-65,cy-18,cx-108,cy-42-int(aw)], fill=body_col, width=24)
    d.ellipse([cx-124,cy-58-int(aw)-16,cx-96,cy-58-int(aw)+16], fill=body_col)
    d.line([cx+65,cy-18,cx+108,cy-42+int(aw)], fill=body_col, width=24)
    d.ellipse([cx+96,cy-58+int(aw)-16,cx+124,cy-58+int(aw)+16], fill=body_col)

    # Legs
    lk = int(math.sin(t*3.5)*8)
    for xo in [-25,25]:
        d.rounded_rectangle([cx+xo-20,cy+28+lk,cx+xo+20,cy+60+lk], radius=10, fill=body_col)

    # Legs
    lk = int(math.sin(t*3.5)*10)
    for xo in [-28,28]:
        d.ellipse([cx+xo-22,cy+22+lk,cx+xo+22,cy+58+lk], fill=body_col)

def draw_fish(d, cx, cy, t):
    """Cute cartoon fish — for Machli"""
    swim_x = int(math.sin(t*1.8)*60)
    swim_y = int(math.sin(t*2.5)*20)
    cx += swim_x
    cy += swim_y

    # Body
    body_col = (50,180,255)
    scale_col = (30,140,220)
    d.ellipse([cx-100,cy-55,cx+100,cy+55], fill=body_col)
    # Scale pattern
    for i in range(3):
        for j in range(2):
            sx2 = cx - 60 + i*45
            sy2 = cy - 20 + j*35
            d.arc([sx2-20,sy2-15,sx2+20,sy2+15], 0,180, fill=scale_col, width=3)

    # Tail fin
    tail_wave = int(math.sin(t*4)*18)
    d.polygon([
        (cx+90,cy-8+tail_wave),(cx+90,cy+8+tail_wave),
        (cx+140,cy-50),(cx+140,cy+50)
    ], fill=(30,140,220))

    # Dorsal fin
    d.polygon([(cx-20,cy-55),(cx+20,cy-55),(cx,cy-95)], fill=(30,140,220))

    # Eye
    d.ellipse([cx-65,cy-20,cx-35,cy+10], fill=(255,255,255))
    d.ellipse([cx-58,cy-15,cx-42,cy+5], fill=(20,20,20))
    d.ellipse([cx-55,cy-13,cx-50,cy-8], fill=(255,255,255))

    # Smile
    d.arc([cx-55,cy+5,cx-20,cy+30], 10,160, fill=(255,255,255), width=4)

    # Bubbles
    for i in range(3):
        bx = cx - 80 + i*8
        by = cy - 50 - i*25 - int(t*30 + i*15) % 80
        br2 = 8 + i*4
        d.ellipse([bx-br2,by-br2,bx+br2,by+br2], fill=(200,235,255))
        d.arc([bx-br2,by-br2,bx+br2,by+br2], 200,310, fill=(255,255,255), width=2)

def draw_elephant(d, cx, cy, t):
    """Cute cartoon elephant — for Hathi Raja"""
    bounce = int(abs(math.sin(t*2.5))*20)
    cy -= bounce

    col = (180,160,200)
    dark = (140,120,165)

    # Shadow
    d.ellipse([cx-95,cy+145,cx+95,cy+168], fill=(0,0,0))

    # Body
    d.ellipse([cx-95,cy-110,cx+95,cy+50], fill=col)

    # Head
    d.ellipse([cx-80,cy-170,cx+80,cy-20], fill=col)

    # Trunk — curvy, animates
    trunk_pts = []
    for i in range(12):
        tx2 = cx - int(30*math.sin(i*0.4 + t*1.5))
        ty2 = cy - 20 + i*18
        trunk_pts.append((tx2,ty2))
    for pi in range(len(trunk_pts)-1):
        d.line([trunk_pts[pi],trunk_pts[pi+1]], fill=col, width=34)
    if trunk_pts:
        d.ellipse([trunk_pts[-1][0]-18,trunk_pts[-1][1]-10,
                   trunk_pts[-1][0]+18,trunk_pts[-1][1]+16], fill=dark)

    # Ears — big flappy
    ear_flap = int(math.sin(t*2)*8)
    d.ellipse([cx-120-ear_flap,cy-155,cx-30-ear_flap,cy-30], fill=dark)
    d.ellipse([cx-110-ear_flap,cy-145,cx-40-ear_flap,cy-45], fill=(220,190,220))
    d.ellipse([cx+30+ear_flap,cy-155,cx+120+ear_flap,cy-30], fill=dark)
    d.ellipse([cx+40+ear_flap,cy-145,cx+110+ear_flap,cy-45], fill=(220,190,220))

    # Eyes
    blink = abs(math.sin(t*0.5))>0.94
    for xo in [-28,28]:
        ex2,ey2 = cx+xo, cy-100
        if blink:
            d.arc([ex2-14,ey2-5,ex2+14,ey2+5], 195,345, fill=(60,40,20), width=5)
        else:
            d.ellipse([ex2-14,ey2-14,ex2+14,ey2+14], fill=(255,255,255))
            d.ellipse([ex2-8,ey2-10,ex2+8,ey2+10], fill=(40,25,15))
            d.ellipse([ex2-5,ey2-9,ex2+0,ey2-4], fill=(255,255,255))

    # Tusks
    d.arc([cx-50,cy-55,cx-10,cy+10], 200,290, fill=(255,240,200), width=12)
    d.arc([cx+10,cy-55,cx+50,cy+10], 250,340, fill=(255,240,200), width=12)

    # Legs
    lk = int(math.sin(t*2.5)*12)
    for xo in [-40,40]:
        d.rounded_rectangle([cx+xo-22,cy+30+lk,cx+xo+22,cy+100+lk],radius=10,fill=col)
        d.ellipse([cx+xo-24,cy+85+lk,cx+xo+24,cy+110+lk],fill=dark)

def draw_moon_character(d, cx, cy, t):
    """Cute crescent moon face — for Chanda Mama"""
    glow = int(abs(math.sin(t*1.5))*20)
    # Outer glow
    for r in range(130+glow,80,-15):
        alpha = int(40*(r-80)/(50+glow))
        col = (255,240,100)
        d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=col)

    # Moon body (crescent)
    d.ellipse([cx-90,cy-90,cx+90,cy+90], fill=(255,230,50))
    d.ellipse([cx+20,cy-80,cx+150,cy+80], fill=(50,30,150))  # cutout

    # Stars around — drawn as shapes
    for i in range(5):
        angle = i/5*2*math.pi + t*0.5
        sx2 = cx + int(130*math.cos(angle))
        sy2 = cy + int(130*math.sin(angle))
        # Draw 5-point star shape
        pts = []
        for j in range(10):
            a = j/10*2*math.pi - math.pi/2
            dist = 18 if j%2==0 else 8
            pts.append((sx2+int(dist*math.cos(a)), sy2+int(dist*math.sin(a))))
        d.polygon(pts, fill=(255,230,50))

    # Face on moon
    face_x = cx - 15
    # Eyes
    blink = abs(math.sin(t*0.7))>0.93
    for xo in [-20,15]:
        ex2,ey2 = face_x+xo, cy-15
        if blink:
            d.arc([ex2-10,ey2-4,ex2+10,ey2+4],195,345,fill=(80,50,10),width=4)
        else:
            d.ellipse([ex2-10,ey2-10,ex2+10,ey2+10],fill=(80,50,10))
            d.ellipse([ex2-4,ey2-8,ex2+1,ey2-3],fill=(255,255,255))
    # Smile
    d.arc([face_x-18,cy+5,face_x+18,cy+28],10,170,fill=(180,100,30),width=4)

def draw_horse(d, cx, cy, t):
    """Cartoon horse — for Lakdi Ki Kathi"""
    trot = int(math.sin(t*5)*18)
    cx += int(math.sin(t*2)*15)
    cy -= abs(trot)

    col = (160,90,30)
    dark = (120,60,15)

    # Shadow
    d.ellipse([cx-85,cy+155,cx+85,cy+178], fill=(0,0,0))

    # Body
    d.ellipse([cx-90,cy-90,cx+90,cy+60], fill=col)

    # Head + neck
    neck_pts = [(cx-30,cy-90),(cx+30,cy-90),(cx+45,cy-150),(cx-15,cy-160)]
    d.polygon(neck_pts, fill=col)
    d.ellipse([cx-50,cy-185,cx+40,cy-110], fill=col)

    # Mane
    for i in range(5):
        mx = cx-20+i*10
        my = cy-175+i*8
        mw = int(math.sin(t*3+i)*6)
        d.ellipse([mx-12+mw,my-18,mx+12+mw,my+18], fill=dark)

    # Eye
    d.ellipse([cx-35,cy-160,cx-10,cy-138], fill=(255,255,255))
    d.ellipse([cx-30,cy-156,cx-16,cy-142], fill=(30,20,10))
    d.ellipse([cx-28,cy-154,cx-23,cy-149], fill=(255,255,255))

    # Nostril
    d.ellipse([cx-20,cy-128,cx-5,cy-118], fill=dark)

    # Ears
    d.polygon([(cx-8,cy-188),(cx-25,cy-220),(cx+2,cy-215)], fill=col)
    d.polygon([(cx-7,cy-190),(cx-20,cy-210),(cx+1,cy-207)], fill=(255,180,180))

    # Legs — trotting
    for i,(xo,phase) in enumerate([(-38,0),(38,1),(-25,1),(25,0)]):
        lk2 = int(math.sin(t*5+phase*math.pi)*20)
        d.rounded_rectangle([cx+xo-14,cy+50+lk2,cx+xo+14,cy+130+lk2],radius=8,fill=col)
        d.ellipse([cx+xo-16,cy+118+lk2,cx+xo+16,cy+142+lk2],fill=dark)

    # Tail
    for i in range(6):
        angle = i*0.2 - 0.5 + math.sin(t*3)*0.3
        tx2 = cx+90+int(40*math.sin(angle+i*0.3))
        ty2 = cy-20+i*20
        d.ellipse([tx2-10,ty2-8,tx2+10,ty2+8], fill=dark)

def draw_star_character(d, cx, cy, t):
    """Twinkling star character — for Twinkle Twinkle"""
    pulse = 1.0 + 0.15*math.sin(t*3)
    r = int(100*pulse)
    glow_r = r + 30

    # Outer glow
    glow_col = (255,240,100)
    for gr in range(glow_r,r,-8):
        fc = lerp_col(glow_col,(50,30,100),(gr-r)/30)
        d.ellipse([cx-gr,cy-gr,cx+gr,cy+gr], fill=fc)

    # Star shape — 5 points
    pts = []
    for i in range(10):
        angle = i/10*2*math.pi - math.pi/2 + t*0.5
        dist = r if i%2==0 else r//2
        pts.append((cx+int(dist*math.cos(angle)), cy+int(dist*math.sin(angle))))
    if pts: d.polygon(pts, fill=(255,235,50))

    # Face
    blink = abs(math.sin(t*0.8))>0.93
    for xo in [-22,22]:
        ex2,ey2 = cx+xo, cy-8
        if blink:
            d.arc([ex2-12,ey2-4,ex2+12,ey2+4],195,345,fill=(100,70,0),width=4)
        else:
            d.ellipse([ex2-12,ey2-12,ex2+12,ey2+12],fill=(100,70,0))
            d.ellipse([ex2-5,ey2-10,ex2+1,ey2-4],fill=(255,255,255))
    d.arc([cx-15,cy+5,cx+15,cy+25],10,170,fill=(180,120,0),width=4)

    # Sparkles around — drawn as 4-point stars
    for i in range(6):
        angle = i/6*2*math.pi + t*2
        sx2 = cx+int((r+45)*math.cos(angle))
        sy2 = cy+int((r+45)*math.sin(angle))
        pts = []
        for j in range(8):
            a = j/8*2*math.pi - math.pi/4
            dist = 14 if j%2==0 else 5
            pts.append((sx2+int(dist*math.cos(a)), sy2+int(dist*math.sin(a))))
        d.polygon(pts, fill=(255,255,200))

def draw_peacock(d, cx, cy, t):
    """Peacock — for Nani Teri Morni"""
    # Tail feathers spread
    for i in range(7):
        angle = -math.pi/2 + (i-3)*0.28 + math.sin(t*1.5)*0.05
        fl = 180 + int(math.sin(t*2+i)*10)
        fx2 = cx + int(fl*math.cos(angle))
        fy2 = cy - 60 + int(fl*math.sin(angle))
        col = [(0,180,100),(0,150,200),(100,50,200),(0,200,150)][i%4]
        d.line([(cx,cy-60),(fx2,fy2)], fill=col, width=10)
        d.ellipse([fx2-20,fy2-20,fx2+20,fy2+20], fill=col)
        d.ellipse([fx2-10,fy2-10,fx2+10,fy2+10], fill=(0,0,80))
        d.ellipse([fx2-5,fy2-5,fx2+5,fy2+5], fill=(100,200,255))

    # Body
    d.ellipse([cx-45,cy-80,cx+45,cy+50], fill=(0,150,100))
    # Head
    d.ellipse([cx-28,cy-125,cx+28,cy-65], fill=(0,150,100))
    # Crest
    for i in range(3):
        d.line([(cx-8+i*8,cy-125),(cx-12+i*8,cy-155)],fill=(0,200,150),width=5)
        d.ellipse([cx-16+i*8,cy-163,cx-4+i*8,cy-151],fill=(0,200,150))

    # Eye
    d.ellipse([cx-12,cy-105,cx+12,cy-83], fill=(255,240,200))
    d.ellipse([cx-7,cy-101,cx+7,cy-87], fill=(20,15,5))
    d.ellipse([cx-5,cy-99,cx+0,cy-94], fill=(255,255,255))

def draw_butterfly(d, cx, cy, t):
    """Butterfly — for Titli"""
    flap = math.sin(t*4)
    wing_open = abs(flap)

    colors = [(255,100,200),(100,200,255),(255,200,50),(200,100,255)]

    # Wings
    for side,sign in [("left",-1),("right",1)]:
        wx = cx + sign*int(120*wing_open)
        # Upper wing
        d.ellipse([cx+sign*10-60,cy-120,wx+sign*20,cy-10], fill=colors[0 if side=="left" else 1])
        # Lower wing
        d.ellipse([cx+sign*10-50,cy-20,wx+sign*10,cy+90],  fill=colors[2 if side=="left" else 3])

    # Body
    d.ellipse([cx-12,cy-110,cx+12,cy+70], fill=(60,30,10))
    # Head
    d.ellipse([cx-14,cy-130,cx+14,cy-100], fill=(80,50,20))
    # Antennae
    for sign in [-1,1]:
        d.line([(cx,cy-128),(cx+sign*30,cy-170)],fill=(60,30,10),width=4)
        d.ellipse([cx+sign*26,cy-178,cx+sign*38,cy-166],fill=(255,150,50))

    # Eye
    d.ellipse([cx-7,cy-122,cx+7,cy-110],fill=(255,255,255))
    d.ellipse([cx-4,cy-120,cx+4,cy-112],fill=(20,15,5))

def draw_kid_character(d, cx, cy, t):
    """Generic cute kid — default fallback"""
    bounce = int(abs(math.sin(t*3.2))*22)
    cy -= bounce

    skin = (255,220,177)
    shirt = (255,100,100)

    d.ellipse([cx-60,cy+105,cx+60,cy+125], fill=(0,0,0))
    d.rounded_rectangle([cx-72,cy-85,cx+72,cy+10], radius=20, fill=shirt)
    d.ellipse([cx-22,cy-85+5,cx+22,cy-85+30], fill=skin)

    pants = (70,100,180)
    d.rounded_rectangle([cx-62,cy-20,cx+62,cy+110], radius=12, fill=pants)
    d.rectangle([cx-5,cy+10,cx+5,cy+110], fill=tuple(max(0,c-30) for c in pants))

    shoe = (60,40,20)
    lk = int(math.sin(t*3.2)*8)
    d.ellipse([cx-62,cy+85+lk, cx-10,cy+120+lk],  fill=shoe)
    d.ellipse([cx+10,cy+85-lk, cx+62,cy+120-lk],  fill=shoe)

    hr = 82
    hx,hy = cx, cy-85-hr+18
    d.ellipse([hx-hr+6,hy-hr+6,hx+hr+6,hy+hr+6], fill=(0,0,0))
    d.ellipse([hx-hr,hy-hr,hx+hr,hy+hr], fill=skin)

    hair = (80,50,20)
    d.ellipse([hx-hr,hy-hr,hx+hr,hy-10], fill=hair)
    d.ellipse([hx-hr-10,hy-hr+30,hx-hr+25,hy-hr+70], fill=hair)
    d.ellipse([hx+hr-25,hy-hr+30,hx+hr+10,hy-hr+70], fill=hair)

    blink = abs(math.sin(t*0.7))>0.92
    for xo in [-28,28]:
        ex2,ey2 = hx+xo, hy-10
        if blink:
            d.arc([ex2-18,ey2-6,ex2+18,ey2+6],185,355,fill=(50,30,20),width=5)
        else:
            d.ellipse([ex2-18,ey2-18,ex2+18,ey2+18],fill=(255,255,255))
            d.ellipse([ex2-11,ey2-12,ex2+11,ey2+12],fill=(80,50,200))
            d.ellipse([ex2-7,ey2-8,ex2+7,ey2+8],fill=(20,15,10))
            d.ellipse([ex2-4,ey2-10,ex2+1,ey2-5],fill=(255,255,255))

    d.ellipse([hx-8,hy+5,hx+8,hy+18],fill=tuple(max(0,c-25) for c in skin))
    sy2 = int(math.sin(t*2)*2)
    d.arc([hx-22,hy+12+sy2,hx+22,hy+38+sy2],15,165,fill=(180,60,80),width=5)
    d.arc([hx-18,hy+14+sy2,hx+18,hy+35+sy2],20,160,fill=(255,250,250),width=8)
    for cx2o in [-42,42]:
        d.ellipse([hx+cx2o-20,hy+5,hx+cx2o+20,hy+30],fill=(255,160,160))

    aw_l = math.sin(t*3.5)*45
    aw_r = math.sin(t*3.5+math.pi)*45
    d.line([cx-72,cy-50,cx-132,cy-75-int(aw_l)],fill=shirt,width=28)
    d.ellipse([cx-148,cy-90-int(aw_l)-18,cx-118,cy-90-int(aw_l)+18],fill=skin)
    d.line([cx+72,cy-50,cx+132,cy-75-int(aw_r)],fill=shirt,width=28)
    d.ellipse([cx+118,cy-90-int(aw_r)-18,cx+148,cy-90-int(aw_r)+18],fill=skin)

# Character dispatcher
CHAR_FUNCS = {
    "cat":       draw_cat,
    "fish":      draw_fish,
    "elephant":  draw_elephant,
    "moon":      draw_moon_character,
    "star":      draw_star_character,
    "horse":     draw_horse,
    "peacock":   draw_peacock,
    "butterfly": draw_butterfly,
    "kid":       draw_kid_character,
}

# ══════════════════════════════════════════════════════════════════════════════
#  WORD-BY-WORD KARAOKE
# ══════════════════════════════════════════════════════════════════════════════

def strip_non_renderable(text):
    """Remove emojis and non-Hindi/ASCII chars that cause boxes"""
    import re as _re
    # Keep: ASCII + Devanagari (Hindi) + spaces + punctuation
    clean = _re.sub(r"[^-ऀ-ॿ\s\|\-\.\,\!\?]", "", text)
    return clean.strip() or text[:20]

def draw_karaoke_v3(d, lines_data, current_idx, t, bg_col1, emojis):
    """Word-by-word karaoke — centered, clean Hindi text"""
    th_accent = bg_col1

    # Parse accent color
    if isinstance(th_accent, str):
        acc = tuple(int(th_accent.lstrip("#")[i:i+2],16) for i in (0,2,4))
    else:
        acc = th_accent

    slots = []
    if current_idx > 0:      slots.append((current_idx-1, False))
    slots.append((current_idx, True))
    if current_idx < len(lines_data)-1: slots.append((current_idx+1, False))

    n = len(slots)
    spacing = 185
    # Center the slots in lower half of screen
    center_y = int(H * 0.60)
    base_y = center_y - spacing*(n-1)//2

    for i, (li, is_active) in enumerate(slots):
        if li < 0 or li >= len(lines_data): continue
        raw_text = lines_data[li]["text"]
        text = strip_non_renderable(raw_text)
        y = base_y + i*spacing

        if is_active:
            fnt_size = 88
            fnt = get_font(fnt_size, bold=True)

            # Word-by-word progress
            line_dur = max(0.1, lines_data[li]["end"] - lines_data[li]["start"])
            prog = (t - lines_data[li]["start"]) / line_dur
            prog = max(0, min(1, prog))
            words = text.split()
            n_words = max(len(words), 1)
            words_shown = max(1, int(prog * (n_words + 0.5)))
            shown_text = " ".join(words[:min(words_shown, n_words)])

            # Measure full text for pill width (stays constant)
            try:
                bb_full = d.textbbox((0,0), text, font=fnt)
                full_w  = bb_full[2] - bb_full[0]
                lh      = bb_full[3] - bb_full[1]
                bb_show = d.textbbox((0,0), shown_text, font=fnt)
                show_w  = bb_show[2] - bb_show[0]
            except:
                full_w = max(len(text)*48, 300)
                show_w = full_w
                lh     = fnt_size

            # Clamp pill width so it never goes off screen
            max_w   = W - 80
            full_w  = min(full_w, max_w)
            pad     = 36

            # Pill centered on screen
            pill_x1 = (W - full_w) // 2 - pad
            pill_x2 = (W + full_w) // 2 + pad
            pill_y1 = y - 18
            pill_y2 = y + lh + 18

            # White semi-transparent pill
            pill_col = (255, 255, 255)
            d.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                                  radius=28, fill=pill_col)
            # Accent border
            d.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                                  radius=28, outline=acc, width=4)

            # Text centered in pill — dark color on white bg
            txt_x = (W - show_w) // 2
            # Shadow
            d.text((txt_x+2, y+2), shown_text, fill=(180,180,180), font=fnt)
            # Main text in accent/dark color
            txt_col = tuple(max(0, c-60) for c in acc) if sum(acc) > 400 else acc
            d.text((txt_x, y), shown_text, fill=txt_col, font=fnt)

        else:
            fnt_size = 56
            fnt = get_font(fnt_size, bold=False)
            try:
                bb  = d.textbbox((0,0), text, font=fnt)
                lw  = bb[2] - bb[0]
                lh  = bb[3] - bb[1]
            except:
                lw = len(text)*30; lh = fnt_size

            lw = min(lw, W-60)
            txt_x = (W - lw) // 2

            # Semi-transparent dark pill for dim lines
            d.rounded_rectangle([txt_x-16, y-10, txt_x+lw+16, y+lh+10],
                                  radius=14, fill=(0,0,0))
            # Dim white text
            d.text((txt_x+1, y+1), text, fill=(0,0,0),       font=fnt)
            d.text((txt_x,   y),   text, fill=(210,205,230),  font=fnt)

def draw_title_v3(d, title, accent_col):
    if not title: return
    # Strip emojis — PIL on Linux cant render them
    import re as _re
    clean_title = _re.sub(r"[^\u0000-\u007F\u0900-\u097F\u0A00-\u0A7F\s]", "", title).strip()
    if not clean_title: clean_title = title[:20]
    fnt = get_font(54, bold=True)
    try:
        bb = d.textbbox((0,0),clean_title,font=fnt)
        tw = bb[2]-bb[0]
    except: tw=len(clean_title)*32
    tw = max(tw, 200)
    tx = (W-tw)//2
    d.rounded_rectangle([tx-22,52,tx+tw+22,122], radius=18, fill=(0,0,0))
    d.rounded_rectangle([tx-20,54,tx+tw+20,120], radius=16,
                         fill=tuple(min(255,c+30) for c in accent_col))
    d.text((tx+2,62), clean_title, fill=(0,0,0), font=fnt)
    d.text((tx,  60), clean_title, fill=(255,255,255), font=fnt)

def draw_progress_v3(d, progress, col1, col2):
    bh = 16
    d.rectangle([0,H-bh,W,H], fill=(25,25,25))
    fw = int(W*progress)
    if fw > 2:
        for x in range(fw):
            col = lerp_col(col1, col2, x/W)
            d.line([(x,H-bh),(x,H)], fill=col)

# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render_frame_v3(lines_data, current_line_idx, fi, total_frames,
                    story_cfg, title=""):
    """
    story_cfg = from get_story_config()
    """
    t = fi / FPS
    progress = fi / max(total_frames, 1)

    _, col1, col2 = story_cfg["bg"]
    emojis = story_cfg["emojis"]
    char_name = story_cfg["char"]

    # Parse accent color from col1
    accent = tuple(int(col1.lstrip('#')[i:i+2],16) for i in (0,2,4))

    img = Image.new("RGB", (W, H), (20,20,40))
    d   = ImageDraw.Draw(img)

    # 1. Background gradient
    draw_bg(d, col1, col2, t)

    # 2. Night theme gets stars
    if "night" in story_cfg["bg"][0].lower() or "space" in story_cfg["bg"][0].lower():
        draw_stars(d, t)
    else:
        draw_bokeh(d, [accent, (255,255,255), tuple(min(255,c+80) for c in accent)], t)

    # 3. Floating emojis
    draw_floating_emojis(d, emojis, t)

    # 4. Title
    draw_title_v3(d, title, accent)

    # 5. Story-matched character — bottom right
    char_fn = CHAR_FUNCS.get(char_name, draw_kid_character)
    char_x = int(W * 0.72)
    char_y = int(H * 0.80)
    char_fn(d, char_x, char_y, t)

    # 6. Karaoke
    if lines_data:
        draw_karaoke_v3(d, lines_data, current_line_idx, t, accent, emojis)

    # 7. Progress bar
    draw_progress_v3(d, progress, accent, (255,200,80))

    return img