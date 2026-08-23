import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable
import config
import database

import re

SYSTEM_PROMPT = """You are an expert, friendly chess coach analyzing a player's recent games to identify recurring playing patterns.

You will receive a JSON array containing summarized data from the player's recent games. Each game includes the color played, accuracy, blunders, critical mistakes, and best moves (with evaluations).

Your task is to analyze the mistakes and output a JSON object with two fields:
1. "coach_chat": A conversational, friendly message (2-4 paragraphs). Use natural paragraphs for the intro and outro, but use a few bullet points in the middle so the specific stats are easy to read quickly. Be highly specific using actual moves (e.g. "When you played Nc3..."). ALWAYS include at least one bullet point highlighting what they did WELL.
2. "mistakes_by_category": A JSON object mapping the provided thematic categories to integer counts representing how many of the player's mistakes fit that category. 
   Categories: "Tactical oversight", "King safety", "Piece activity", "Pawn structure", "Plan / strategic", "Endgame technique", "Opening / theory".

Output ONLY valid JSON. Do not include markdown formatting like ```json.
"""

def _extract_piece_and_square(san: str, player_color: str):
    clean_san = san.replace('+', '').replace('#', '')
    if clean_san in ['O-O', 'O-O-O']:
        return 'king', 'g1' if player_color == 'white' else 'g8'
        
    piece_map = {'N': 'knight', 'B': 'bishop', 'R': 'rook', 'Q': 'queen', 'K': 'king'}
    piece = piece_map.get(clean_san[0], 'pawn')
        
    match = re.search(r'([a-h][1-8])', clean_san)
    square = match.group(1) if match else None
    
    return piece, square

