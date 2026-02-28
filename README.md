# Chess Scoresheet OCR & Digitizer

A powerful tool that converts handwritten chess scoresheets into digital PGN files using AI-powered OCR. This project creates a bridge between physical chess games and digital analysis tools.

## Key Features

- **Google Authentication**: Secure login to save and track your personal game history.
- **MongoDB Storage**: Automatically save valid games to the cloud. Load them back anytime from the "My Games" dashboard.
- **Game Management**: Easily load, review, and delete your saved games. 
- **Stockfish Evaluation API**: Real-time position analysis using the Stockfish 18 engine.
- **Visual Evaluation Bar**: An animated bar next to the board instantly shows who is winning based on engine centipawns.
- **Interactive UI**: Drag and drop pieces to make moves, automatically updating the grid and PGN.
- **PGN Upload & Export**: Seamlessly load existing `.pgn` files to visualize games, or download your digitized OCR games as `.pgn`.
- **Validation**: Strict validation of OCR moves using `python-chess`. Illegible or illegal moves are red-flagged so you can correct them manually.
- **Web Interface**: Review and correct the OCR results in a friendly spreadsheet UI with a native Calendar widget for game dates.

## Project Structure

- `app.py`: FastAPI backend entry point handling routing and API endpoints (`/api/games`, `/api/evaluate`, `/api/auth`).
- `services.py`: Core logic for OCR extraction (Groq) and chess validation (`python-chess`).
- `database.py` & `auth.py`: MongoDB connection management and JWT Google OAuth2 verification.
- `schema.py`: Pydantic models for structured data validation.
- `static/`: Frontend assets (`index.html`, `app.js`, `style.css`) for the interactive web app.

## Setup & Installation

### Prerequisites

- Python 3.10+
- A [Groq API Key](https://console.groq.com/keys) (for the Vision LLM).
- A MongoDB Instance (local or Atlas cluster).
- Google OAuth2 Client ID (for authentication).
- `stockfish` installed locally (e.g., `brew install stockfish` or `apt-get install stockfish`).

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/abhi542/ChessLensAI.git
cd ChessLensAI

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory and add your keys:

```ini
GROQ_API_KEY=gsk_your_key_here
GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_oauth_secret
MONGO_URI=mongodb://localhost:27017  # or your Atlas URI
JWT_SECRET_KEY=your_secure_random_string
```

## Running the Application

1.  **Start the Server**:
    ```bash
    uvicorn app:app --reload
    ```
    *The server will start at `http://127.0.0.1:8000`.*

2.  **Open the Web Interface**:
    Navigate to **[http://127.0.0.1:8000/static/index.html](http://127.0.0.1:8000/static/index.html)** in your browser.

## Usage Guide

1.  **Upload**: Click "Upload Image" and select a clear photo of a chess scoresheet.
2.  **Review**: The moves will appear in the grid on the left. Calculated board positions appear on the right.
3.  **Edit**: 
    - If a move is red (invalid), click it to edit.
    - The board will show the position immediately *before* that move, so you can decipher what was played.
    - Correct the text (e.g., change `Nf5` to `Ng5`).
4.  **Export**: Once all moves are green (valid), the "Export PGN" button will enable. Click it to save your game.

## Observability (LangSmith)

This project is instrumented with LangSmith for full observability of LLM interactions.

1.  **Tracing**: Every extraction request is traced end-to-end.
2.  **Metrics**: View token usage (Input/Output), latency, and errors for the `ChatGroq` model.
3.  **Setup**: Configuration is automatic via `.env`:
    ```bash
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=...
    ```
    No manual wrappers (like `wrap_openai`) are needed; the `ChatGroq` integration handles tracing natively.
    Visit your [LangSmith Dashboard](https://smith.langchain.com) to see the "ChessSheetOCR" project.

## Tech Stack

- **Backend**: Python, FastAPI, python-chess, Motor (MongoDB Async), Stockfish, PyJWT
- **Frontend**: HTML5, TailwindCSS, jQuery, Chessboard.js
- **Model**: Llama 3.2 Vision (via Groq)
- **Database**: MongoDB
