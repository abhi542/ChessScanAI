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
                db_state.db = db_state.client.get_default_database("chess_ocr")
                import pymongo
                await db_state.db.games.create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
                await db_state.db.analysis.create_index("game_id", unique=True)
                await db_state.db.reviews.create_index("game_id", unique=True)
                await db_state.db.usage_metrics.create_index([("user_id", pymongo.ASCENDING), ("date", pymongo.DESCENDING)])
                print("[INFO] Connected to MongoDB and ensured indexes.")
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

async def get_user_by_id(user_id: str):
    from bson.objectid import ObjectId
    db = get_db()
    if db is None: return None
    return await db.users.find_one({"_id": ObjectId(user_id)})

async def delete_user_account(user_id: str, keep_games: bool):
    from bson.objectid import ObjectId
    db = get_db()
    if db is None: return False
    
    # 1. Always delete the user profile
    await db.users.delete_one({"_id": ObjectId(user_id)})
    
    # 2. Always delete their usage metrics (these aren't useful for fine-tuning anyway)
    await db.usage_metrics.delete_many({"user_id": user_id})
    
    # 3. If they didn't donate games, delete games, analysis, and reviews
    if not keep_games:
        await db.games.delete_many({"user_id": user_id})
        await db.analysis.delete_many({"user_id": user_id})
        await db.reviews.delete_many({"user_id": user_id})
        
    return True

async def accept_terms(user_id: str):
    from datetime import datetime
    from bson.objectid import ObjectId
    db = get_db()
    if db is None: return False
    
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"terms_accepted_at": datetime.utcnow()}}
    )
    return result.modified_count > 0
async def create_user(user_data: dict):
    from datetime import datetime
    db = get_db()
    if db is None: return None
    now = datetime.utcnow()
    user_data["created_at"] = now
    user_data["updated_at"] = now
    result = await db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    return user_data

async def save_game(game_data: dict):
    from datetime import datetime
    db = get_db()
    if db is None: return None
    now = datetime.utcnow()
    game_data["created_at"] = now
    game_data["updated_at"] = now
    result = await db.games.insert_one(game_data)
    game_data["_id"] = result.inserted_id
    return str(result.inserted_id)

async def list_user_games(user_id: str, page: int = 1, limit: int = 20):
    db = get_db()
    if db is None: return [], 0
    skip = (page - 1) * limit
    cursor = db.games.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    total = await db.games.count_documents({"user_id": user_id})
    games = await cursor.to_list(length=limit)
    for g in games:
        g["_id"] = str(g["_id"])
    return games, total

async def get_latest_games_with_tag(user_id: str, count: int = 5):
    db = get_db()
    if db is None: return []
    cursor = db.games.find(
        {"user_id": user_id, "its_me": {"$in": ["white", "black"]}}
    ).sort("created_at", -1).limit(count)
    games = await cursor.to_list(length=count)
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

async def get_game_by_id(game_id: str):
    from bson.objectid import ObjectId
    db = get_db()
    if db is None: return None
    try:
        game = await db.games.find_one({"_id": ObjectId(game_id)})
        if game:
            game["_id"] = str(game["_id"])
        return game
    except Exception:
        return None

async def get_analysis(game_id: str):
    db = get_db()
    if db is None: return None
    analysis = await db.analysis.find_one({"game_id": game_id})
    if analysis:
        analysis["_id"] = str(analysis["_id"])
    return analysis

async def save_or_update_analysis(game_id: str, analysis_data: dict):
    from datetime import datetime
    db = get_db()
    if db is None: return None
    now = datetime.utcnow()
    analysis_data["updated_at"] = now
    await db.analysis.update_one(
        {"game_id": game_id},
        {
            "$set": analysis_data,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    return analysis_data

async def get_review(game_id: str):
    db = get_db()
    if db is None: return None
    review = await db.reviews.find_one({"game_id": game_id})
    if review:
        review["_id"] = str(review["_id"])
    return review

async def save_or_update_review(game_id: str, review_data: dict):
    from datetime import datetime
    db = get_db()
    if db is None: return None
    now = datetime.utcnow()
    review_data["updated_at"] = now
    await db.reviews.update_one(
        {"game_id": game_id},
        {
            "$set": review_data,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    return review_data

async def get_cached_insight(user_id: str, game_ids: list[str]):
    db = get_db()
    if db is None: return None
    sorted_ids = sorted(game_ids)
    insight = await db.insights.find_one({
        "user_id": user_id, 
        "game_ids": sorted_ids
    })
    if insight:
        insight["_id"] = str(insight["_id"])
    return insight

async def save_insight(user_id: str, game_ids: list[str], insight_json: dict):
    from datetime import datetime
    db = get_db()
    if db is None: return None
    now = datetime.utcnow()
    sorted_ids = sorted(game_ids)
    
    insight_data = {
        "user_id": user_id,
        "game_ids": sorted_ids,
        "insight_json": insight_json,
        "created_at": now
    }
    
    await db.insights.update_one(
        {"user_id": user_id, "game_ids": sorted_ids},
        {"$set": insight_data},
        upsert=True
    )
    return insight_data

async def increment_usage_metric(user_id: str, metric_field: str):
    from datetime import datetime
    db = get_db()
    if db is None: return
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await db.usage_metrics.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {metric_field: 1}},
        upsert=True
    )

async def check_usage_limit(user_id: str, feature: str) -> bool:
    """
    Checks if the user has hit their daily limit for a specific feature.
    feature should be "ocr" or "review".
    Returns True if allowed, False if limit reached.
    """
    from datetime import datetime
    from bson.objectid import ObjectId
    
    db = get_db()
    if db is None: return True # Fail open if DB is down
    
    # Get user plan
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user: return False
    
    plan = user.get("plan", "free")
    limits = config.PRO_TIER_LIMITS if plan == "premium" else config.FREE_TIER_LIMITS
    max_allowed = limits.get(feature, 5)
    
    # Get today's usage
    today = datetime.utcnow().strftime("%Y-%m-%d")
    metrics = await db.usage_metrics.find_one({"user_id": user_id, "date": today})
    
    if not metrics:
        return True
        
    metric_field = f"{feature}_count"
    current_usage = metrics.get(metric_field, 0)
    
    return current_usage < max_allowed
