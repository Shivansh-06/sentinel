import logging
from dataclasses import dataclass

from app.workers.country_risk import get_country_risk_score
from app.workers.screener import ScreeningResult

logger = logging.getLogger(__name__)

# Weights must sum to 1.0
WEIGHT_SANCTIONS = 0.40
WEIGHT_COUNTRY = 0.25
WEIGHT_ENTITY_TYPE = 0.15
WEIGHT_MATCH_CONFIDENCE = 0.20

# Risk label thresholds
RISK_HIGH = 70.0
RISK_MEDIUM = 40.0


@dataclass
class RiskAssessment:
    score: float           # 0-100
    label: str             # low / medium / high / critical
    components: dict       # breakdown of each contributing signal
    recommended_action: str


def score_entity_type(entity_type: str | None) -> tuple[float, str]:
    """
    Entity type affects base risk. PEPs (politically exposed persons)
    and government officials are inherently higher risk under FATF guidance
    regardless of sanctions matches — they have greater opportunity for
    corruption and money laundering.
    """
    if not entity_type:
        return 0.3, "unknown"

    et = entity_type.lower()

    if et in ("pep", "politically exposed person", "government official"):
        return 0.9, "pep"
    if et in ("individual", "person"):
        return 0.3, "individual"
    if et in ("organization", "org", "company", "corporation"):
        return 0.2, "organization"
    if et in ("financial institution", "bank"):
        return 0.4, "financial_institution"

    return 0.3, "unknown"


def compute_risk_score(
    screening_result: ScreeningResult,
    entity_type: str | None,
    country: str | None,
) -> RiskAssessment:
    """
    Composite risk scoring. Each component contributes a 0-1 signal,
    weighted and summed to produce a final 0-100 score.

    The weighting reflects real AML priorities:
    - Sanctions match is the strongest signal (40%) — a direct hit means
      the entity is on a government watchlist
    - Country risk (25%) — jurisdiction matters enormously in AML
    - Match confidence (20%) — how certain are we? A 95% match is
      different from a 65% one
    - Entity type (15%) — PEPs are higher risk by regulation
    """
    # Component 1: sanctions signal
    if screening_result.is_match:
        sanctions_signal = 1.0
    elif screening_result.requires_review:
        sanctions_signal = screening_result.best_score / 100.0 * 0.8
    else:
        sanctions_signal = min(screening_result.best_score / 100.0 * 0.3, 0.3)

    # Component 2: country risk
    country_signal, country_label = get_country_risk_score(country)

    # Component 3: entity type risk
    type_signal, type_label = score_entity_type(entity_type)

    # Component 4: match confidence
    confidence_signal = screening_result.best_score / 100.0

    # Weighted composite
    raw_score = (
        (sanctions_signal * WEIGHT_SANCTIONS) +
        (country_signal * WEIGHT_COUNTRY) +
        (type_signal * WEIGHT_ENTITY_TYPE) +
        (confidence_signal * WEIGHT_MATCH_CONFIDENCE)
    )

    final_score = round(raw_score * 100, 2)

    # Determine label — critical is reserved for confirmed sanctions hits
    if screening_result.is_match:
        label = "critical"
    elif final_score >= RISK_HIGH:
        label = "high"
    elif final_score >= RISK_MEDIUM:
        label = "medium"
    else:
        label = "low"

    if label == "critical":
        action = "block_and_report"
    elif label == "high":
        action = "escalate_for_review"
    elif label == "medium":
        action = "enhanced_due_diligence"
    else:
        action = "standard_monitoring"

    return RiskAssessment(
        score=final_score,
        label=label,
        components={
            "sanctions_signal": round(sanctions_signal * 100, 2),
            "country_risk": {"score": round(country_signal * 100, 2), "label": country_label},
            "entity_type_risk": {"score": round(type_signal * 100, 2), "label": type_label},
            "match_confidence": round(confidence_signal * 100, 2),
            "weights": {
                "sanctions": WEIGHT_SANCTIONS,
                "country": WEIGHT_COUNTRY,
                "entity_type": WEIGHT_ENTITY_TYPE,
                "match_confidence": WEIGHT_MATCH_CONFIDENCE,
            },
        },
        recommended_action=action,
    )