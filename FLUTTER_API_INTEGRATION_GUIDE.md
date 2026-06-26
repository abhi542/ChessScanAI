# ChessLensAI - Flutter Developer API Integration Guide

This document is the **single source of truth** for integrating the Flutter mobile app with the new ChessLensAI Backend API, MongoDB structure, and Dual-Architecture (Local Stockfish) workflow.

---

## 1. Flutter Developer Task List (Repo 1)

**Task 1 — Google Sign In**
*   Add `google_sign_in` package.
*   Create `AuthService`.
*   **Responsibilities:**
    *   Trigger Google Login on device.
    *   Get Google ID Token.
    *   Send ID Token to backend (`/api/auth/google`).
    *   Receive backend JWT (`access_token`, `refresh_token`).
    *   Store JWT securely.
    *   Logout.

**Task 2 — Secure Storage**
*   Add `flutter_secure_storage`.
*   Store `access_token` and `refresh_token`.
*   *Critical:* Never store JWTs in plain text or in Hive.

**Task 3 — Auth Provider**
*   Create `authProvider` state management.
*   **States:** `Unauthenticated`, `Loading`, `Authenticated`.

**Task 4 — Dio Interceptor**
*   Automatically attach `Authorization: Bearer <JWT>` to all outgoing requests.
*   No manual token handling in UI screens.

**Task 5 — Update GameModel**
*   Modify existing `GameModel`.
*   **Add fields:** `serverGameId`, `syncStatus`, `lastSyncAt`.
*   **Possible states:** `pending`, `synced`, `failed`.

**Task 6 — Hive Migration**
*   Keep logic that saves the last 5 scans.
*   Add the new tracking fields (`serverGameId`, `syncStatus`, `lastSyncAt`) to the Hive adapter schema.

**Task 7 — Background Sync**
*   Create `SyncService`.
*   **Responsibilities:** Find pending games in Hive, upload to MongoDB, retry failed uploads, mark as synced.
*   **Flow:** Scan → Hive → Pending → Background Sync → MongoDB → Synced.

**Task 8 — Retry On Network Recovery**
*   When internet returns, automatically call `retryPendingGames()`.

**Task 9 — Pagination Support**
*   Prepare the ListView UI to handle: `GET /api/games?page=1&limit=20`
*   Build this even if the user's data is currently small.

**Task 10 — Local Cache**
*   Cache Recent Games, Openings, Analysis Results, and Review Results locally so the app works flawlessly offline.
*   Do NOT cache forever (implement standard expiration logic).

---

## 2. API Contract & Endpoints

> [!IMPORTANT]
> All endpoints (except `/api/auth/google`) require the HTTP Header:
> `Authorization: Bearer <access_token>`

### Auth
*   **`POST /api/auth/google`**: Send `{ "token": "<GOOGLE_ID_TOKEN>" }`. Returns your JWTs and user info.
*   **`POST /api/auth/refresh`**: Send `{ "refresh_token": "<TOKEN>" }`. Returns a new `access_token`.

### Core Flow
*   **`POST /api/upload`**: Upload multipart image file. Returns raw extracted moves. (Requires Auth for tracking usage metrics).
*   **`POST /api/validate`**: Send raw moves + metadata. Returns fully validated moves and PGN string.
*   **`POST /api/games`**: Send validated game JSON. **Backend automatically attaches `user_id` from JWT**. Returns `{ "status": "success", "game_id": "..." }`.
*   **`GET /api/games?page=1&limit=20`**: Returns paginated games list `{"items": [...], "total": 0, "page": 1, "has_next": false}`.
*   **`DELETE /api/games/{game_id}`**: Deletes game from DB (Validates JWT ownership).

### Dual-Architecture Review Pipeline
**Mobile First (Cost-Saving Flow):**
Because you will use the `flutter_stockfish` package locally on the phone, the backend DOES NOT need to waste money running Stockfish on cloud servers.
1. Mobile app analyzes the game locally using Stockfish.
2. Mobile app packages the result.
3. Mobile app sends the packaged result directly to: **`POST /api/review-summary`**

```json
// POST /api/review-summary
{
  "game_id": "6a22cb77c514a24987e78b62",
  "payload": {
    "opening": "Italian Game",
    "result": "White",
    "players": {
        "white": {"blunders": 1, "accuracy": 92.5},
        "black": {"blunders": 3, "accuracy": 65.2}
    },
    "critical_mistake": "Black blundered their queen on move 15.",
    "notable_good_move": "White found a brilliant discovered attack."
  }
}
```
*The backend skips Stockfish, instantly hits Groq LLM, caches the summary, increments the `review_count` usage metric, and returns the AI paragraph.*

