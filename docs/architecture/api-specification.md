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
`document_type`, `min_confidence`, `max_confidence`, `page`, `page_size`.
This is the review-queue endpoint (FR5, TASK-022) once documents reach
`in_review`, but also usable to see documents at any stage.

`[ASSUMPTION]` `min_confidence`/`max_confidence` filter on `documents.confidence`
-- a single, document-level score (TASK-022), not the per-field confidence in
`extracted_fields`. It's nullable and unpopulated until extraction is wired
into the processing pipeline (still a gap as of TASK-022 — see
`documents/processing.py`), so a document with no score yet is correctly
excluded by either bound (SQL `NULL >= x` is neither true nor false).

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

---

## Week 4 review against `docs/product/requirements.md`

Checking Week 4's output (`AIProvider` protocol + `MockProvider`, the OpenAI-
backed `CloudProvider`, invoice classification/extraction, confidence
scoring/duplicate detection, and the extraction-quality evaluation added
this task) against the requirements this phase was meant to satisfy:

| Requirement | Addressed by |
|---|---|
| FR2 classify before extraction | `classify_document()` gates `extract_invoice()` — raises `NotAnInvoiceError` before any extraction call is made if the document isn't classified as an invoice |
| FR3 extract all fields with a confidence score, per document type | `InvoiceData` covers every invoice field from the master plan; `score_invoice_fields()` gives every field a confidence score. Invoices only this week — change orders are TASK-021 (Week 5), correctly out of scope here |
| FR4 flag missing/invalid fields, numeric mismatch, likely duplicates | `extract_invoice()` returns `missing_required_fields`; `numeric_inconsistencies()` cross-validates subtotal+tax=total and line-item sums; `find_duplicate()` matches on vendor+invoice#+amount |
| NFR1 failed jobs retry with backoff | Extends to the model-call level this week: `CloudProvider` configures the OpenAI client's own retry/timeout handling (TASK-017), on top of the job-level retry already built in TASK-014 |
| NFR2 secrets via env, never logged | `OPENAI_API_KEY` loads through `Settings` (pydantic-settings) from `.env`, never hardcoded; `CloudProvider`'s usage logging records token counts and cost, never the key itself |
| NFR4 latency | `[ASSUMPTION]` resolved: the TASK-020 evaluation ran 5 documents (10 real `gpt-5-nano` calls: classify + extract each) in 89s total, ~9s/call — comfortably under a minute per document even with margin for larger invoices |
| NFR5 external services mocked in unit tests, real paid APIs never in default CI | `test_invoice_evaluation.py` is `skipif`-gated on `AI_PROVIDER=cloud` + a real key being configured, so it never runs (or costs money) in a default `pytest` invocation; every other AI-touching test uses `MockProvider` or a fake client |
| NFR6 AI accessed only through `AIProvider`, swappable without touching business logic | Confirmed working, not just designed: `extraction.py`/`validation.py` import only `AIProvider`, never `openai`; swapping `MockProvider` ↔ `CloudProvider` is a one-line config change (`AI_PROVIDER`) |

**Evaluation findings (TASK-020):** the first real run against the 5
synthetic fixtures scored 96% (2 field mismatches out of 5 documents).
Both were reviewed and categorized before fixing anything:

- **Prompt problem:** `duplicate-b`'s dates were printed as US-format
  `03/11/2026`; the extraction prompt never said how to normalize dates,
  and the model mangled the ISO conversion. Fixed by adding an explicit
  date-normalization instruction to `_EXTRACTION_SYSTEM_PROMPT`.
- **Not a prompt or code problem — a bad fixture:** `missing-optional-fields`
  "failed" because the model returned one line item (just a description,
  no quantity/price) for a document whose only billing detail was a
  descriptive sentence with no item table. The extraction was correct; the
  TASK-019 ground truth wrongly assumed an empty `line_items` list. Fixed
  by correcting the fixture, not the code — the distinguishing question was
  "does the output match what a careful human would read off the
  document," not "does it match what I assumed when I wrote the fixture."

Re-running after both fixes: **100%** (0 mismatches across all 5 fixtures).

**Gap closed this task:** NFR4's latency target was an open `[ASSUMPTION]`
since the Week 3 review, explicitly deferred pending TASK-017. It's now
backed by a real measurement rather than a guess.

**Carried forward, not blocking Week 4 close-out:** extraction/validation
are not yet called from `documents/processing.py` — the job handler still
only moves a document `uploaded → processing → extracted` as a placeholder.
Wiring the real pipeline in, persisting `extracted_fields`/`invoice_data`,
and change-order extraction are Week 5 scope (TASK-021–024), not Week 4's.

---

## Week 5 review against `docs/product/requirements.md`

Checking Week 5's output (change-order classification/extraction, the
review queue API, the document detail/correction API and its
`extracted_fields` table, the approval/rejection workflow, and the
review dashboard UI) against the requirements this phase was meant to
satisfy:

