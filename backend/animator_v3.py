"""
animator_v3.py  — FIXED v4
============================
FIXES:
  1. Hindi font: FreeSerifBold (Linux) / Nirmala (Windows) — NO MORE BOXES
  2. Characters: 2x bigger, centered properly, NOT cut off
  3. Bokeh circles: small + subtle, don't cover characters
  4. Karaoke: clean word-by-word, proper pill design
  5. Song mixing: robust fallback chain
"""

import math, random, re
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS  = 30

# ── Font loader — Hindi support ───────────────────────────────────────────────
# FreeSerifBold works on Linux (verified), Nirmala on Windows
LINUX_BOLD = [
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
LINUX_REG = [
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
WIN_BOLD = [
    "C:/Windows/Fonts/NirmalaB.ttf",
    "C:/Windows/Fonts/mangalb.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]
WIN_REG = [
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/mangal.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]

_fc = {}
def get_font(size, bold=False):
    key = (size, bold)
    if key in _fc: return _fc[key]
    candidates = (WIN_BOLD + LINUX_BOLD) if bold else (WIN_REG + LINUX_REG)
    for path in candidates:
        try:
            f = ImageFont.truetype(path, size)
            _fc[key] = f
            return f
        except: pass
    _fc[key] = ImageFont.load_default()
    return _fc[key]

# ── Color helpers ─────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_col(c1, c2, t):
    if isinstance(c1, str): c1 = hex_to_rgb(c1)
    if isinstance(c2, str): c2 = hex_to_rgb(c2)
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

# ── Story config ──────────────────────────────────────────────────────────────
STORY_CONFIG = {
    "billi":   {"char":"cat",       "bg":("#ff9a9e","#fecfef"), "dot_col":"#ff6b9d"},
    "cat":     {"char":"cat",       "bg":("#ff9a9e","#fecfef"), "dot_col":"#ff6b9d"},
    "machli":  {"char":"fish",      "bg":("#0096c7","#caf0f8"), "dot_col":"#48cae4"},
    "fish":    {"char":"fish",      "bg":("#0096c7","#caf0f8"), "dot_col":"#48cae4"},
    "hathi":   {"char":"elephant",  "bg":("#52b788","#b7e4c7"), "dot_col":"#40916c"},
    "chanda":  {"char":"moon",      "bg":("#03045e","#023e8a"), "dot_col":"#4895ef"},
    "mama":    {"char":"moon",      "bg":("#03045e","#023e8a"), "dot_col":"#4895ef"},
    "tara":    {"char":"star",      "bg":("#10002b","#3c096c"), "dot_col":"#9d4edd"},
    "twinkle": {"char":"star",      "bg":("#10002b","#3c096c"), "dot_col":"#9d4edd"},
    "lakdi":   {"char":"horse",     "bg":("#ff6b35","#ffd166"), "dot_col":"#f4a261"},
    "johny":   {"char":"kid",       "bg":("#ff99c8","#fcf6bd"), "dot_col":"#ff85a1"},
    "nani":    {"char":"peacock",   "bg":("#2d6a4f","#74c69d"), "dot_col":"#52b788"},
    "lori":    {"char":"moon",      "bg":("#1a1a2e","#16213e"), "dot_col":"#e2b714"},
    "default": {"char":"kid",       "bg":("#f72585","#7209b7"), "dot_col":"#b5179e"},
}

def get_story_config(text):
    text = (text or "").lower()
    for kw, cfg in STORY_CONFIG.items():
        if kw in text and kw != "default":
            return cfg
    return STORY_CONFIG["default"]

# ── Background ────────────────────────────────────────────────────────────────
def draw_bg(d, col1, col2, t):
    for y in range(H):
        yf = y / H
        wave = math.sin(yf * math.pi * 4 + t * 0.6) * 0.03
        col = lerp_col(col1, col2, max(0, min(1, yf + wave)))
        d.line([(0, y), (W, y)], fill=col)

def draw_subtle_bokeh(d, dot_col, t):
    """Small subtle floating dots — don't cover characters"""
    rng = random.Random(42)
    dot_rgb = hex_to_rgb(dot_col) if isinstance(dot_col, str) else dot_col
    light = tuple(min(255, c + 80) for c in dot_rgb)
    for i in range(10):
        r = rng.randint(12, 45)
        sx = rng.uniform(0.05, 0.95) * W
        sy = rng.uniform(0.05, 0.50) * H   # only top 50%
        sp = rng.uniform(15, 50)
        ph = rng.random() * 10
        cx = int((sx + math.sin(t * 0.4 + ph) * 60) % W)
        cy = int((sy - t * sp + ph * 200) % (H * 0.50))
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=light)

def draw_stars_bg(d, t):
    """For dark themes (moon/star/lori)"""
    rng = random.Random(99)
    for _ in range(150):
        sx = rng.randint(0, W)
        sy = rng.randint(0, int(H * 0.55))
        fl = 0.3 + 0.7 * abs(math.sin(t * rng.uniform(1, 5) + rng.random() * 6.28))
        br = int(150 * fl + 80)
        sr = rng.choice([1, 1, 2, 2, 3])
        d.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(br, br, min(255, br+20)))

# ══════════════════════════════════════════════════════════════════════════════
#  CHARACTERS — all bigger, centered properly
# ══════════════════════════════════════════════════════════════════════════════

def draw_cat(d, cx, cy, t):
    """Big cute bouncing cat"""
    bounce = int(abs(math.sin(t * 3.5)) * 35)
    cy -= bounce

    bc  = (255, 140, 50)
    bel = (255, 200, 150)
    ec  = (220, 90,  25)
    ie  = (255, 170, 185)

    # Shadow
    d.ellipse([cx-95, cy+155, cx+95, cy+182], fill=(180, 80, 100))

    # Tail
    px, py = None, None
    for i in range(20):
        ang = i / 20 * math.pi + t * 0.9
        tx2 = cx + 108 + int(50 * math.sin(ang))
        ty2 = cy + 42 - i * 10
        if px is not None:
            d.line([(px, py), (tx2, ty2)], fill=bc, width=28)
        px, py = tx2, ty2
    if px:
        d.ellipse([px-16, py-16, px+16, py+16], fill=(255, 175, 75))

    # Body
    d.ellipse([cx-98, cy-125, cx+98, cy+65], fill=bc)
    d.ellipse([cx-52, cy-82,  cx+52, cy+42], fill=bel)

    # Head
    hr = 105; hx = cx; hy = cy - 125 - hr + 14

    # Ears (draw before head)
    d.polygon([(hx-78, hy+14), (hx-35, hy-hr-70), (hx-8,  hy-hr+12)], fill=ec)
    d.polygon([(hx-68, hy+8),  (hx-37, hy-hr-48), (hx-12, hy-hr+8)],  fill=ie)
    d.polygon([(hx+78, hy+14), (hx+35, hy-hr-70), (hx+8,  hy-hr+12)], fill=ec)
    d.polygon([(hx+68, hy+8),  (hx+37, hy-hr-48), (hx+12, hy-hr+8)],  fill=ie)

    # Head
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=bc)

    # Eyes
    blink = abs(math.sin(t * 0.6)) > 0.93
    for xo in [-32, 32]:
        ex2, ey2 = hx + xo, hy - 9
        if blink:
            d.arc([ex2-20, ey2-6, ex2+20, ey2+6], 195, 345, fill=(40,25,8), width=7)
        else:
            d.ellipse([ex2-20, ey2-18, ex2+20, ey2+18], fill=(255,255,255))
            d.ellipse([ex2-11, ey2-16, ex2+11, ey2+16], fill=(40,25,8))
            d.ellipse([ex2-6,  ey2-14, ex2-1,  ey2-8],  fill=(255,255,255))
            d.arc([ex2-19, ey2-17, ex2+19, ey2+17], 0, 360, fill=(70,170,70), width=3)

    # Nose
    d.polygon([(hx, hy+14), (hx-11, hy+3), (hx+11, hy+3)], fill=(255,110,145))
    d.arc([hx-20, hy+16, hx+20, hy+40], 15, 165, fill=(170,55,75), width=5)

    # Cheeks
    for xo in [-56, 56]:
        d.ellipse([hx+xo-22, hy+6, hx+xo+22, hy+30], fill=(255,155,155))

    # Whiskers
    wy = hy + 18
    for wx1, wx2, wy1, wy2 in [(-18,-80,2,-9),(-18,-76,9,-2),(-18,-72,16,5)]:
        d.line([(hx+wx1, wy+wy1), (hx+wx2, wy+wy2)], fill=(200,155,115), width=3)
    for wx1, wx2, wy1, wy2 in [(18,80,2,-9),(18,76,9,-2),(18,72,16,5)]:
        d.line([(hx+wx1, wy+wy1), (hx+wx2, wy+wy2)], fill=(200,155,115), width=3)

    # Arms waving
    aw = math.sin(t * 3.5) * 48
    d.line([cx-95, cy-26, cx-155, cy-62-int(aw)], fill=bc, width=34)
    d.ellipse([cx-179, cy-86-int(aw)-24, cx-135, cy-86-int(aw)+24], fill=bc)
    d.line([cx+95, cy-26, cx+155, cy-62+int(aw)], fill=bc, width=34)
    d.ellipse([cx+135, cy-86+int(aw)-24, cx+179, cy-86+int(aw)+24], fill=bc)

    # Legs
    lk = int(math.sin(t * 3.5) * 14)
    for xo in [-36, 36]:
        d.ellipse([cx+xo-32, cy+36+lk, cx+xo+32, cy+88+lk], fill=bc)