**Backend Fallback (For Web / Weak Phones):**
1. Call `POST /api/review` with just `{ "game_id": "..." }`. The server runs Stockfish heavily, caches the analysis, and returns the stats.
2. Call `POST /api/review-summary` with `{ "game_id": "..." }` (omitting the payload). The server fetches the cached stats, generates the LLM summary, and returns it.

---

## 3. Testing Guide (Postman)

To simulate the mobile app's workflow and test your endpoints before writing Flutter code:

1. **Get an Access Token:** Log into the Web UI (`http://localhost:8000`). Open Chrome DevTools (F12) -> Application -> Local Storage. Copy `chess_token`.
2. **Get a Game ID:** Look in your MongoDB `games` collection, or save a game on the Web UI.
3. **Open Postman:**
   *   Method: `POST`
   *   URL: `http://localhost:8000/api/review-summary`
   *   Headers:
       *   `Authorization: Bearer <YOUR_TOKEN>`
       *   `Content-Type: application/json`
   *   Body (Raw JSON): Paste the JSON payload from the *Dual-Architecture* section above.
4. **Send:** You will instantly receive an LLM summary paragraph back in milliseconds because the backend completely bypassed Stockfish!

---

## 4. MongoDB Database Schemas
Here is exactly how the data looks in the MongoDB Atlas Cluster.

### `users`
```json
{
  "_id": { "$oid": "6a22c958fa1d102437df28d6" },
  "email": "abhinavmbhatt@gmail.com",
  "name": "Abhinav Bhatt",
  "picture": "https://lh3.googleusercontent.com/a/ACg8ocKW...",
  "plan": "free"
}
```

### `usage_metrics` (Updates synchronously on new operations)
```json
{
  "_id": { "$oid": "6a22ca7c9f29399f056d4617" },
  "date": "2026-06-05",
  "user_id": "6a22c958fa1d102437df28d6",
  "ocr_count": 1,
  "analysis_count": 4,
  "review_count": 4
}
```

### `games`
```json
{
  "white_player": "game 2 w",
  "black_player": "game 2 b",
  "event": "Game 2",
  "site": "offline",
  "date": "2026.06.05",
  "round": "1",
  "result": "1-0",
  "pgn": "[Event \"Game 2\"]\n...",
  "annotated_moves": [
    {
      "move_number": 1,
      "white": { "san": "e4", "valid": true, "error": null, "fen": "..." },
      "black": { "san": "c5", "valid": true, "error": null, "fen": "..." }
    }
  ],
  "user_id": "6a22c958fa1d102437df28d6"
}
```

### `analysis` (Stockfish Cache)
```json
{
  "_id": { "$oid": "6a22cbed9f29399f056d464b" },
  "game_id": "6a22cb77c514a24987e78b62",
  "user_id": "6a22c958fa1d102437df28d6",
  "engine_version": "Stockfish17",
  "analysis_version": "1.0",
  "analysis_json": {
    "opening": { "name": "Italian Game", "eco": "C57" },
    "result": "0-1",
    "players": {
      "white": { "blunder": 1, "accuracy": 75 },
      "black": { "blunder": 0, "accuracy": 82.2 }
    },
    "moves": [],
    "eval_graph": [],
    "critical_positions": [],
    "llm_payload": {}
  }
}
```

### `reviews` (Groq LLM Cache)
```json
{
  "game_id": "6a22cb77c514a24987e78b62",
  "user_id": "6a22c958fa1d102437df28d6",
  "llm_model": "meta-llama/llama-4-scout-17b-16e-instruct",
  "review_version": "1.0",
  "review_text": "The game started with a sharp Italian Game..."
}
```

---

## 5. Rate Limiting & Paywalls (Crucial)

The backend now enforces strict daily limits based on user subscription tiers (`free` vs `premium`). 

**Limits:**
- **Free Tier:** 5 OCR Scans & 5 Game Reviews per day.
- **Premium Tier:** 10 OCR Scans & 10 Game Reviews per day.

### How to handle the limits in Flutter:
Both `POST /api/upload` and `POST /api/review-summary` will intercept the request *before* any compute is run if the user is out of credits.

When a limit is reached, the API will return a **`403 Forbidden`** status code with the following JSON body:
```json
{
  "detail": {
    "error": "LIMIT_REACHED",
    "feature": "ocr" // Will be "ocr" or "review"
  }
}
```

**Your Obligation:**
In your API client (e.g., `Dio` or `http`), catch the `403` status code. Parse the JSON body. If `detail.error == "LIMIT_REACHED"`, immediately stop the loading spinner and trigger the native **"Upgrade to Pro"** bottom sheet / modal. Do not show a generic network error.
