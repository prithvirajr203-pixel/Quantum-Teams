from flask import Flask, request, send_file, jsonify
import os
import requests
import random
import time
from PIL import Image

app = Flask(__name__)

VARIANTS = {
    "hiring": {
        "prompts": [
            "confident software developer portrait office",
            "young professional programmer smiling office",
            "IT professional standing office portrait",
            "software engineer smiling at camera office",
            "confident tech employee portrait workplace",
            "professional programmer headshot modern office",
            "tech worker smiling office portrait",
            "confident businesswoman tech office portrait",
            "young developer standing office smiling",
            "IT recruiter professional portrait office",
        ],
    },
    "ongoing": {
        "prompts": [
            "tech office hallway computers",
            "coworkers walking tech office",
            "server racks data center",
            "colleagues computer screen office",
            "developer team code screen",
            "cloud technology digital background",
            "tech office breakout laptops",
            "programming code screen computer",
            "tech startup office computers",
            "IT professional standing desk monitor computer",
        ],
    },
}

# Track recently used prompts (in-memory) to avoid repeats across consecutive posts
_recent_prompts = {"hiring": [], "ongoing": []}
_HISTORY_LIMIT = 4  # won't repeat the last 4 backgrounds used for that variant

BG_PATH = "images/background.jpg"

# ---- PEXELS API KEY ----
PEXELS_API_KEY = "IhrL6knCRykPJzuHqRe6hwcXYvbKYCECNJReyX1bru5QPZkItrsmj12P"

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
PEXELS_HEADERS = {"Authorization": PEXELS_API_KEY}


def simplify_prompt_for_search(text, max_words=5):
    """
    n8n's Image_describer node sends a long descriptive sentence.
    Pexels search works best with short keyword phrases, so we trim
    long AI-style prompts down to their first few meaningful words.
    """
    # Drop common filler/style words that don't help image search
    stopwords = {
        "a", "an", "the", "with", "and", "no", "text", "logo", "photorealistic",
        "cinematic", "sharp", "focus", "lighting", "professional", "photography",
        "empty", "space", "at", "top", "bottom", "of", "in", "on", "for",
    }
    words = text.replace(",", " ").replace(".", " ").split()
    keywords = [w for w in words if w.lower() not in stopwords]
    return " ".join(keywords[:max_words]) if keywords else text[:40]


def generate_poster(variant_key, custom_prompt=None):
    if variant_key not in VARIANTS:
        raise ValueError(f"Unknown variant '{variant_key}'. Choose from: {list(VARIANTS.keys())}")

    variant = VARIANTS[variant_key]

    if custom_prompt:
        # Long AI-style prompts (e.g. from n8n) get simplified into search keywords
        PROMPT = simplify_prompt_for_search(custom_prompt)
    else:
        available = [p for p in variant["prompts"] if p not in _recent_prompts[variant_key]]
        if not available:
            available = variant["prompts"]  # reset if we've used them all
        PROMPT = random.choice(available)
        _recent_prompts[variant_key].append(PROMPT)
        if len(_recent_prompts[variant_key]) > _HISTORY_LIMIT:
            _recent_prompts[variant_key].pop(0)

    OUTPUT_PATH = f"output/final_post_{variant_key}.jpg"

    # Bias the search differently per variant:
    # - "hiring" posts favor a real professional's portrait
    # - "ongoing" posts favor tech/office environment shots (no bias toward people)
    if variant_key == "hiring":
        SEARCH_QUERY = f"{PROMPT} portrait professional"
    else:
        SEARCH_QUERY = f"{PROMPT} technology office"

    print(f"Generating '{variant_key}' post...")
    print("Search query:", SEARCH_QUERY)

    MAX_RETRIES = 5
    RETRY_DELAY = 5
    image_bytes = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Attempt {attempt}/{MAX_RETRIES}...")

            # Step 1: search Pexels for a matching photo
            search_response = requests.get(
                PEXELS_SEARCH_URL,
                headers=PEXELS_HEADERS,
                params={
                    "query": SEARCH_QUERY,
                    "per_page": 15,
                    "orientation": "square",
                },
                timeout=30
            )

            print("=" * 60)
            print("Search Status Code:", search_response.status_code)

            if search_response.status_code != 200:
                print("Search Response Body:", search_response.text[:500])
                print("=" * 60)
                if attempt < MAX_RETRIES:
                    print(f"Retrying in {RETRY_DELAY} seconds...\n")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    raise Exception(f"Pexels search failed after {MAX_RETRIES} attempts.")

            photos = search_response.json().get("photos", [])
            if not photos:
                print(f"No photos found for query '{PROMPT}'. Retrying.")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    raise Exception(f"No Pexels photos found for query '{PROMPT}'.")

            # Step 2: pick a random photo from the results, download it
            chosen_photo = random.choice(photos)
            image_url = chosen_photo["src"]["large"]

            img_response = requests.get(image_url, timeout=60)
            if img_response.status_code == 200 and "image" in img_response.headers.get("Content-Type", ""):
                image_bytes = img_response.content
                print("Image downloaded successfully from Pexels.")
                break
            else:
                print(f"Failed to download image. Status: {img_response.status_code}")

            print("=" * 60)

        except requests.exceptions.RequestException as e:
            print("Network Error:", e)

        if attempt < MAX_RETRIES:
            print(f"Retrying in {RETRY_DELAY} seconds...\n")
            time.sleep(RETRY_DELAY)
        else:
            raise Exception(f"Failed to get image after {MAX_RETRIES} attempts.")

    if image_bytes is None:
        raise Exception("Failed to download a valid image from Pexels.")

    if not os.path.isdir("output"):
        os.makedirs("output", exist_ok=True)

    with open(BG_PATH, "wb") as f:
        f.write(image_bytes)

    print("Background image saved successfully.")

    # No text overlay — save the clean background photo as the final post image
    img = Image.open(BG_PATH).convert("RGB")
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