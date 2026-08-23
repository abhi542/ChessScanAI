import asyncio
import database
import json

async def main():
    await database.connect_db()
    db = database.get_db()
    cursor = db.analysis.find().limit(5)
    async for doc in cursor:
        stats = doc["analysis_json"]["players"]["white"]
        print(f"Game ID: {doc['game_id']}")
        print(f"White stats keys: {stats.keys()}")
        if "accuracy_by_phase" in stats:
            print(f"accuracy_by_phase: {stats['accuracy_by_phase']}")
        else:
            print("NO ACCURACY BY PHASE!")
    
    await database.close_db()

asyncio.run(main())
