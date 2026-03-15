"""
diagnose.py - Run this to find all problems
python diagnose.py
"""
import os, sys, json, subprocess

print("=" * 60)
print("  YT Channel AI - Diagnosis Tool")
print("=" * 60)

issues = []
fixes  = []

# 1. Check ffmpeg
print("\n[1] Checking ffmpeg...")
import shutil
ff = shutil.which("ffmpeg")
if ff:
    print(f"  ✅ ffmpeg found: {ff}")
else:
    print("  ❌ ffmpeg NOT found in PATH")
    issues.append("ffmpeg not in PATH")
    fixes.append("winget install ffmpeg  OR  download from ffmpeg.org and add to PATH")

# 2. Check Python packages
print("\n[2] Checking Python packages...")
required = ["flask", "flask_cors", "dotenv", "edge_tts", "PIL", "requests"]
for pkg in required:
    try:
        __import__(pkg)
        print(f"  ✅ {pkg}")
    except ImportError:
        print(f"  ❌ {pkg} missing")
        issues.append(f"Missing package: {pkg}")
        fixes.append(f"pip install {pkg.replace('_','-').replace('dotenv','python-dotenv').replace('PIL','Pillow')}")

# 3. Check songs folder
print("\n[3] Checking songs folder...")
songs_dir = os.path.join("backend", "songs")
if not os.path.exists(songs_dir):
    print(f"  ❌ Songs folder missing: {songs_dir}")
    issues.append("Songs folder missing")
    fixes.append(f"mkdir {songs_dir}")
else:
    mp3s = [f for f in os.listdir(songs_dir) if f.endswith(".mp3")]
    if mp3s:
        print(f"  ✅ Songs found: {mp3s}")
    else:
        print(f"  ⚠️  Songs folder exists but EMPTY - no .mp3 files")
        issues.append("No MP3 files in backend/songs/")
        fixes.append("Upload Suno MP3 via frontend OR copy manually to backend/songs/")

# 4. Check song_mapping.json
print("\n[4] Checking song_mapping.json...")
mapping_file = os.path.join("backend", "song_mapping.json")
if os.path.exists(mapping_file):
    with open(mapping_file) as f:
        mapping = json.load(f)
    print(f"  ✅ Mapping exists: {mapping}")
    # Check if mapped files exist
    if os.path.exists(songs_dir):
        for key, fname in mapping.items():
            fpath = os.path.join(songs_dir, fname)
            if os.path.exists(fpath):
                print(f"    ✅ {key} -> {fname} (EXISTS)")
            else:
                print(f"    ❌ {key} -> {fname} (FILE MISSING!)")
                issues.append(f"Mapped file missing: {fname}")
                fixes.append(f"Copy/rename your MP3 to: backend/songs/{fname}")
else:
    print("  ⚠️  song_mapping.json missing (will be created on first run)")

# 5. Check Hindi fonts
print("\n[5] Checking Hindi fonts...")
font_candidates = [
    "C:/Windows/Fonts/NirmalaB.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/mangalb.ttf",
    "C:/Windows/Fonts/mangal.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]
found_font = False
for f in font_candidates:
    if os.path.exists(f):
        print(f"  ✅ Font found: {f}")
        found_font = True
        break
if not found_font:
    print("  ❌ No Hindi font found! Text will show as boxes")
    issues.append("Hindi font missing")
    fixes.append("Windows: Already included (Nirmala.ttf). Linux: sudo apt install fonts-freefont-ttf")

# 6. Check .env file
print("\n[6] Checking .env file...")
env_path = os.path.join("backend", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        content = f.read()
    if "GROQ_API_KEY" in content and "gsk_" in content:
        print("  ✅ GROQ_API_KEY found")
    else:
        print("  ⚠️  GROQ_API_KEY missing or empty (AI generation won't work)")
        issues.append("GROQ_API_KEY missing")
        fixes.append("Get free key from console.groq.com and add to backend/.env")
else:
    print("  ❌ backend/.env file missing")
    issues.append(".env file missing")
    fixes.append("Create backend/.env with: GROQ_API_KEY=gsk_your_key_here")

# Summary
print("\n" + "=" * 60)
if not issues:
    print("  🎉 No issues found! Everything looks good.")
    print("  Run: cd backend && python app.py")
else:
    print(f"  ❌ Found {len(issues)} issue(s):\n")
    for i, (issue, fix) in enumerate(zip(issues, fixes), 1):
        print(f"  {i}. PROBLEM: {issue}")
        print(f"     FIX:     {fix}")
        print()

print("=" * 60)