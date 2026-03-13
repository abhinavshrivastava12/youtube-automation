"""
animator.py — Complete Rewrite
• Colorful animated gradient background
• Bouncing cartoon character (niche ke hisaab se alag)
• Flying emojis + sparkles + confetti
• SIRF VOICE — screen pe koi text nahi
"""

import math, random
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS  = 30

def get_font(size, bold=False):
    paths = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/NirmalaB.ttf" if bold else "C:/Windows/Fonts/Nirmala.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

def lerp_col(c1, c2, t):
    if isinstance(c1, str): c1 = tuple(int(c1.lstrip('#')[i:i+2],16) for i in (0,2,4))
    if isinstance(c2, str): c2 = tuple(int(c2.lstrip('#')[i:i+2],16) for i in (0,2,4))
    t = max(0, min(1, t))
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))


# ── Backgrounds ───────────────────────────────────────────────────────────────

def draw_gradient_bg(d, t, colors):
    n = len(colors)
    phase = (t * 0.3) % n
    i = int(phase)
    blend = phase - i
    c1 = colors[i % n]
    c2 = colors[(i+1) % n]
    c3 = colors[(i+2) % n]
    for y in range(H):
        yf = y / H
        wave = math.sin(yf * math.pi * 2 + t * 1.2) * 0.06
        top = lerp_col(c1, c2, blend)
        bot = lerp_col(c2, c3, blend)
        col = lerp_col(top, bot, max(0, min(1, yf + wave)))
        d.line([(0, y), (W, y)], fill=col)

def draw_floating_circles(d, t, color):
    rng = random.Random(42)
    for i in range(18):
        speed  = rng.uniform(40, 120)
        startx = rng.uniform(0, W)
        starty = rng.uniform(0, H)
        size   = rng.randint(60, 200)
        phase  = rng.random() * 10
        cx = int((startx + math.sin(t * 0.4 + phase) * 80) % W)
        cy = int((starty - t * speed + phase * 300) % H)
        base_col = lerp_col(color, (255, 255, 255), 0.3)
        bright   = tuple(min(255, c + 60) for c in base_col)
        for r in range(size, 0, -15):
            frac = 1 - r / size
            c = lerp_col(base_col, bright, frac)
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)

def draw_stars_bg(d, t):
    rng = random.Random(99)
    for _ in range(300):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        flicker = 0.4 + 0.6 * math.sin(t * rng.uniform(1, 5) + rng.random() * 6.28)
        br = int(120 * flicker + 80)
        sr = rng.choice([1, 1, 2, 2, 3])
        d.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(br, br, min(255, br+20)))