def draw_fish(d, cx, cy, t):
    swim_x = int(math.sin(t * 1.8) * 70)
    swim_y = int(math.sin(t * 2.5) * 25)
    cx += swim_x; cy += swim_y
    bc = (50, 180, 255); sc = (30, 140, 220)
    d.ellipse([cx-120, cy-68, cx+120, cy+68], fill=bc)
    for i in range(3):
        for j in range(2):
            sx2 = cx-72+i*54; sy2 = cy-25+j*42
            d.arc([sx2-24, sy2-18, sx2+24, sy2+18], 0, 180, fill=sc, width=4)
    tw = int(math.sin(t * 4) * 22)
    d.polygon([(cx+108, cy-10+tw),(cx+108, cy+10+tw),(cx+168, cy-62),(cx+168, cy+62)], fill=sc)
    d.polygon([(cx-24, cy-68),(cx+24, cy-68),(cx, cy-115)], fill=sc)
    d.ellipse([cx-78, cy-24, cx-42, cy+14], fill=(255,255,255))
    d.ellipse([cx-70, cy-18, cx-50, cy+6],  fill=(20,20,20))
    d.ellipse([cx-67, cy-16, cx-61, cy-10], fill=(255,255,255))
    d.arc([cx-66, cy+6, cx-24, cy+36], 10, 160, fill=(255,255,255), width=5)
    for i in range(3):
        bx = cx-96+i*10; by = int((cy-60-i*30-t*36+i*18)%(H*0.4)); br2=10+i*5
        d.ellipse([bx-br2, by-br2, bx+br2, by+br2], fill=(200,235,255))


