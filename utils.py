
import base64
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
import config

def encode_image(image_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_image_media_type(image_path: str) -> str:
    """Return the MIME type for the given image file."""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    return mime_map.get(ext, "image/jpeg")

def create_llm():
    """Instantiate the Gemini vision LLM with a lite fallback."""
    key = config.get_gemini_key()
    primary = ChatGoogleGenerativeAI(
        model=config.PRIMARY_MODEL, 
        temperature=0.8,
        google_api_key=key
    )
    fallback = ChatGoogleGenerativeAI(
        model=config.FALLBACK_MODEL, 
        temperature=0.8,
        google_api_key=key
    )
    return primary.with_fallbacks([fallback])
