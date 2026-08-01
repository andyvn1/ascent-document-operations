# API Specification — Ascent Document Operations

> Draft v0.1. Initial endpoint list satisfying `docs/product/requirements.md`
> FR1–FR10. Implementation is FastAPI (TASK-010+); this document defines
> the surface, not the code. Request/response bodies are illustrative, not
> final Pydantic schemas.

## Conventions

- All endpoints are under `/api/v1`.
- All endpoints require an authenticated request; the tenant is derived
  from the auth context, never from a client-supplied parameter — this is
  what makes tenant scoping (FR10) enforceable at the framework level
  rather than something each handler has to remember.
- List endpoints are paginated (`?page=`, `?page_size=`) and return a
  consistent envelope: `{ "items": [...], "page": 1, "page_size": 20,
  "total": 42 }`.
- Errors return `{ "error": { "code": "...", "message": "..." } }` with an
  appropriate HTTP status.
- Authentication itself (login, tokens) is a placeholder until TASK-015;
  every endpoint below assumes it already exists.

## Endpoints

### Health

```
GET /healthz
```
No auth required. Returns `{ "status": "ok" }`. Used by deployment health
checks (NFR-adjacent, not a product feature).

### Documents — intake (FR1, FR2)

```
POST /api/v1/documents
```
Multipart upload of a single PDF. Creates a `documents` row with
`status=uploaded`, stores the file via the object-storage interface,
enqueues a processing job, and writes an `uploaded` audit event.

Response: `201 Created` with the document's id and initial status.

```
GET /api/v1/documents
```
Lists documents for the current tenant. Query params: `status`,
`document_type`, `page`, `page_size`. This is the review-queue endpoint
(FR5, TASK-022) once documents reach `in_review`, but also usable to see
documents at any stage.

### Documents — detail & correction (FR3–FR7)

```
GET /api/v1/documents/{id}
```
Returns the document, its classification, all extracted fields (with
confidence and correction state), and typed invoice/change-order data if
present. `404` if the document doesn't belong to the caller's tenant —
never `403`, to avoid confirming another tenant's document IDs exist.

```
PATCH /api/v1/documents/{id}/fields/{field_name}
```
Body: `{ "corrected_value": "..." }`. Sets `corrected_value` and
`is_corrected=true` on the matching `extracted_fields` row, and writes a
`field_corrected` audit event containing the old and new value. Only
allowed while the document is `in_review` — correcting a field on an
already-approved/exported document is rejected with `409 Conflict`.

```
POST /api/v1/documents/{id}/approve
```
Only allowed from `in_review`. Sets `status=approved`, writes an
`approved` audit event with the acting user, and is the **only** code path
that makes the document eligible for export (FR6). No other endpoint or
background process may set this status.

```
POST /api/v1/documents/{id}/reject
```
Body: `{ "comment": "..." }` (required — FR6). Sets `status=rejected` and
writes a `rejected` audit event including the comment.

### Documents — audit trail (FR7)

```
GET /api/v1/documents/{id}/audit
```
Returns the full, chronologically ordered `audit_events` history for a
document — every transition and correction, never filtered or summarized
in a way that hides an event.

### Export (FR8, FR9)

```
GET /api/v1/documents/{id}/export.csv
```
Only allowed for `status=approved` documents. Returns a single-row CSV.
Sets `status=exported` and writes an `exported` audit event on success.

```
POST /api/v1/webhooks
GET /api/v1/webhooks
```
Register/list webhook endpoints for the tenant (URL + secret for signing).
Actual delivery on approval is a background job (TASK-026), not
synchronous with the approve call.

## What's intentionally not here yet

- Email-attachment intake endpoints — deferred non-goal per
  requirements.md.
- Any accounting/ERP-specific integration endpoints — only the generic
  webhook + mock adapter interface exist in the MVP.
- User/tenant management endpoints (invite users, create tenant) — needed
  eventually, but not blocking the document-processing loop this API
  spec exists to define.
- Billing endpoints — pricing is a plan, not implemented billing.

## Open question

Should `PATCH /documents/{id}/fields/{field_name}` accept multiple field
corrections in one request (batch correction) instead of one field at a
time? One-at-a-time is simpler to audit (one event per correction) but
could mean more round-trips for a reviewer correcting several fields at
once. Revisit once TASK-023 builds the actual correction UI and this
becomes a real usability question instead of a hypothetical one.