def draw_elephant(d, cx, cy, t):
    bounce = int(abs(math.sin(t * 2.5)) * 22); cy -= bounce
    col=(180,160,200); dark=(140,120,165)
    d.ellipse([cx-110, cy+155, cx+110, cy+182], fill=(30,30,30))
    d.ellipse([cx-110, cy-130, cx+110, cy+60], fill=col)
    d.ellipse([cx-95,  cy-200, cx+95,  cy-24],  fill=col)
    px, py = None, None
    for i in range(14):
        tx2 = cx - int(36 * math.sin(i * 0.4 + t * 1.5))
        ty2 = cy - 24 + i * 22
        if px: d.line([(px,py),(tx2,ty2)], fill=col, width=40)
        px, py = tx2, ty2
    ear_f = int(math.sin(t * 2) * 10)
    d.ellipse([cx-145-ear_f, cy-185, cx-36-ear_f, cy-36], fill=dark)
    d.ellipse([cx-132-ear_f, cy-172, cx-48-ear_f, cy-54], fill=(220,190,220))
    d.ellipse([cx+36+ear_f,  cy-185, cx+145+ear_f, cy-36], fill=dark)
    d.ellipse([cx+48+ear_f,  cy-172, cx+132+ear_f, cy-54], fill=(220,190,220))
    blink = abs(math.sin(t * 0.5)) > 0.94
    for xo in [-34, 34]:
        ex2, ey2 = cx+xo, cy-120
        if blink: d.arc([ex2-16, ey2-6, ex2+16, ey2+6], 195, 345, fill=(60,40,20), width=6)
        else:
            d.ellipse([ex2-16, ey2-16, ex2+16, ey2+16], fill=(255,255,255))
            d.ellipse([ex2-9,  ey2-12, ex2+9,  ey2+12], fill=(40,25,15))
    lk = int(math.sin(t * 2.5) * 14)
    for xo in [-48, 48]:
        d.rounded_rectangle([cx+xo-26, cy+36+lk, cx+xo+26, cy+120+lk], radius=12, fill=col)


