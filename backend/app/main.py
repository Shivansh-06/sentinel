from contextlib import asynccontextmanager
from select import select

from fastapi import Depends, FastAPI, Request
from sqlalchemy import select, func

from fastapi.responses import JSONResponse
import logging
from app.database import engine, Base, get_db
import app.models  # noqa: F401
from app.api import ingestion, results
from app.models.case import Case

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Sentinel",
    description="Entity risk intelligence pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(results.router, prefix="/api/v1", tags=["results"])



@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "sentinel"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )
