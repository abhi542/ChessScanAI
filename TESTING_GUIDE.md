# ChessLensAI Testing & Debugging Guide

## 1. Fixing the Google Auth Error 400
The `invalid_request` (Error 400) happens because the URL you are viewing the website on does not exactly match the allowed URLs in your Google Cloud Console.

**How to fix it:**
1. Go to the [Google Cloud Console -> APIs & Services -> Credentials](https://console.cloud.google.com/apis/credentials).
2. Click on your OAuth 2.0 Client ID (named something like "Chess Scan APP").
3. Under **Authorized JavaScript origins**, click **Add URI** and add exactly:
   - `http://localhost:8000`
   - `http://127.0.0.1:8000`
4. Under **Authorized redirect URIs** (if applicable), add:
   - `http://localhost:8000`
   - `http://127.0.0.1:8000`
5. Click **Save**. *(Note: Google sometimes takes 5-10 minutes to register the changes).*
6. Go back to your browser, ensure the URL bar says exactly `http://localhost:8000` (not 127.0.0.1), refresh the page, and try logging in again.

---

## 2. Testing the Web UI
Once Google Auth is working, test the backend integration step-by-step:

**Step 1: Save a Game**
1. Ensure you are logged in (your profile picture will appear in the top right).
2. Upload a PGN or make a few valid moves on the board.
3. Click the **"Save Game"** button on the bottom left. 
4. You should see an alert: `"Game saved successfully!"`.

**Step 2: Generate the Backend Review**
1. After saving, click the **"Game Review"** button.
2. A modal will pop up. Behind the scenes, the Web App just sent your `game_id` to the backend. The backend is now running Stockfish and generating the analysis.
3. Wait for the graph and stats to appear.

**Step 3: Generate the AI Summary**
1. Inside the Review Modal, click the **"Ask AI Coach"** button.
2. This sends your `game_id` to `/api/review-summary`.
3. The backend fetches the analysis, runs the Groq prompt, and returns the paragraph.

**Step 4: Load Saved Games**
1. Click the **"My Saved Games"** button.
2. Ensure your paginated list of games appears. Click **"Load"** to reload the state.

---

## 3. Testing the Mobile App Flow (via Postman)
This simulates what your Flutter developer will do when they bypass the backend Stockfish.

**Step 1: Get your Tokens**
1. Go to your browser where you are logged into the Web UI.
2. Open **Developer Tools** (Right Click -> Inspect).
3. Go to the **Application** tab -> **Local Storage**.
4. Copy the value of `chess_token`.

**Step 2: Get a Game ID**
1. You can find a valid `game_id` inside your MongoDB `games` collection, or by watching the Network tab when you hit "Save Game".

**Step 3: Ping Postman**
1. Open Postman.
2. Set the method to **POST**.
3. Set the URL to: `http://localhost:8000/api/review-summary`
4. Go to the **Headers** tab and add:
   - Key: `Authorization`, Value: `Bearer <YOUR_CHESS_TOKEN>`
   - Key: `Content-Type`, Value: `application/json`
5. Go to the **Body** tab, select **raw** -> **JSON**, and paste this exact test payload:

```json
{
  "game_id": "<YOUR_GAME_ID>",
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

**Step 4: Verify**
Click **Send**. You should instantly get a Groq LLM summary response back. Because you provided the `payload`, the backend knew to skip Stockfish entirely!