def draw_moon_character(d, cx, cy, t):
    glow = int(abs(math.sin(t * 1.5)) * 24)
    for r in range(150+glow, 90, -18):
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255,240,100))
    d.ellipse([cx-105, cy-105, cx+105, cy+105], fill=(255,230,50))
    d.ellipse([cx+24,  cy-95,  cx+170, cy+95],  fill=(50,30,150))
    face_x = cx - 18
    blink = abs(math.sin(t * 0.7)) > 0.93
    for xo in [-24, 18]:
        ex2, ey2 = face_x+xo, cy-18
        if blink: d.arc([ex2-12, ey2-5, ex2+12, ey2+5], 195, 345, fill=(80,50,10), width=5)
        else:
            d.ellipse([ex2-12, ey2-12, ex2+12, ey2+12], fill=(80,50,10))
            d.ellipse([ex2-5,  ey2-10, ex2+1,  ey2-4],  fill=(255,255,255))
    d.arc([face_x-22, cy+6, face_x+22, cy+34], 10, 170, fill=(180,100,30), width=5)
    for i in range(5):
        ang = i/5*2*math.pi + t*0.5
        sx2 = cx+int(155*math.cos(ang)); sy2 = cy+int(155*math.sin(ang))
        pts = []
        for j in range(10):
            a = j/10*2*math.pi - math.pi/2
            dist = 22 if j%2==0 else 10
            pts.append((sx2+int(dist*math.cos(a)), sy2+int(dist*math.sin(a))))
        d.polygon(pts, fill=(255,230,50))


def draw_star_character(d, cx, cy, t):
    pulse = 1.0 + 0.18*math.sin(t*3)
    r = int(115*pulse)
    for gr in range(r+36, r, -10):
        fc = lerp_col((255,240,100), (50,30,100), (gr-r)/36)
        d.ellipse([cx-gr, cy-gr, cx+gr, cy+gr], fill=fc)
    pts = []
    for i in range(10):
        ang = i/10*2*math.pi - math.pi/2 + t*0.5
        dist = r if i%2==0 else r//2
        pts.append((cx+int(dist*math.cos(ang)), cy+int(dist*math.sin(ang))))
    if pts: d.polygon(pts, fill=(255,235,50))
    blink = abs(math.sin(t*0.8))>0.93
    for xo in [-26, 26]:
        ex2, ey2 = cx+xo, cy-9
        if blink: d.arc([ex2-14, ey2-5, ex2+14, ey2+5], 195, 345, fill=(100,70,0), width=5)
        else:
            d.ellipse([ex2-14, ey2-14, ex2+14, ey2+14], fill=(100,70,0))
            d.ellipse([ex2-6,  ey2-12, ex2+1,  ey2-5],  fill=(255,255,255))
    d.arc([cx-18, cy+6, cx+18, cy+30], 10, 170, fill=(180,120,0), width=5)
    for i in range(6):
        ang = i/6*2*math.pi + t*2
        sx2 = cx+int((r+55)*math.cos(ang)); sy2 = cy+int((r+55)*math.sin(ang))
        pts2 = []
        for j in range(8):
            a = j/8*2*math.pi - math.pi/4
            dist = 16 if j%2==0 else 6
            pts2.append((sx2+int(dist*math.cos(a)), sy2+int(dist*math.sin(a))))
        d.polygon(pts2, fill=(255,255,200))