def draw_confetti(d, t, colors):
    rng = random.Random(77)
    for i in range(40):
        cx = int((rng.random() * W + math.sin(t * rng.uniform(0.5,1.5) + i) * 60) % W)
        cy = int((rng.random() * H + t * rng.uniform(60, 150)) % H)
        size = rng.randint(12, 28)
        col  = random.Random(i).choice(colors)
        pts = [(cx, cy-size),(cx+size//2, cy),(cx, cy+size),(cx-size//2, cy)]
        d.polygon(pts, fill=col)

def draw_sparkles(d, t, color=(255, 230, 50)):
    rng = random.Random(55)
    for i in range(30):
        sx = int((rng.random() * W + math.sin(t * 0.8 + i * 1.3) * 40) % W)
        sy = int((rng.random() * H - t * 50) % H)
        pulse = abs(math.sin(t * 3 + i * 0.7))
        size  = int(6 + 14 * pulse)
        col   = lerp_col(color, (255, 255, 255), pulse * 0.5)
        d.polygon([
            (sx, sy-size),(sx+3, sy-3),(sx+size, sy),(sx+3, sy+3),
            (sx, sy+size),(sx-3, sy+3),(sx-size, sy),(sx-3, sy-3),
        ], fill=col)


# ── Characters ────────────────────────────────────────────────────────────────

def draw_bunny(d, cx, cy, t, size=1.0):
    s = size
    bounce = int(abs(math.sin(t * 4)) * 35)
    cy = cy - bounce

    # Shadow
    sw = int(100 * s)
    d.ellipse([cx-sw, cy+int(130*s)-10, cx+sw, cy+int(130*s)+20], fill=(0,0,0))

    # Body
    bw, bh = int(90*s), int(110*s)
    d.ellipse([cx-bw, cy-bh, cx+bw, cy+int(30*s)], fill=(255, 230, 220))
    d.ellipse([cx-int(45*s), cy-int(70*s), cx+int(45*s), cy+int(20*s)], fill=(255, 200, 200))

    # Head
    hr = int(75*s)
    hx, hy = cx, cy - bh - hr + int(20*s)
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=(255, 230, 220))

    # Ears
    for ex_off, tilt in [(-int(28*s), -8), (int(28*s), 8)]:
        ex = hx + ex_off
        ear_pts = [(ex+tilt, hy-hr-int(10*s)),(ex-int(18*s), hy-hr-int(100*s)),(ex+int(18*s), hy-hr-int(100*s))]
        d.polygon(ear_pts, fill=(255, 230, 220))
        inner = [(ex+tilt, hy-hr-int(15*s)),(ex-int(9*s), hy-hr-int(88*s)),(ex+int(9*s), hy-hr-int(88*s))]
        d.polygon(inner, fill=(255, 160, 180))

    # Eyes
    blink = abs(math.sin(t * 0.7)) > 0.96
    for ex_off in [-int(25*s), int(25*s)]:
        ex = hx + ex_off
        ey = hy - int(15*s)
        if blink:
            d.arc([ex-int(14*s), ey-int(5*s), ex+int(14*s), ey+int(5*s)], 190, 350, fill=(60,30,20), width=5)
        else:
            d.ellipse([ex-int(14*s), ey-int(14*s), ex+int(14*s), ey+int(14*s)], fill=(50, 25, 15))
            d.ellipse([ex-int(6*s), ey-int(12*s), ex+int(2*s), ey-int(4*s)], fill=(255,255,255))

    # Nose
    d.ellipse([hx-int(8*s), hy+int(5*s), hx+int(8*s), hy+int(18*s)], fill=(255, 120, 150))

    # Smile
    smile_y = int(math.sin(t * 2) * 3)
    d.arc([hx-int(22*s), hy+int(12*s)+smile_y, hx+int(22*s), hy+int(42*s)+smile_y],
          start=10, end=170, fill=(200, 80, 100), width=int(5*s))

    # Cheeks
    for ex_off in [-int(45*s), int(45*s)]:
        d.ellipse([hx+ex_off-int(20*s), hy+int(8*s), hx+ex_off+int(20*s), hy+int(28*s)], fill=(255, 160, 160))

    # Arms waving
    arm_wave = math.sin(t * 3) * 30
    d.line([cx-int(80*s), cy-int(40*s), cx-int(130*s), cy-int(60*s)-int(arm_wave)], fill=(255,230,220), width=int(28*s))
    d.line([cx+int(80*s), cy-int(40*s), cx+int(130*s), cy-int(60*s)+int(arm_wave)], fill=(255,230,220), width=int(28*s))

    # Legs
    leg_kick = math.sin(t * 4) * 15
    for lx_off in [-int(35*s), int(35*s)]:
        d.ellipse([cx+lx_off-int(25*s), cy+int(15*s)+int(leg_kick),
                   cx+lx_off+int(25*s), cy+int(55*s)+int(leg_kick)], fill=(255,230,220))

    # Tail
    d.ellipse([cx+int(70*s), cy-int(20*s), cx+int(110*s), cy+int(20*s)], fill=(255,255,255))


def draw_robot(d, cx, cy, t, size=1.0):
    s = size
    bob = int(math.sin(t * 3) * 12)
    cy = cy + bob

    head_col = (80, 160, 220)
    body_col = (60, 130, 190)
    dark_col = (30, 80, 130)

    # Shadow
    sw = int(90 * s)
    d.ellipse([cx-sw, cy+int(160*s)-10, cx+sw, cy+int(160*s)+18], fill=(0,0,0))

    # Body
    bw, bh = int(80*s), int(100*s)
    d.rectangle([cx-bw, cy-bh, cx+bw, cy+int(40*s)], fill=body_col)
    d.rectangle([cx-bw, cy-bh, cx+bw, cy+int(40*s)], outline=dark_col, width=4)

    # Chest panel + lights
    d.rectangle([cx-int(45*s), cy-int(70*s), cx+int(45*s), cy+int(10*s)], fill=dark_col)
    for li, lc in enumerate([(255,50,50),(50,255,50),(50,100,255),(255,200,50)]):
        lx = cx - int(30*s) + li * int(20*s)
        ly = cy - int(50*s)
        pulse = 0.5 + 0.5 * math.sin(t * (2+li) + li * 1.5)
        bright = tuple(int(c * pulse) for c in lc)
        d.ellipse([lx-int(7*s), ly-int(7*s), lx+int(7*s), ly+int(7*s)], fill=bright)

    # Head
    hw, hh = int(70*s), int(60*s)
    hx, hy = cx, cy - bh - hh
    d.rectangle([hx-hw, hy-hh, hx+hw, hy+hh], fill=head_col)
    d.rectangle([hx-hw, hy-hh, hx+hw, hy+hh], outline=dark_col, width=4)

    # Antenna
    ant_wave = int(math.sin(t * 5) * 12)
    d.line([hx, hy-hh, hx+ant_wave, hy-hh-int(55*s)], fill=dark_col, width=int(6*s))
    d.ellipse([hx+ant_wave-int(12*s), hy-hh-int(67*s), hx+ant_wave+int(12*s), hy-hh-int(43*s)], fill=(255,50,50))

    # Eyes LED
    glow = int(abs(math.sin(t * 2)) * 80)
    for ex_off in [-int(25*s), int(25*s)]:
        ex = hx + ex_off
        ey = hy - int(15*s)
        d.ellipse([ex-int(18*s), ey-int(18*s), ex+int(18*s), ey+int(18*s)],
                  fill=(0, min(255,180+glow), min(255,100+glow)))
        d.ellipse([ex-int(8*s), ey-int(8*s), ex+int(8*s), ey+int(8*s)], fill=(255,255,255))

    # Mouth
    mouth_col = (0,220,180) if math.sin(t * 2) > 0 else (255,80,50)
    d.rectangle([hx-int(30*s), hy+int(20*s), hx+int(30*s), hy+int(35*s)], fill=mouth_col)

    # Arms dance
    arm_angle = math.sin(t * 4) * 40
    lax = cx - bw - int(50*s);  lay = cy - int(60*s) + int(arm_angle)
    d.line([cx-bw, cy-int(60*s), lax, lay], fill=body_col, width=int(22*s))
    d.ellipse([lax-int(18*s), lay-int(18*s), lax+int(18*s), lay+int(18*s)], fill=dark_col)
    rax = cx + bw + int(50*s);  ray = cy - int(60*s) - int(arm_angle)
    d.line([cx+bw, cy-int(60*s), rax, ray], fill=body_col, width=int(22*s))
    d.ellipse([rax-int(18*s), ray-int(18*s), rax+int(18*s), ray+int(18*s)], fill=dark_col)

    # Legs
    leg_step = math.sin(t * 4) * 20
    for lx_off, sign in [(-int(35*s), 1), (int(35*s), -1)]:
        ly_step = int(sign * leg_step)
        d.rectangle([cx+lx_off-int(18*s), cy+int(40*s)+ly_step,
                     cx+lx_off+int(18*s), cy+int(110*s)+ly_step], fill=dark_col)
        d.rectangle([cx+lx_off-int(25*s), cy+int(100*s)+ly_step,
                     cx+lx_off+int(25*s), cy+int(125*s)+ly_step], fill=body_col)


def draw_monster(d, cx, cy, t, size=1.0):
    s = size
    bob = int(math.sin(t * 2.5) * 18)
    cy = cy + bob

    body_col = (80, 200, 120)
    dark_col = (40, 140, 70)

    # Shadow
    sw = int(100 * s)
    d.ellipse([cx-sw, cy+int(140*s)-10, cx+sw, cy+int(140*s)+18], fill=(0,0,0))

    # Body
    bw, bh = int(95*s), int(115*s)
    d.ellipse([cx-bw, cy-bh, cx+bw, cy+int(40*s)], fill=body_col)

    # Spots
    rng = random.Random(7)
    for _ in range(5):
        spx = cx + rng.randint(-int(60*s), int(60*s))
        spy = cy - rng.randint(int(10*s), int(80*s))
        spr = rng.randint(int(10*s), int(22*s))
        d.ellipse([spx-spr, spy-spr, spx+spr, spy+spr], fill=(60,170,100))

    # Head
    hr = int(80*s)
    hx, hy = cx, cy - bh - hr + int(20*s)
    d.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=body_col)

    # Horns
    for hx_off, tilt in [(-int(35*s), -1), (int(35*s), 1)]:
        horn_x = hx + hx_off
        d.polygon([(horn_x-int(15*s), hy-hr+int(10*s)),
                   (horn_x+int(15*s), hy-hr+int(10*s)),
                   (horn_x+tilt*int(8*s), hy-hr-int(55*s))], fill=(255,150,50))

    # Big shocked eyes
    shock = 0.6 + 0.4 * abs(math.sin(t * 1.5))
    for ex_off in [-int(28*s), int(28*s)]:
        ex = hx + ex_off
        ey = hy - int(10*s)
        er = int(22*s * shock)
        d.ellipse([ex-er, ey-er, ex+er, ey+er], fill=(255,255,255))
        shake = int(math.sin(t * 8) * 5)
        pr = int(12*s * shock)
        d.ellipse([ex-pr+shake, ey-pr, ex+pr+shake, ey+pr], fill=(20,20,20))
        d.ellipse([ex-int(5*s)+shake, ey-int(10*s), ex+int(2*s)+shake, ey-int(3*s)], fill=(255,255,255))

    # Open mouth
    mouth_open = 0.5 + 0.5 * abs(math.sin(t * 2))
    mw = int(30*s)
    mh = int(35*s * mouth_open)
    d.ellipse([hx-mw, hy+int(20*s), hx+mw, hy+int(20*s)+mh*2], fill=(40,10,10))
    d.ellipse([hx-mw+5, hy+int(25*s), hx+mw-5, hy+int(25*s)+mh], fill=(200,60,80))

    # Arms flailing
    arm_flail = math.sin(t * 5) * 50
    d.line([cx-bw, cy-int(50*s), cx-bw-int(60*s), cy-int(50*s)-int(arm_flail)], fill=body_col, width=int(30*s))
    d.line([cx+bw, cy-int(50*s), cx+bw+int(60*s), cy-int(50*s)+int(arm_flail)], fill=body_col, width=int(30*s))

    # Legs
    for lx_off in [-int(40*s), int(40*s)]:
        d.ellipse([cx+lx_off-int(28*s), cy+int(20*s), cx+lx_off+int(28*s), cy+int(80*s)], fill=dark_col)


