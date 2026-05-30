import asyncio
from review_service import process_game_review
import json

sample_pgn = """
[Event "FIDE World Cup 2017"]
[Site "Tbilisi GEO"]
[Date "2017.09.09"]
[Round "4.1"]
[White "Carlsen,M"]
[Black "Bu Xiangzhi"]
[Result "0-1"]
[WhiteElo "2827"]
[BlackElo "2710"]
[EventDate "2017.09.03"]
[ECO "C50"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 d6 6. c3 a6 7. Re1 Ba7
8. a4 h6 9. Nbd2 O-O 10. h3 Re8 11. b4 Be6 12. Bxe6 Rxe6 13. Qc2 Qd7
14. Nf1 Ne7 15. Be3 Bxe3 16. Nxe3 Ng6 17. c4 a5 18. b5 c6 19. Rab1 Ree8
20. Rb2 d5 21. bxc6 bxc6 22. cxd5 cxd5 23. Rb5 Rac8 24. Qb3 Nf4 25. exd5
e4 26. dxe4 Nxe4 27. Nc4 Nc3 28. Qxc3 Ne2+ 29. Rxe2 Rxe2 30. Qd3 Ra2
31. Nb6 Rc1+ 32. Kh2 Qd6+ 33. g3 Rxf2+ 34. MathMateIn 1
"""

def test():
    try:
        # We need a simpler PGN for a quick test so we don't wait too long
        quick_pgn = "1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4 4. Nxe5 Qg5 5. Nxf7 Qxg2 6. Rf1 Qxe4+ 7. Be2 Nf3#"
        print("Running analysis on quick PGN...")
        res = process_game_review(quick_pgn)
        print("Success! JSON output:")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
