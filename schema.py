
from typing import List, Optional
from pydantic import BaseModel, Field

# --- Core Domain Models ---

class ChessMove(BaseModel):
    move_number: int = Field(..., description="The move number (e.g., 1, 2, ...)")
    white: str | None = Field(None, description="White's move in SAN (Standard Algebraic Notation), or null if empty.")
    black: str | None = Field(None, description="Black's move in SAN, or null if empty.")

class Scoresheet(BaseModel):
    moves: list[ChessMove] = Field(..., description="List of all chess moves found on the scoresheet.")

# --- API Request/Response Models ---

class MoveRequest(BaseModel):
    move_number: int
    white: Optional[str] = None
    black: Optional[str] = None

class ValidationRequest(BaseModel):
    moves: List[MoveRequest]
    white_player: str = "?"
    black_player: str = "?"
    event: str = "Chess OCR"
    site: str = "?"
    date: Optional[str] = None
    round: str = "?"
    result: str = "*"

# Response models are typically implicit dicts in FastAPI but defining them is good practice
class ValidationResponse(BaseModel):
    annotated_moves: List[dict] # Using dict for flexibility with existing structure
    valid: bool
    pgn: Optional[str] = None

from datetime import datetime

class User(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SavedGame(BaseModel):
    user_email: str
    white_player: str
    black_player: str
    event: str
    site: str
    date: str
    round: str
    result: str
    pgn: str
    annotated_moves: list[dict]
    created_at: datetime = Field(default_factory=datetime.utcnow)
