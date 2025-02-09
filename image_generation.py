import os
import requests
from datetime import datetime
import logging
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Instantiate the client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_image_256(prompt: str, model: str = "dall-e-3") -> str:
    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,                 # Only 1 image
            size="1024x1024",      # Cost-efficient resolution
            response_format="url"
        )
        image_url = response.data[0].url
        logging.info(f"Generated Image URL: {image_url}")
        return image_url
    except Exception as e:
        logging.error(f"Image generation error: {e}")
        return ""

def download_image(image_url: str, filename: str = "output.png"):
    try:
        resp = requests.get(image_url, timeout=10)
        if resp.status_code == 200:
            with open(filename, "wb") as f:
                f.write(resp.content)
            logging.info(f"Saved image to {filename}")
        else:
            logging.error(f"Failed to download: HTTP {resp.status_code}")
    except Exception as e:
        logging.error(f"Download error: {e}")

if __name__ == "__main__":
    # 1) Construct a minimal prompt
    prompt_text = (
    "A gothic anime-style girlfriend with sleek black hair, edgy clothing, and an intense expression."
    "Your boyfriend has expressed Playful/Sexual content and Love/Desire so the girlfriends expression should reflect that."
    )

    # 2) Generate the image
    image_url = generate_image_256(prompt_text)

    if image_url:
        # 3) Download it locally with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"ai_girlfriend_{timestamp}.png"
        download_image(image_url, filename)
    else:
        logging.error("No image URL returned.")