# ── Emoji overlays ────────────────────────────────────────────────────────────

def draw_flying_emojis(d, t, emojis, count=6):
    fnt = get_font(100)
    rng = random.Random(33)
    for i in range(count):
        emoji = emojis[i % len(emojis)]
        speed = rng.uniform(50, 130)
        sx    = rng.uniform(0.05, 0.95) * W
        phase = rng.random() * 10
        sway  = math.sin(t * rng.uniform(0.5,1.5) + phase) * 80
        ex    = int((sx + sway) % W)
        ey    = int((H * rng.random() - t * speed + phase * 300) % H)
        try: d.text((ex, ey), emoji, font=fnt)
        except: pass

def draw_big_emoji_center(d, t, emoji):
    size = int(280 * (1.0 + 0.12 * math.sin(t * 3)))
    fnt  = get_font(size)
    try:
        bb = d.textbbox((0,0), emoji, font=fnt)
        ew = bb[2]-bb[0]
        ex = (W - ew) // 2
        ey = int(H * 0.06)
        d.text((ex+8, ey+8), emoji, fill=(0,0,0), font=fnt)
        d.text((ex, ey), emoji, font=fnt)
    except: pass


# ── Configs ───────────────────────────────────────────────────────────────────

CONFIGS = {
    "memes": {
        "bg":      ["#ff2d2d","#ff6b00","#ffcc00","#ff2d2d"],
        "circle":  (255, 100, 50),
        "emojis":  ["😂","🤣","💀","😭","🔥","👀","💯"],
        "char":    "bunny",
        "sparkle": (255, 230, 50),
        "confetti":[(255,80,80),(255,200,50),(80,255,150),(100,150,255),(255,100,200)],
    },
    "kids": {
        "bg":      ["#06d6a0","#118ab2","#ffd166","#ef476f","#06d6a0"],
        "circle":  (100, 220, 180),
        "emojis":  ["⭐","🌈","🎉","🦋","🌸","✨","🎀"],
        "char":    "bunny",
        "sparkle": (255, 220, 80),
        "confetti":[(255,100,200),(100,255,180),(255,230,50),(150,100,255),(100,200,255)],
    },
    "facts": {
        "bg":      ["#0a0a2e","#1a0050","#2d0070","#0a0a2e"],
        "circle":  (100, 50, 200),
        "emojis":  ["😱","🤯","💥","🔍","❓","⚡","🌍"],
        "char":    "monster",
        "sparkle": (200, 100, 255),
        "confetti":[],
    },
}


