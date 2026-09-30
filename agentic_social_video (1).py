"""
AGENTIC AI SOCIAL MEDIA VIDEO AUTOMATION
----------------------------------------
Single-file Python implementation.

Workflow:
Topic -> AI content plan -> scene images -> AI voice ->
vertical video scenes -> final MP4 -> caption/hashtags/metadata.

Requirements:
    pip install openai pillow python-dotenv

System requirement:
    FFmpeg must be installed and available in PATH.

Create a .env file:
    OPENAI_API_KEY=your_api_key_here

Run:
    python agentic_social_video.py "5 AI tools every student should know"
"""

import os
import sys
import json
import re
import time
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

client = OpenAI(api_key=API_KEY)

TEXT_MODEL = "gpt-5.6-luna"
TTS_MODEL = "gpt-4o-mini-tts"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

TEMP_DIR = OUTPUT_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]


def log(message):
    print(f"\n[AGENT] {message}")


def find_font(size=60):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def run_command(command):
    print(" ".join(map(str, command)))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("Command failed.")
    return result


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg was not found. Install FFmpeg and add it to PATH."
        )


def create_content_plan(topic):
    log("Content Strategist is planning the video...")

    prompt = f"""
You are an autonomous social-media content strategist.

Create a short-form vertical video about:
TOPIC: {topic}

Target audience:
Students, young professionals and beginners.

Video length:
Approximately 30-45 seconds.

Return ONLY valid JSON.

Required JSON structure:
{{
    "title": "short video title",
    "hook": "strong opening hook",
    "scenes": [
        {{
            "scene_number": 1,
            "narration": "spoken narration",
            "screen_text": "short text displayed on screen",
            "visual": "simple visual description"
        }}
    ],
    "cta": "short call to action",
    "caption": "social media caption",
    "hashtags": ["#AI", "#Technology"]
}}

Rules:
- 6 to 8 scenes.
- Each narration should be short.
- Screen text must be concise.
- Avoid unsupported factual claims.
- Keep the content suitable for general audiences.
"""

    response = client.responses.create(
        model=TEXT_MODEL,
        input=prompt
    )

    try:
        return json.loads(clean_json(response.output_text))
    except json.JSONDecodeError:
        print("AI returned invalid JSON:")
        print(response.output_text)
        raise


def validate_plan(plan):
    log("Content Validator is checking the plan...")

    required = [
        "title", "hook", "scenes",
        "cta", "caption", "hashtags"
    ]

    for field in required:
        if field not in plan:
            raise ValueError(f"Missing required field: {field}")

    if len(plan["scenes"]) < 4:
        raise ValueError("Too few scenes generated.")

    for scene in plan["scenes"]:
        if "narration" not in scene:
            raise ValueError("Scene narration missing.")
        if "screen_text" not in scene:
            raise ValueError("Scene screen text missing.")

    log("Content validation successful.")


def generate_voice(text, output_file):
    log(f"Generating voice: {text[:60]}...")

    speech = client.audio.speech.create(
        model=TTS_MODEL,
        voice="alloy",
        input=text
    )

    speech.stream_to_file(output_file)
    return output_file


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def create_scene_image(scene_number, title, screen_text, output_file):
    image = Image.new(
        "RGB",
        (VIDEO_WIDTH, VIDEO_HEIGHT),
        (15, 15, 25)
    )

    draw = ImageDraw.Draw(image)

    title_font = find_font(52)
    text_font = find_font(82)
    small_font = find_font(42)

    draw.rounded_rectangle(
        (70, 90, 420, 170),
        radius=30,
        fill=(255, 255, 255)
    )

    draw.text(
        (105, 105),
        f"SCENE {scene_number}",
        font=small_font,
        fill=(20, 20, 30)
    )

    title_lines = wrap_text(draw, title, title_font, 850)
    y = 300

    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        width = bbox[2] - bbox[0]
        draw.text(
            ((VIDEO_WIDTH - width) / 2, y),
            line,
            font=title_font,
            fill=(220, 220, 230)
        )
        y += 75

    text_lines = wrap_text(draw, screen_text, text_font, 850)
    y = 700

    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=text_font)
        width = bbox[2] - bbox[0]

        draw.text(
            ((VIDEO_WIDTH - width) / 2 + 4, y + 4),
            line,
            font=text_font,
            fill=(0, 0, 0)
        )

        draw.text(
            ((VIDEO_WIDTH - width) / 2, y),
            line,
            font=text_font,
            fill=(255, 255, 255)
        )

        y += 110

    draw.text(
        (70, 1800),
        "AI GENERATED CONTENT",
        font=small_font,
        fill=(160, 160, 170)
    )

    image.save(output_file)
    return output_file


