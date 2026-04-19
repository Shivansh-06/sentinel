from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.entity import Entity
from app.models.job import Job
from app.models.case import Case

router = APIRouter()


@router.get("/jobs/{job_id}/entities")
async def get_job_entities(
    job_id: str,
    risk_label: Optional[str] = Query(None, description="Filter by: low, medium, high, critical"),
    sanctions_match: Optional[bool] = Query(None),
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Query entities for a job with rich filtering.
    This is the primary data retrieval endpoint — equivalent to
    Zigram's entity results table with column filters.
    """
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    filters = [Entity.job_id == job_id]

    if risk_label:
        filters.append(Entity.risk_label == risk_label)
    if sanctions_match is not None:
        filters.append(Entity.sanctions_match == sanctions_match)
    if country:
        filters.append(Entity.country.ilike(f"%{country}%"))
    if status:
        filters.append(Entity.status == status)
    if min_score is not None:
        filters.append(Entity.risk_score >= min_score)
    if max_score is not None:
        filters.append(Entity.risk_score <= max_score)

    count_result = await db.execute(
        select(func.count(Entity.id)).where(and_(*filters))
    )
    total = count_result.scalar()

    offset = (page - 1) * page_size
    entities_result = await db.execute(
        select(Entity)
        .where(and_(*filters))
        .order_by(Entity.risk_score.desc().nulls_last())
        .offset(offset)
        .limit(page_size)
    )
    entities = entities_result.scalars().all()

    return {
        "job_id": job_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "entities": [
            {
                "id": e.id,
                "raw_name": e.raw_name,
                "normalized_name": e.normalized_name,
                "entity_type": e.entity_type,
                "country": e.country,
                "risk_score": e.risk_score,
                "risk_label": e.risk_label,
                "sanctions_match": e.sanctions_match,
                "status": e.status,
                "match_details": e.match_details,
            }
            for e in entities
        ],
    }


@router.get("/jobs/{job_id}/summary")
async def get_job_summary(job_id: str, db: AsyncSession = Depends(get_db)):
    """
    Aggregated risk summary for a job.
    This is the dashboard view — what a compliance manager sees first.
    """
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    risk_dist = await db.execute(
        select(Entity.risk_label, func.count(Entity.id))
        .where(Entity.job_id == job_id)
        .group_by(Entity.risk_label)
    )

    sanctions_count = await db.execute(
        select(func.count(Entity.id)).where(
            Entity.job_id == job_id,
            Entity.sanctions_match == True,
        )
    )

    avg_score = await db.execute(
        select(func.avg(Entity.risk_score)).where(Entity.job_id == job_id)
    )

    cases_count = await db.execute(
        select(func.count(Case.id))
        .join(Entity, Case.entity_id == Entity.id)
        .where(Entity.job_id == job_id)
    )

    return {
        "job_id": job_id,
        "job_status": job.status,
        "total_entities": job.total_records,
        "processed": job.processed_records,
        "sanctions_matches": sanctions_count.scalar() or 0,
        "average_risk_score": round(avg_score.scalar() or 0, 2),
        "open_cases": cases_count.scalar() or 0,
        "risk_distribution": {
            label: count for label, count in risk_dist.all() if label
        },
    }


@router.get("/cases")
async def list_cases(
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all open cases with filtering.
    This is the Case Manager queue — what compliance officers work from daily.
    """
    filters = []
    if status:
        filters.append(Case.status == status)
    if assigned_to:
        filters.append(Case.assigned_to == assigned_to)

    count_result = await db.execute(
        select(func.count(Case.id)).where(and_(*filters)) if filters
        else select(func.count(Case.id))
    )
    total = count_result.scalar()

    query = (
        select(Case, Entity)
        .join(Entity, Case.entity_id == Entity.id)
        .order_by(Case.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    rows = result.all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "cases": [
            {
                "case_id": case.id,
                "status": case.status,
                "assigned_to": case.assigned_to,
                "risk_score": case.risk_score_at_creation,
                "entity": {
                    "id": entity.id,
                    "raw_name": entity.raw_name,
                    "normalized_name": entity.normalized_name,
                    "country": entity.country,
                    "risk_label": entity.risk_label,
                    "sanctions_match": entity.sanctions_match,
                },
                "created_at": case.created_at,
            }
            for case, entity in rows
        ],
    }


@router.patch("/cases/{case_id}")
async def update_case(
    case_id: str,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    notes: Optional[str] = None,
    resolution: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a case status, assignment, notes, or resolution.
    This is what a compliance officer does when they review a flagged entity.

    Valid statuses: pending_review → under_investigation → resolved / escalated / false_positive
    Valid resolutions: cleared, confirmed_match, escalated_to_regulator
    """
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if status:
        case.status = status
    if assigned_to:
        case.assigned_to = assigned_to
    if notes:
        case.notes = notes
    if resolution:
        case.resolution = resolution
        case.resolved_at = datetime.now(timezone.utc)

    return {
        "case_id": case.id,
        "status": case.status,
        "assigned_to": case.assigned_to,
        "notes": case.notes,
        "resolution": case.resolution,
        "resolved_at": case.resolved_at,
    }


@router.get("/cases/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Full case detail with entity and match information."""
    result = await db.execute(
        select(Case, Entity)
        .join(Entity, Case.entity_id == Entity.id)
        .where(Case.id == case_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    case, entity = row

    return {
        "case_id": case.id,
        "status": case.status,
        "assigned_to": case.assigned_to,
        "risk_score": case.risk_score_at_creation,
        "notes": case.notes,
        "resolution": case.resolution,
        "resolved_at": case.resolved_at,
        "created_at": case.created_at,
        "entity": {
            "id": entity.id,
            "raw_name": entity.raw_name,
            "normalized_name": entity.normalized_name,
            "entity_type": entity.entity_type,
            "country": entity.country,
            "risk_score": entity.risk_score,
            "risk_label": entity.risk_label,
            "sanctions_match": entity.sanctions_match,
            "match_details": entity.match_details,
        },
    }