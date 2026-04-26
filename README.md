<div align="center">

# 🛡️ Sentinel

### Sanctions Screening & Entity Risk Scoring Backend

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-asyncpg-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-RQ-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)](https://pytest.org)

*Ingest entities. Queue jobs. Screen against sanctions lists. Score risk. Get results.*

</div>

---

## 📌 Overview

Sentinel is a production-style backend that screens individuals and organisations against sanctions lists and assigns them a risk score. Given an entity (name, country, identifiers), it runs it through a **multi-stage async worker pipeline** — normalisation → sanctions fetching → screening → risk scoring → resolution — and exposes structured results via a REST API.

---

## ⚙️ How It Works

```
POST /ingest
      │
      ▼
 Entity persisted to PostgreSQL
      │
      ▼
 Job enqueued → Redis Queue (RQ)
      │
      ▼
  ┌──────────────────────────────────────────┐
  │             Worker Pipeline              │
  │                                          │
  │  normalizer  ──►  sanctions_fetcher      │
  │       │                  │               │
  │       ▼                  ▼               │
  │   country_risk  ──►   screener           │
  │                          │               │
  │                          ▼               │
  │                     risk_scorer          │
  │                          │               │
  │                          ▼               │
  │                       resolver           │
  │                          │               │
  │                          ▼               │
  │                      processing          │
  └──────────────────────────────────────────┘
      │
      ▼
 Case + results saved to PostgreSQL
      │
      ▼
GET /results/{job_id}
```

---

## 🗂️ Project Structure

```
sentinel/
└── backend/
    ├── app/
    │   ├── api/
    │   │   ├── ingestion.py        # POST /ingest
    │   │   └── results.py          # GET /results/{job_id}
    │   ├── models/
    │   │   ├── case.py
    │   │   ├── entity.py
    │   │   ├── job.py
    │   │   └── sanctioned_entity.py
    │   ├── workers/
    │   │   ├── normalizer.py
    │   │   ├── sanctions_fetcher.py
    │   │   ├── screener.py
    │   │   ├── risk_scorer.py
    │   │   ├── country_risk.py
    │   │   ├── resolver.py
    │   │   └── processing.py
    │   ├── config.py
    │   ├── database.py
    │   ├── main.py
    │   └── queue.py
    ├── test_data/
    │   ├── test.csv
    │   ├── empty.csv
    │   ├── missing_name.csv
    │   └── invalid_format.txt
    ├── tests/
    │   ├── test_ingestion_negative.py
    │   └── test_pipeline.py
    ├── Dockerfile
    ├── docker-compose.yml
    ├── pytest.ini
    └── requirements.txt
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI |
| **Database** | PostgreSQL via asyncpg + SQLAlchemy (async) |
| **Migrations** | Alembic |
| **Job Queue** | Redis + RQ |
| **Containerisation** | Docker + Docker Compose |
| **Config** | pydantic-settings + python-dotenv |
| **Testing** | pytest + httpx |

---

## 🚀 Getting Started

### Run with Docker *(recommended)*

```bash
git clone https://github.com/Shivansh-06/sentinel.git
cd sentinel/backend

cp .env.example .env
# fill in DATABASE_URL and REDIS_URL

docker-compose up --build
```

> API: `http://localhost:8000` &nbsp;|&nbsp; Docs: `http://localhost:8000/docs`

### Run locally

```bash
cd sentinel/backend
python -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

alembic upgrade head
uvicorn app.main:app --reload

# separate terminal
rq worker
```

---

## 📡 API Reference

### `POST /ingest`
Ingest entities for screening. Accepts CSV upload or JSON body.

```json
{
  "entities": [
    { "name": "John Doe", "country": "IR", "identifier": "PASS-12345" }
  ]
}
```
```json
{
  "job_id": "a1b2c3d4-...",
  "status": "queued",
  "entity_count": 1
}
```

---

### `GET /results/{job_id}`
Retrieve screening results for a completed job.

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "completed",
  "cases": [
    {
      "entity": "John Doe",
      "match_found": true,
      "risk_score": 87.5,
      "country_risk": "high",
      "resolution": "confirmed_match"
    }
  ]
}
```

---

## 🧪 Tests

```bash
cd sentinel/backend
pytest tests/ -v
```

| File | What it covers |
|---|---|
| `test_ingestion_negative.py` | Empty CSV, invalid format, missing required fields |
| `test_pipeline.py` | End-to-end pipeline execution and result validation |

---

## 🔐 Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sentinel
REDIS_URL=redis://localhost:6379
```

---

<div align="center">

Made by [Shivansh Goyal](https://github.com/Shivansh-06)

</div>
