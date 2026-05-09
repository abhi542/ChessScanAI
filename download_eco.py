import os
import json
import urllib.request
import chess

TSV_URLS = [
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/b.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/c.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/d.tsv",
    "https://raw.githubusercontent.com/lichess-org/chess-openings/master/e.tsv",
]

def generate_eco_json():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    out_file = os.path.join(data_dir, "eco.json")

    openings = []

    for url in TSV_URLS:
        print(f"Downloading {url}...")
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                
                lines = content.strip().split('\n')
                # Skip header: eco \t name \t pgn
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        eco = parts[0].strip()
                        name = parts[1].strip()
                        pgn_moves = parts[2].strip()

                        # Convert PGN string to FEN using python-chess
                        board = chess.Board()
                        try:
                            for move_san in pgn_moves.split():
                                # skip move numbers like "1."
                                if "." in move_san:
                                    continue
                                board.push_san(move_san)
                            
                            openings.append({
                                "eco": eco,
                                "name": name,
                                "fen": board.fen()
                            })
                        except Exception as e:
                            # If a move is invalid, skip
                            continue
        except Exception as e:
            print(f"Failed to process {url}: {e}")

    with open(out_file, "w") as f:
        json.dump(openings, f, indent=2)
    
    print(f"Successfully compiled {len(openings)} openings into {out_file}!")

if __name__ == "__main__":
    generate_eco_json()
