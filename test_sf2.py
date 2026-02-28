from stockfish import Stockfish
s = Stockfish("stockfish")
s.set_fen_position("rnb1kbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 2")
print(s.get_evaluation())