@traceable
async def generate_pattern_insights(user_id: str, games: list[dict]) -> dict:
    # 1. Fetch analysis for each game
    analysis_data = []
    
    # Aggregation stores
    total_games_with_stats = 0
    sum_acc_opening = 0
    sum_acc_middlegame = 0
    sum_acc_endgame = 0
    
    problematic_pieces_counts = {
        "pawn": {"count": 0, "example": None},
        "rook": {"count": 0, "example": None},
        "queen": {"count": 0, "example": None},
        "knight": {"count": 0, "example": None},
        "king": {"count": 0, "example": None},
        "bishop": {"count": 0, "example": None}
    }
    total_mistakes = 0
    error_heatmap = {}
    
    for game in games:
        game_id = game["_id"]
        its_me = game.get("its_me") # "white" or "black"
        
        if not its_me or its_me not in ["white", "black"]:
            continue
            
        analysis = await database.get_analysis(game_id)
        if not analysis or "analysis_json" not in analysis:
            # Auto-trigger game review
            try:
                import review_service
                review_data = review_service.process_game_review(game["pgn"])
                
                analysis_doc = {
                    "game_id": game_id,
                    "user_id": user_id,
                    "engine_version": config.ENGINE_VERSION,
                    "analysis_version": config.ANALYSIS_VERSION,
                    "analysis_json": review_data
                }
                await database.save_or_update_analysis(game_id, analysis_doc)
                await database.increment_usage_metric(user_id, "analysis_count")
                
                analysis_json = review_data
            except Exception as e:
                print(f"[ERROR] Failed to auto-generate review for game {game_id}: {e}")
                continue
        else:
            analysis_json = analysis["analysis_json"]
        
        result = game.get("result", "*")
        opening = analysis_json.get("opening", {}).get("name", "Unknown")
        stats = analysis_json.get("players", {}).get(its_me, {})
        
        # Extract user's specific mistakes and best moves from the moves array
        moves = analysis_json.get("moves", [])
        
        my_mistakes = []
        my_best_moves = []
        
        for ply_index, m in enumerate(moves):
            if m.get("player") == its_me:
                move_obj = {
                    "move_number": (ply_index // 2) + 1,
                    "move": m.get("san"),
                    "classification": m.get("classification"),
                    "eval_after": m.get("eval")
                }
                
                if m.get("classification") in ["blunder", "mistake", "miss"]:
                    my_mistakes.append(move_obj)
                    
                    # Dashboard Aggregations
                    piece, square = _extract_piece_and_square(m.get("san", ""), its_me)
                    if piece in problematic_pieces_counts:
                        problematic_pieces_counts[piece]["count"] += 1
                        if not problematic_pieces_counts[piece]["example"]:
                            problematic_pieces_counts[piece]["example"] = {
                                "game_id": str(game_id),
                                "move_number": move_obj["move_number"],
                                "ply": ply_index,
                                "san": move_obj["move"]
                            }
                    if square:
                        if square not in error_heatmap:
                            error_heatmap[square] = {"count": 0, "example": None}
                        error_heatmap[square]["count"] += 1
                        if not error_heatmap[square]["example"]:
                            error_heatmap[square]["example"] = {
                                "game_id": str(game_id),
                                "move_number": move_obj["move_number"],
                                "ply": ply_index,
                                "san": move_obj["move"]
                            }
                    total_mistakes += 1
                    
                elif m.get("classification") in ["brilliant", "great", "best"]:
                    my_best_moves.append(move_obj)
                    
        extracted = {
            "played_as": its_me,
            "result": result,
            "opening": opening,
            "accuracy": stats.get("accuracy"),
            "blunders_count": stats.get("blunders", 0),
            "mistakes_count": stats.get("mistakes", 0),
            "critical_mistakes": my_mistakes[:3], # Top 3 mistakes
            "best_moves": my_best_moves[:3]       # Top 3 best moves
        }
        
        # Only add if there's actually some data (at least we have stats)
        if stats:
            analysis_data.append(extracted)
            total_games_with_stats += 1
            
            # Phase accuracy aggregation
            phase_acc = stats.get("accuracy_by_phase", {})
            sum_acc_opening += phase_acc.get("opening", 0)
            sum_acc_middlegame += phase_acc.get("middlegame", 0)
            sum_acc_endgame += phase_acc.get("endgame", 0)
            
    if not analysis_data:
        return {"error": "Not enough analyzed games with the 'Played As' tag to generate insights."}
        
    # 3. Construct prompt
    payload = json.dumps(analysis_data, indent=2)
    
    key = config.get_gemini_key()
    primary = ChatGoogleGenerativeAI(
        model=config.PRIMARY_MODEL, 
        temperature=0.3, 
        google_api_key=key
    )
    fallback = ChatGoogleGenerativeAI(
        model=config.FALLBACK_MODEL, 
        temperature=0.3, 
        google_api_key=key
    )
    llm = primary.with_fallbacks([fallback]).with_config({"run_name": "pattern_insights"})
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Here is the data for my recent games:\n\n{payload}")
    ]
    
    response = await llm.ainvoke(messages)
    content = response.content
    
    if isinstance(content, list):
        content = " ".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in content])
        
    content = content.strip()
    
    # Strip markdown code blocks if LLM still includes them
    if content.startswith("```json"):
        content = content.replace("```json", "", 1)
        if content.endswith("```"):
            content = content[:-3]
    elif content.startswith("```"):
        content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content[:-3]
            
    try:
        llm_json = json.loads(content)
    except Exception as e:
        print(f"[ERROR] Failed to parse insights JSON from LLM: {e}")
        llm_json = {
            "coach_chat": "I couldn't properly format your analysis, but your games have been processed.",
            "mistakes_by_category": {}
        }
        
    # Calculate problem pieces percentages
    problematic_pieces = {}
    for piece, data in problematic_pieces_counts.items():
        count = data["count"]
        pct = round((count / total_mistakes * 100)) if total_mistakes > 0 else 0
        problematic_pieces[piece] = {"percentage": pct, "count": count, "example": data["example"]}
        
    # Sort problematic pieces by count descending
    problematic_pieces = dict(sorted(problematic_pieces.items(), key=lambda item: item[1]['count'], reverse=True))

    deep_analysis = {
        "accuracy_by_phase": {
            "opening": round(sum_acc_opening / total_games_with_stats, 1) if total_games_with_stats else 0,
            "middlegame": round(sum_acc_middlegame / total_games_with_stats, 1) if total_games_with_stats else 0,
            "endgame": round(sum_acc_endgame / total_games_with_stats, 1) if total_games_with_stats else 0
        },
        "problematic_pieces": problematic_pieces,
        "mistakes_by_category": llm_json.get("mistakes_by_category", {}),
        "error_heatmap": error_heatmap
    }

    final_payload = {
        "coach_chat": llm_json.get("coach_chat", ""),
        "deep_analysis": deep_analysis
    }

    return final_payload
