from stockfish import Stockfish
s = Stockfish("stockfish")
s.set_fen_position("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
print("White to move (e4 e5):", s.get_evaluation())
s.set_fen_position("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
print("Black to move (e4 e5) (same board but black turn):", s.get_evaluation())
# Black is crushing (down a queen for white)
s.set_fen_position("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 2")
print("Black crushing:", s.get_evaluation())
