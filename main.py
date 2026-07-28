"""
Chess Scoresheet OCR → PGN Pipeline
====================================
Takes a photograph of a handwritten chess scoresheet, extracts ALL moves
in a single LLM call, validates them offline with python-chess, flags
any invalid moves as comments, and writes a PGN file.

Usage:
    python main.py --image scoresheet.jpg
    python main.py --image scoresheet.jpg --output game.pgn
    python main.py --image scoresheet.jpg --white "Magnus" --black "Hikaru"
"""

import argparse
import base64
import json
import re
import sys
import os
from datetime import date
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv
load_dotenv(override=True)

import chess
import chess.pgn
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable
import config

load_dotenv(override=True)


# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
OUTPUT_DIR = Path("output")


from pydantic import BaseModel, Field
# ── Pydantic Models ──────────────────────────────────────────────────────────

class ChessMove(BaseModel):
    move_number: int = Field(..., description="The move number (e.g., 1, 2, ...)")
    white: str | None = Field(None, description="White's move in SAN (Standard Algebraic Notation), or null if empty.")
    black: str | None = Field(None, description="Black's move in SAN, or null if empty.")

class Scoresheet(BaseModel):
    moves: list[ChessMove] = Field(..., description="List of all chess moves found on the scoresheet.")


# ── Extraction Prompt ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a deterministic chess notation recognition engine.
Your task is to read ALL handwritten chess moves from the scoresheet image.

CRITICAL — Scoresheet layout:
Chess scoresheets almost always have a TWO-COLUMN layout:
  - LEFT column:  move numbers 1–30 with White and Black columns
  - RIGHT column: move numbers 31–60 with White and Black columns
You MUST read BOTH the left AND right columns.
Read the LEFT column first, then the RIGHT column.

Strict rules:
- Extract ONLY standard algebraic notation (SAN).
- Do not include commentary.
- If a cell is empty or illegible, use null.
- Correct common OCR errors if strictly clear (e.g. '0-0' -> 'O-O').
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ── Extraction (Single LLM Call) ─────────────────────────────────────────────

@traceable
def extract_moves(image_path: str) -> list[dict]:
    """
    Send the scoresheet image to the LLM once and extract all moves.
    Returns a list of dicts: [{"move_number": int, "white": str|None, "black": str|None}, ...]
    """
    image_b64 = encode_image(image_path)
    media_type = get_image_media_type(image_path)
    
    # Configure LLM for structured output
    llm = create_llm().with_structured_output(Scoresheet).with_config({"run_name": "extract_moves"})

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extract all chess moves from this scoresheet.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_b64}",
                    },
                },
            ]
        ),
    ]

    try:
        # returns a Scoresheet object
        result: Scoresheet = llm.invoke(messages)
    except Exception as e:
        print(f"[ERROR] LLM Extraction failed: {e}")
        sys.exit(1)

    # Convert back to list of dicts for compatibility with existing code
    return [move.dict() for move in result.moves]


# ── Analysis ──────────────────────────────────────────────────────────────────

@traceable(run_type="chain", name="token_usage_analysis")
def analyze_token_usage(image_path: str):
    """
    Perform separate text-only and image-based calls to simpler prompts
    to isolate and verify token usage in LangSmith.
    """
    llm = create_llm()
    
    print("\n--- [Analysis] 1. Text-Only Request ---")
    text_msg = [HumanMessage(content="Return the word 'Check'.")]
    # We use a simple invoke here, not structured output, to keep it raw
    response_text = llm.invoke(text_msg)
    print(f"Response: {response_text.content}")
    print("Check LangSmith for input tokens (Text).")

    print("\n--- [Analysis] 2. Image + Text Request ---")
    image_b64 = encode_image(image_path)
    media_type = get_image_media_type(image_path)
    
    image_msg = [
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Just say 'Image received'.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_b64}",
                    },
                },
            ]
        )
    ]
    response_image = llm.invoke(image_msg)
    print(f"Response: {response_image.content}")
    print("Check LangSmith for input tokens (Image + Text).")


# ── Validation ────────────────────────────────────────────────────────────────

