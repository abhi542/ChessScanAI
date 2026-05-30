import math

# Win Probability Constant
# This constant converts centipawns to a win probability (50% = 0.0 eval)
WP_CONSTANT = -0.00368208

def eval_to_wp(cp: int) -> float:
    """
    Convert a centipawn evaluation (from White's perspective) to a Win Probability for White (0.0 to 100.0).
    A mate score should be capped (e.g. +/- 10000).
    """
    # Cap extreme values to prevent overflow in math.exp
    cp = max(-10000, min(10000, cp))
    wp = 50 + 50 * (2 / (1 + math.exp(WP_CONSTANT * cp)) - 1)
    return wp

def classify_moves(moves_data: list):
    """
    Process raw engine data, calculate win probability drops, and classify each move.
    """
    stats = {
        "white": {"brilliant": 0, "great": 0, "best": 0, "mistake": 0, "miss": 0, "blunder": 0},
        "black": {"brilliant": 0, "great": 0, "best": 0, "mistake": 0, "miss": 0, "blunder": 0}
    }

    white_wp_losses = []
    black_wp_losses = []

    for i, data in enumerate(moves_data):
        player = data["player"]
        wp_before = eval_to_wp(data["eval_before"])
        wp_after = eval_to_wp(data["eval_after"])

        # Calculate WP Loss for the player who made the move
        if player == "white":
            wp_loss = wp_before - wp_after
        else:
            # For black, win probability is 100 - white's win probability
            wp_loss = (100 - wp_before) - (100 - wp_after)
            
        wp_loss = max(0, wp_loss) # Cannot have negative loss for classification

        classification = "good" # Default fallback
        is_mate_before = abs(data["eval_before"]) > 9000
        is_mate_after = abs(data["eval_after"]) > 9000

        # Missed forced win
        if is_mate_before and not is_mate_after:
            # If player had mate and lost it
            if (player == "white" and data["eval_before"] > 0) or (player == "black" and data["eval_before"] < 0):
                classification = "miss"
        elif wp_loss <= 2.0:
            classification = "best"
        elif wp_loss <= 5.0:
            classification = "excellent"
        elif wp_loss <= 10.0:
            classification = "good"
        elif wp_loss <= 15.0:
            classification = "inaccuracy"
        elif wp_loss <= 30.0:
            classification = "mistake"
        else:
            classification = "blunder"

        # Overrides for Great/Brilliant (MVP simple heuristic)
        # If it's a 'best' move and involves a large eval improvement from a tricky spot
        # (This can be improved later, for now we just map some Best moves to Great)
        if classification == "best" and data["played_best"]:
            # Just a placeholder for Great: if it's the absolute best move
            # In a real app we'd check if it's an 'only move'
            pass

        data["wp_loss"] = wp_loss
        data["classification"] = classification
        data["eval_graph"] = data["eval_after"] / 100.0 # Convert to pawns for graph

        # Tally stats (only for the requested categories)
        if classification in stats[player]:
            stats[player][classification] += 1

        if player == "white":
            white_wp_losses.append(wp_loss)
        else:
            black_wp_losses.append(wp_loss)

    # Calculate Accuracy
    k = 0.05 # Tuning constant
    avg_white_loss = sum(white_wp_losses) / len(white_wp_losses) if white_wp_losses else 0
    avg_black_loss = sum(black_wp_losses) / len(black_wp_losses) if black_wp_losses else 0

    white_accuracy = 100 * math.exp(-k * avg_white_loss)
    black_accuracy = 100 * math.exp(-k * avg_black_loss)

    stats["white"]["accuracy"] = round(white_accuracy, 1)
    stats["black"]["accuracy"] = round(black_accuracy, 1)

    return moves_data, stats
