
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
from schema import ValidationRequest, ValidationResponse, User, SavedGame
import database
import auth
import httpx
from typing import Optional

try:
    from stockfish import Stockfish
    # Attempt to initialize with common paths; will error on route call if missing
    STOCKFISH_PATH = "stockfish" 
    stockfish_engine = Stockfish(path=STOCKFISH_PATH, depth=15, parameters={"Threads": 1, "Hash": 16})
except Exception:
    stockfish_engine = None

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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "google_client_id": config.GOOGLE_CLIENT_ID
    })


# ── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "healthy", "model": config.MODEL_NAME}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    1. Upload Image
    2. Run OCR (via LLM Service)
    3. Return Raw Moves
    """
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
        
        return {"moves": raw_moves}

    except Exception as e:
        print(f"[ERROR] Image processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
                await database.create_user({"email": email, "name": name, "picture": picture})

            # Issue our own JWT
            access_token = auth.create_access_token(data={"sub": email})
            return {"access_token": access_token, "token_type": "bearer", "user": {"email": email, "name": name, "picture": picture}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/games")
async def save_user_game(game: SavedGame, email: str = Depends(auth.get_current_user_email)):
    """
    Save a fully validated game to the current user's profile.
    """
    if game.user_email != email:
        raise HTTPException(status_code=403, detail="Not authorized to save for this user")
    
    game_dict = game.dict()
    # MongoDB handles datetime creation if not provided, but BaseModel already sets it.
    game_id = await database.save_game(game_dict)
    if not game_id:
        raise HTTPException(status_code=500, detail="Failed to save game to database")
    
    return {"status": "success", "game_id": game_id}


@app.get("/api/games")
async def get_user_games(email: str = Depends(auth.get_current_user_email)):
    """
    List all games saved by the current user.
    """
    games = await database.list_user_games(email)
    return {"games": games}

@app.delete("/api/games/{game_id}")
async def delete_user_game(game_id: str, email: str = Depends(auth.get_current_user_email)):
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
        if game.get("user_email") != email:
            raise HTTPException(status_code=403, detail="Not authorized to delete this game")
            
        # Delete
        success = await database.delete_game(game_id)
        if success:
            return {"status": "success", "message": "Game deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete game")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid game ID format")


@app.get("/api/evaluate")
async def evaluate_position(fen: str, depth: Optional[int] = 15):
    """
    Evaluate a FEN position using Stockfish and return the score.
    Returns:
        {"type": "cp", "value": 150} for centipawns
        {"type": "mate", "value": 3} for mate in 3
    """
    if not stockfish_engine:
        raise HTTPException(
            status_code=503, 
            detail="Stockfish engine is not configured on this server. Please install stockfish locally."
        )
        
    try:
        # Update depth if requested (within reasonable bounds)
        current_depth = min(max(depth, 5), 20)
        stockfish_engine.set_depth(current_depth)
        
        # Set position
        if not stockfish_engine.is_fen_valid(fen):
            raise HTTPException(status_code=400, detail="Invalid FEN string")
            
        stockfish_engine.set_fen_position(fen)
        
        # Get evaluation
        eval_result = stockfish_engine.get_evaluation()
        return eval_result
        
    except Exception as e:
        print(f"Error in evaluate_position: {e}")
        raise HTTPException(status_code=500, detail="Error evaluating position")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting ChessLensAI API on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
