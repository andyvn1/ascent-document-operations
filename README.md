# Ascent Document Operations

AI-assisted document processing for construction invoices and change
orders. Documents are uploaded, classified, and have structured data
extracted with confidence scores — but nothing is ever released downstream
without a human reviewing and approving it first. No auto-approval of
payments, contracts, or any legally significant decision, ever.

See [`docs/product/product-vision.md`](docs/product/product-vision.md) for
the full product vision and [`docs/product/requirements.md`](docs/product/requirements.md)
for MVP scope.

## Status

Early development. Currently built: a FastAPI backend with a health
endpoint, typed environment-based configuration, structured logging,
PostgreSQL via SQLAlchemy/Alembic, and the first two data models (`Tenant`,
`User`) with tenant isolation enforced at the schema level. Document
intake, AI extraction, and the review workflow are not built yet.

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

# Start Postgres (and the API) via Docker Compose
docker compose up --build

# In another terminal: apply database migrations
uv run alembic upgrade head
```

The API is then available at `http://localhost:8000`, with a health check
at `http://localhost:8000/healthz`.

Note: Postgres is exposed on host port **5433**, not the default 5432, to
avoid clashing with any Postgres instance already running locally.

## Running checks

```bash
make check   # ruff + mypy --strict + pytest
make fmt      # auto-format and auto-fix lint issues
make test     # pytest only
```

Integration tests (`tests/integration/`) run against a real PostgreSQL
database — start it first with `docker compose up -d db`.

## Project structure

```
apps/api/          FastAPI application (routes, entrypoint)
src/ascent/         Application code (shared config/db/logging so far;
                    documents, invoices, change_orders, ai, etc. land as
                    those features are built)
alembic/            Database migrations
tests/unit/         Fast, isolated tests
tests/integration/  Tests against a real database
docs/product/       Product vision, requirements, customer persona
docs/architecture/  System architecture and diagrams
```

## License

Proprietary — all rights reserved. Not open source.