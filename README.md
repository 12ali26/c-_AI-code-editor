# P&C Reserving Analytics Dashboard

A cloud-SaaS starter for small actuarial teams that upload claims triangles, run governed reserving analyses, review diagnostics, save selections, and export management-ready reports.

The repository is split into:

- `backend/` - FastAPI API, triangle validation, chain-ladder reserving engine, audit trail, and export jobs.
- `frontend/` - Next.js dashboard scaffold for the actuarial workbench.

## V1 Scope

- P&C reserving only.
- CSV/XLSX triangle imports.
- Paid, incurred, reported claim count, and earned premium triangle metadata.
- Chain ladder calculations with link ratios, age-to-age factors, selected LDFs, projected cumulative triangles, incremental triangles, ultimates, and IBNR.
- Immutable model runs, assumption/selection records, review notes, audit events, and export jobs.
- Local in-memory repository for development, with boundaries designed for Postgres/S3 replacement.

## Engine Roadmap

The engine is intentionally method-adapter friendly. The current implemented method is chain ladder. The next actuarial engine slices should be:

- Bornhuetter-Ferguson using earned premium/exposure and expected loss ratio inputs.
- Cape Cod using implied expected loss ratios from the triangle and exposure base.
- Bootstrap reserve distribution for ranges, percentiles, and risk margins.
- Explicit cumulative vs incremental import mode.

## Quick Start

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run tests:

```bash
cd backend
pytest
```

## API

The REST API is served under `/api/v1`.

- `POST /projects`
- `POST /projects/{id}/datasets`
- `POST /datasets/{id}/validate`
- `POST /datasets/{id}/runs`
- `GET /runs/{id}`
- `POST /runs/{id}/selections`
- `POST /runs/{id}/exports`
- `GET /projects/{id}/audit-events`

Development tenancy is header based:

- `X-Org-Id`: organization id, defaults to `demo-org`
- `X-User-Id`: user id, defaults to `demo-user`

## Sample Data

`backend/samples/sample_triangle.csv` contains a small cumulative paid triangle suitable for the first chain-ladder run.
