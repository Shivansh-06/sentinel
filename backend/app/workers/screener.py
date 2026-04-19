import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select, text

from app.models.sanctioned_entity import SanctionedEntity
from app.workers.resolver import find_best_match, batch_score

logger = logging.getLogger(__name__)

SANCTIONS_MATCH_THRESHOLD = 80.0
SANCTIONS_REVIEW_THRESHOLD = 65.0


@dataclass
class ScreeningResult:
    is_match: bool
    requires_review: bool
    best_score: float
    matched_name: str | None
    matched_source: str | None
    matched_program: str | None
    top_candidates: list[dict]


def screen_entity(
    normalized_name: str,
    session: Session,
    entity_type: str | None = None,
) -> ScreeningResult:
    """
    Screens a single normalized name against the local sanctions database.

    Two-stage approach:
    1. Pre-filter: SQL LIKE query to get candidate names sharing at least
       one significant token. This narrows ~15,000 entries down to ~50-200
       candidates before fuzzy matching kicks in.
    2. Fuzzy match: score all candidates with our weighted algorithm.

    Why pre-filter: fuzzy matching every entity against all 15,000+
    sanctioned names would be extremely slow. The SQL pre-filter is fast
    and has high recall — it only misses entries where no token overlaps,
    which is rare after normalization.
    """
    tokens = normalized_name.split()
    if not tokens:
        return ScreeningResult(
            is_match=False, requires_review=False, best_score=0.0,
            matched_name=None, matched_source=None,
            matched_program=None, top_candidates=[],
        )

    # Build a query that finds sanctioned entries sharing at least one token
    # with our normalized name. This is the fast pre-filter step.
    conditions = " OR ".join(
        [f"normalized_name LIKE :token_{i}" for i in range(len(tokens))]
    )
    params = {f"token_{i}": f"%{token}%" for i, token in enumerate(tokens)}

    if entity_type and entity_type.lower() in ("individual", "person"):
        type_filter = " AND entity_type = 'individual'"
    elif entity_type and entity_type.lower() in ("organization", "org", "company"):
        type_filter = " AND entity_type = 'organization'"
    else:
        type_filter = ""

    raw_sql = text(
        f"SELECT normalized_name, primary_name, source, program "
        f"FROM sanctioned_entities "
        f"WHERE ({conditions}){type_filter} "
        f"LIMIT 500"
    )

    candidates_rows = session.execute(raw_sql, params).fetchall()

    if not candidates_rows:
        return ScreeningResult(
            is_match=False, requires_review=False, best_score=0.0,
            matched_name=None, matched_source=None,
            matched_program=None, top_candidates=[],
        )

    candidate_names = [row[0] for row in candidates_rows]
    candidate_map = {
        row[0]: {"primary_name": row[1], "source": row[2], "program": row[3]}
        for row in candidates_rows
    }

    match_result = find_best_match(
        normalized_name,
        candidate_names,
        threshold=SANCTIONS_MATCH_THRESHOLD,
    )

    top_matches = batch_score(normalized_name, candidate_names, limit=5)

    top_candidates = []
    for name, score in top_matches:
        meta = candidate_map.get(name, {})
        top_candidates.append({
            "normalized_name": name,
            "primary_name": meta.get("primary_name"),
            "source": meta.get("source"),
            "program": meta.get("program"),
            "score": score,
        })

    matched_meta = candidate_map.get(match_result.matched_value, {}) if match_result.matched_value else {}

    best_score = match_result.score if match_result.matched_value else (
        top_matches[0][1] if top_matches else 0.0
    )

    return ScreeningResult(
        is_match=match_result.matched,
        requires_review=(
            not match_result.matched
            and best_score >= SANCTIONS_REVIEW_THRESHOLD
        ),
        best_score=best_score,
        matched_name=matched_meta.get("primary_name"),
        matched_source=matched_meta.get("source"),
        matched_program=matched_meta.get("program"),
        top_candidates=top_candidates,
    )