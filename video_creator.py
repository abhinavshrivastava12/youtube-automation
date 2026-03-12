"""
video_creator.py  –  Animated Kids Cartoon Video Generator
===========================================================
• Draws real cartoon scenes (sky, grass, trees, sun, characters)
• Characters animate (bounce, move across screen)
• [PAUSE] in script = actual silence, NOT spoken
• Uses PIL for frames + ffmpeg for encoding (no moviepy needed)
• Each section gets a unique scene & color palette
• Windows + Linux compatible
"""

import os
import sys
import asyncio
import struct
import wave
import math
import subprocess
import shutil
import json
import numpy as np
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ── Settings ────────────────────────────────────────────────────────────────
FPS        = 24
WIDTH      = 1280
HEIGHT     = 720
THREADS    = 4
FAST_MODE  = False      # True = only 15 sec for quick test
PAUSE_SEC  = 0.6        # seconds of silence per [PAUSE]
# ────────────────────────────────────────────────────────────────────────────

# ── Auto-detect ffmpeg (Windows + Linux) ────────────────────────────────────
def find_ffmpeg():
    """
    Find ffmpeg — checks PATH, Windows where command, winget/scoop/choco paths,
    glob search in WinGet packages, and common manual install locations.
    """
    import shutil as _sh
    import glob

    # 1. Already in PATH?
    found = _sh.which("ffmpeg")
    if found:
        probe = _sh.which("ffprobe") or found.replace("ffmpeg", "ffprobe")
        return found, probe

    # 2. Ask Windows 'where' command (finds winget/scoop/choco installs too)
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["where.exe", "ffmpeg"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                ff = result.stdout.strip().splitlines()[0].strip()
                if os.path.exists(ff):
                    probe = ff.replace("ffmpeg.exe", "ffprobe.exe")
                    return ff, probe
        except Exception:
            pass

    # 3. Winget installs to versioned path — glob search
    user_home = os.path.expanduser("~")
    winget_base = os.path.join(user_home, "AppData", "Local",
                               "Microsoft", "WinGet", "Packages")
    if os.path.isdir(winget_base):
        pattern = os.path.join(winget_base, "*ffmpeg*", "**", "ffmpeg.exe")
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            # Also try without ffmpeg in folder name (some winget versions)
            pattern2 = os.path.join(winget_base, "**", "ffmpeg.exe")
            matches = glob.glob(pattern2, recursive=True)
        if matches:
            ff = matches[0]
            probe = ff.replace("ffmpeg.exe", "ffprobe.exe")
            return ff, probe

    # 4. Scoop
    scoop_ff = os.path.join(user_home, "scoop", "apps", "ffmpeg",
                            "current", "bin", "ffmpeg.exe")
    if os.path.exists(scoop_ff):
        return scoop_ff, scoop_ff.replace("ffmpeg.exe", "ffprobe.exe")

    # 5. Chocolatey
    choco_ff = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
    if os.path.exists(choco_ff):
        return choco_ff, choco_ff.replace("ffmpeg.exe", "ffprobe.exe")

    # 6. Common manual paths
    manual_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.join(user_home, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(user_home, "Downloads", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(user_home, "Downloads", "ffmpeg-master-latest-win64-gpl",
                     "bin", "ffmpeg.exe"),
    ]
    for p in manual_paths:
        if os.path.exists(p):
            probe = p.replace("ffmpeg.exe", "ffprobe.exe")
            return p, probe

    # 7. PowerShell fallback (handles all edge cases)
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-Command ffmpeg -ErrorAction SilentlyContinue).Source"],
                capture_output=True, text=True, timeout=10
            )
            ff = result.stdout.strip()
            if ff and os.path.exists(ff):
                probe = ff.replace("ffmpeg.exe", "ffprobe.exe")
                return ff, probe
        except Exception:
            pass

    # ── NOT FOUND — print helpful fix ────────────────────────────────────────
    print("\n" + "="*60)
    print("ffmpeg is installed but this script cannot locate it.")
    print("="*60)
    print()
    print("Run this ONE command in PowerShell to permanently fix PATH:")
    print()
    print('  $ff = Get-ChildItem "$env:LOCALAPPDATA\\Microsoft\\WinGet\\Packages" -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty DirectoryName')
    print('  [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$ff", "User")')
    print()
    print("Then RESTART this terminal and run python main.py again.")
    print()
    print("OR — tell the script exactly where ffmpeg.exe is:")
    print("  Set FFMPEG_PATH environment variable, e.g.:")
    print('  $env:FFMPEG_PATH = "C:\\path\\to\\ffmpeg.exe"')
    print("="*60 + "\n")

    # 8. Check env variable override as last resort
    env_path = os.environ.get("FFMPEG_PATH", "")
    if env_path and os.path.exists(env_path):
        probe = env_path.replace("ffmpeg.exe", "ffprobe.exe")
        return env_path, probe

    sys.exit(1)