def draw_horse(d, cx, cy, t):
    trot = int(math.sin(t*5)*22); cx += int(math.sin(t*2)*18); cy -= abs(trot)
    col=(160,90,30); dark=(120,60,15)
    d.ellipse([cx-100, cy+165, cx+100, cy+192], fill=(30,20,10))
    d.ellipse([cx-105, cy-105, cx+105, cy+72], fill=col)
    d.polygon([(cx-36,cy-105),(cx+36,cy-105),(cx+54,cy-178),(cx-18,cy-190)], fill=col)
    d.ellipse([cx-60, cy-220, cx+48,  cy-132], fill=col)
    for i in range(5):
        mx=cx-24+i*12; my=cy-210+i*10; mw=int(math.sin(t*3+i)*8)
        d.ellipse([mx-14+mw, my-22, mx+14+mw, my+22], fill=dark)
    d.ellipse([cx-42, cy-192, cx-12, cy-165], fill=(255,255,255))
    d.ellipse([cx-36, cy-188, cx-18, cy-170], fill=(30,20,10))
    d.ellipse([cx-24, cy-154, cx-6,  cy-142], fill=dark)
    d.polygon([(cx-9,cy-225),(cx-30,cy-264),(cx+2,cy-258)], fill=col)
    d.polygon([(cx-8,cy-228),(cx-24,cy-252),(cx+1,cy-248)], fill=(255,180,180))
    for i,(xo,phase) in enumerate([(-46,0),(46,1),(-30,1),(30,0)]):
        lk2=int(math.sin(t*5+phase*math.pi)*24)
        d.rounded_rectangle([cx+xo-16,cy+60+lk2,cx+xo+16,cy+155+lk2],radius=10,fill=col)
        d.ellipse([cx+xo-18,cy+142+lk2,cx+xo+18,cy+170+lk2],fill=dark)


def draw_peacock(d, cx, cy, t):
    for i in range(7):
        ang = -math.pi/2 + (i-3)*0.3 + math.sin(t*1.5)*0.06
        fl = 210 + int(math.sin(t*2+i)*12)
        fx2 = cx+int(fl*math.cos(ang)); fy2 = cy-72+int(fl*math.sin(ang))
        col = [(0,180,100),(0,150,200),(100,50,200),(0,200,150)][i%4]
        d.line([(cx,cy-72),(fx2,fy2)], fill=col, width=12)
        d.ellipse([fx2-24,fy2-24,fx2+24,fy2+24], fill=col)
        d.ellipse([fx2-12,fy2-12,fx2+12,fy2+12], fill=(0,0,80))
        d.ellipse([fx2-6, fy2-6, fx2+6, fy2+6],  fill=(100,200,255))
    d.ellipse([cx-54, cy-96, cx+54, cy+60],  fill=(0,150,100))
    d.ellipse([cx-34, cy-150, cx+34, cy-78], fill=(0,150,100))
    for i in range(3):
        d.line([(cx-10+i*10,cy-150),(cx-14+i*10,cy-186)],fill=(0,200,150),width=6)
        d.ellipse([cx-19+i*10,cy-198,cx-5+i*10,cy-183],fill=(0,200,150))
    d.ellipse([cx-14,cy-126,cx+14,cy-100],fill=(255,240,200))
    d.ellipse([cx-8, cy-122,cx+8, cy-106],fill=(20,15,5))


