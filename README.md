# Ascent Document Operations

AI-assisted document processing for construction invoices and change
orders. Documents are uploaded, classified, and have structured data
extracted with confidence scores — but nothing is ever released downstream
without a human reviewing and approving it first. No auto-approval of
payments, contracts, or any legally significant decision, ever.

See [`docs/product/product-vision.md`](docs/product/product-vision.md) for
the full product vision, [`docs/product/requirements.md`](docs/product/requirements.md)
for MVP scope, and [`docs/architecture/`](docs/architecture/) for system
design and architecture decision records.

## Status

Early development, building in public in small increments. Currently built:

- A FastAPI backend with typed, environment-driven configuration and
  structured logging.
- PostgreSQL via SQLAlchemy 2.0 + Alembic migrations, with tenant isolation
  enforced at the schema level (every tenant-owned table carries a
  `tenant_id`).
- `Tenant` / `User` models, and `Document` / `AuditEvent` models implementing
  an explicit workflow state machine (`uploaded → processing → extracted →
  in_review → approved/rejected → exported`) — every transition is
  recorded as an append-only audit event, never overwritten.
- A file-upload endpoint that validates content by sniffing actual file
  bytes (never trusting the client's filename or `Content-Type` header),
  behind an `ObjectStorage` interface (local disk for now; a cloud backend
  is a drop-in replacement later).
- A Postgres-backed background job queue (`SELECT ... FOR UPDATE SKIP
  LOCKED` — no message broker needed at this scale) and a worker process
  that claims jobs, retries transient failures with exponential backoff,
  and gives up after a max-attempts limit.

Not built yet: real AI classification/extraction (the current worker
handler is a placeholder), the human review dashboard, authentication, and
integrations (CSV export, webhooks, email intake).

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · Pydantic /
pydantic-settings · uv · pytest · ruff · mypy (strict) · Docker Compose

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker Desktop.

```bash
# Install dependencies
make setup

# Copy the example environment file and adjust if needed
cp .env.example .env

# Start Postgres, the API, and the worker via Docker Compose
docker compose up --build

# In another terminal: apply database migrations
uv run alembic upgrade head
```

The API is then available at `http://localhost:8000` (health check at
`/healthz`), and the worker is running alongside it, polling for jobs.

Note: Postgres is exposed on host port **5433**, not the default 5432, to
avoid clashing with any Postgres instance already running locally.

## Running checks

```bash
make check   # ruff + mypy --strict + pytest
make fmt      # auto-format and auto-fix lint issues
make test     # pytest only
```

Integration tests (`tests/integration/`) run against a real PostgreSQL
database — start it first with `docker compose up -d db`, then
`uv run alembic upgrade head`.

## Project structure

```
apps/
├── api/              FastAPI application: entrypoint + routes
└── worker/           Background worker: claims and processes jobs
src/ascent/
├── documents/        Document/AuditEvent models, workflow repository,
│                     object storage interface, processing handler
├── jobs/             Postgres-backed job queue (models + queue logic)
└── shared/           Config, database setup, logging, base models
alembic/              Database migrations
tests/
├── unit/             Fast, isolated tests
├── integration/       Tests against a real database (shared fixtures
│                     in conftest.py)
└── fixtures/         Synthetic test documents
docs/
├── product/          Product vision, requirements, customer persona
└── architecture/     System architecture, ADRs, database/API design
```

## License

See [LICENSE](LICENSE) — proprietary, all rights reserved. This repository
is public for portfolio/evaluation purposes only; it is not open source.