# T010 original buggy code

def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    max_score = max(scores)
    if max_score == 0:
        return [0 for _ in scores]
    return [x / max_score for x in scores]  # BUG
