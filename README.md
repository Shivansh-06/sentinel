Sentinel
A sanctions screening and entity risk-scoring backend built with FastAPI, PostgreSQL, Redis, and RQ. Sentinel ingests entities (individuals or organisations), runs them through a multi-stage async worker pipeline — normalisation → sanctions list fetching → screening → risk scoring → resolution — and exposes results via a REST API.

What it does
Given an entity (a person or company name, country, identifiers), Sentinel:

Ingests the entity via API and persists it as a Job
Queues the job using Redis Queue (RQ) for background processing
Normalises the entity name and identifiers for consistent matching
Fetches sanctions data from external sources
Screens the normalised entity against the fetched sanctions list
Scores country risk and computes an aggregate risk score
Resolves matches and produces a final Case with screening results
Serves results via a dedicated results endpoint


Architecture
POST /ingest
     │
     ▼
 Entity saved to PostgreSQL
     │
     ▼
 Job enqueued → Redis Queue (RQ)
     │
     ▼
┌─────────────────────────────────┐
│         Worker Pipeline         │
│                                 │
│  normalizer → sanctions_fetcher │
│       → screener → risk_scorer  │
│            → country_risk       │
│              → resolver         │
│                → processing     │
└─────────────────────────────────┘
     │
     ▼
 Case + results saved to PostgreSQL
     │
     ▼
GET /results/{job_id}

Tech Stack
LayerTechnologyFrameworkFastAPIDatabasePostgreSQL (asyncpg + SQLAlchemy async)MigrationsAlembicJob QueueRedis + RQ (Redis Queue)ContainerisationDocker + Docker ComposeConfigpydantic-settings + python-dotenvTestingpytestHTTP clienthttpx

Project Structure
sentinel/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── ingestion.py       # POST /ingest endpoint
│   │   │   └── results.py         # GET /results endpoint
│   │   ├── models/
│   │   │   ├── case.py            # Screening case model
│   │   │   ├── entity.py          # Entity model
│   │   │   ├── job.py             # Job model
│   │   │   └── sanctioned_entity.py
│   │   ├── workers/
│   │   │   ├── normalizer.py      # Name/identifier normalisation
│   │   │   ├── sanctions_fetcher.py # Fetch external sanctions data
│   │   │   ├── screener.py        # Match entity against sanctions list
│   │   │   ├── risk_scorer.py     # Compute aggregate risk score
│   │   │   ├── country_risk.py    # Country-level risk assessment
│   │   │   ├── resolver.py        # Resolve and finalise matches
│   │   │   └── processing.py      # Pipeline orchestration
│   │   ├── config.py
│   │   ├── database.py            # Async DB session setup
│   │   ├── main.py                # FastAPI app entrypoint
│   │   └── queue.py               # RQ queue setup
│   ├── test_data/
│   │   ├── test.csv
│   │   ├── empty.csv
│   │   ├── missing_name.csv
│   │   └── invalid_format.txt
│   ├── tests/
│   │   ├── test_ingestion_negative.py
│   │   └── test_pipeline.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── pytest.ini
│   └── requirements.txt
└── requirements.txt

Getting Started
Prerequisites

Docker and Docker Compose
Python 3.11+

Run with Docker (recommended)
bashgit clone https://github.com/Shivansh-06/sentinel.git
cd sentinel/backend

cp .env.example .env
# Edit .env with your config

docker-compose up --build
The API will be available at http://localhost:8000.
Interactive docs: http://localhost:8000/docs
Run locally
bashcd sentinel/backend

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Set DATABASE_URL and REDIS_URL in .env

# Run Alembic migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload

# In a separate terminal, start the RQ worker
rq worker --with-scheduler

API Reference
POST /ingest
Ingest one or more entities for screening.
Request body (CSV upload or JSON):
json{
  "entities": [
    {
      "name": "John Doe",
      "country": "IR",
      "identifier": "PASS-12345"
    }
  ]
}
Response:
json{
  "job_id": "a1b2c3d4-...",
  "status": "queued",
  "entity_count": 1
}
GET /results/{job_id}
Retrieve screening results for a job.
Response:
json{
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

Running Tests
bashcd sentinel/backend

pytest tests/ -v
Test coverage includes:

test_ingestion_negative.py — invalid file formats, empty CSVs, missing required fields
test_pipeline.py — end-to-end pipeline execution and result validation

Test fixtures are located in test_data/.

Environment Variables
Copy .env.example to .env and configure:
envDATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sentinel
REDIS_URL=redis://localhost:6379

Design Decisions
Why RQ over Celery? RQ is simpler to configure and debug for a single-broker setup. The job model maps cleanly to RQ's job lifecycle (queued → started → finished/failed).
Why async SQLAlchemy + asyncpg? The ingestion endpoint can receive batch entity submissions. Async I/O ensures the API remains non-blocking while workers process jobs concurrently.
Why Alembic? Schema migrations are versioned and reproducible across environments — a requirement for any production-grade backend.

Author
Shivansh Goyal
github.com/Shivansh-06 · linkedin.com/in/shivansh-goyal-052154321
