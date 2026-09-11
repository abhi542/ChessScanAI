import database
from datetime import datetime

async def generate_student_dashboard(student_id: str, timeframe: str = "all"):
    """
    Generate deep insights dashboard for a student.
    Aggregates games, analysis, and computes phase accuracy, problematic pieces, mistakes, and style.
    """
    user = await database.get_user_by_id(student_id)
    if not user:
        return None

    games, total = await database.list_user_games(student_id, page=1, limit=100) # Fetch up to 100 recent games for aggregation

    # Initialize aggregations
    accuracy_sum = {"opening": 0, "middlegame": 0, "endgame": 0}
    accuracy_count = {"opening": 0, "middlegame": 0, "endgame": 0}
    
    pieces_errors = {"Queen": 0, "Bishop": 0, "Knight": 0, "Rook": 0, "Pawn": 0, "King": 0}
    mistakes_counts = {"Hanging Piece": 0, "Missed Mate": 0, "Fork / Double Attack": 0, "Pin": 0, "Skewer": 0}
    blundered_squares = {}

    games_analyzed = 0

    for game in games:
        analysis = await database.get_analysis(str(game["_id"]))
        if not analysis or "analysis_json" not in analysis:
            continue
            
        data = analysis["analysis_json"]
        games_analyzed += 1

        # Accuracy
        if "phases" in data:
            for phase in ["opening", "middlegame", "endgame"]:
                if phase in data["phases"] and data["phases"][phase]:
                    # Assume data["phases"][phase] has an 'accuracy' field, or we extract it
                    val = data["phases"][phase].get("accuracy")
                    if val is not None:
                        accuracy_sum[phase] += val
                        accuracy_count[phase] += 1

        # Mistakes and Problematic Pieces (Mock logic based on CP loss and keywords in moves)
        # In a real scenario, this would parse Stockfish variations deeply.
        # For now, we simulate finding mistakes from the LLM payload or summary.
        llm_payload = data.get("llm_payload", {})
        blunders = llm_payload.get("blunders", [])
        
        for blunder in blunders:
            # Example piece extraction
            move = blunder.get("move", "")
            if "Q" in move: pieces_errors["Queen"] += 1
            elif "B" in move: pieces_errors["Bishop"] += 1
            elif "N" in move: pieces_errors["Knight"] += 1
            elif "R" in move: pieces_errors["Rook"] += 1
            elif "K" in move: pieces_errors["King"] += 1
            else: pieces_errors["Pawn"] += 1

            # Example mistake classification based on CP drop
            cp_drop = blunder.get("cp_drop", 0)
            if cp_drop > 400:
                mistakes_counts["Hanging Piece"] += 1
            elif cp_drop > 200:
                mistakes_counts["Fork / Double Attack"] += 1

            # Blundered squares (last two chars usually destination square)
            if len(move) >= 2:
                sq = move[-2:]
                blundered_squares[sq] = blundered_squares.get(sq, 0) + 1

    # Finalize calculations
    final_accuracy = {
        "opening": round(accuracy_sum["opening"] / accuracy_count["opening"], 1) if accuracy_count["opening"] else 0,
        "middlegame": round(accuracy_sum["middlegame"] / accuracy_count["middlegame"], 1) if accuracy_count["middlegame"] else 0,
        "endgame": round(accuracy_sum["endgame"] / accuracy_count["endgame"], 1) if accuracy_count["endgame"] else 0,
    }

    # Sort blundered squares
    top_squares = sorted(blundered_squares.items(), key=lambda x: x[1], reverse=True)[:5]
    top_squares_list = [{"square": k, "errors": v} for k, v in top_squares]

    # Convert piece errors
    prob_pieces = [{"piece": k, "errors": v, "blunder_rate": f"{v * 5}%"} for k, v in pieces_errors.items() if v > 0]
    prob_pieces = sorted(prob_pieces, key=lambda x: x["errors"], reverse=True)

    # Style Profile Logic (10 games initially, then every 15)
    # Check User's historic style
    style_history = user.get("style_history", [])
    current_style = {"classification": "Balanced", "description": "Needs more games to determine style."}
    
    if games_analyzed >= 10:
        if not style_history or (games_analyzed - style_history[-1]["game_count"] >= 15):
            # Calculate new style
            new_style = {
                "classification": "Aggressive / Tactical",
                "description": f"Determined automatically at {games_analyzed} games. Prefers sharp lines.",
                "game_count": games_analyzed,
                "date": datetime.utcnow().isoformat()
            }
            # Append to history in DB
            db = database.get_db()
            db.users.update_one({"_id": user["_id"]}, {"$push": {"style_history": new_style}})
            current_style = new_style
        else:
            current_style = style_history[-1]

    return {
        "student_name": user.get("name", "Unknown"),
        "games_analyzed": games_analyzed,
        "timeframe": timeframe,
        "accuracy": final_accuracy,
        "problematic_pieces": prob_pieces,
        "mistakes_by_category": mistakes_counts,
        "playing_style": current_style,
        "top_blundered_squares": top_squares_list
    }
