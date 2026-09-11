# ChessLensAI Enterprise Model Architecture & Design

## 1. Overview & Vision
The Enterprise Model transforms ChessLensAI from a single-player tool into a comprehensive B2B/B2C platform for Chess Academies and Independent Coaches. 
- **Coach View (Web)**: A powerful dashboard to monitor student progress, identify weaknesses, and assign targeted puzzles.
- **Player View (Mobile)**: An interactive app where students can scan scoresheets, see their own stats, and solve puzzles assigned by their coach.

The core value proposition is data-driven coaching. By aggregating game analysis, the platform provides deep insights that are impossible to track manually.

## 2. Authentication & Identity Linking
Users currently sign in with Google Auth. To handle roles (Coach, Student, Admin) without forcing new logins:
- Google Auth provides a unique `email` and Google ID.
- We use the internal MongoDB `_id` as the global `user_id`.
- **Linking**: When an Academy invites a student or coach, they invite them via email. Once the user logs in with Google (using that email), the system automatically links their Google-authenticated `user_id` to the Academy membership.

## 3. Database Schema Design (MongoDB)

### 3.1. `users` (Existing, Expanded)
```json
{
  "_id": "ObjectId",
  "email": "user@gmail.com",
  "name": "John Doe",
  "plan": "free/premium",
  "roles": ["player", "coach"], // NEW: Array of roles
  "created_at": "ISODate"
}
```

### 3.2. `academies` (NEW)
```json
{
  "_id": "ObjectId",
  "name": "Grandmaster Chess Academy",
  "owner_id": "ObjectId (User)",
  "created_at": "ISODate"
}
```

### 3.3. `academy_memberships` (NEW)
Links users, coaches, and academies together.
```json
{
  "_id": "ObjectId",
  "academy_id": "ObjectId",
  "user_id": "ObjectId (Student or Coach)",
  "role": "student | coach | admin",
  "assigned_coach_id": "ObjectId (Coach User ID) // For students",
  "joined_at": "ISODate"
}
```

### 3.4. `dashboard_snapshots` (NEW - Optional caching layer)
Used to store the heavy aggregation for the Coach Dashboard so it loads instantly.
```json
{
  "_id": "ObjectId",
  "student_id": "ObjectId",
  "timeframe": "last_30_days",
  "snapshot_data": { /* See Payload Structure below */ },
  "generated_at": "ISODate"
}
```

## 4. Backend API Endpoints

### Academy Management
- `POST /api/enterprise/academy` - Create a new academy.
- `POST /api/enterprise/academy/{academy_id}/invite` - Invite a user (by email) as a student or coach.
- `GET /api/enterprise/academy/{academy_id}/members` - List all members.

### Coach Endpoints
- `GET /api/coach/students` - List all students assigned to the current coach (uses `academy_memberships`).
- `GET /api/coach/students/{student_id}/dashboard?timeframe=6months` - Generates or retrieves the dashboard payload.

## 5. Dashboard Data & Payload Structure
The `GET /api/coach/students/{student_id}/dashboard` endpoint will aggregate data from the `analysis` and `reviews` collections.

```json
{
  "student_name": "Magnus C.",
  "games_analyzed": 42,
  "timeframe": "last_6_months",
  
  "accuracy": {
    "overall": 82.5,
    "opening": 90.1,
    "middlegame": 76.4,
    "endgame": 85.0
  },
  
  "problematic_pieces": [
    { "piece": "Queen", "blunder_rate": "15%", "errors": 12 },
    { "piece": "Knight", "blunder_rate": "8%", "errors": 6 }
  ],
  
  "mistakes_by_category": {
    "Tactical oversight": 18,
    "King safety": 5,
    "Endgame technique": 9
  },
  
  "playing_style": {
    "classification": "Aggressive / Tactical",
    "description": "Prefers sharp lines, often sacrifices pawns for initiative, but struggles in quiet positional maneuvering."
  },
  
  "recommended_puzzles": [
    { "theme": "Pin", "count": 10, "action_link": "/puzzles/pin?level=1500" },
    { "theme": "Back Rank", "count": 10, "action_link": "/puzzles/back-rank?level=1500" }
  ]
}
```

## 6. Implementation Strategies

### 6.1. Playing Style Determination (Math + LLM)
- **Math/Stats**: We can calculate the average centipawn loss in different positions (open vs closed), castling frequency, and material imbalance.
- **LLM Call**: Feed the last 20 game review summaries to the LLM with a strict prompt: 
  *"Based on these game summaries, classify the player's style (Aggressive, Positional, Universal, Defensive) and give a 2-sentence summary of their strengths and weaknesses."*

### 6.2. Common Mistakes & Puzzles
- When the LLM generates a game review, we can instruct it to output structured `tags` (e.g., `["Fork", "Pin", "Missed Mate"]`).
- We aggregate these tags over the last $N$ games to find the most frequent mistakes.
- If "Pin" is the top mistake, the UI can link out to Lichess/Chess.com puzzle APIs or an internal puzzle database filtered by the "Pin" theme.

### 6.3. Report Card / Progress Tracking
- Compare the metrics (Accuracy, Blunders per game) of the *first* 3 months vs the *last* 3 months in the timeframe.
- Visualize this with a line chart on the web UI.

## 7. Next Steps for this Repository
To build the foundation for this enterprise model in the current API, we should:
1. Update `schema.py` and `database.py` with the new Academy and Membership collections.
2. Build the aggregate endpoint `GET /api/coach/students/{student_id}/dashboard`.
3. Modify the game analysis prompt to output structured tactical motifs (e.g., "Pin", "Fork") to enable the mistakes classification.
