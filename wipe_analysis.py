import asyncio
import database

async def main():
    await database.connect_db()
    db = database.get_db()
    res = await db.analysis.delete_many({})
    print(f"Deleted {res.deleted_count} old analysis records to force regeneration.")
    res2 = await db.insights.delete_many({})
    print(f"Deleted {res2.deleted_count} cached insights.")
    await database.close_db()

asyncio.run(main())