def validate_moves(raw_moves: list[dict]) -> tuple[list[dict], chess.Board]:
    """
    Replay all extracted moves on a chess.Board.
    Each move gets a 'valid' flag, an 'error' message if invalid, and a 'fen' string.
    Returns (annotated_moves, board_at_last_valid_position).
    """
    board = chess.Board()
    annotated: list[dict] = []
    board_broken = False  # Once we hit an invalid move, all subsequent are unverifiable

    for row in raw_moves:
        move_num = row.get("move_number", "?")
        entry = {"move_number": move_num, "white": None, "black": None}

        for color, key in [("white", "white"), ("black", "black")]:
            raw_san = row.get(key)
            if raw_san is None:
                entry[key] = {"san": None, "valid": True, "error": None, "fen": None}
                continue

            # Normalize common OCR glitches
            san = raw_san.strip().replace("`", "").replace(" ", "")
            san = san.replace("0-0-0", "O-O-O").replace("0-0", "O-O")

            current_fen = board.fen()

            if board_broken:
                entry[key] = {
                    "san": san,
                    "valid": False,
                    "error": "Cannot verify — earlier move was invalid",
                    "fen": current_fen,
                }
                continue

            try:
                # Parse SAN to check validity
                move = board.parse_san(san)
                board.push(move)
                entry[key] = {
                    "san": san,
                    "valid": True,
                    "error": None,
                    "fen": board.fen(),
                }
            except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
                # If invalid, we keep the PREVIOUS FEN so the UI shows the position before the bad move
                entry[key] = {
                    "san": san,
                    "valid": False,
                    "error": str(e),
                    "fen": current_fen,
                }
                board_broken = True

        annotated.append(entry)

    return annotated, board


# ── PGN Builder ──────────────────────────────────────────────────────────────

def build_pgn(
    annotated_moves: list[dict],
    board: chess.Board,
    output_path: str,
    white: str = "?",
    black: str = "?",
    event: str = "Chess Scoresheet OCR",
    site: str = "?",
    date_str: str = None,
    round_str: str = "?",
    result_str: str = "*"
) -> str:
    """
    Build a PGN from validated moves. Invalid moves are added as comments.
    Returns the PGN string.
    """
    game = chess.pgn.Game()

    # ── Headers ──
    game.headers["Event"] = event
    game.headers["Site"] = site
    game.headers["Date"] = date_str if date_str else date.today().strftime("%Y.%m.%d")
    game.headers["Round"] = round_str
    game.headers["White"] = white
    game.headers["Black"] = black

    # Determine result
    if result_str != "*" and result_str != "?":
        result = result_str
    elif board.is_checkmate():
        result = "0-1" if board.turn == chess.WHITE else "1-0"
    elif board.is_stalemate() or board.is_insufficient_material():
        result = "1/2-1/2"
    else:
        result = "*"
    game.headers["Result"] = result

    # ── Add moves ──
    node = game
    replay_board = chess.Board()
    hit_invalid = False

    for row in annotated_moves:
        move_num = row["move_number"]

        for color in ["white", "black"]:
            cell = row[color]
            if cell is None or cell["san"] is None:
                continue

            if hit_invalid:
                # Append remaining moves as a comment on the last valid node
                remaining = _collect_remaining(annotated_moves, move_num, color)
                if remaining:
                    node.comment = (node.comment + " " if node.comment else "") + remaining
                return _write_pgn(game, output_path)

            if cell["valid"]:
                move = replay_board.parse_san(cell["san"])
                node = node.add_variation(move)
                replay_board.push(move)
            else:
                # Flag invalid move as a comment and stop adding to the mainline
                flag = f"[INVALID at move {move_num} {color}: \"{cell['san']}\" — {cell['error']}]"
                node.comment = (node.comment + " " if node.comment else "") + flag

                # Still append all subsequent raw moves as comments for reference
                remaining = _collect_remaining(annotated_moves, move_num, color, skip_current=True)
                if remaining:
                    node.comment += " " + remaining
                hit_invalid = True
                return _write_pgn(game, output_path)

    return _write_pgn(game, output_path)


