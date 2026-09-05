
from typing import List, Optional, Literal
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
    event: Optional[str] = "?"
    site: Optional[str] = "?"
    tournament_id: Optional[str] = None
    game_format: Literal["Standard", "Rapid", "Blitz", "?"] = "?"
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
    plan: str = "free"
    terms_accepted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GameCreateRequest(BaseModel):
    white_player: str
    black_player: str
    event: Optional[str] = "?"
    site: Optional[str] = "?"
    tournament_id: Optional[str] = None
    game_format: Literal["Standard", "Rapid", "Blitz", "?"] = "?"
    date: str
    round: str
    result: str = "*"
    pgn: str
    annotated_moves: list[dict]
    its_me: Optional[str] = None

class SavedGame(BaseModel):
    user_id: str
    white_player: str
    black_player: str
    event: Optional[str] = "?"
    site: Optional[str] = "?"
    tournament_id: Optional[str] = None
    game_format: Literal["Standard", "Rapid", "Blitz", "?"] = "?"
    date: str
    round: str
    result: str = "*"
    pgn: str
    annotated_moves: list[dict]
    its_me: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisModel(BaseModel):
    game_id: str
    user_id: str
    engine_version: str
    analysis_version: str
    analysis_json: dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewModel(BaseModel):
    game_id: str
    user_id: str
    review_version: str
    llm_model: str
    review_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UsageMetricsModel(BaseModel):
    user_id: str
    date: str
    ocr_count: int = 0
    analysis_count: int = 0
    review_count: int = 0
    insights_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TournamentCreateRequest(BaseModel):
    name: str

class TournamentResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

class InsightModel(BaseModel):
    user_id: str
    game_ids: list[str]
    insight_json: dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
