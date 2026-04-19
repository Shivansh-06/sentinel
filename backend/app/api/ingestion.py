import csv
import io

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.job import Job
from app.models.entity import Entity
from app.queue import ingestion_queue
from app.models.case import Case
from app.models.sanctioned_entity import SanctionedEntity

router = APIRouter()

REQUIRED_COLUMNS = {"name"}
OPTIONAL_COLUMNS = {"entity_type", "country"}
MAX_ROWS = 10_000


def parse_csv(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file encoding")

    try:
        reader = csv.DictReader(io.StringIO(text))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV format")

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    headers = {str(h).strip().lower() for h in reader.fieldnames if h}
    if not REQUIRED_COLUMNS.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain columns: {REQUIRED_COLUMNS}. Found: {headers}",
        )

    rows = []

    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_ROWS} rows allowed per upload",
            )

        if not isinstance(row, dict):
            continue

        normalized = {}

        for k, v in row.items():
            if not k:
                continue
            key = k.strip().lower()
            value = str(v).strip() if v is not None else ""
            if value:
                normalized[key] = value

        if normalized.get("name"):
            rows.append(normalized)

    if not rows:
        raise HTTPException(status_code=400, detail="No valid rows found in CSV")

    return rows


@router.post("/ingest", status_code=202)
async def ingest_entities(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()

    try:
        rows = parse_csv(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV format: {str(e)}"
        )

    job = Job(total_records=len(rows))
    db.add(job)
    await db.flush()

    entities = [
        Entity(
            job_id=job.id,
            raw_name=row["name"],
            entity_type=row.get("entity_type"),
            country=row.get("country"),
        )
        for row in rows
    ]
    db.add_all(entities)
    await db.flush()

    ingestion_queue.enqueue(
        "app.workers.processing.process_job",
        job.id,
        job_timeout=600,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "total_records": len(rows),
        "message": f"{len(rows)} entities queued for processing",
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "total_records": job.total_records,
        "processed_records": job.processed_records,
        "error_message": job.error_message,
        "created_at": job.created_at,
    }


@router.post("/sanctions/sync", status_code=202)
async def trigger_sanctions_sync(db: AsyncSession = Depends(get_db)):
    """
    Triggers a background sync of OFAC and UN sanctions lists.
    In production this would be a scheduled job (daily cron).
    For development, call this endpoint manually before running screens.
    """
    from app.queue import ingestion_queue
    ingestion_queue.enqueue(
        "app.workers.sanctions_fetcher.sync_sanctions_lists",
        job_timeout=300,
    )
    return {"status": "queued", "message": "Sanctions list sync started"}


@router.get("/sanctions/stats")
async def get_sanctions_stats(db: AsyncSession = Depends(get_db)):
    """
    Shows how many entries are loaded per source.
    Useful for verifying the sync worked before running screens.
    """
    result = await db.execute(
        select(SanctionedEntity.source, func.count(SanctionedEntity.id))
        .group_by(SanctionedEntity.source)
    )
    rows = result.all()
    return {
        "counts": {source: count for source, count in rows},
        "total": sum(count for _, count in rows),
    }