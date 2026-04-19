import logging

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.job import Job
from app.models.entity import Entity
from app.models.case import Case

from app.workers.normalizer import get_normalizer
from app.workers.screener import screen_entity
from app.workers.risk_scorer import compute_risk_score

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.sync_database_url)


def process_job(job_id: str) -> None:
    """
    Full pipeline: normalize → screen → score.
    Ensures job always reaches a terminal state.
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

                except Exception as e:
                    logger.exception(f"Entity {entity.id} failed")

                    entity.status = "error"
                    entity.error = str(e)

                finally:
                    job.processed_records += 1
                    session.commit()

            failed = sum(1 for e in entities if e.status == "error")

            # IMPORTANT: keep status within DB limits
            job.status = "completed" if failed == 0 else "completed_error"

            session.commit()
            logger.info(
                f"Job {job_id} done. {job.processed_records}/{job.total_records} processed. Failed: {failed}"
            )

        except Exception as e:
            logger.exception(f"Job {job_id} failed fatally")

            job.status = "failed"
            job.error_message = str(e)

            session.commit()


def _process_entity(session: Session, entity: Entity) -> None:
    """
    Single entity pipeline — normalize → screen → score → case creation.
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

    # Store structured details
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

    # Stage 4: Auto-case creation
    if entity.risk_label in ("critical", "high") or screening_result.requires_review:
        existing_case = session.execute(
            select(Case).where(Case.entity_id == entity.id)
        ).scalar_one_or_none()

        if not existing_case:
            case = Case(
                entity_id=entity.id,
                risk_score_at_creation=entity.risk_score,
                status=(
                    "pending_review"
                    if entity.risk_label in ("critical", "high")
                    else "needs_investigation"
                ),
            )
            session.add(case)

    # Final entity status
    entity.status = "reviewed" if screening_result.requires_review else "screened"