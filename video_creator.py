import os
import asyncio
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# ---------- SETTINGS ----------
FAST_MODE = False   # True = 15 sec test render
FPS = 24
THREADS = 4
# ------------------------------


def create_simple_background(text, size=(1280, 720)):
    """Create simple background image"""

    img = Image.new("RGB", size, color=(25, 25, 25))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 70)
    except:
        font = ImageFont.load_default()

    words = text.split()
    lines = []
    temp = []

    for word in words[:10]:
        temp.append(word)
        if len(temp) >= 3:
            lines.append(" ".join(temp))
            temp = []

    if temp:
        lines.append(" ".join(temp))

    y = size[1] // 2 - 100

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((size[0] - w) / 2, y), line, fill="white", font=font)
        y += 90

    return img


async def generate_audio(text, output_path):
    """Generate voice using Edge TTS"""

    print("🔊 Generating voice...")

    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_path)

    print("✅ Audio generated")


def create_video(script_data):
    """Create video from script"""

    os.makedirs("output/audio", exist_ok=True)
    os.makedirs("output/videos", exist_ok=True)

    safe_title = script_data["title"][:30].replace(" ", "_")

    audio_path = f"output/audio/{safe_title}.mp3"

    asyncio.run(generate_audio(script_data["script"], audio_path))

    print("🎧 Loading audio...")
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    if FAST_MODE:
        duration = min(duration, 15)

    section_duration = duration / len(script_data["sections"])

    clips = []

    print("🖼 Creating slides...")

    for i, section in enumerate(script_data["sections"]):

        img = create_simple_background(section["title"])
        img_path = f"output/temp_{i}.png"
        img.save(img_path)

        clip = (
            ImageClip(img_path)
            .with_duration(section_duration)
            .with_position("center")
        )

        clips.append(clip)

    print("🎬 Rendering video...")

    video = concatenate_videoclips(clips)
    video = video.with_audio(audio_clip)

    output_path = f"output/videos/{safe_title}.mp4"

    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=THREADS,
        preset="ultrafast",
        logger="bar"
    )

    print("🧹 Cleaning temp files...")

    for i in range(len(script_data["sections"])):
        try:
            os.remove(f"output/temp_{i}.png")
        except:
            pass

    print("✅ Video Done:", output_path)

    return output_path
