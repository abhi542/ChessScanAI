import asyncio
import database

async def main():
    await database.connect_db()
    db = database.get_db()
    colls = await db.list_collection_names()
    print("Collections:", colls)
    for coll in colls:
        count = await db[coll].count_documents({})
        print(f"{coll}: {count} docs")
    await database.close_db()

asyncio.run(main())
