# Sentinel Frontend

React dashboard for the Sentinel sanctions screening backend.

## Stack

- React 18 and React Router v6
- CSS Modules
- System UI fonts, no external font dependency
- Responsive sidebar and data tables

## Pages

| Route | Description |
| --- | --- |
| `/` | Ingest single entities or upload CSV batches |
| `/results` | Fetch job results by job ID and poll while processing |
| `/queue` | View recent ingestion jobs |
| `/pipeline` | Inspect worker pipeline stages |
| `/flags` | View country-level entity distribution |

## Setup

```bash
cd frontend
npm install
npm start
```

The development server runs at `http://localhost:3000` and proxies API requests
to `http://localhost:8000`.

## API Surface

| Method | Path | Used in |
| --- | --- | --- |
| `POST` | `/api/v1/ingest/manual` | Single entity ingest |
| `POST` | `/api/v1/ingest` | CSV upload |
| `GET` | `/api/v1/jobs/{job_id}` | Job status |
| `GET` | `/api/v1/jobs/{job_id}/entities` | Entity results |
| `GET` | `/api/v1/jobs/{job_id}/summary` | Job summary |
| `GET` | `/api/v1/queue` | Job queue |
| `GET` | `/api/v1/flags` | Country totals |
