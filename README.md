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

**Foundation**
- A FastAPI backend with typed, environment-driven configuration and
  structured logging.
- PostgreSQL via SQLAlchemy 2.0 + Alembic migrations, with tenant isolation
  enforced at the schema level (every tenant-owned table carries a
  `tenant_id`).
- A Postgres-backed background job queue (`SELECT ... FOR UPDATE SKIP
  LOCKED` — no message broker needed at this scale) and a worker process
  that claims jobs, retries transient failures with exponential backoff,
  and gives up after a max-attempts limit.
- A file-upload endpoint that validates content by sniffing actual file
  bytes (never trusting the client's filename or `Content-Type` header),
  behind an `ObjectStorage` interface (local disk for now; a cloud backend
  is a drop-in replacement later).
- `Document` / `AuditEvent` models implementing an explicit workflow state
  machine (`uploaded → processing → extracted → in_review →
  approved/rejected → exported`) — every transition is recorded as an
  append-only audit event, never overwritten.

**AI provider layer**
- An `AIProvider` protocol (structured output, text generation, embeddings)
  that business logic depends on instead of any vendor SDK directly, plus a
  `MockProvider` for zero-cost, zero-network tests.
- A `CloudProvider` backed by OpenAI (`gpt-5-nano` by default, vision-capable
  for scanned documents), with request timeout/retry and per-request
  token/cost logging. Swapping providers is a one-line config change
  (`AI_PROVIDER=mock|cloud`), not a code change.

**Invoice & change-order extraction**
- Classification (is this an invoice, a change order, or unrecognized?)
  gates extraction — the expensive structured-output call only runs once a
  document's type is known.
- Full field extraction for both document types (`InvoiceData`,
  `ChangeOrderData`, matching every field in the product vision), with
  missing required fields flagged rather than silently defaulted.
- Change-order extraction treats a missing approver as a distinct signal
  from a missing field: it's a normal pre-approval state, not an extraction
  defect, but it still hard-blocks auto-processing downstream.
- Rule-based (not model-self-reported) per-field confidence scoring and
  numeric cross-validation for invoices (does subtotal + tax = total? do
  line items sum to the subtotal?), plus explainable duplicate-invoice
  detection (vendor + invoice number + amount).
- A real evaluation run against a synthetic invoice dataset — 100% field
  accuracy after one round of prompt fixes, gated behind a real OpenAI key
  so it never runs (or costs money) in default test runs.

**Review workflow**
- A review-queue API (`GET /api/v1/documents`) — paginated, filterable by
  status/document type/confidence, scoped to the requesting tenant by
  construction.
- A document detail API (`GET /api/v1/documents/{id}`) returning every
  extracted field with its confidence score, and a correction endpoint
  (`PATCH .../fields/{field_name}`) that never overwrites the original AI
  output — a correction and the value it replaced both stay on the record,
  and every correction produces an audit event.
- Approval/rejection logic (`approve_document`, `reject_document`) that is
  the only code path allowed to mark a document approved, requires a real
  human actor by construction (not an optional parameter), and requires a
  comment to reject.

**Not built yet:**
- The review dashboard UI (next up).
- HTTP routes for the approve/reject actions above (the underlying logic
  exists and is tested; nothing calls it over HTTP yet).
- Wiring extraction into the actual document pipeline — `extract_invoice`/
  `extract_change_order` exist and work, but the background worker's
  handler is still a placeholder that doesn't call them, and nothing yet
  converts an uploaded PDF's bytes into the text those functions expect.
- Real authentication (a verified-but-unauthenticated `X-User-Id` header
  stands in for it today), CSV export, webhooks, and email intake.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · Pydantic /
pydantic-settings · OpenAI SDK · jsonschema · uv · pytest · ruff · mypy
(strict) · Docker Compose

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

To exercise real AI extraction (instead of the free, offline `MockProvider`),
set `AI_PROVIDER=cloud` and `OPENAI_API_KEY=...` in `.env` — everything else
defaults sensibly (`gpt-5-nano`, 3 retries, 30s timeout).

## Running checks

```bash
make check   # ruff + mypy --strict + pytest
make fmt      # auto-format and auto-fix lint issues
make test     # pytest only
```

Integration tests (`tests/integration/`) run against a real PostgreSQL
database — start it first with `docker compose up -d db`, then
`uv run alembic upgrade head`. One test file
(`tests/unit/test_invoice_evaluation.py`) makes real, paid OpenAI calls and
is automatically skipped unless `AI_PROVIDER=cloud` and `OPENAI_API_KEY` are
both set — it never runs in a default `pytest` invocation.

## Project structure

```
apps/
├── api/              FastAPI application: entrypoint + routes
│   └── routes/       documents (upload, detail, correction), review (queue)
└── worker/           Background worker: claims and processes jobs
src/ascent/
├── ai/               AIProvider protocol, MockProvider/CloudProvider,
│                     structured-output schema shaping
├── documents/        Document/AuditEvent/ExtractedField models,
│                     repository, classification, corrections, approval/
│                     rejection workflow, object storage, processing handler
├── invoices/         Invoice schema, classification+extraction, validation
│                     (confidence scoring, duplicate detection)
├── change_orders/    Change-order schema, classification+extraction
├── jobs/             Postgres-backed job queue (models + queue logic)
├── security/         Tenant-scoping auth placeholder
└── shared/           Config, database setup, logging, base models
alembic/              Database migrations
tests/
├── unit/             Fast, isolated tests
├── integration/       Tests against a real database (shared fixtures
│                     in conftest.py)
└── fixtures/         Synthetic test documents, incl. invoice extraction
                      eval fixtures
docs/
├── product/          Product vision, requirements, customer persona
└── architecture/     System architecture, ADRs, database/API design
```

## License

See [LICENSE](LICENSE) — proprietary, all rights reserved. This repository
is public for portfolio/evaluation purposes only; it is not open source.
