from contextlib import asynccontextmanager

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
import app.models  # noqa: F401
from app.api import ingestion, results

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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "sentinel"}