| Requirement | Addressed by |
|---|---|
| FR3 extract all fields with confidence, per document type | `ChangeOrderData` (TASK-021) completes what Week 4 started for invoices only — both document types now extract fully |
| FR4 flag missing/invalid fields | Change orders add a signal invoices didn't need: `requires_approval_review` (TASK-021) is deliberately *not* folded into `missing_required_fields` — a missing approver is a normal pre-approval state, not an extraction defect, but still must hard-block auto-processing downstream |
| FR5 reviewer view + correct + approve/reject | `GET /api/v1/documents` (queue, TASK-022), `GET /api/v1/documents/{id}` + `PATCH .../fields/{field_name}` (detail/correction, TASK-023), `approve_document`/`reject_document` (TASK-024), and the dashboard UI (`apps/web/`, TASK-025) tying all of it together for a human |
| FR6 only approval releases data; reject requires comment | `approve_document` is the only function that sets `status=approved`, and requires a real `user_id` by construction (not optional, unlike `transition_status` elsewhere) — "no auto-approval" is enforced by the signature, not a convention. `reject_document` raises `MissingRejectionCommentError` on a blank comment |
| FR7 every transition/correction audited, never overwritten | `extracted_fields.extracted_value` is never overwritten — a correction only ever sets `corrected_value`/`is_corrected`, and `record_event()` (promoted from a private helper once `corrections.py` needed it too) writes an audit event for every correction and every approval/rejection |
| FR10 tenant-scoped, no cross-tenant leak | `ExtractedField` carries `tenant_id` directly, same as `AuditEvent` — not in the original database-design.md sketch, added to match that existing pattern so a query is a plain equality filter, not a join through `documents` |

**Gap closed this task:** TASK-022 flagged that `documents.confidence`
would sit `NULL` for every document until something populated it. The
dashboard (TASK-025) is the first thing to actually *read and display*
`extracted_fields.confidence` per field (highlighting anything under 0.5),
even though nothing populates either column from a real extraction run
yet — see the gap below.

**Two real bugs found building the dashboard, both fixed, both worth
recording:**

- Calling `db.rollback()` in a route's exception handler for a
  guard-clause exception (raised *before* any mutation) discards more
  than intended — in production it's merely redundant (`get_db`'s
  `finally: db.close()` already discards anything uncommitted when the
  request ends), but combined with the integration tests' SAVEPOINT-based
  session it silently wiped out the test's own setup data created earlier
  in the same test. Removed, matching `apps/api/routes/documents.py`'s
  `correct_document_field`, which never called it either.
- FastAPI/Starlette treats a required `Form(str)` field submitted as an
  **empty string** as *missing entirely* (confirmed with a minimal
  repro), returning a raw JSON 422 before the route body ever runs. For
  a browser-facing HTML route this is a real UX defect, not just an edge
  case: a reviewer submitting a blank rejection comment would see raw
  JSON instead of `reject_document`'s own rendered error page. Fixed by
  defaulting the field to `""` and letting the existing business-logic
  check (`MissingRejectionCommentError`) handle validation instead of
  relying on FastAPI's parameter validation for it.

**A real, named tradeoff from choosing server-rendered HTML + HTMX over a
React SPA (TASK-025's second learning objective):** the dashboard's
mutating routes (`apps/web/routes.py`) call `correct_field`/
`approve_document`/`reject_document` directly, in-process — not through
the JSON API (`apps/api/routes/documents.py`). That leaves two parallel,
slightly redundant route layers over the same business logic, rather than
the JSON API being the dashboard's only way to talk to the backend. A
React SPA would not have this redundancy (a browser-side JS app has no
way to call Python functions directly, so the JSON API would necessarily
be its only path in) — the one genuine overlap is `GET
/api/v1/documents/{id}/file`, which the dashboard's preview `<iframe>`
calls directly as a real HTTP request, same as any other client would.

**Carried forward, not blocking Week 5 close-out:**

- Extraction still isn't wired into `documents/processing.py` — the
  worker still only moves a document through placeholder status
  transitions. Nothing populates `extracted_fields` or
  `documents.confidence` from a real `extract_invoice`/
  `extract_change_order` run, and nothing yet turns an uploaded PDF's
  bytes into the `document_text` those functions expect. Flagged
  repeatedly since TASK-022; still open, no ticket currently owns it.
- The JSON API has no `POST /api/v1/documents/{id}/approve` or
  `.../reject` — `apps/web/routes.py` calls `workflow.py` directly
  instead. An external API client (as opposed to the dashboard) still
  has no way to approve or reject a document. Also flagged since
  TASK-024; no ticket currently owns this either.
- Real authentication (a verified-but-unauthenticated `X-User-Id`
  header or `user_id` cookie stands in for it) remains unbuilt, as it
  has been since TASK-015 — scanning the full remaining roadmap
  (TASK-026–030), no ticket builds it.