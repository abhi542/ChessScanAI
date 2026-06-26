
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# Application Config
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
ENGINE_VERSION = "Stockfish17"
ANALYSIS_VERSION = "1.0"
REVIEW_VERSION = "1.0"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
OUTPUT_DIR = Path("output")

# Tracing
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "ChessSheetOCR")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_KEY_FOR_GAME_REVIEW = os.getenv("GROQ_API_KEY_FOR_GAME_REVIEW")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in environment variables.")
if not GROQ_API_KEY_FOR_GAME_REVIEW:
    print("WARNING: GROQ_API_KEY_FOR_GAME_REVIEW is not set in environment variables.")

# DB & Auth Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-prod")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Usage Limits
FREE_TIER_LIMITS = {"ocr": 5, "review": 5}
PRO_TIER_LIMITS = {"ocr": 10, "review": 10}
