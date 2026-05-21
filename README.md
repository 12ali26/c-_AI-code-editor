# P&C Reserving Analytics Dashboard

A cloud-SaaS starter for small actuarial teams that upload claims triangles, run governed reserving analyses, review diagnostics, save selections, and export management-ready reports.

The repository is split into:

- `backend/` - FastAPI API, triangle validation, chain-ladder reserving engine, audit trail, and export jobs.
- `frontend/` - Next.js dashboard scaffold for the actuarial workbench.

## V1 Scope

- P&C reserving only.
- CSV/XLSX triangle imports.
- Cumulative and incremental triangle import modes, with incremental uploads normalized to cumulative values for reserving calculations.
- Paid, incurred, reported claim count, and earned premium triangle metadata.
- Chain ladder calculations with link ratios, age-to-age factors, selected LDFs, projected cumulative triangles, incremental triangles, ultimates, and IBNR.
- Bornhuetter-Ferguson calculations with exposure/premium inputs, expected loss ratio, expected ultimate, percent reported/unreported, ultimate, and IBNR.
- Cape Cod calculations with exposure/premium inputs, derived apriori loss ratio, expected ultimate, percent reported/unreported, ultimate, and IBNR.
- Immutable model runs, assumption/selection records, review notes, audit events, and export jobs.
- Local in-memory repository for development, with boundaries designed for Postgres/S3 replacement.

## Engine Roadmap

The engine is intentionally method-adapter friendly. The current implemented methods are chain ladder, Bornhuetter-Ferguson, and Cape Cod. The next actuarial engine slices should be:

- Bootstrap reserve distribution for ranges, percentiles, and risk margins.
- Persisting normalized/source triangle views in Postgres and exposing both in the UI.

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

- `GET /projects`
- `POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/datasets`
- `GET /projects/{id}/datasets`
- `GET /projects/{id}/runs`
- `POST /datasets/{id}/validate`
- `GET /datasets/{id}/triangle`
- `POST /datasets/{id}/runs`
- `GET /runs/{id}`
- `POST /runs/{id}/selections`
- `POST /runs/{id}/exports`
- `GET /projects/{id}/audit-events`

Development tenancy is header based:

- `X-Org-Id`: organization id, defaults to `demo-org`
- `X-User-Id`: user id, defaults to `demo-user`

Dataset upload accepts query parameters:

- `origin_column`, default `origin_period`
- `value_type`, default `paid`
- `triangle_basis`, either `cumulative` or `incremental`, default `cumulative`

## Sample Data

`backend/samples/sample_triangle.csv` contains a small cumulative paid triangle suitable for the first chain-ladder run.