def draw_kid_character(d, cx, cy, t):
    bounce = int(abs(math.sin(t*3.2))*26); cy -= bounce
    skin=(255,220,177); shirt=(255,100,100)
    d.ellipse([cx-72, cy+126, cx+72, cy+150], fill=(30,20,10))
    d.rounded_rectangle([cx-86, cy-102, cx+86, cy+12], radius=24, fill=shirt)
    d.ellipse([cx-26, cy-98, cx+26, cy-66], fill=skin)
    pants=(70,100,180)
    d.rounded_rectangle([cx-74, cy-24, cx+74, cy+132], radius=14, fill=pants)
    d.rectangle([cx-6, cy+12, cx+6, cy+132], fill=tuple(max(0,c-30) for c in pants))
    shoe=(60,40,20); lk=int(math.sin(t*3.2)*10)
    d.ellipse([cx-74, cy+102+lk,  cx-12, cy+144+lk],  fill=shoe)
    d.ellipse([cx+12, cy+102-lk,  cx+74, cy+144-lk],  fill=shoe)
    hr=98; hx,hy = cx, cy-102-hr+22
    d.ellipse([hx-hr+7, hy-hr+7, hx+hr+7, hy+hr+7], fill=(20,15,10))
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=skin)
    hair=(80,50,20)
    d.ellipse([hx-hr, hy-hr, hx+hr, hy-12], fill=hair)
    d.ellipse([hx-hr-12, hy-hr+36, hx-hr+30, hy-hr+84], fill=hair)
    d.ellipse([hx+hr-30, hy-hr+36, hx+hr+12, hy-hr+84], fill=hair)
    blink = abs(math.sin(t*0.7))>0.92
    for xo in [-34, 34]:
        ex2, ey2 = hx+xo, hy-12
        if blink: d.arc([ex2-22, ey2-7, ex2+22, ey2+7], 185, 355, fill=(50,30,20), width=6)
        else:
            d.ellipse([ex2-22, ey2-22, ex2+22, ey2+22], fill=(255,255,255))
            d.ellipse([ex2-13, ey2-15, ex2+13, ey2+15], fill=(80,50,200))
            d.ellipse([ex2-8,  ey2-9,  ex2+8,  ey2+9],  fill=(20,15,10))
            d.ellipse([ex2-5,  ey2-12, ex2+1,  ey2-6],  fill=(255,255,255))
    d.ellipse([hx-10, hy+6, hx+10, hy+22], fill=tuple(max(0,c-30) for c in skin))
    sy2=int(math.sin(t*2)*2)
    d.arc([hx-26, hy+14+sy2, hx+26, hy+46+sy2], 15, 165, fill=(180,60,80), width=6)
    for cxo in [-50, 50]:
        d.ellipse([hx+cxo-24, hy+6, hx+cxo+24, hy+36], fill=(255,160,160))
    aw_l=math.sin(t*3.5)*54; aw_r=math.sin(t*3.5+math.pi)*54
    d.line([cx-86, cy-60, cx-158, cy-90-int(aw_l)], fill=shirt, width=34)
    d.ellipse([cx-178, cy-108-int(aw_l)-22, cx-140, cy-108-int(aw_l)+22], fill=skin)
    d.line([cx+86, cy-60, cx+158, cy-90-int(aw_r)], fill=shirt, width=34)
    d.ellipse([cx+140, cy-108-int(aw_r)-22, cx+178, cy-108-int(aw_r)+22], fill=skin)


CHAR_FUNCS = {
    "cat":       draw_cat,
    "fish":      draw_fish,
    "elephant":  draw_elephant,
    "moon":      draw_moon_character,
    "star":      draw_star_character,
    "horse":     draw_horse,
    "peacock":   draw_peacock,
    "kid":       draw_kid_character,
}

# ══════════════════════════════════════════════════════════════════════════════
#  KARAOKE — clean word-by-word
# ══════════════════════════════════════════════════════════════════════════════

