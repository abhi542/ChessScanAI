import asyncio
from database import get_latest_games_with_tag, get_analysis, connect_db, close_db

async def main():
    await connect_db()
    
    # We will fetch the user from one of the games the user provided.
    user_id = "6a22c958fa1d102437df28d6"
    
    games = await get_latest_games_with_tag(user_id)
    print(f"Found {len(games)} games with its_me tag.")
    
    analyzed_count = 0
    for g in games:
        game_id = g["_id"]
        analysis = await get_analysis(game_id)
        print(f"Game {game_id} - its_me: {g.get('its_me')} - Analysis exists: {analysis is not None}")
        if analysis:
            analyzed_count += 1
            print(f"  Analysis keys: {analysis['analysis_json'].keys()}")
            print(f"  Players: {analysis['analysis_json'].get('players')}")
            
    print(f"Total analyzed games: {analyzed_count}")
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
