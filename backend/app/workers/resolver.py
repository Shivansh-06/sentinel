from dataclasses import dataclass

from rapidfuzz import fuzz, process as rfprocess


@dataclass
class MatchResult:
    matched: bool
    score: float
    matched_value: str | None
    algorithm: str


def score_pair(query: str, candidate: str) -> float:
    """
    Combines multiple fuzzy algorithms and returns a weighted score.

    - token_sort_ratio: order-insensitive token comparison (best for names)
    - token_set_ratio: handles subset matches ('Putin' vs 'Vladimir Putin')
    - partial_ratio: handles one string being contained in another

    We weight token_sort highest because after normalization we've already
    sorted tokens — it's the most reliable signal.
    """
    if not query or not candidate:
        return 0.0

    token_sort = fuzz.token_sort_ratio(query, candidate)
    token_set = fuzz.token_set_ratio(query, candidate)
    partial = fuzz.partial_ratio(query, candidate)

    weighted = (token_sort * 0.5) + (token_set * 0.3) + (partial * 0.2)
    return round(weighted, 2)


def find_best_match(
    query: str,
    candidates: list[str],
    threshold: float = 85.0,
) -> MatchResult:
    """
    Find the best fuzzy match for a query string among a list of candidates.

    Uses rapidfuzz's process.extractOne for efficient search across large
    candidate lists, then scores the winner with our weighted algorithm.

    threshold: minimum score to consider a match 'confirmed'.
    85 is deliberately conservative — in compliance contexts, a false
    negative (missing a match) is less dangerous than a false positive
    (wrongly flagging an innocent person), but we still want high recall.
    You'd tune this based on your risk tolerance.
    """
    if not candidates:
        return MatchResult(matched=False, score=0.0, matched_value=None, algorithm="none")

    best_match, quick_score, _ = rfprocess.extractOne(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
    )

    final_score = score_pair(query, best_match)

    return MatchResult(
        matched=final_score >= threshold,
        score=final_score,
        matched_value=best_match if final_score >= threshold else None,
        algorithm="weighted_fuzzy",
    )


def batch_score(
    query: str,
    candidates: list[str],
    limit: int = 5,
) -> list[tuple[str, float]]:
    """
    Returns top-N matches with scores. Used for audit trails —
    you want to show *why* something was flagged, not just that it was.
    In Zigram's Case Manager this is what populates the match details panel.
    """
    results = rfprocess.extract(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )

    return [
        (candidate, score_pair(query, candidate))
        for candidate, _, _ in results
    ]