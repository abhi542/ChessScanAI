
import os
import shutil
import uvicorn
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import chess.pgn

# Modular Imports
import config
import services
from schema import ValidationRequest, ValidationResponse, User, SavedGame, GameCreateRequest
import database
import auth
import httpx
from typing import Optional
from pydantic import BaseModel
import openings
import review_service
import os
# Removed stockfish logic

# Initialize FastAPI
app = FastAPI(
    title="ChessLensAI API",
    description="Backend for ChessLensAI: OCR, PGN parsing, and Validation.",
    version="1.0.0"
)

# ── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files & Templates ─────────────────────────────────────────────────

# Ensure static directory exists
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static")

@app.on_event("startup")
async def startup_event():
    await database.connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    await database.close_db()

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "google_client_id": config.GOOGLE_CLIENT_ID}
    )


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "healthy", "model": config.MODEL_NAME}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...), user_id: str = Depends(auth.get_current_user_id)):
    """
    1. Upload Image
    2. Run OCR (via LLM Service)
    3. Return Raw Moves
    """
    
    # Check limit
    allowed = await database.check_usage_limit(user_id, "ocr")
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": "LIMIT_REACHED", "feature": "ocr"})
        
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / file.filename
    try:
        # Save temp file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"[INFO] Processing image: {file_path}")
        
        # Call Service
        raw_moves = services.extract_moves(str(file_path))
        
        # Increment metric
        await database.increment_usage_metric(user_id, "ocr_count")
        
        return {"moves": raw_moves}

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Image processing failed: {error_msg}")
        
        # Handle Groq refusal / tool use failure for non-chess images
        if "tool_use_failed" in error_msg or "invalid_request_error" in error_msg:
            raise HTTPException(
                status_code=400, 
                detail={"error": "INVALID_IMAGE", "message": "No valid chess scoresheet detected. Please make sure the image clearly shows a chess scoresheet."}
            )
            
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # Cleanup
        if file_path.exists():
            os.remove(file_path)


@app.post("/api/validate", response_model=ValidationResponse)
async def validate_game(request: ValidationRequest):
    """
    1. Receive Moves
    2. Validate against Chess Rules (Service)
    3. Return Annotated Moves + PGN
    """
    # Convert Pydantic models to list of dicts for service
    raw_moves = [m.dict() for m in request.moves]
    
    annotated_moves, board = services.validate_moves(raw_moves)
    
    # Check if completely valid
    is_valid = all(
        (row["white"] is None or row["white"]["valid"]) and 
        (row["black"] is None or row["black"]["valid"])
        for row in annotated_moves
    )
    
    pgn_string = None
    if is_valid:
        # Generate PGN (using a temp file as required by current build_pgn interface)
        output_path = config.OUTPUT_DIR / "temp_web_export.pgn"
        pgn_string = services.build_pgn(
            annotated_moves, 
            board, 
            str(output_path), 
            white=request.white_player, 
            black=request.black_player, 
            event=request.event,
            site=request.site,
            date_str=request.date,
            round_str=request.round,
            result_str=request.result
        )
        # We can return the string directly, `build_pgn` returns it too.

    return {
        "annotated_moves": annotated_moves,
        "valid": is_valid,
        "pgn": pgn_string
    }