# ── Master render ─────────────────────────────────────────────────────────────

def render_frame(scene_data, fi, total_frames, scene_idx, total_scenes, niche):
    t        = fi / FPS
    progress = fi / max(total_frames, 1)
    overall  = (scene_idx + progress) / total_scenes

    cfg = CONFIGS.get(niche, CONFIGS["facts"])

    img = Image.new("RGB", (W, H), (20, 20, 40))
    d   = ImageDraw.Draw(img)

    # 1. Animated gradient bg
    bg_colors = scene_data.get("bg_colors", cfg["bg"])
    if not isinstance(bg_colors, list) or len(bg_colors) < 2:
        bg_colors = cfg["bg"]
    draw_gradient_bg(d, t, bg_colors)

    # 2. Bokeh circles
    draw_floating_circles(d, t, cfg["circle"])

    # 3. Sparkles
    draw_sparkles(d, t, cfg["sparkle"])

    # 4. Confetti (memes + kids)
    if cfg["confetti"]:
        draw_confetti(d, t, cfg["confetti"])

    # 5. Stars (facts only)
    if niche == "facts":
        draw_stars_bg(d, t)

    # 6. Big emoji top center
    emojis  = cfg["emojis"]
    draw_big_emoji_center(d, t, emojis[scene_idx % len(emojis)])

    # 7. Flying small emojis
    draw_flying_emojis(d, t, emojis, count=5)

    # 8. Character bottom center
    char_x = W // 2
    char_y = int(H * 0.70)

    if cfg["char"] == "robot":
        draw_robot(d, char_x, char_y, t, size=1.6)
    elif cfg["char"] == "monster":
        draw_monster(d, char_x, char_y, t, size=1.5)
    else:
        draw_bunny(d, char_x, char_y, t, size=1.6)

    # 9. Progress bar only (NO TEXT)
    bar_h = 16
    d.rectangle([0, H-bar_h, W, H], fill=(30,30,30))
    for x in range(int(W * overall)):
        col = lerp_col((255,80,80),(255,200,50), x/W)
        d.line([(x, H-bar_h),(x, H)], fill=col)

    # 10. Subscribe button (last scene)
    if scene_idx == total_scenes - 1 and progress > 0.6:
        pulse = 1 + 0.1 * math.sin(t * 5)
        bw2, bh2 = int(420*pulse), int(110*pulse)
        cx2, cy2 = W//2, H-260
        d.rounded_rectangle([cx2-bw2//2+6, cy2-bh2//2+6, cx2+bw2//2+6, cy2+bh2//2+6], radius=28, fill=(0,0,0))
        d.rounded_rectangle([cx2-bw2//2, cy2-bh2//2, cx2+bw2//2, cy2+bh2//2], radius=28, fill=(220,0,0))
        fnt_sub = get_font(58, bold=True)
        label = "SUBSCRIBE"
        try:
            bb = d.textbbox((0,0), label, font=fnt_sub)
            lw2 = bb[2]-bb[0]
            d.text(((W-lw2)//2, cy2-28), label, fill=(255,255,255), font=fnt_sub)
        except: pass

    return img