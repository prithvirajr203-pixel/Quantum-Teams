import requests
import random
import time
import sys
from PIL import Image, ImageDraw, ImageFont

# ---------- 1. CONFIG ----------

# Pick which post variant to generate.
# Change this one value (or pass it as a command-line arg) to switch posts.
# Usage: python poster.py hiring
#        python poster.py ongoing
VARIANTS = {
    "hiring": {
        "main": "WE ARE HIRING",
        "sub": "Join Our Team",
        "prompt": "professional modern office background, blurred, corporate blue theme, no text, no logo, minimalist",
    },
    "ongoing": {
        "main": "HIRING ONGOING",
        "sub": "Apply Now",
        "prompt": "professional modern office background, blurred, corporate green theme, no text, no logo, minimalist",
    },
}

variant_key = sys.argv[1] if len(sys.argv) > 1 else "hiring"
if variant_key not in VARIANTS:
    raise ValueError(f"Unknown variant '{variant_key}'. Choose from: {list(VARIANTS.keys())}")

variant = VARIANTS[variant_key]
MAIN_TEXT = variant["main"]
SUB_TEXT = variant["sub"]
PROMPT = variant["prompt"]

SEED = random.randint(1, 1000000)
IMG_URL = f"https://image.pollinations.ai/prompt/{requests.utils.quote(PROMPT)}?seed={SEED}&nologo=true&width=1080&height=1080"

BG_PATH = "images/background.jpg"
OUTPUT_PATH = f"output/final_post_{variant_key}.jpg"

FONT_BOLD = "fonts/Poppins-Bold.ttf"
FONT_REGULAR = "fonts/Poppins-Regular.ttf"

# ---------- 2. DOWNLOAD BACKGROUND FROM POLLINATIONS ----------
print(f"Generating '{variant_key}' post...")
print("Downloading background image...")
print("URL:", IMG_URL)

MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds between attempts, gives Pollinations time to recover
response = None

for attempt in range(1, MAX_RETRIES + 1):
    try:
        print(f"Attempt {attempt}/{MAX_RETRIES}...")
        response = requests.get(IMG_URL, timeout=90)
        if response.status_code == 200:
            break
        else:
            print("Got status:", response.status_code, "- retrying...")
    except requests.exceptions.RequestException as e:
        # Covers timeouts, SSLError (e.g. UNEXPECTED_EOF_WHILE_READING), connection resets, etc.
        print(f"Attempt {attempt} failed: {type(e).__name__}: {e}")
        if attempt == MAX_RETRIES:
            raise Exception(
                "Could not reach Pollinations after multiple attempts. "
                "This is usually the Pollinations server being temporarily overloaded — "
                "try again in a minute. If it persists, check firewall/antivirus."
            )
    time.sleep(RETRY_DELAY)

if response is None or response.status_code != 200:
    raise Exception(f"Failed to download image. Status: {response.status_code if response else 'no response'}")

with open(BG_PATH, "wb") as f:
    f.write(response.content)

print("Background downloaded successfully.")

# ---------- 3. OVERLAY TEXT ----------
img = Image.open(BG_PATH).convert("RGB")
W, H = img.size
draw = ImageDraw.Draw(img)

# semi-transparent dark band behind text for readability
overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
band_top = int(H * 0.38)
band_bottom = int(H * 0.62)
overlay_draw.rectangle([(0, band_top), (W, band_bottom)], fill=(0, 0, 0, 140))
img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
draw = ImageDraw.Draw(img)

# fonts (scale with image width)
main_font_size = int(W * 0.11)
sub_font_size = int(W * 0.045)
main_font = ImageFont.truetype(FONT_BOLD, main_font_size)
sub_font = ImageFont.truetype(FONT_REGULAR, sub_font_size)

def draw_centered(text, font, y_center, fill="white"):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (W - text_w) / 2
    y = y_center - text_h / 2
    draw.text((x, y), text, font=font, fill=fill)

draw_centered(MAIN_TEXT, main_font, H * 0.46)
draw_centered(SUB_TEXT, sub_font, H * 0.57)

img.save(OUTPUT_PATH, quality=95)
print(f"Final poster saved to {OUTPUT_PATH}")