FFMPEG, FFPROBE = find_ffmpeg()
print(f"✅ Using ffmpeg: {FFMPEG}")
# ────────────────────────────────────────────────────────────────────────────

# ── Color palettes per scene ─────────────────────────────────────────────────
PALETTES = [
    dict(sky_top=(135,206,235), sky_bot=(255,220,100),  # morning
         grass=(80,180,60),    hill=(60,150,40),
         sun=(255,230,50),     sun_glow=(255,200,50,80)),
    dict(sky_top=(255,180,100), sky_bot=(255,120,60),   # sunset
         grass=(100,160,50),   hill=(70,130,40),
         sun=(255,100,50),     sun_glow=(255,150,50,80)),
    dict(sky_top=(100,160,255), sky_bot=(180,220,255),  # blue day
         grass=(60,190,80),    hill=(40,160,60),
         sun=(255,240,80),     sun_glow=(255,220,80,80)),
    dict(sky_top=(200,100,255), sky_bot=(255,180,220),  # magic evening
         grass=(80,170,60),    hill=(50,140,40),
         sun=(255,200,50),     sun_glow=(255,180,50,80)),
]

# ── Font helpers ─────────────────────────────────────────────────────────────
def get_font(size=48, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/comicbd.ttf" if bold else "C:/Windows/Fonts/comic.ttf",
    ]
    for p in candidates:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

# ═══════════════════════════════════════════════════════════════════════════════
#  SCENE DRAWING PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════════

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

def draw_sky(d, pal, w=WIDTH, h=HEIGHT):
    for y in range(h):
        d.line([(0,y),(w,y)], fill=lerp_color(pal["sky_top"], pal["sky_bot"], y/h))

def draw_sun(d, pal, cx, cy, r=80, t=0):
    # Pulsing glow
    glow_r = r + 20 + int(10 * math.sin(t * 3))
    glow_col = pal["sun_glow"][:3] + (60,)
    d.ellipse([cx-glow_r, cy-glow_r, cx+glow_r, cy+glow_r],
              fill=pal["sun_glow"][:3])
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=pal["sun"])
    # Rays
    for i in range(8):
        angle = (i / 8) * 2 * math.pi + t
        x1 = cx + int((r+5)  * math.cos(angle))
        y1 = cy + int((r+5)  * math.sin(angle))
        x2 = cx + int((r+25) * math.cos(angle))
        y2 = cy + int((r+25) * math.sin(angle))
        d.line([x1,y1,x2,y2], fill=pal["sun"], width=4)

def draw_cloud(d, cx, cy, scale=1.0):
    bubbles = [(0,0,50),(-55,18,38),(55,18,38),(-28,34,32),(28,34,32)]
    for dx,dy,r in bubbles:
        sr = int(r*scale)
        sdx,sdy = int(dx*scale), int(dy*scale)
        d.ellipse([cx+sdx-sr, cy+sdy-sr, cx+sdx+sr, cy+sdy+sr],
                  fill=(255,255,255))

def draw_clouds(d, t=0):
    # Slowly drifting clouds
    offsets = [0, 300, 700, 1050]
    for i, base_x in enumerate(offsets):
        cx = int((base_x + t * (15 + i*5)) % (WIDTH + 200)) - 100
        cy = 60 + i*25
        draw_cloud(d, cx, cy, scale=0.9 + i*0.1)

def draw_ground(d, pal, w=WIDTH, h=HEIGHT):
    # Gradient grass
    ground_top = h - 220
    for y in range(ground_top, h):
        t = (y - ground_top) / (h - ground_top)
        col = lerp_color(pal["grass"], lerp_color(pal["hill"],(20,80,20),0.5), t*0.6)
        d.line([(0,y),(w,y)], fill=col)
    # Rolling hills
    d.ellipse([-150, h-300,  650, h+200], fill=pal["hill"])
    d.ellipse([ 550, h-280, 1430, h+200], fill=pal["hill"])