def draw_karaoke_v3(d, lines_data, current_idx, t, accent):
    slots = []
    if current_idx > 0:                      slots.append((current_idx-1, False))
    slots.append((current_idx, True))
    if current_idx < len(lines_data)-1:      slots.append((current_idx+1, False))

    spacing = 195
    center_y = int(H * 0.38)
    base_y = center_y - spacing * (len(slots)-1) // 2

    for i, (li, is_active) in enumerate(slots):
        if li < 0 or li >= len(lines_data): continue
        text = lines_data[li]["text"]
        y = base_y + i * spacing

        if is_active:
            fnt = get_font(88, bold=True)
            line_dur = max(0.1, lines_data[li]["end"] - lines_data[li]["start"])
            prog = max(0, min(1, (t - lines_data[li]["start"]) / line_dur))
            words = text.split()
            n_words = max(len(words), 1)
            shown = " ".join(words[:max(1, int(prog * (n_words + 0.5)))])

            try:
                bb = d.textbbox((0,0), text, font=fnt)
                fw = min(bb[2]-bb[0], W-100); lh = bb[3]-bb[1]
                bb2 = d.textbbox((0,0), shown, font=fnt)
                sw = bb2[2]-bb2[0]
            except:
                fw=600; sw=300; lh=88

            pad=42
            x1=(W-fw)//2-pad; x2=(W+fw)//2+pad
            # Pill shadow
            d.rounded_rectangle([x1+5, y-20+5, x2+5, y+lh+20+5], radius=32, fill=(160,160,160))
            # White pill
            d.rounded_rectangle([x1, y-20, x2, y+lh+20], radius=32, fill=(255,255,255))
            d.rounded_rectangle([x1, y-20, x2, y+lh+20], radius=32, outline=accent, width=5)
            # Text
            tx = (W-sw)//2
            d.text((tx, y), shown, fill=tuple(max(0,c-40) for c in accent), font=fnt)

        else:
            fnt = get_font(58, bold=False)
            try:
                bb = d.textbbox((0,0), text, font=fnt)
                lw = min(bb[2]-bb[0], W-80); lh = bb[3]-bb[1]
            except: lw=460; lh=58
            tx = (W-lw)//2
            d.rounded_rectangle([tx-18, y-12, tx+lw+18, y+lh+12], radius=16, fill=(0,0,0))
            d.text((tx, y), text, fill=(215,205,240), font=fnt)


def draw_title_v3(d, title, accent):
    if not title: return
    clean = re.sub(r"[^\u0000-\u007F\u0900-\u097F\s\|\-\.\,]", "", title).strip()
    if not clean: clean = title[:30]
    fnt = get_font(52, bold=True)
    try:
        bb = d.textbbox((0,0), clean, font=fnt); tw = bb[2]-bb[0]
    except: tw = len(clean)*32
    tw = max(tw, 180)
    tx = (W-tw)//2
    # Shadow
    d.rounded_rectangle([tx-26+4, 50+4, tx+tw+26+4, 122+4], radius=20, fill=(100,100,100))
    # Bg
    d.rounded_rectangle([tx-26, 50, tx+tw+26, 122], radius=20, fill=accent)
    d.text((tx+2, 60), clean, fill=(0,0,0), font=fnt)
    d.text((tx,   58), clean, fill=(255,255,255), font=fnt)


def draw_progress_v3(d, progress, col1, col2):
    bh=18
    d.rectangle([0, H-bh, W, H], fill=(25,25,25))
    fw = int(W*progress)
    if fw > 2:
        for x in range(fw):
            col = lerp_col(col1, col2, x/W)
            d.line([(x,H-bh),(x,H)], fill=col)


# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RENDER
# ══════════════════════════════════════════════════════════════════════════════

def render_frame_v3(lines_data, current_line_idx, fi, total_frames, story_cfg, title=""):
    t = fi / FPS
    progress = fi / max(total_frames, 1)

    col1, col2 = story_cfg["bg"]
    dot_col    = story_cfg.get("dot_col", col1)
    char_name  = story_cfg["char"]
    accent     = hex_to_rgb(col1)

    img = Image.new("RGB", (W, H), (20,20,40))
    d   = ImageDraw.Draw(img)

    # 1. Background
    draw_bg(d, col1, col2, t)

    # 2. Stars for dark themes, subtle dots for light themes
    is_dark = any(k in story_cfg.get("bg",("",""))[0] for k in ["#0","#1","#2","#3"])
    if is_dark:
        draw_stars_bg(d, t)
    else:
        draw_subtle_bokeh(d, dot_col, t)

    # 3. Title
    draw_title_v3(d, title, accent)

    # 4. Character — big, centered horizontally, lower portion
    char_fn = CHAR_FUNCS.get(char_name, draw_kid_character)
    char_fn(d, W//2, int(H * 0.76), t)

    # 5. Karaoke — above character
    if lines_data:
        draw_karaoke_v3(d, lines_data, current_line_idx, t, accent)

    # 6. Progress bar
    draw_progress_v3(d, progress, accent, (255, 200, 80))

    return img