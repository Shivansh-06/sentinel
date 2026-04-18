import csv
import io
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.job import Job
from app.models.entity import Entity
from app.queue import ingestion_queue

router = APIRouter()

REQUIRED_COLUMNS = {"name"}
OPTIONAL_COLUMNS = {"entity_type", "country"}
MAX_ROWS = 10_000


def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # strips BOM if present
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    headers = {h.strip().lower() for h in reader.fieldnames}
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
        normalized = {k.strip().lower(): v.strip() for k, v in row.items() if v and v.strip()}
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
    rows = parse_csv(content)

    job = Job(total_records=len(rows))
    db.add(job)
    await db.flush()  # writes job to db and assigns id, without committing

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