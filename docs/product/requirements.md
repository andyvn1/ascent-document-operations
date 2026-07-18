# MVP Requirements — Ascent Document Operations

> Draft v0.1. Scope is derived from `docs/product/product-vision.md` and the
> master plan. `[ASSUMPTION]` marks anything worth double-checking against
> pilot-customer reality once TASK-002's interviews happen.

## MVP features (in scope)

1. **Document intake** — upload a PDF (invoice or change order) through the
   application. Email-attachment intake is explicitly deferred (see
   non-goals) — manual upload is enough to prove the extraction/review loop.
2. **Classification** — determine whether an uploaded document is an
   invoice, a change order, or unrecognized.
3. **Extraction** — pull the structured fields listed in
   `docs/product/product-vision.md` for whichever document type was
   classified, each with a confidence score.
4. **Validation** — check required fields are present, numeric fields
   reconcile (e.g. subtotal + tax = total), and flag likely duplicate
   invoices.
5. **Human review** — a reviewer sees extracted fields side-by-side with
   the source document, can correct any field, and explicitly approves or
   rejects the document. Nothing is released downstream without this step.
6. **Audit trail** — every state transition (uploaded → processing →
   extracted → in_review → approved/rejected → exported) and every field
   correction is recorded and never overwritten.
7. **Export** — approved documents can be exported as CSV. Webhook delivery
   is included per the roadmap (Week 6) but is still MVP-in-scope, since a
   pilot customer may want to push data into their own system.
8. **Multi-tenant foundation** — even with a single pilot customer, every
   query is tenant-scoped from day one, because retrofitting tenant
   isolation later is far riskier than building it in from the start.

## Non-goals (explicitly out of scope for the MVP)

- **No auto-approval, ever.** Restated from the product vision because it's
  the one rule every other requirement must respect.
- **No email-attachment intake yet** — manual upload only for MVP; email
  intake is Week 6 per the roadmap, not MVP-blocking.
- **No accounting/ERP integrations beyond CSV + generic webhook** — no
  QuickBooks/Sage/Procore-specific adapters in the MVP. A mock accounting
  integration exists to prove the adapter interface, not a real one.
- **No local AI inference** — cloud AI providers only until the cloud MVP
  is proven (master plan §4, §13).
- **No other document types** — no purchase orders, quotes, inspection
  reports, receipts, or delivery documents, even though the persona
  encounters them. Invoices and change orders only.
- **No other future products** — distributor PO automation,
  property-management workflows, RFP assistant, accounting document
  intake, support document assistant, and email-to-workflow automation are
  all explicitly deferred (master plan §3). The architecture must not
  block them, but none of them get built now.
- **No billing/payment processing** — pricing exists as a plan
  (`docs/business/pricing.md`), not as an implemented billing system, in
  the MVP.
- **No mobile app** — web dashboard only.

## Functional requirements

- FR1: A user can upload a PDF document and see it appear in a processing
  queue.
- FR2: The system classifies the document type before attempting extraction.
- FR3: The system extracts all fields defined in the product vision for the
  classified document type, each with a confidence score.
- FR4: The system flags missing required fields and fields that fail
  validation (numeric mismatch, likely duplicate).
- FR5: A reviewer can view extracted fields against the source document,
  edit any field, and approve or reject the document.
- FR6: Approving a document is the only path that makes its data available
  for export; rejecting requires a comment.
- FR7: Every workflow transition and every field correction produces an
  audit event that is never deleted or overwritten.
- FR8: A reviewer can export approved documents as CSV.
- FR9: The system can deliver a signed webhook on document approval, with
  retry on failure.
- FR10: All data access is scoped to the authenticated tenant; no query can
  return another tenant's data.

## Nonfunctional requirements

- NFR1 (Reliability): A failed background job (extraction, webhook
  delivery) retries with backoff rather than silently dropping the
  document.
- NFR2 (Security): Uploaded files are validated for type and size before
  storage; secrets are loaded from environment variables, never hardcoded
  or logged.
- NFR3 (Auditability): Audit history is append-only; no code path may
  update or delete a past audit event.
- NFR4 (Latency): `[ASSUMPTION]` A single document should complete
  classification + extraction in well under a minute so a reviewer isn't
  left waiting mid-session — exact target to be set once a real cloud
  provider is wired up (TASK-017).
- NFR5 (Testability): External services (AI provider, object storage) are
  mocked in unit tests; integration tests may hit real local
  infrastructure (e.g. a test database) but not real paid APIs.
- NFR6 (Portability): AI inference is accessed only through the
  `AIProvider` protocol, so a future local AI provider can be substituted
  without changing business logic (master plan §4, §13).

## MVP acceptance criteria

The MVP is done when:

- [ ] A user can upload an invoice or change-order PDF and it is correctly
      classified.
- [ ] Extraction returns all fields defined for that document type with
      confidence scores, and missing/invalid fields are flagged.
- [ ] A reviewer can correct fields, and only an explicit approval action
      releases the document for export — verified with a test that no code
      path can mark a document approved without that action.
- [ ] Every workflow transition and correction has a corresponding audit
      event, verified by an audit-log test that checks append-only
      behavior.
- [ ] An approved document can be exported as CSV and delivered via a
      signed webhook.
- [ ] All of the above works correctly when two different tenants have
      documents in the system at the same time, with no cross-tenant data
      leakage.

## Open questions

- Is CSV + generic webhook actually sufficient for a first pilot, or does
  the pilot customer need a specific integration to consider this usable?
  (Depends on TASK-002 interview answers about their accounting/PM
  software.)
- Does NFR4's latency target need to be stricter if a reviewer processes
  documents in a batch, waiting on several at once?