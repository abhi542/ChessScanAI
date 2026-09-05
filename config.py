
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# Application Config
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.5-flash"
ENGINE_VERSION = "Stockfish17"
ANALYSIS_VERSION = "1.0"
REVIEW_VERSION = "1.0"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
OUTPUT_DIR = Path("output")
PATTERN_INSIGHTS_ENABLED_TIERS = ["premium", "free"]
INSIGHTS_GAMES_COUNT = 5

# Tracing
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").strip().lower() == "true"
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "ChessSheetOCR").strip()
import itertools

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_API_KEY_FOR_GAME_REVIEW = os.getenv("GROQ_API_KEY_FOR_GAME_REVIEW", "").strip()

# Support multiple Gemini keys for rotation (comma-separated)
gemini_keys_env = (os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY", "")).strip()
GEMINI_API_KEYS = [k.strip() for k in gemini_keys_env.split(",") if k.strip()]

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in environment variables.")
if not GEMINI_API_KEYS:
    print("WARNING: GEMINI_API_KEYS is not set in environment variables.")

# Create an infinite round-robin iterator for the keys
_gemini_key_cycle = itertools.cycle(GEMINI_API_KEYS) if GEMINI_API_KEYS else None

def get_gemini_key() -> str:
    """Returns the next Gemini API key in the rotation."""
    if not _gemini_key_cycle:
        return ""
    return next(_gemini_key_cycle)

# DB & Auth Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017").strip()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production").strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

# Usage Limits (Per User Per Day)
FREE_TIER_LIMITS = {"ocr": 50, "review": 3, "insights": 2}
PRO_TIER_LIMITS = {"ocr": 500, "review": 500, "insights": 500}