@app.post("/api/upload-pgn")
async def upload_pgn_file(file: UploadFile = File(...)):
    """
    1. Upload PGN File
    2. Parse PGN
    3. Extract & Validate Moves
    4. Return State
    """
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / file.filename

    try:
        # Save temp file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse PGN using python-chess
        with open(file_path, "r") as f:
            game = chess.pgn.read_game(f)

        if game is None:
            raise HTTPException(status_code=400, detail="Invalid or empty PGN file")

        # Extract Headers
        headers = game.headers
        metadata = {
            "white_player": headers.get("White", "?"),
            "black_player": headers.get("Black", "?"),
            "event": headers.get("Event", "?"),
            "site": headers.get("Site", "?"),
            "date": headers.get("Date", ""),
            "round": headers.get("Round", "?"),
            "result": headers.get("Result", "*"),
        }

        # Extract Moves from Mainline
        moves_list = []
        node = game
        move_number = 0
        
        while node.variations:
            next_node = node.variation(0)
            move = next_node.move
            san = node.board().san(move)
            
            if node.board().turn == chess.WHITE:
                move_number += 1
                moves_list.append({
                    "move_number": move_number,
                    "white": san,
                    "black": None
                })
            else:
                if moves_list:
                    moves_list[-1]["black"] = san
                else:
                    # Rare: Black starts (e.g. from position), handle gracefully
                    moves_list.append({
                        "move_number": move_number,
                        "white": None,
                        "black": san
                    })
            
            node = next_node
        
        # Validate Extracted Moves
        annotated_moves, board = services.validate_moves(moves_list)

        return {
            "annotated_moves": annotated_moves,
            "valid": True, 
            "pgn": str(game),
            **metadata
        }

    except Exception as e:
        print(f"[ERROR] PGN Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if file_path.exists():
            os.remove(file_path)

# ── Auth & Database Endpoints ────────────────────────────────────────────────

from pydantic import BaseModel

class GoogleAuthRequest(BaseModel):
    token: str

@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    """
    Verify Google ID token and issue a local JWT.
    """
    try:
        # Verify token with Google's public endpoint
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={request.token}")
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            
            user_info = resp.json()
            email = user_info.get("email")
            name = user_info.get("name")
            picture = user_info.get("picture")

            if not email:
                raise HTTPException(status_code=400, detail="Email not provided by Google")

            # Check if user exists in our DB, if not create them
            user = await database.get_user_by_email(email)
            if not user:
                user = await database.create_user({"email": email, "name": name, "picture": picture, "plan": "free"})

            user_id = str(user["_id"])

            # Issue our own JWT
            access_token = auth.create_access_token(data={"sub": user_id})
            refresh_token = auth.create_refresh_token(data={"sub": user_id})
            return {
                "access_token": access_token, 
                "refresh_token": refresh_token,
                "token_type": "bearer", 
                "user": {"id": user_id, "email": email, "name": name, "picture": picture}
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RefreshRequest(BaseModel):
    refresh_token: str

@app.post("/api/auth/refresh")
async def refresh_token(req: RefreshRequest):
    payload = auth.verify_refresh_token(req.refresh_token)
    user_id = payload.get("sub")
    access_token = auth.create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/games")
async def save_user_game(game: GameCreateRequest, user_id: str = Depends(auth.get_current_user_id)):
    """
    Save a fully validated game to the current user's profile.
    """
    game_dict = game.dict()
    game_dict["user_id"] = user_id
    game_id = await database.save_game(game_dict)
    if not game_id:
        raise HTTPException(status_code=500, detail="Failed to save game to database")
    
    return {"status": "success", "game_id": game_id}


@app.get("/api/games")
async def get_user_games(page: int = 1, limit: int = 20, user_id: str = Depends(auth.get_current_user_id)):
    """
    List all games saved by the current user.
    """
    games, total = await database.list_user_games(user_id, page, limit)
    return {
        "items": games,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total
    }

@app.get("/api/games/{game_id}")
async def get_game(game_id: str, user_id: str = Depends(auth.get_current_user_id)):
    game = await database.get_game_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this game")
    return game

@app.delete("/api/games/{game_id}")
async def delete_user_game(game_id: str, user_id: str = Depends(auth.get_current_user_id)):
    """
    Delete a specific game by ID, verifying ownership.
    """
    from bson.objectid import ObjectId
    from fastapi import HTTPException
    
    db = database.get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    try:
        # Check ownership
        game = await db.games.find_one({"_id": ObjectId(game_id)})
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        if game.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this game")
            
        # Delete
        success = await database.delete_game(game_id)
        if success:
            return {"status": "success", "message": "Game deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete game")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid game ID format")


# Evaluation API removed

class OpeningRequest(BaseModel):
    fens: list[str]

@app.post("/api/opening")
async def get_opening(req: OpeningRequest):
    """
    Identify the ECO code and name of the opening based on game history.
    """
    match = openings.identify_opening(req.fens)
    return match

class ReviewRequest(BaseModel):
    game_id: str

@app.post("/api/review")
async def generate_game_review(req: ReviewRequest, user_id: str = Depends(auth.get_current_user_id)):
    """
    Generate a complete Game Review Card JSON from a game_id.
    """
    try:
        game = await database.get_game_by_id(req.game_id)
        if not game or game.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Game not found or unauthorized")

        # Cache lookup
        analysis = await database.get_analysis(req.game_id)
        if analysis:
            # Validate versions
            if analysis.get("engine_version") == config.ENGINE_VERSION and analysis.get("analysis_version") == config.ANALYSIS_VERSION:
                return analysis["analysis_json"]

        # Cache miss or stale -> Regenerate
        review_data = review_service.process_game_review(game["pgn"])
        
        analysis_doc = {
            "game_id": req.game_id,
            "user_id": user_id,
            "engine_version": config.ENGINE_VERSION,
            "analysis_version": config.ANALYSIS_VERSION,
            "analysis_json": review_data
        }
        await database.save_or_update_analysis(req.game_id, analysis_doc)
        
        # Synchronously increment usage metric for NEW analysis
        await database.increment_usage_metric(user_id, "analysis_count")

        return review_data
    except Exception as e:
        print(f"[ERROR] Game review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ReviewSummaryRequest(BaseModel):
    game_id: str
    payload: Optional[dict] = None

@app.post("/api/review-summary")
async def generate_game_review_summary_only(req: ReviewSummaryRequest, user_id: str = Depends(auth.get_current_user_id)):
    """
    Generate only the LLM summary from a game_id. 
    If a payload is provided (e.g. from the mobile app running Stockfish locally), uses that payload.
    Otherwise, will fallback to backend analysis if missing.
    """
    
    # Check limit
    allowed = await database.check_usage_limit(user_id, "review")
    if not allowed:
        raise HTTPException(status_code=403, detail={"error": "LIMIT_REACHED", "feature": "review"})
        
    try:
        game = await database.get_game_by_id(req.game_id)
        if not game or game.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Game not found or unauthorized")

        # Cache lookup for review
        review = await database.get_review(req.game_id)
        if review:
            if review.get("review_version") == config.REVIEW_VERSION and review.get("llm_model") == config.MODEL_NAME:
                return {"summary": review["review_text"]}

        if req.payload:
            # MOBILE FLOW: Mobile App ran Stockfish locally and provided the stats/mistakes
            llm_payload = req.payload
        else:
            # FALLBACK/WEB FLOW: Need valid Analysis from Backend
            analysis = await database.get_analysis(req.game_id)
            is_analysis_valid = analysis and analysis.get("engine_version") == config.ENGINE_VERSION and analysis.get("analysis_version") == config.ANALYSIS_VERSION
            
            if not is_analysis_valid:
                # Generate Analysis Backend-side
                review_data = review_service.process_game_review(game["pgn"])
                analysis_doc = {
                    "game_id": req.game_id,
                    "user_id": user_id,
                    "engine_version": config.ENGINE_VERSION,
                    "analysis_version": config.ANALYSIS_VERSION,
                    "analysis_json": review_data
                }
                await database.save_or_update_analysis(req.game_id, analysis_doc)
                await database.increment_usage_metric(user_id, "analysis_count")
                analysis_json = review_data
            else:
                analysis_json = analysis["analysis_json"]

            llm_payload = analysis_json.get("llm_payload", {})
        
        # Generate Review
        summary_text = review_service.generate_review_summary(llm_payload)
        
        review_doc = {
            "game_id": req.game_id,
            "user_id": user_id,
            "review_version": config.REVIEW_VERSION,
            "llm_model": config.MODEL_NAME,
            "review_text": summary_text
        }
        await database.save_or_update_review(req.game_id, review_doc)
        
        # Synchronously increment usage metric for NEW review
        await database.increment_usage_metric(user_id, "review_count")

        return {"summary": summary_text}
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Game review summary failed: {error_msg}")
        
        # Handle Groq refusal / tool use failure 
        if "tool_use_failed" in error_msg or "invalid_request_error" in error_msg:
            raise HTTPException(
                status_code=400, 
                detail={"error": "INVALID_REVIEW", "message": "The AI could not generate a review for this game. Please ensure the game data is valid."}
            )
            
        raise HTTPException(status_code=500, detail=error_msg)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting ChessLensAI API on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