def draw_tree(d, x, y, height=180, trunk_col=(100,60,20), leaf_col=(40,160,50)):
    tw = 22
    # Trunk
    d.rectangle([x-tw//2, y-height//3, x+tw//2, y], fill=trunk_col)
    # Three layered triangles
    for layer, (off, w2, h2) in enumerate([
        (0,  80, 90),
        (50, 65, 80),
        (90, 50, 70),
    ]):
        pts = [(x, y-height+layer*10+off-h2),
               (x-w2, y-height+layer*10+off+20),
               (x+w2, y-height+layer*10+off+20)]
        darker = lerp_color(leaf_col, (20,100,20), layer*0.15)
        d.polygon(pts, fill=darker)

def draw_flower(d, x, y, color=(255,100,150), size=12):
    # 5 petals + center
    for i in range(5):
        angle = i/5 * 2*math.pi
        px = x + int(size * math.cos(angle))
        py = y + int(size * math.sin(angle))
        d.ellipse([px-size//2, py-size//2, px+size//2, py+size//2], fill=color)
    d.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], fill=(255,230,50))

def draw_box(d, x, y, open_box=False):
    """Draw a cartoon box/gift"""
    w, h = 90, 80
    # Shadow
    d.rectangle([x-w//2+8, y-h+8, x+w//2+8, y+8], fill=(80,50,20))
    # Box body
    d.rectangle([x-w//2, y-h, x+w//2, y], fill=(200,120,50))
    d.rectangle([x-w//2, y-h, x+w//2, y], outline=(140,80,20), width=3)
    # Ribbon
    d.rectangle([x-6, y-h, x+6, y], fill=(220,50,80))
    d.rectangle([x-w//2, y-h//2-6, x+w//2, y-h//2+6], fill=(220,50,80))
    if open_box:
        # Lid open
        pts = [(x-w//2, y-h), (x+w//2, y-h),
               (x+w//2+20, y-h-30), (x-w//2-20, y-h-30)]
        d.polygon(pts, fill=(180,100,40))
        d.polygon(pts, outline=(140,80,20), width=3)
        # Stars coming out
        for sx, sy in [(x-20, y-h-50),(x+10, y-h-60),(x+35, y-h-40)]:
            d.polygon(star_pts(sx,sy,12,5), fill=(255,230,50))

def draw_nest(d, x, y):
    """Draw a cozy nest with a bird in it"""
    # Nest base (bowl shape)
    d.ellipse([x-50, y-15, x+50, y+25], fill=(150,100,50))
    d.ellipse([x-42, y-8, x+42, y+18], fill=(200,150,80))
    # Twigs
    for tx, ty, tx2, ty2 in [
        (x-50,y+5, x-30,y-10),
        (x+30,y-10, x+50,y+5),
        (x-40,y+10, x-15,y-5),
    ]:
        d.line([tx,ty,tx2,ty2], fill=(120,80,30), width=3)
    # Small bird in nest
    draw_small_bird(d, x, y-15, flap=0)

def draw_small_bird(d, x, y, flap=0, color=(100,150,220)):
    """Tiny bird with wing flap"""
    # Body
    d.ellipse([x-18, y-12, x+18, y+12], fill=color)
    # Head
    d.ellipse([x+10, y-20, x+30, y], fill=color)
    # Beak
    d.polygon([(x+28, y-12),(x+40, y-8),(x+28, y-4)], fill=(255,180,50))
    # Eye
    d.ellipse([x+18, y-18, x+26, y-10], fill=(255,255,255))
    d.ellipse([x+20, y-16, x+24, y-12], fill=(30,30,30))
    # Wing (animated flap)
    wy = y - int(flap * 10)
    d.polygon([(x-10,y-5),(x-35,wy-5),(x-20,y+8)], fill=lerp_color(color,(200,220,255),0.4))

def star_pts(cx, cy, r, n=5):
    pts = []
    for i in range(n*2):
        angle = i * math.pi / n - math.pi/2
        dist = r if i%2==0 else r//2
        pts.append((cx + int(dist*math.cos(angle)),
                    cy + int(dist*math.sin(angle))))
    return pts

# ═══════════════════════════════════════════════════════════════════════════════
#  CHARACTER DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def draw_bunny(d, cx, cy, size=1.0, bounce=0, facing="right", happy=True):
    """Benny the Bunny 🐰"""
    s = size
    b = int(bounce)
    cy = cy - b  # apply bounce

    body_w, body_h = int(60*s), int(70*s)
    head_r = int(38*s)

    # Body
    d.ellipse([cx-body_w//2, cy-body_h, cx+body_w//2, cy], fill=(240,220,210))
    # Head
    hx, hy = cx, cy - body_h - head_r + 10
    d.ellipse([hx-head_r, hy-head_r, hx+head_r, hy+head_r], fill=(240,220,210))

    # Ears (long bunny ears)
    ear_col = (240,220,210)
    inner_ear = (255,180,190)
    flip = -1 if facing == "right" else 1
    for ex in [cx - int(20*s)*flip, cx + int(20*s)*flip]:
        # Outer ear
        d.ellipse([ex-int(12*s), hy-head_r-int(70*s),
                   ex+int(12*s), hy-head_r+int(15*s)], fill=ear_col)
        # Inner ear
        d.ellipse([ex-int(7*s), hy-head_r-int(60*s),
                   ex+int(7*s), hy-head_r+int(5*s)], fill=inner_ear)

    # Eyes
    eye_dir = int(12*s) * (1 if facing=="right" else -1)
    for ex_off in [-int(12*s), int(12*s)]:
        d.ellipse([hx+ex_off-int(7*s), hy-int(10*s),
                   hx+ex_off+int(7*s), hy+int(6*s)], fill=(50,30,20))
        d.ellipse([hx+ex_off-int(3*s), hy-int(9*s),
                   hx+ex_off-int(1*s), hy-int(7*s)], fill=(255,255,255))

    # Nose
    d.ellipse([hx-int(5*s), hy+int(2*s), hx+int(5*s), hy+int(10*s)],
              fill=(255,150,160))

    # Smile / expression
    if happy:
        d.arc([hx-int(15*s), hy, hx+int(15*s), hy+int(20*s)],
              start=10, end=170, fill=(150,80,80), width=3)
    else:
        d.arc([hx-int(15*s), hy+int(8*s), hx+int(15*s), hy+int(22*s)],
              start=190, end=350, fill=(150,80,80), width=3)

    # Arms
    arm_y = cy - int(45*s)
    d.ellipse([cx-int(70*s), arm_y-int(10*s),
               cx-int(35*s), arm_y+int(10*s)], fill=(240,220,210))
    d.ellipse([cx+int(35*s), arm_y-int(10*s),
               cx+int(70*s), arm_y+int(10*s)], fill=(240,220,210))

    # Legs
    for lx in [cx-int(20*s), cx+int(20*s)]:
        d.ellipse([lx-int(15*s), cy-int(15*s),
                   lx+int(15*s), cy+int(15*s)], fill=(240,220,210))

    # Tail
    tail_x = cx - int(35*s) if facing=="right" else cx + int(35*s)
    d.ellipse([tail_x-int(16*s), cy-int(25*s),
               tail_x+int(16*s), cy+int(5*s)], fill=(255,255,255))


def draw_squirrel(d, cx, cy, size=1.0, bounce=0, facing="left"):
    """Sammy the Squirrel 🐿️"""
    s = size
    cy = cy - int(bounce)

    body_w, body_h = int(55*s), int(65*s)
    head_r = int(33*s)

    flip = 1 if facing == "right" else -1

    # Big fluffy tail
    tail_pts = [
        (cx + int(45*s)*flip, cy),
        (cx + int(80*s)*flip, cy - int(30*s)),
        (cx + int(90*s)*flip, cy - int(80*s)),
        (cx + int(70*s)*flip, cy - int(120*s)),
        (cx + int(40*s)*flip, cy - int(100*s)),
        (cx + int(30*s)*flip, cy - int(60*s)),
        (cx + int(50*s)*flip, cy - int(30*s)),
    ]
    d.polygon(tail_pts, fill=(180,100,40))
    # Tail highlight
    inner_tail = [(p[0]-int(8*s)*flip, p[1]+int(4*s)) for p in tail_pts[1:5]]
    d.polygon(inner_tail, fill=(220,150,60))

    # Body
    d.ellipse([cx-body_w//2, cy-body_h, cx+body_w//2, cy], fill=(160,90,40))
    # Belly
    d.ellipse([cx-int(22*s), cy-int(50*s), cx+int(22*s), cy-int(5*s)],
              fill=(230,190,140))

    # Head
    hx, hy = cx, cy - body_h - head_r + 12
    d.ellipse([hx-head_r, hy-head_r, hx+head_r, hy+head_r], fill=(160,90,40))

    # Round ears
    for ex in [hx-int(22*s), hx+int(22*s)]:
        d.ellipse([ex-int(14*s), hy-head_r-int(10*s),
                   ex+int(14*s), hy-head_r+int(10*s)], fill=(160,90,40))
        d.ellipse([ex-int(8*s), hy-head_r-int(6*s),
                   ex+int(8*s), hy-head_r+int(6*s)], fill=(220,140,100))

    # Eyes
    for ex_off in [-int(11*s), int(11*s)]:
        d.ellipse([hx+ex_off-int(7*s), hy-int(8*s),
                   hx+ex_off+int(7*s), hy+int(8*s)], fill=(50,30,10))
        d.ellipse([hx+ex_off-int(3*s), hy-int(7*s),
                   hx+ex_off-int(1*s), hy-int(5*s)], fill=(255,255,255))

    # Nose
    d.ellipse([hx-int(5*s), hy+int(3*s), hx+int(5*s), hy+int(10*s)],
              fill=(200,100,60))

    # Smile
    d.arc([hx-int(12*s), hy+int(5*s), hx+int(12*s), hy+int(18*s)],
          start=10, end=170, fill=(120,60,30), width=2)

    # Arms
    arm_y = cy - int(40*s)
    d.ellipse([cx-int(65*s), arm_y-int(10*s),
               cx-int(30*s), arm_y+int(10*s)], fill=(160,90,40))
    d.ellipse([cx+int(30*s), arm_y-int(10*s),
               cx+int(65*s), arm_y+int(10*s)], fill=(160,90,40))


# ═══════════════════════════════════════════════════════════════════════════════
#  SCENE COMPOSERS  (one function per scene type)
# ═══════════════════════════════════════════════════════════════════════════════

def scene_intro(frame_idx, total_frames, pal, title_text):
    """Characters wave hello — bunny bounces in from left, squirrel from right"""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    t = frame_idx / total_frames
    raw_t = frame_idx / FPS  # seconds

    draw_sky(d, pal)
    draw_sun(d, pal, 160, 120, r=75, t=raw_t * 0.3)
    draw_clouds(d, t=raw_t * 8)
    draw_ground(d, pal)

    # Trees in background
    for tx, ty in [(200,HEIGHT-230),(900,HEIGHT-240),(1100,HEIGHT-220)]:
        draw_tree(d, tx, ty, height=170)

    # Flowers
    for fx,fy,fc in [(300,HEIGHT-170,(255,100,150)),
                     (500,HEIGHT-165,(255,200,50)),
                     (750,HEIGHT-172,(200,100,255)),
                     (1000,HEIGHT-168,(100,200,255))]:
        draw_flower(d, fx, fy, fc)

    # Bunny slides in from left
    bunny_x = int(lerp_val(-80, 330, min(1.0, t * 3)))
    bounce = abs(math.sin(raw_t * 6)) * 20
    draw_bunny(d, bunny_x, HEIGHT-200, size=1.1, bounce=bounce, facing="right")

    # Squirrel slides in from right
    sq_x = int(lerp_val(WIDTH+80, 850, min(1.0, t * 3)))
    draw_squirrel(d, sq_x, HEIGHT-210, size=1.0, bounce=bounce*0.7, facing="left")

    # Title card
    draw_title_card(d, title_text, t)
    return img


def scene_story(frame_idx, total_frames, pal, story_text, story_phase=0):
    """Characters walk together, box appears, reaction"""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    t = frame_idx / total_frames
    raw_t = frame_idx / FPS

    draw_sky(d, pal)
    draw_sun(d, pal, WIDTH-160, 130, r=70, t=raw_t*0.2)
    draw_clouds(d, t=raw_t*6)
    draw_ground(d, pal)

    # Trees
    for tx, ty in [(120,HEIGHT-220),(400,HEIGHT-240),(1050,HEIGHT-230),(1200,HEIGHT-215)]:
        draw_tree(d, tx, ty, height=160)

    bounce = abs(math.sin(raw_t*5)) * 15

    if story_phase == 0:
        # Characters walking toward box
        bx = int(lerp_val(200, 420, min(1.0, t*2)))
        sx = int(lerp_val(1100, 850, min(1.0, t*2)))
        draw_bunny(d, bx, HEIGHT-205, size=1.0, bounce=bounce, facing="right")
        draw_squirrel(d, sx, HEIGHT-210, size=0.95, bounce=bounce*0.8, facing="left")
        # Box in center
        box_scale = min(1.0, t * 4)
        boxy = HEIGHT - 185 - int((1-box_scale)*60)
        draw_box(d, WIDTH//2, boxy, open_box=False)

    elif story_phase == 1:
        # Characters next to open box, excited
        draw_bunny(d, 380, HEIGHT-205, size=1.1, bounce=bounce*1.5,
                   facing="right", happy=True)
        draw_squirrel(d, 750, HEIGHT-210, size=1.0, bounce=bounce*1.2, facing="left")
        draw_box(d, 580, HEIGHT-185, open_box=True)
        # Stars/sparkles bursting out
        for i in range(6):
            angle = i/6 * 2*math.pi + raw_t
            sx2 = 580 + int(70*math.cos(angle))
            sy2 = HEIGHT-220 + int(40*math.sin(angle))
            d.polygon(star_pts(sx2, sy2, 10, 5), fill=(255,230,50))

    # Subtitle
    draw_subtitle(d, story_text)
    return img


def scene_moral(frame_idx, total_frames, pal, moral_text):
    """Warm scene — characters shaking hands/hugging, heart floats up"""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    t = frame_idx / total_frames
    raw_t = frame_idx / FPS

    draw_sky(d, pal)
    draw_sun(d, pal, WIDTH//2, 100, r=90, t=raw_t*0.15)
    draw_clouds(d, t=raw_t*5)
    draw_ground(d, pal)

    for tx, ty in [(180,HEIGHT-230),(1100,HEIGHT-225)]:
        draw_tree(d, tx, ty, height=190)
    for fx,fy,fc in [(320,HEIGHT-168,(255,100,150)),
                     (600,HEIGHT-170,(255,200,50)),
                     (960,HEIGHT-165,(200,100,255))]:
        draw_flower(d, fx, fy, fc)

    # Characters close together — friendship
    bounce = abs(math.sin(raw_t*4)) * 8
    draw_bunny(d, 480, HEIGHT-205, size=1.15, bounce=bounce, facing="right", happy=True)
    draw_squirrel(d, 750, HEIGHT-210, size=1.05, bounce=bounce*0.9, facing="left")

    # Floating hearts
    for i in range(3):
        hx = 600 + i*60
        hy = int(HEIGHT - 280 - (t * 120) - i*30) % (HEIGHT-50)
        alpha = max(0, 1.0 - t*1.5)
        hs = 18 + i*4
        draw_heart(d, hx, hy, hs, color=(255,80,120))

    # Moral message box
    draw_message_box(d, moral_text, raw_t)
    return img


def scene_cta(frame_idx, total_frames, pal, cta_text):
    """Both characters jump and wave, subscribe bell animation"""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    t = frame_idx / total_frames
    raw_t = frame_idx / FPS

    draw_sky(d, pal)
    draw_sun(d, pal, 200, 140, r=80, t=raw_t*0.4)
    draw_clouds(d, t=raw_t*10)
    draw_ground(d, pal)

    for tx,ty in [(300,HEIGHT-230),(900,HEIGHT-235)]:
        draw_tree(d, tx, ty, height=175)

    # Both characters jumping excitedly
    jump = abs(math.sin(raw_t * 7)) * 35
    draw_bunny(d, 360, HEIGHT-205, size=1.1, bounce=jump, facing="right", happy=True)
    draw_squirrel(d, 820, HEIGHT-210, size=1.0, bounce=jump*0.8, facing="left")

    # Subscribe button animation
    draw_subscribe_button(d, WIDTH//2, HEIGHT//2 - 60, raw_t)

    draw_subtitle(d, cta_text)
    return img


def scene_generic(frame_idx, total_frames, pal, text):
    """Fallback scenic shot with slow camera pan feel"""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d = ImageDraw.Draw(img)
    t = frame_idx / total_frames
    raw_t = frame_idx / FPS

    draw_sky(d, pal)
    draw_sun(d, pal, 150, 130, r=80, t=raw_t*0.2)
    draw_clouds(d, t=raw_t*7)
    draw_ground(d, pal)

    for tx,ty in [(200,HEIGHT-225),(500,HEIGHT-245),(850,HEIGHT-230),(1150,HEIGHT-220)]:
        draw_tree(d, tx, ty, height=180)

    bounce = abs(math.sin(raw_t*5)) * 15
    draw_bunny(d, 400, HEIGHT-205, size=1.05, bounce=bounce, facing="right")
    draw_squirrel(d, 780, HEIGHT-210, size=0.95, bounce=bounce*0.7, facing="left")

    draw_subtitle(d, text)
    return img


# ═══════════════════════════════════════════════════════════════════════════════
#  UI DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def lerp_val(a, b, t):
    return a + (b-a)*t

def draw_heart(d, cx, cy, r, color=(255,80,120)):
    # Heart using two circles + triangle
    d.ellipse([cx-r, cy-r, cx, cy+r//2], fill=color)
    d.ellipse([cx, cy-r, cx+r, cy+r//2], fill=color)
    d.polygon([(cx-r, cy+r//3),(cx+r, cy+r//3),(cx, cy+r*2)], fill=color)

def draw_title_card(d, text, t):
    """Animated title that slides down from top"""
    y_off = int(lerp_val(-120, 0, min(1.0, t*4)))
    font_big = get_font(72, bold=True)
    font_sm  = get_font(36)

    # Card shadow
    d.rounded_rectangle([140+4, 30+y_off+4, WIDTH-140+4, 180+y_off+4],
                         radius=30, fill=(0,0,0))
    # Card bg
    d.rounded_rectangle([140, 30+y_off, WIDTH-140, 180+y_off],
                         radius=30, fill=(255,230,50))
    d.rounded_rectangle([140, 30+y_off, WIDTH-140, 180+y_off],
                         radius=30, outline=(200,150,20), width=5)

    # Stars on sides
    for sx,sy in [(165, 85+y_off),(WIDTH-165, 85+y_off)]:
        d.polygon(star_pts(sx, sy, 16, 5), fill=(255,180,20))

    # Title text
    bbox = d.textbbox((0,0), text, font=font_big)
    tw = bbox[2]-bbox[0]
    d.text(((WIDTH-tw)//2, 55+y_off), text, fill=(80,40,0), font=font_big)

def draw_subtitle(d, text, max_chars=52):
    """Subtitle bar at bottom"""
    if not text: return
    font_s = get_font(40, bold=False)

    # Wrap text
    words = text.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= max_chars:
            lines.append(" ".join(cur[:-1])); cur=[w]
    if cur: lines.append(" ".join(cur))

    bar_h = len(lines) * 55 + 30
    bar_y = HEIGHT - bar_h - 10

    # Semi-transparent dark bar
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([30, bar_y, WIDTH-30, HEIGHT-10],
                          radius=20, fill=(0,0,0,170))
    # Merge
    img_tmp = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    img_tmp.paste(overlay, (0,0))
    # Can't paste RGBA onto RGB directly, draw rectangle instead
    d.rounded_rectangle([30, bar_y, WIDTH-30, HEIGHT-10],
                         radius=20, fill=(20,20,30))
    d.rounded_rectangle([30, bar_y, WIDTH-30, HEIGHT-10],
                         radius=20, outline=(80,80,120), width=2)

    for i, line in enumerate(lines):
        bbox = d.textbbox((0,0), line, font=font_s)
        lw = bbox[2]-bbox[0]
        d.text(((WIDTH-lw)//2, bar_y + 15 + i*55), line,
               fill=(255,255,255), font=font_s)

def draw_message_box(d, text, t):
    """Centered message box with appear animation"""
    scale = min(1.0, t * 2)
    if scale < 0.05: return

    font_m = get_font(46, bold=True)
    words = text.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= 35: lines.append(" ".join(cur[:-1])); cur=[w]
    if cur: lines.append(" ".join(cur))

    line_h = 60
    total_h = len(lines)*line_h + 60
    max_w = max((d.textbbox((0,0),l,font=font_m)[2]-d.textbbox((0,0),l,font=font_m)[0]) for l in lines) if lines else 200

    cx, cy = WIDTH//2, HEIGHT//2 - 80
    bx1, by1 = cx-max_w//2-40, cy-30
    bx2, by2 = cx+max_w//2+40, cy+total_h

    d.rounded_rectangle([bx1+6,by1+6,bx2+6,by2+6], radius=25, fill=(0,0,0))
    d.rounded_rectangle([bx1,by1,bx2,by2], radius=25, fill=(255,240,60))
    d.rounded_rectangle([bx1,by1,bx2,by2], radius=25, outline=(200,150,20), width=5)

    for i,line in enumerate(lines):
        bbox = d.textbbox((0,0),line,font=font_m)
        lw = bbox[2]-bbox[0]
        d.text((cx-lw//2, by1+30+i*line_h), line, fill=(80,40,0), font=font_m)

def draw_subscribe_button(d, cx, cy, t):
    """Animated subscribe button"""
    pulse = 1.0 + 0.08 * math.sin(t * 4)
    w, h = int(280*pulse), int(80*pulse)

    d.rounded_rectangle([cx-w//2+4, cy-h//2+4, cx+w//2+4, cy+h//2+4],
                         radius=15, fill=(0,0,0))
    d.rounded_rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2],
                         radius=15, fill=(220,30,30))
    d.rounded_rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2],
                         radius=15, outline=(180,10,10), width=3)

    font_s = get_font(42, bold=True)
    label = "▶  SUBSCRIBE"
    bbox = d.textbbox((0,0), label, font=font_s)
    lw = bbox[2]-bbox[0]
    d.text((cx-lw//2, cy-20), label, fill=(255,255,255), font=font_s)

    # Bell icon to the right
    bell_x, bell_y = cx + w//2 + 55, cy
    bell_r = int(28*pulse)
    d.ellipse([bell_x-bell_r, bell_y-bell_r, bell_x+bell_r, bell_y+bell_r],
              fill=(255,200,30))
    font_bell = get_font(36)
    d.text((bell_x-10, bell_y-18), "🔔", font=font_bell)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO: [PAUSE] → real silence
# ═══════════════════════════════════════════════════════════════════════════════

def make_silence_wav(path, duration_sec=0.6, sample_rate=24000):
    """Create WAV silence — pure Python, zero extra dependencies."""
    n_samples = int(sample_rate * duration_sec)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00\x00' * n_samples)


def mp3_to_wav(mp3_path, wav_path):
    """Convert mp3 to wav using ffmpeg."""
    subprocess.run([
        FFMPEG, "-i", mp3_path, "-ar", "24000", "-ac", "1",
        wav_path, "-y", "-loglevel", "quiet"
    ], check=True)


def concat_wavs_to_mp3(wav_files, output_mp3):
    """Concatenate WAV files and output as MP3 via ffmpeg."""
    list_path = output_mp3 + "_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for wf in wav_files:
            # Forward slashes work on both Windows and Linux for ffmpeg
            safe = os.path.abspath(wf).replace("\\", "/")
            f.write(f"file '{safe}'\n")
    subprocess.run([
        FFMPEG, "-f", "concat", "-safe", "0",
        "-i", list_path, "-c:a", "libmp3lame", "-q:a", "4",
        output_mp3, "-y", "-loglevel", "quiet"
    ], check=True)
    try: os.remove(list_path)
    except: pass


async def generate_audio_with_pauses(text, output_path):
    """
    Split script on [PAUSE] markers.
    Each part -> TTS mp3 -> wav.
    Real WAV silence inserted between parts (pure Python, no ffmpeg needed for silence).
    All wavs concatenated -> final mp3.
    """
    print("\U0001f50a Processing script pauses...")
    parts = [p.strip() for p in text.split("[PAUSE]") if p.strip()]
    parts_dir = os.path.join("output", "audio_parts")
    os.makedirs(parts_dir, exist_ok=True)

    # Make silence with pure Python (no ffmpeg needed here)
    silence_wav = os.path.join(parts_dir, "silence.wav")
    make_silence_wav(silence_wav, PAUSE_SEC)

    wav_sequence = []
    for i, part in enumerate(parts):
        mp3_p = os.path.join(parts_dir, f"part_{i:03d}.mp3")
        wav_p = os.path.join(parts_dir, f"part_{i:03d}.wav")
        communicate = edge_tts.Communicate(part, "en-US-GuyNeural")
        await communicate.save(mp3_p)
        print(f"   \u2714 Part {i+1}/{len(parts)} synthesized")
        mp3_to_wav(mp3_p, wav_p)
        wav_sequence.append(wav_p)
        if i < len(parts) - 1:
            wav_sequence.append(silence_wav)

    concat_wavs_to_mp3(wav_sequence, output_mp3=output_path)
    print("\u2705 Audio with real pauses generated")
    shutil.rmtree(parts_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  VIDEO ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════════

def get_audio_duration(path):
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_streams", path],
        capture_output=True, text=True
    )
    import json
    data = json.loads(result.stdout)
    return float(data["streams"][0]["duration"])


def render_section_to_video(section, section_idx, num_sections,
                             duration, pal, temp_dir, video_title):
    """Render one section: generate all frames → encode with ffmpeg"""

    title   = section.get("title", f"Part {section_idx+1}").lower()
    text    = section.get("text", "")
    n_frames = int(duration * FPS)

    frame_dir = os.path.join(temp_dir, f"sec_{section_idx:02d}")
    os.makedirs(frame_dir, exist_ok=True)

    print(f"   🖼️  Rendering section {section_idx+1}/{num_sections}: '{section.get('title','')}' ({n_frames} frames)")

    for fi in range(n_frames):
        t_sec = fi / FPS

        # Pick scene type by title keyword
        if "intro" in title or section_idx == 0:
            img = scene_intro(fi, n_frames, pal, video_title)
        elif "story" in title or "walk" in title or "found" in title:
            phase = 1 if fi > n_frames // 2 else 0
            img = scene_story(fi, n_frames, pal, text, story_phase=phase)
        elif "moral" in title or "lesson" in title or "learn" in title:
            img = scene_moral(fi, n_frames, pal, text)
        elif "cta" in title or "subscri" in title or "channel" in title:
            img = scene_cta(fi, n_frames, pal, text)
        else:
            img = scene_generic(fi, n_frames, pal, text)

        frame_path = os.path.join(frame_dir, f"frame_{fi:05d}.png")
        img.save(frame_path, optimize=False)

    # Encode frames → silent mp4 with ffmpeg
    seg_video = os.path.join(temp_dir, f"seg_{section_idx:02d}.mp4")
    cmd = [
        FFMPEG,
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%05d.png"),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        seg_video, "-y", "-loglevel", "quiet"
    ]
    subprocess.run(cmd, check=True)

    # Cleanup frames to save disk
    shutil.rmtree(frame_dir)
    print(f"      ✔ Segment encoded: {seg_video}")
    return seg_video


def create_video(script_data):
    os.makedirs("output/audio",  exist_ok=True)
    os.makedirs("output/videos", exist_ok=True)
    temp_dir = "output/temp_render"
    os.makedirs(temp_dir, exist_ok=True)

    safe_title = script_data["title"][:30].replace(" ", "_")
    audio_path = f"output/audio/{safe_title}.mp3"

    # ── Step 1: Generate audio with real pauses ──────────────────────────────
    asyncio.run(generate_audio_with_pauses(script_data["script"], audio_path))

    total_duration = get_audio_duration(audio_path)
    if FAST_MODE:
        total_duration = min(total_duration, 15)

    print(f"🎧 Total audio duration: {total_duration:.1f}s")

    sections = script_data["sections"]
    sec_dur  = total_duration / len(sections)

    # ── Step 2: Render each section ──────────────────────────────────────────
    pal = PALETTES[0]
    seg_files = []

    for i, section in enumerate(sections):
        pal = PALETTES[i % len(PALETTES)]
        seg = render_section_to_video(
            section, i, len(sections), sec_dur, pal, temp_dir,
            script_data["title"]
        )
        seg_files.append(seg)

    # ── Step 3: Concat all video segments ───────────────────────────────────
    print("🎬 Concatenating video segments...")
    concat_list = os.path.join(temp_dir, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for seg in seg_files:
            safe = os.path.abspath(seg).replace("\\\\", "/")
            f.write(f"file '{safe}'\n")

    concat_video = os.path.join(temp_dir, "combined.mp4")
    subprocess.run([
        FFMPEG, "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy",
        concat_video, "-y", "-loglevel", "quiet"
    ], check=True)

    # ── Step 4: Mux video + audio ────────────────────────────────────────────
    print("🔗 Merging audio + video...")
    output_path = f"output/videos/{safe_title}.mp4"
    subprocess.run([
        FFMPEG,
        "-i", concat_video,
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac",
        "-shortest",
        output_path, "-y", "-loglevel", "quiet"
    ], check=True)

    # ── Cleanup ──────────────────────────────────────────────────────────────
    shutil.rmtree(temp_dir)
    print(f"\n✅ Video Done: {output_path}")
    return output_path