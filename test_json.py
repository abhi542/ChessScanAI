import asyncio
import database
from insights_service import generate_pattern_insights

async def main():
    await database.connect_db()
    games = await database.get_latest_games_with_tag("test_user_id_which_is_not_real_just_need_to_fetch_a_real_users_games", count=5)
    # wait, I need a real user ID. Let's just fetch any 5 games.
    db = database.get_db()
    games = await db.games.find({"its_me": {"$exists": True}}).limit(5).to_list(length=5)
    if games:
        user_id = games[0]["user_id"]
        res = await generate_pattern_insights(user_id, games)
        print(res["deep_analysis"]["error_heatmap"])
    
    await database.close_db()

asyncio.run(main())
