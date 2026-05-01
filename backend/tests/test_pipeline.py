import asyncio

import pytest
from httpx import AsyncClient

from auth_helpers import auth_headers

BASE_URL = "http://localhost:8000"

SANCTIONS_SYNC_TIMEOUT = 30
JOB_COMPLETION_TIMEOUT = 120


@pytest.mark.asyncio
async def test_full_pipeline():
    async with AsyncClient(base_url=BASE_URL) as client:
        headers = await auth_headers(client)

        res = await client.post("/api/v1/sanctions/sync", headers=headers)
        assert res.status_code == 202

        total = 0
        for _ in range(SANCTIONS_SYNC_TIMEOUT):
            res = await client.get("/api/v1/sanctions/stats", headers=headers)
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

        res = await client.get("/api/v1/sanctions/stats", headers=headers)
        assert res.status_code == 200
        stats = res.json()
        counts = stats["counts"]
        assert isinstance(counts, dict)
        assert stats["total"] > 0
        if "UN" in counts:
            assert counts["UN"] > 0
        if "OFAC" in counts:
            assert counts["OFAC"] > 0

        with open("test_data/test.csv", "rb") as f:
            res = await client.post(
                "/api/v1/ingest",
                headers=headers,
                files={"file": ("test.csv", f, "text/csv")},
            )
        assert res.status_code == 202
        data = res.json()
        job_id = data["job_id"]

        job = {}
        final_status = "unknown"

        for _ in range(JOB_COMPLETION_TIMEOUT):
            res = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
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

        res = await client.get(
            f"/api/v1/jobs/{job_id}/entities",
            headers=headers,
            params={"risk_label": "critical"},
        )
        assert res.status_code == 200
        payload = res.json()

        assert "entities" in payload
        assert "total" in payload
        assert "page" in payload

        entities = payload["entities"]
        assert isinstance(entities, list)
        if entities:
            assert "status" in entities[0]
            assert "raw_name" in entities[0]

        res = await client.get(f"/api/v1/jobs/{job_id}/summary", headers=headers)
        assert res.status_code == 200
        summary = res.json()
        assert "total_entities" in summary
        assert "processed_records" in summary
        assert summary["total_entities"] >= summary["processed_records"]

        res = await client.get("/api/v1/cases", headers=headers)
        assert res.status_code == 200
        cases_payload = res.json()

        assert "cases" in cases_payload
        cases = cases_payload["cases"]

        if cases:
            case_id = cases[0]["case_id"]

            res = await client.patch(
                f"/api/v1/cases/{case_id}",
                headers=headers,
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
