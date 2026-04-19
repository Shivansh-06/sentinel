# backend/tests/test_pipeline.py
#
# IMPORTANT — prerequisites before running this test:
#
#   This is an INTEGRATION test. It requires all services to be running:
#
#   Terminal 1 (Redis + Postgres):
#       docker-compose up
#
#   Terminal 2 (FastAPI server):
#       cd backend && .venv\Scripts\activate
#       uvicorn app.main:app --reload
#
#   Terminal 3 (RQ worker — REQUIRED or jobs stay "queued" forever):
#       cd backend && .venv\Scripts\activate
#       rq worker ingestion
#
#   Terminal 4 (run tests):
#       pytest tests/test_pipeline.py

import pytest
import asyncio
from httpx import AsyncClient

BASE_URL = "http://localhost:8000"

SANCTIONS_SYNC_TIMEOUT = 30   # seconds to wait for sanctions sync
JOB_COMPLETION_TIMEOUT = 120  # seconds to wait for job to complete


@pytest.mark.asyncio
async def test_full_pipeline():
    async with AsyncClient(base_url=BASE_URL) as client:

        # ── 1. Sync sanctions ────────────────────────────────────────────────
        res = await client.post("/api/v1/sanctions/sync")
        assert res.status_code == 202

        total = 0
        for _ in range(SANCTIONS_SYNC_TIMEOUT):
            res = await client.get("/api/v1/sanctions/stats")
            assert res.status_code == 200
            stats = res.json()
            assert "counts" in stats
            total = stats.get("total", 0)
            if total > 0:
                break
            await asyncio.sleep(1)

        assert total > 0, (
            f"Sanctions sync did not complete in {SANCTIONS_SYNC_TIMEOUT}s. "
            "Is 'rq worker ingestion' running in a separate terminal?"
        )

        # ── 2. Verify sanctions stats ────────────────────────────────────────
        res = await client.get("/api/v1/sanctions/stats")
        assert res.status_code == 200
        stats = res.json()
        counts = stats["counts"]
        assert isinstance(counts, dict)
        assert stats["total"] > 0
        if "UN" in counts:
            assert counts["UN"] > 0
        if "OFAC" in counts:
            assert counts["OFAC"] > 0

        # ── 3. Upload CSV ────────────────────────────────────────────────────
        with open("test_data/test.csv", "rb") as f:
            res = await client.post(
                "/api/v1/ingest",
                files={"file": ("test.csv", f, "text/csv")},
            )
        assert res.status_code == 202
        data = res.json()
        job_id = data["job_id"]

        # ── 4. Poll job status until completed ──────────────────────────────
        job = {}
        final_status = "unknown"

        for _ in range(JOB_COMPLETION_TIMEOUT):
            res = await client.get(f"/api/v1/jobs/{job_id}")
            assert res.status_code == 200
            job = res.json()
            final_status = job["status"]

            if final_status in ("completed", "completed_error"):
                break
            if final_status == "failed":
                pytest.fail(
                    f"Job failed. Error: {job.get('error_message', 'none')}"
                )
            await asyncio.sleep(1)

        assert final_status in ("completed", "completed_error"), (
            f"Job did not complete after {JOB_COMPLETION_TIMEOUT}s. "
            f"Final status: '{final_status}'. "
            "Is 'rq worker ingestion' running in a separate terminal?"
        )

        # ── 5. Get high-risk entities (paginated dict, not raw list) ─────────
        res = await client.get(
            f"/api/v1/jobs/{job_id}/entities",
            params={"risk_label": "critical"},
        )
        assert res.status_code == 200
        payload = res.json()

        assert "entities" in payload, f"Expected 'entities' key, got: {list(payload.keys())}"
        assert "total" in payload
        assert "page" in payload

        entities = payload["entities"]
        assert isinstance(entities, list)
        if entities:
            assert "status" in entities[0]
            assert "raw_name" in entities[0]

        # ── 6. Summary ───────────────────────────────────────────────────────
        res = await client.get(f"/api/v1/jobs/{job_id}/summary")
        assert res.status_code == 200
        summary = res.json()
        assert "total_entities" in summary
        assert "processed_records" in summary
        assert summary["total_entities"] >= summary["processed_records"]

        # ── 7. Cases ─────────────────────────────────────────────────────────
        res = await client.get("/api/v1/cases")
        assert res.status_code == 200
        cases_payload = res.json()

        # /cases returns {"total", "page", "page_size", "cases": [...]}
        assert "cases" in cases_payload, f"Expected 'cases' key, got: {list(cases_payload.keys())}"
        cases = cases_payload["cases"]

        if cases:
            case_id = cases[0]["case_id"]  # key is "case_id", not "id"

            res = await client.patch(
                f"/api/v1/cases/{case_id}",
                json={
                    "status": "under_investigation",
                    "assigned_to": "analyst_1",
                    "notes": "Test update",
                },
            )
            assert res.status_code == 200
            updated = res.json()
            assert updated["status"] == "under_investigation"
            assert updated["assigned_to"] == "analyst_1"