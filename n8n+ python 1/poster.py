import requests
import random
import time
import sys
from PIL import Image

# ---------- 1. CONFIG ----------

# Pick which post variant to generate.
# Change this one value (or pass it as a command-line arg) to switch posts.
# Usage: python poster.py hiring
#        python poster.py ongoing
VARIANTS = {
    "hiring": {
        "prompt": "professional modern office background, blurred, corporate blue theme, no text, no logo, minimalist",
    },
    "ongoing": {
        "prompt": "professional modern office background, blurred, corporate green theme, no text, no logo, minimalist",
    },
}

variant_key = sys.argv[1] if len(sys.argv) > 1 else "hiring"
if variant_key not in VARIANTS:
    raise ValueError(f"Unknown variant '{variant_key}'. Choose from: {list(VARIANTS.keys())}")

variant = VARIANTS[variant_key]
PROMPT = variant["prompt"]

SEED = random.randint(1, 1000000)
IMG_URL = f"https://image.pollinations.ai/prompt/{requests.utils.quote(PROMPT)}?seed={SEED}&nologo=true&width=1080&height=1080"

BG_PATH = "images/background.jpg"
OUTPUT_PATH = f"output/final_post_{variant_key}.jpg"

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

# ---------- 3. SAVE FINAL IMAGE ----------
img = Image.open(BG_PATH).convert("RGB")
img.save(OUTPUT_PATH, quality=95)
print(f"Final poster saved to {OUTPUT_PATH}")