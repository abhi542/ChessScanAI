import json
import os
import chess

OPENINGS_DB = {}

def load_openings():
    global OPENINGS_DB
    filepath = os.path.join(os.path.dirname(__file__), "data", "eco.json")
    if not os.path.exists(filepath):
        print(f"Warning: Openings database not found at {filepath}")
        return

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            for entry in data:
                try:
                    board = chess.Board(entry["fen"])
                    epd = board.epd()
                    OPENINGS_DB[epd] = {"eco": entry["eco"], "name": entry["name"]}
                except Exception:
                    pass
        print(f"Loaded {len(OPENINGS_DB)} openings from ECO database.")
    except Exception as e:
        print(f"Failed to load openings database: {e}")

load_openings()

def identify_opening(fens: list[str]) -> dict:
    deepest_match = {"eco": "", "name": "Unknown Opening"}
    for fen in fens:
        try:
            board = chess.Board(fen)
            epd = board.epd()
            if epd in OPENINGS_DB:
                deepest_match = OPENINGS_DB[epd]
        except ValueError:
            continue
    return deepest_match
