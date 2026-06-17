# Chess Scoresheet OCR & Digitizer

A powerful tool that converts handwritten chess scoresheets into digital PGN files using AI-powered OCR. This project creates a bridge between physical chess games and digital analysis tools.

## Key Features

- **Google Authentication**: Secure login to save and track your personal game history.
- **AI Game Review (LLM Coach)**: Generates a personalized, plain-English 3-sentence summary of your game, explaining your biggest blunders using a Groq LLM.
- **Dual-Architecture Stockfish Evaluation**: 
  - **Mobile App**: Bypasses expensive server compute by running Stockfish locally on the device and sending a tiny payload to the backend.
  - **Web App**: Runs Stockfish 17 on the backend server for robust, real-time position analysis.
- **MongoDB Storage & Usage Tracking**: Automatically save games, cache engine analysis, cache LLM reviews, and track daily free-tier usage limits.
- **Visual Evaluation Bar**: An animated bar next to the board instantly shows who is winning based on engine centipawns.
- **PGN Upload & Export**: Seamlessly load existing `.pgn` files or download your digitized OCR games.
- **Validation**: Strict validation of OCR moves using `python-chess`. Illegible or illegal moves are red-flagged so you can correct them manually.

## Project Structure

- `app.py`: FastAPI backend entry point handling routing and API endpoints (`/api/games`, `/api/review`, `/api/auth/google`).
- `services.py`: Core logic for OCR extraction, Stockfish evaluation, and LLM Coach summaries.
- `database.py` & `auth.py`: MongoDB connection management, metrics tracking, and JWT Google OAuth2 verification.
- `schema.py`: Pydantic models for structured data validation.
- `static/`: Frontend assets (`index.html`, `app.js`, `style.css`) for the interactive web app.
- `build.sh`: Shell script used by Render to automatically install the Linux Stockfish binary during deployment.

## Setup & Installation

### Prerequisites

- Python 3.10+
- A [Groq API Key](https://console.groq.com/keys) (For OCR and Game Reviews).
- A MongoDB Instance (local or Atlas cluster).
- Google OAuth2 Client ID (for authentication).
- `stockfish` installed locally (e.g., `brew install stockfish` or via `build.sh` on Linux).

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/abhi542/ChessLensAI.git
cd ChessLensAI

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory and add your keys:

```ini
GROQ_API_KEY=gsk_your_key_here
GROQ_API_KEY_FOR_GAME_REVIEW=gsk_your_other_key_here
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
MONGO_URI=mongodb+srv://...  # your Atlas URI
JWT_SECRET_KEY=your_secure_random_string
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
```

## Running Locally

1.  **Start the Server**:
    ```bash
    uvicorn app:app --reload
    ```
    *The server will start at `http://127.0.0.1:8000`.*

2.  **Open the Web Interface**:
    Navigate to **[http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)** in your browser.

## Production Deployment (Render)

This project is configured for seamless deployment on [Render](https://render.com).
1. Connect your GitHub repository to a new Render "Web Service".
2. Set the Build Command: `./build.sh && pip install -r requirements.txt`
3. Set the Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables (from `.env`) to the Render dashboard.

## Tech Stack

- **Backend**: Python, FastAPI, python-chess, Motor (MongoDB Async), PyJWT, httpx
- **Frontend**: HTML5, Vanilla CSS, jQuery, Chessboard.js
- **Models**: Llama 3.2 Vision (OCR) & Llama 3 70B (Coach) via Groq
- **Database**: MongoDB Atlas
