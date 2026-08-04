from flask import Flask, request, send_file, jsonify
import requests
import random
import time
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

VARIANTS = {
    "hiring": {
        "main": "WE ARE HIRING",
        "sub": None,
        "prompts": [
            "modern software developer workstation, multiple monitors with code, blue and purple neon glow, empty desk, no text, no logo, minimalist, wide shot",
            "server room with glowing blue lights, rows of racks, futuristic data center, no text, no logo, cinematic",
            "diverse team of developers standing together looking at a laptop screen, modern office, natural light, candid, professional photography, no text, no logo, photorealistic",
            "young professional standing confidently in modern tech office, arms crossed, smiling, blurred background, professional photography, no text, no logo, photorealistic",
            "team of coworkers sitting together at a table, laughing, bright startup office, candid photo, professional photography, no text, no logo, photorealistic",
            "software engineer sitting at desk coding, smiling at camera, modern office background, professional photography, no text, no logo, photorealistic",
            "group of coworkers standing in a meeting room discussing ideas, laptops open, natural light, professional photography, no text, no logo, photorealistic",
            "startup tech office space, exposed brick, laptops on desks, warm amber lighting, no text, no logo",
            "futuristic control room, multiple screens with data graphs, cyan glow, no text, no logo, cinematic",
            "professional woman standing in modern office hallway, arms crossed, confident smile, professional photography, no text, no logo, photorealistic",
        ],
    },
    "ongoing": {
        "main": "WE ARE ONGOING",
        "sub": None,
        "prompts": [
            "modern tech office hallway, glass walls, teal and silver lighting, no text, no logo, minimalist",
            "team of coworkers walking together in bright office corridor, candid, professional photography, no text, no logo, photorealistic",
            "data center server racks, glowing green indicator lights, no text, no logo, cinematic",
            "two colleagues standing and smiling together in modern office, professional attire, professional photography, no text, no logo, photorealistic",
            "developer team sitting together reviewing code on screen, collaborative, professional photography, no text, no logo, photorealistic",
            "cloud technology abstract background, soft purple gradient, circuit patterns, no text, no logo",
            "software company breakout area, coworkers chatting on bean bags, laptops, warm lighting, professional photography, no text, no logo, photorealistic",
            "futuristic coding interface on large screen, cyan and white theme, no text, no logo, cinematic",
            "tech startup office rooftop, city skyline, blue hour lighting, no text, no logo",
            "professional man standing at standing desk with monitor, confident pose, modern office, professional photography, no text, no logo, photorealistic",
        ],
    },
}

# Track recently used prompts (in-memory) to avoid repeats across consecutive posts
_recent_prompts = {"hiring": [], "ongoing": []}
_HISTORY_LIMIT = 4  # won't repeat the last 4 backgrounds used for that variant

FONT_BOLD = "fonts/Poppins-Bold.ttf"
FONT_REGULAR = "fonts/Poppins-Regular.ttf"
BG_PATH = "images/background.jpg"


def generate_poster(variant_key, custom_prompt=None):
    if variant_key not in VARIANTS:
        raise ValueError(f"Unknown variant '{variant_key}'. Choose from: {list(VARIANTS.keys())}")

    variant = VARIANTS[variant_key]
    MAIN_TEXT = variant["main"]
    SUB_TEXT = variant["sub"]

    if custom_prompt:
        PROMPT = custom_prompt
    else:
        available = [p for p in variant["prompts"] if p not in _recent_prompts[variant_key]]
        if not available:
            available = variant["prompts"]  # reset if we've used them all
        PROMPT = random.choice(available)
        _recent_prompts[variant_key].append(PROMPT)
        if len(_recent_prompts[variant_key]) > _HISTORY_LIMIT:
            _recent_prompts[variant_key].pop(0)

    SEED = random.randint(1, 1000000)
    IMG_URL = f"https://image.pollinations.ai/prompt/{requests.utils.quote(PROMPT)}?seed={SEED}&nologo=true&width=1080&height=1080"
    OUTPUT_PATH = f"output/final_post_{variant_key}.jpg"

    print(f"Generating '{variant_key}' post...")
    print("URL:", IMG_URL)

    MAX_RETRIES = 5
    RETRY_DELAY = 5
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
            print(f"Attempt {attempt} failed: {type(e).__name__}: {e}")
            if attempt == MAX_RETRIES:
                raise Exception("Could not reach Pollinations after multiple attempts.")
        time.sleep(RETRY_DELAY)

    if response is None or response.status_code != 200:
        raise Exception(f"Failed to download image. Status: {response.status_code if response else 'no response'}")

    with open(BG_PATH, "wb") as f:
        f.write(response.content)

    print("Background downloaded successfully.")

    img = Image.open(BG_PATH).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    band_top = int(H * 0.72)
    band_bottom = H
    overlay_draw.rectangle([(0, band_top), (W, band_bottom)], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    main_font_size = int(W * 0.095)
    main_font = ImageFont.truetype(FONT_BOLD, main_font_size)

    def draw_centered(text, font, y_center, fill="white"):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (W - text_w) / 2
        y = y_center - text_h / 2
        draw.text((x, y), text, font=font, fill=fill)

    if SUB_TEXT:
        sub_font_size = int(W * 0.04)
        sub_font = ImageFont.truetype(FONT_REGULAR, sub_font_size)
        draw_centered(MAIN_TEXT, main_font, H * 0.83)
        draw_centered(SUB_TEXT, sub_font, H * 0.92)
    else:
        draw_centered(MAIN_TEXT, main_font, H * 0.86)

    img.save(OUTPUT_PATH, quality=95)
    print(f"Final poster saved to {OUTPUT_PATH}")
    return OUTPUT_PATH


@app.route("/generate", methods=["GET"])
def generate():
    variant_key = request.args.get("variant", "hiring")
    custom_prompt = request.args.get("prompt", None)

    try:
        output_path = generate_poster(variant_key, custom_prompt)
        return send_file(output_path, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)