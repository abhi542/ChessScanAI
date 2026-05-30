import os
import chess
import chess.engine
import chess.pgn
import io

# By default, rely on 'stockfish' being in PATH or specify via STOCKFISH_PATH env var
STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")

class ChessEngine:
    def __init__(self, depth=12, hash_size=16, threads=1):
        self.depth = depth
        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self.engine.configure({"Hash": hash_size, "Threads": threads})

    def analyze_game(self, pgn_string: str):
        pgn = io.StringIO(pgn_string)
        game = chess.pgn.read_game(pgn)
        if game is None:
            raise ValueError("Invalid PGN")

        board = game.board()
        moves_data = []

        # Analyze the starting position (move 0)
        info_start = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
        # Get score relative to white
        score_start = info_start["score"].white().score(mate_score=10000)
        
        current_eval = score_start
        best_move = info_start.get("pv", [None])[0]

        for move in game.mainline_moves():
            player_is_white = board.turn == chess.WHITE
            san = board.san(move)
            
            # The evaluation before this move was made
            eval_before = current_eval
            best_move_before = best_move

            board.push(move)
            fen_after = board.fen()

            # Analyze the position AFTER the move
            info_after = self.engine.analyse(board, chess.engine.Limit(depth=self.depth))
            eval_after = info_after["score"].white().score(mate_score=10000)
            best_move_after = info_after.get("pv", [None])[0]

            # We store the evaluation AFTER the move has been played as the primary eval of this move
            # We also store eval_before so we can calculate the difference.
            moves_data.append({
                "san": san,
                "move_uci": move.uci(),
                "player": "white" if player_is_white else "black",
                "eval_before": eval_before,
                "eval_after": eval_after,
                "best_move": best_move_before.uci() if best_move_before else None,
                "played_best": best_move_before == move if best_move_before else False,
                "fen": fen_after
            })

            current_eval = eval_after
            best_move = best_move_after

        return moves_data, game.headers, board.outcome()

    def close(self):
        self.engine.quit()