def create_scene_video(image_file, audio_file, output_file):
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_file),
        "-i", str(audio_file),
        "-c:v", "libx264",
        "-preset", "medium",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-vf",
        (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        ),
        str(output_file)
    ]

    run_command(command)
    return output_file


def combine_videos(video_files, output_file):
    log("Video Assembly Agent is combining scenes...")

    concat_file = TEMP_DIR / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for video in video_files:
            f.write(f"file '{Path(video).absolute().as_posix()}'\n")

    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_file)
    ]

    run_command(command)
    return output_file


def create_metadata(plan, topic):
    log("Metadata Agent is creating the publishing package...")

    metadata = {
        "topic": topic,
        "title": plan["title"],
        "caption": plan["caption"],
        "hashtags": plan["hashtags"],
        "full_caption": (
            plan["caption"] + "\n\n" + " ".join(plan["hashtags"])
        ),
        "cta": plan["cta"]
    }

    metadata_file = OUTPUT_DIR / "metadata.json"

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    return metadata_file


def save_script(plan):
    script_file = OUTPUT_DIR / "script.txt"

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"TITLE\n{plan['title']}\n\n")
        f.write(f"HOOK\n{plan['hook']}\n\n")

        for scene in plan["scenes"]:
            f.write(f"SCENE {scene['scene_number']}\n")
            f.write(f"NARRATION:\n{scene['narration']}\n\n")
            f.write(f"SCREEN TEXT:\n{scene['screen_text']}\n\n")

        f.write(f"CTA\n{plan['cta']}\n")

    return script_file


def clean_temp():
    for item in TEMP_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception:
            pass


def run_agent(topic):
    start_time = time.time()

    log("======================================")
    log("AGENTIC SOCIAL VIDEO AUTOMATION")
    log("======================================")

    check_ffmpeg()

    plan = create_content_plan(topic)
    validate_plan(plan)
    save_script(plan)

    scene_videos = []

    for index, scene in enumerate(plan["scenes"], start=1):
        log(f"Processing scene {index}/{len(plan['scenes'])}")

        image_file = TEMP_DIR / f"scene_{index:02d}.png"
        create_scene_image(
            scene_number=index,
            title=plan["title"],
            screen_text=scene["screen_text"],
            output_file=image_file
        )

        audio_file = TEMP_DIR / f"scene_{index:02d}.mp3"
        generate_voice(scene["narration"], audio_file)

        video_file = TEMP_DIR / f"scene_{index:02d}.mp4"
        create_scene_video(
            image_file=image_file,
            audio_file=audio_file,
            output_file=video_file
        )

        scene_videos.append(video_file)

    final_video = OUTPUT_DIR / "final_video.mp4"
    combine_videos(scene_videos, final_video)

    metadata_file = create_metadata(plan, topic)

    for image in TEMP_DIR.glob("scene_*.png"):
        shutil.copy2(image, OUTPUT_DIR / image.name)

    elapsed = time.time() - start_time

    log("======================================")
    log("AUTOMATION COMPLETE")
    log("======================================")

    print(f"\nVideo: {final_video}")
    print(f"Metadata: {metadata_file}")
    print(f"Script: {OUTPUT_DIR / 'script.txt'}")
    print(f"Time: {elapsed:.2f} seconds")

    print(f"\nTITLE:\n{plan['title']}")
    print(f"\nCAPTION:\n{plan['caption']}")
    print(f"\nHASHTAGS:\n{' '.join(plan['hashtags'])}")
    print(f"\nCTA:\n{plan['cta']}")

    return final_video


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            '\nUsage:\n'
            'python agentic_social_video.py '
            '"Your video topic"\n'
        )
        print(
            'Example:\n'
            'python agentic_social_video.py '
            '"5 AI tools every college student should know"\n'
        )
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    try:
        run_agent(topic)
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(1)
    except Exception as error:
        print("\nERROR:")
        print(error)
        sys.exit(1)
