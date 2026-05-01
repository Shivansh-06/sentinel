# backend/tests/test_ingestion_negative.py

import pytest
from httpx import AsyncClient
from auth_helpers import auth_headers

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_missing_name_column():
    async with AsyncClient(base_url=BASE_URL) as client:
        headers = await auth_headers(client)
        with open("test_data/missing_name.csv", "rb") as f:
            res = await client.post(
                "/api/v1/ingest",
                headers=headers,
                files={"file": ("bad.csv", f, "text/csv")},
            )

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_empty_csv():
    async with AsyncClient(base_url=BASE_URL) as client:
        headers = await auth_headers(client)
        with open("test_data/empty.csv", "rb") as f:
            res = await client.post(
                "/api/v1/ingest",
                headers=headers,
                files={"file": ("empty.csv", f, "text/csv")},
            )

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_invalid_file_type():
    async with AsyncClient(base_url=BASE_URL) as client:
        headers = await auth_headers(client)
        with open("test_data/invalid_format.txt", "rb") as f:
            res = await client.post(
                "/api/v1/ingest",
                headers=headers,
                files={"file": ("file.txt", f, "text/plain")},
            )

    assert res.status_code == 400
