import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable
import config
import database

SYSTEM_PROMPT = """You are an expert, friendly chess coach analyzing a player's recent games to identify recurring playing patterns.

You will receive a JSON array containing summarized data from the player's recent games. Each game includes the color played, accuracy, blunders, critical mistakes, and best moves (with evaluations).

Your task is to talk directly to the player in a highly conversational, simple, and punchy tone. Do NOT write a long, formal report. Imagine you are chatting with them over a chessboard after a tournament.

## Output Format
Write a short, engaging message. Use natural paragraphs for the intro and outro, but use a few bullet points in the middle so the specific stats are easy to read quickly.

Structure your message naturally to cover:
1. **Conversational Intro**: A short friendly greeting (e.g., "Pull up a chair. Let's look at your recent games...").
2. **Key Patterns (Bulleted)**: Use 2-4 short bullet points to highlight specific stats, recurring mistakes, AND their strengths. For example:
   * "In 4 out of 5 games, you blundered early in the opening (around move 5)."
   * "Your move Nc3 was often a severe blunder, likely dropping material or walking into a tactic, costing you heavily in the evaluation."
   * "On the bright side, your first 2 moves are rock solid in every game and you consistently find great moves like d4."
3. **Conversational Outro / Actionable Advice**: Give them ONE or TWO highly actionable, simple things to practice, wrapping up with an encouraging sign-off.

## Rules
- Keep it extremely conversational and direct ("You", "I").
- Keep sentences short and punchy. No long, dense paragraphs.
- Be highly specific using the actual moves from the data (e.g., "When you played Nc3...").
- You may carefully infer the type of blunder (e.g., hanging a piece, missed tactic) if the evaluation drop and the move strongly suggest it, but keep it reasonable.
- ALWAYS include at least one bullet point highlighting what they did WELL to keep it encouraging.
- Make sure the bullet points are very concise so the user doesn't have to read a wall of text.
"""

@traceable
async def generate_pattern_insights(user_id: str, games: list[dict]) -> str:
    # 1. Fetch analysis for each game
    analysis_data = []
    
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
            
    if not analysis_data:
        return "Not enough analyzed games with the 'Played As' tag to generate insights. Make sure you select White or Black when saving games, and run a Game Review on them first."
        
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
        
    return content.strip()
