# Database Design — Ascent Document Operations

> Draft v0.1. Covers the core MVP schema per `docs/product/requirements.md`
> (FR1–FR10) and the system boundaries from
> `docs/architecture/system-architecture.md`. Implementation (SQLAlchemy
> models, Alembic migrations) is TASK-011–012; this document defines the
> shape those tasks build.

## Design principles

1. **Every tenant-owned row carries a `tenant_id`.** No table holding
   customer data is exempt — a missing `tenant_id` filter on a query is
   treated as a security bug (AI.md §6).
2. **Audit is append-only.** `audit_events` is insert-only; nothing in this
   schema ever updates or deletes a past audit row.
3. **Extraction results are proposals, not facts**, until a human approves
   them — the schema keeps the AI's original output and the reviewer's
   corrected value as distinct fields, never overwriting one with the
   other.
4. **Workflow state lives on the document itself** as an enum, while every
   *transition* between states is a separate audit event — the current
   state is a projection, not the source of truth.

## Entity-relationship diagram

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    TENANT ||--o{ DOCUMENT : owns
    USER ||--o{ AUDIT_EVENT : performs
    DOCUMENT ||--o{ EXTRACTED_FIELD : has
    DOCUMENT ||--o{ AUDIT_EVENT : "is subject of"
    DOCUMENT ||--o| INVOICE_DATA : "classified as"
    DOCUMENT ||--o| CHANGE_ORDER_DATA : "classified as"

    TENANT {
        uuid id PK
        string name
        timestamp created_at
    }
    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string role
        timestamp created_at
    }
    DOCUMENT {
        uuid id PK
        uuid tenant_id FK
        uuid uploaded_by_user_id FK
        string original_filename
        string storage_key
        string document_type
        string status
        timestamp created_at
        timestamp updated_at
    }
    EXTRACTED_FIELD {
        uuid id PK
        uuid document_id FK
        string field_name
        string extracted_value
        float confidence
        string corrected_value
        boolean is_corrected
        timestamp created_at
    }
    INVOICE_DATA {
        uuid document_id PK_FK
        string vendor_name
        string invoice_number
        date invoice_date
        date due_date
        string project_name
        string customer_name
        string po_number
        decimal subtotal
        decimal tax
        decimal total
        string currency
        string payment_terms
    }
    CHANGE_ORDER_DATA {
        uuid document_id PK_FK
        string project_name
        string change_order_number
        date request_date
        string requesting_company
        string description
        string reason
        decimal requested_amount
        string schedule_impact
        string approver
        string status
        string related_contract_or_po
    }
    AUDIT_EVENT {
        uuid id PK
        uuid tenant_id FK
        uuid document_id FK
        uuid user_id FK
        string event_type
        json event_data
        timestamp created_at
    }
```

## Tables

### `tenants`
The isolation boundary. Every other table (except `audit_events`'s
system-level entries, if any) is scoped to a tenant.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| name | text | |
| created_at | timestamptz | |

### `users`
`[ASSUMPTION]` One user belongs to exactly one tenant for the MVP —
multi-tenant users (e.g. a consultant working across companies) are out of
scope until there's a real need.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| tenant_id | uuid, FK → tenants.id | |
| email | text, unique | |
| role | text | `[ASSUMPTION]` `reviewer` / `admin` for MVP; expand later |
| created_at | timestamptz | |

### `documents`
The central entity. `document_type` is set by classification;
`status` is the current workflow state.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| tenant_id | uuid, FK → tenants.id | |
| uploaded_by_user_id | uuid, FK → users.id | |
| original_filename | text | |
| storage_key | text | pointer into object storage, not the file itself |
| document_type | text | `invoice` \| `change_order` \| `unrecognized` |
| status | text | `uploaded` → `processing` → `extracted` → `in_review` → `approved` \| `rejected` → `exported` |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `extracted_fields`
One row per extracted field, so confidence and correction tracking apply
uniformly regardless of document type — this is what lets FR3/FR4/FR7 work
without a different table shape per document type.

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| document_id | uuid, FK → documents.id | |
| field_name | text | e.g. `vendor_name`, `total` |
| extracted_value | text | raw AI output, never overwritten |
| confidence | float | 0.0–1.0 |
| corrected_value | text, nullable | set only by a reviewer action |
| is_corrected | boolean | |
| created_at | timestamptz | |

### `invoice_data` / `change_order_data`
Typed, queryable projections of the fields most likely to be filtered,
reported on, or joined against (e.g. "find all invoices from vendor X").
`extracted_fields` remains the audit-safe raw record; these tables are a
convenience layer populated once extraction completes, one row per
document, keyed by `document_id`.

`[ASSUMPTION]` Splitting into two typed tables (rather than one generic
`document_data` JSON blob) is chosen because the field sets are already
fully known and stable (product-vision.md), and typed columns make
duplicate-detection and validation queries (FR4) straightforward SQL
instead of JSON-path queries.

### `audit_events`
Append-only. Every workflow transition and every field correction
produces exactly one row here; nothing here is ever updated or deleted
(NFR3).

| Column | Type | Notes |
|---|---|---|
| id | uuid, PK | |
| tenant_id | uuid, FK → tenants.id | |
| document_id | uuid, FK → documents.id | |
| user_id | uuid, FK → users.id, nullable | null for system-generated events (e.g. classification completing) |
| event_type | text | e.g. `uploaded`, `classified`, `extracted`, `field_corrected`, `approved`, `rejected`, `exported` |
| event_data | jsonb | event-specific detail (e.g. which field changed, old/new value) |
| created_at | timestamptz | |

## Indexes (initial)

- `documents(tenant_id, status)` — powers the review queue (FR5, TASK-022).
- `documents(tenant_id, document_type)` — filtering by type.
- `extracted_fields(document_id)`.
- `audit_events(document_id, created_at)` — powers the audit timeline
  (TASK-025) in chronological order.
- `invoice_data(tenant_id, vendor_name, invoice_number)` — supports
  duplicate-invoice detection (FR4, TASK-019).

## Explicitly deferred

- Webhook delivery log table (TASK-026) — not needed until export/webhook
  work begins.
- Any billing/subscription tables — pricing is a plan, not implemented
  billing, per requirements.md non-goals.
- Full-text/embedding search tables — out of scope until AI provider work
  (TASK-016+) needs them.