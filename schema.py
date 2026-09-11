
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
    result: Literal["1-0", "0-1", "1/2-1/2", "*"] = "*"

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
    plan: str = "free" # "free", "premium", "admin_dev"
    role: Optional[str] = "user" # "user", "admin", "dev"
    roles: List[str] = ["player"]
    academy_id: Optional[str] = None
    coach_id: Optional[str] = None
    custom_limits: Optional[dict] = None # e.g. {"ocr": 100, "review": 50}
    terms_accepted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserLimitsUpdateRequest(BaseModel):
    plan: Optional[str] = None
    role: Optional[str] = None
    custom_limits: Optional[dict] = None


class GameCreateRequest(BaseModel):
    white_player: str
    black_player: str
    event: Optional[str] = "?"
    site: Optional[str] = "?"
    tournament_id: Optional[str] = None
    game_format: Literal["Standard", "Rapid", "Blitz", "?"] = "?"
    date: str
    round: str
    result: Literal["1-0", "0-1", "1/2-1/2", "*"] = "*"
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
    result: Literal["1-0", "0-1", "1/2-1/2", "*"] = "*"
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

# --- Enterprise Models ---

class AcademyCreateRequest(BaseModel):
    name: str

class AcademyResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime

class AssignCoachRequest(BaseModel):
    coach_id: str

class DashboardSnapshotResponse(BaseModel):
    student_name: str
    games_analyzed: int
    timeframe: str
    accuracy: dict
    problematic_pieces: list
    mistakes_by_category: dict
    playing_style: dict
    top_blundered_squares: list

class AssignPuzzleRequest(BaseModel):
    motif: str
    count: int
