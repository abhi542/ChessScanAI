
import sys
import chess
import chess.pgn
from pathlib import Path
from datetime import date
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

import config
import utils
import prompts
from schema import Scoresheet

# ── Extraction Service ────────────────────────────────────────────────────────

@traceable
def extract_moves(image_path: str) -> list[dict]:
    """
    Send the scoresheet image to the LLM once and extract all moves.
    Returns a list of dicts: [{"move_number": int, "white": str|None, "black": str|None}, ...]
    """
    image_b64 = utils.encode_image(image_path)
    media_type = utils.get_image_media_type(image_path)
    
    # Configure LLM for structured output
    llm = utils.create_llm().with_structured_output(Scoresheet).with_config({"run_name": "extract_moves"})

    messages = [
        SystemMessage(content=prompts.SYSTEM_PROMPT),
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
        # In API context, re-raising might be better to let FastAPI handle it, 
        # but maintaining existing behavior for now or just return empty/error dict
        raise e 

    # Convert back to list of dicts for compatibility
    return [move.dict() for move in result.moves]


# ── Validation Service ────────────────────────────────────────────────────────

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
        # Pydantic models might be passed? No, raw_moves here is list[dict] from extract_moves
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


# ── PGN Service ──────────────────────────────────────────────────────────────

def build_pgn(
    annotated_moves: list[dict],
    board: chess.Board,
    output_path: str, # Keeping arg for compatibility but logic below handles writing
    white: str = "?",
    black: str = "?",
    tournament_name: str = "Chess OCR",
    game_format: str = "?",
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
    game.headers["Event"] = tournament_name
    game.headers["Site"] = game_format
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


# ── Analysis ──────────────────────────────────────────────────────────────────

@traceable(run_type="chain", name="token_usage_analysis")
def analyze_token_usage(image_path: str):
    """
    Perform separate text-only and image-based calls to simpler prompts
    to isolate and verify token usage in LangSmith.
    """
    llm = utils.create_llm()
    
    print("\n--- [Analysis] 1. Text-Only Request ---")
    text_msg = [HumanMessage(content="Return the word 'Check'.")]
    # We use a simple invoke here, not structured output, to keep it raw
    response_text = llm.invoke(text_msg)
    print(f"Response: {response_text.content}")
    print("Check LangSmith for input tokens (Text).")

    print("\n--- [Analysis] 2. Image + Text Request ---")
    image_b64 = utils.encode_image(image_path)
    media_type = utils.get_image_media_type(image_path)
    
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