def _collect_remaining(
    annotated_moves: list[dict],
    from_move: int,
    from_color: str,
    skip_current: bool = False,
) -> str:
    """Collect all remaining raw SAN strings after a given point as a readable string."""
    parts: list[str] = []
    started = False

    for row in annotated_moves:
        move_num = row["move_number"]
        for color in ["white", "black"]:
            cell = row.get(color)
            if cell is None or (isinstance(cell, dict) and cell.get("san") is None):
                continue

            # Find our starting position
            if move_num == from_move and color == from_color:
                started = True
                if skip_current:
                    continue
            if not started:
                continue

            san = cell["san"] if isinstance(cell, dict) else cell
            prefix = f"{move_num}." if color == "white" else f"{move_num}..."
            valid_marker = "" if (isinstance(cell, dict) and cell.get("valid")) else "?"
            parts.append(f"{prefix}{san}{valid_marker}")

    if parts:
        return "[Remaining OCR moves: " + " ".join(parts) + "]"
    return ""


def _write_pgn(game: chess.pgn.Game, output_path: str) -> str:
    """Write PGN to file and return the string."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pgn_string = str(game)

    with open(output, "w") as f:
        f.write(pgn_string)
        f.write("\n")

    return pgn_string


# ── Report ───────────────────────────────────────────────────────────────────

def print_report(annotated_moves: list[dict]) -> None:
    """Print a human-readable validation report to stdout."""
    total = 0
    valid_count = 0
    invalid_moves: list[str] = []

    for row in annotated_moves:
        move_num = row["move_number"]
        for color in ["white", "black"]:
            cell = row[color]
            if cell is None or cell["san"] is None:
                continue
            total += 1
            if cell["valid"]:
                valid_count += 1
                print(f"  ✓ {move_num}. {color}: {cell['san']}")
            else:
                desc = f"  ✗ {move_num}. {color}: {cell['san']}  ← {cell['error']}"
                invalid_moves.append(desc)
                print(desc)

    print(f"\n── Summary ──")
    print(f"  Total moves extracted: {total}")
    print(f"  Valid moves:           {valid_count}")
    print(f"  Invalid/flagged:       {total - valid_count}")

    if invalid_moves:
        print(f"\n── Flagged Moves ──")
        for m in invalid_moves:
            print(m)


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Chess Scoresheet OCR → PGN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py --image scoresheet.jpg
  python main.py --image scoresheet.jpg --output game.pgn
  python main.py --image scoresheet.jpg --white "Magnus" --black "Hikaru"
        """,
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="Path to the chess scoresheet image",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output PGN file path (default: output/<image_stem>.pgn)",
    )
    parser.add_argument("--white", "-w", default="?", help="White player name")
    parser.add_argument("--black", "-b", default="?", help="Black player name")
    parser.add_argument("--event", "-e", default="Chess Scoresheet OCR", help="Event name")
    parser.add_argument("--analyze", action="store_true", help="Run token usage analysis instead of full extraction")

    args = parser.parse_args()

    # Validate image
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"[ERROR] Unsupported image format: {image_path.suffix}")
        print(f"        Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    output_path = args.output or str(OUTPUT_DIR / f"{image_path.stem}.pgn")

    # ── Run Pipeline ──
    print("=" * 60)
    print("  Chess Scoresheet OCR → PGN")
    print("=" * 60)

    if args.analyze:
        analyze_token_usage(str(image_path))
        return

    # Step 1: Extract all moves in one LLM call
    print("\n[1/3] Extracting moves from scoresheet...")
    raw_moves = extract_moves(str(image_path))
    total_cells = sum(
        (1 if row.get("white") else 0) + (1 if row.get("black") else 0)
        for row in raw_moves
    )
    print(f"       Extracted {len(raw_moves)} rows, {total_cells} move cells.\n")

    # Step 2: Validate all moves offline
    print("[2/3] Validating moves against board state...")
    annotated_moves, board = validate_moves(raw_moves)
    print_report(annotated_moves)

    # Step 3: Build PGN
    print(f"\n[3/3] Building PGN...")
    pgn = build_pgn(
        annotated_moves, board, output_path,
        white=args.white, black=args.black, event=args.event,
    )

    print(f"\n[✓] PGN saved to: {output_path}")
    print("-" * 60)
    print(pgn)
    print("-" * 60)


if __name__ == "__main__":
    main()