---

## Week 1 review against `docs/product/requirements.md`

Checking this week's output (persona, vision, MVP requirements, cloud
architecture, and this schema/API design) against the functional and
nonfunctional requirements before calling Week 1 done:

| Requirement | Addressed by |
|---|---|
| FR1 upload → queue visibility | `documents` table + `POST /documents`, `GET /documents` |
| FR2 classify before extraction | `documents.document_type`, set before `invoice_data`/`change_order_data` populated |
| FR3 extract with confidence | `extracted_fields.confidence` |
| FR4 flag missing/invalid fields | `extracted_fields` + typed tables enable required-field and numeric-reconciliation checks (implementation is TASK-018–019) |
| FR5 reviewer view + correct + approve/reject | `GET /documents/{id}`, `PATCH .../fields/{field_name}`, `POST .../approve`, `POST .../reject` |
| FR6 only approval releases data; reject requires comment | enforced by endpoint design (`approve` is the sole status-setter; `reject` requires `comment`) |
| FR7 every transition/correction audited, never overwritten | `audit_events` (append-only) + `extracted_fields` keeping `extracted_value` distinct from `corrected_value` |
| FR8 CSV export | `GET /documents/{id}/export.csv` |
| FR9 signed webhook w/ retry | `POST/GET /webhooks` (registration); delivery mechanics are TASK-026 |
| FR10 tenant-scoped, no cross-tenant leak | `tenant_id` on every table; auth-derived tenant context, never client-supplied, on every endpoint |
| NFR1 retries on failed jobs | Deferred to worker implementation (TASK-014); schema doesn't block it |
| NFR2 upload validation, secrets via env | Deferred to TASK-013 implementation; schema doesn't block it |
| NFR3 append-only audit | `audit_events` design (no update/delete path) |
| NFR4 latency | Not addressed by schema/API — depends on TASK-017's real provider, as already flagged in requirements.md |
| NFR5 mockable external services | `AIProvider` protocol (ADR-0002) keeps this schema/API provider-agnostic |
| NFR6 provider portability | Same — nothing in this schema assumes a specific AI provider |

**Gaps carried forward, not blocking Week 1 close-out:** NFR1/NFR2/NFR4
depend on worker and provider implementation (Weeks 3–4), not on schema or
API shape — correctly out of scope for this task.

**Non-goals check:** nothing designed here adds email intake, ERP-specific
integrations, local AI inference, other document types, or billing —
consistent with `requirements.md`'s non-goals list.

---

## Week 3 review against `docs/product/requirements.md`

Checking Week 3's output (Postgres + migrations + tenant/user models,
document/audit models, the upload endpoint, the job queue/worker, and the
auth placeholder/tenant scoping added this task) against the requirements
this phase was meant to satisfy:

| Requirement | Addressed by |
|---|---|
| FR1 upload → appear in a processing queue | `POST /api/v1/documents` creates the `Document` row and enqueues a `jobs` row in the same transaction |
| FR10 all data access scoped to the authenticated tenant | `get_current_actor` derives `tenant_id` from a verified `User` lookup (never a client-supplied value); `list_audit_events` now requires `tenant_id` as a mandatory, keyword-only filter |
| NFR1 failed jobs retry with backoff | `apps/worker/main.py` + `jobs/queue.py` (`fail_job`, exponential backoff, max-attempts) — built in TASK-014 |
| NFR2 upload validation; secrets via env | content-sniffing (`_detect_content_type`) + size limit in `documents.py`; `Settings` loads from environment (TASK-010) |
| NFR3 append-only audit | `AuditEvent`/`_record_event` — no update/delete path (TASK-012) |
| NFR5 mockable external services, real DB in integration tests | integration tests hit a real test Postgres via `conftest.py`'s SAVEPOINT fixture; no paid API calls exist yet to mock |

**Gap closed this task:** the authentication placeholder was the one
concrete gap flagged back in the Week 1 review (FR10 depended on an
auth-derived tenant context that didn't exist yet). `test_upload_flow.py`
now also proves an unauthenticated request produces zero side effects
(no `Document` row, no `Job` row) rather than only checking the HTTP
status code.

**Carried forward, not blocking Week 3 close-out:** FR2–FR9 (classification,
extraction, review, export, webhooks) are Week 4–6 scope, not Week 3's —
correctly out of scope here.