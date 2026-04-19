import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.job import Job
from app.models.entity import Entity
from app.workers.normalizer import get_normalizer
from app.workers.resolver import find_best_match, batch_score
from app.workers.screener import screen_entity
from app.workers.risk_scorer import compute_risk_score
from app.models.case import Case

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.sync_database_url)


def process_job(job_id: str) -> None:
    """
    Full pipeline: normalize → screen → score.
    Each entity goes through all three stages.
    """
    logger.info(f"Starting job {job_id}")

    with Session(sync_engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "processing"
        session.commit()

        try:
            entities = session.execute(
                select(Entity).where(Entity.job_id == job_id)
            ).scalars().all()

            for entity in entities:
                try:
                    _process_entity(session, entity)
                    job.processed_records += 1
                    session.commit()
                except Exception as e:
                    logger.error(f"Entity {entity.id} failed: {e}")
                    entity.status = "error"
                    entity.error = str(e)
                    session.commit()

            failed = sum(1 for e in entities if e.status == "error")
            job.status = "completed" if failed == 0 else "completed_with_errors"
            session.commit()
            logger.info(f"Job {job_id} done. {job.processed_records} processed.")

        except Exception as e:
            logger.error(f"Job {job_id} failed fatally: {e}")
            job.status = "failed"
            job.error_message = str(e)
            session.commit()


def _process_entity(session: Session, entity: Entity) -> None:
    """
    Single entity pipeline — three sequential stages.
    Failures in screening/scoring don't discard normalization work.
    """
    # Stage 1: Normalize
    normalizer = get_normalizer(entity.entity_type)
    entity.normalized_name = normalizer(entity.raw_name)

    # Stage 2: Sanctions screening
    screening_result = screen_entity(
        entity.normalized_name,
        session,
        entity.entity_type,
    )
    entity.sanctions_match = screening_result.is_match

    # Stage 3: Risk scoring
    risk = compute_risk_score(
        screening_result,
        entity.entity_type,
        entity.country,
    )
    entity.risk_score = risk.score
    entity.risk_label = risk.label

    entity.match_details = {
        "screening": {
            "is_match": screening_result.is_match,
            "requires_review": screening_result.requires_review,
            "best_score": screening_result.best_score,
            "matched_name": screening_result.matched_name,
            "matched_source": screening_result.matched_source,
            "matched_program": screening_result.matched_program,
            "top_candidates": screening_result.top_candidates,
        },
        "risk": {
            "score": risk.score,
            "label": risk.label,
            "components": risk.components,
            "recommended_action": risk.recommended_action,
        },
    }

    entity.status = "reviewed" if screening_result.requires_review else "screened"

# Auto-create a case for anything that needs attention
def _process_entity(session: Session, entity: Entity) -> None:
    # ... existing stages 1-3 above ...

    # Stage 4: Auto-case creation
    # Critical and high risk entities, plus anything requiring review,
    # automatically get a case opened. Low/medium risk entities that
    # cleanly pass don't generate case overhead.
    if entity.risk_label in ("critical", "high") or screening_result.requires_review:
        existing_case = session.execute(
            select(Case).where(Case.entity_id == entity.id)
        ).scalar_one_or_none()

        if not existing_case:
            case = Case(
                entity_id=entity.id,
                risk_score_at_creation=entity.risk_score,
                status="pending_review" if entity.risk_label in ("critical", "high")
                       else "needs_investigation",
            )
            session.add(case)

    entity.status = "reviewed" if screening_result.requires_review else "screened"