import asyncio
import database
import config
from engine import ChessEngine
import review_logic
import review_service

async def main():
    await database.connect_db()
    db = database.get_db()
    game = await db.games.find_one()
    if not game:
        print("No game found")
        return
    
    pgn = game["pgn"]
    review = review_service.process_game_review(pgn)
    
    # print the white stats
    print("White stats:", review["players"]["white"])
    
    await database.close_db()

asyncio.run(main())
