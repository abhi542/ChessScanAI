from stockfish import Stockfish
s = Stockfish("stockfish")
s.set_fen_position("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
print("W turn, Standard E4 E5:", s.get_evaluation())
# Remove Black's queen, White's turn
s.set_fen_position("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
print("W turn, B down Queen:", s.get_evaluation())
# Remove Black's queen, Black's turn
s.set_fen_position("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
print("B turn, B down Queen:", s.get_evaluation())
