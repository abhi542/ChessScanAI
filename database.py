import config
from motor.motor_asyncio import AsyncIOMotorClient

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_state = Database()

async def connect_db():
    if config.MONGO_URI:
        # Avoid connecting multiple times
        if db_state.client is None:
            try:
                db_state.client = AsyncIOMotorClient(config.MONGO_URI)
                # Select the default database to use
                db_state.db = db_state.client.get_default_database("chess_ocr")
                print("[INFO] Connected to MongoDB.")
            except Exception as e:
                print(f"[ERROR] Failed to connect to MongoDB: {e}")
    else:
        print("[WARNING] MONGO_URI not found. Database features will be disabled.")

async def close_db():
    if db_state.client is not None:
        db_state.client.close()
        print("[INFO] Disconnected from MongoDB.")

def get_db():
    return db_state.db

# ── Helper methods for collections ──
async def get_user_by_email(email: str):
    db = get_db()
    if db is None: return None
    return await db.users.find_one({"email": email})

async def create_user(user_data: dict):
    db = get_db()
    if db is None: return None
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    return user_data

async def save_game(game_data: dict):
    db = get_db()
    if db is None: return None
    result = await db.games.insert_one(game_data)
    game_data["_id"] = result.inserted_id
    return str(result.inserted_id)

async def list_user_games(email: str):
    db = get_db()
    if db is None: return []
    cursor = db.games.find({"user_email": email}).sort("created_at", -1)
    games = await cursor.to_list(length=100)
    for g in games:
        g["_id"] = str(g["_id"])
    return games

async def delete_game(game_id: str):
    from bson.objectid import ObjectId
    db = get_db()
    if db is None: return False
    try:
        result = await db.games.delete_one({"_id": ObjectId(game_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting game: {e}")
        return False
