# Product Vision — Ascent Document Operations

## One-line vision

Ascent Document Operations turns incoming construction invoices and change
orders into reviewed, approved, structured data — without anyone retyping a
PDF — while keeping a human in control of every approval.

## The problem

Construction companies and subcontractors receive invoices, change orders,
purchase orders, and related project documents by email and PDF. Employees
manually read these documents and copy the information into spreadsheets,
accounting systems, or project-management tools. This is slow, error-prone,
and leaves a weak audit trail (see `docs/product/customer-persona.md`).

## The product (first release)

A system that:

1. Accepts documents (PDF upload or email attachment).
2. Classifies each document (invoice vs. change order vs. other).
3. Extracts structured fields (see field lists below).
4. Validates the extraction and flags low-confidence or missing fields.
5. Presents the result to a human reviewer, who corrects and approves it.
6. Only after human approval, releases the data downstream (CSV export,
   webhook, future accounting integrations).

### Invoice fields extracted

Vendor name, invoice number, invoice date, due date, project name, customer
name, PO number, subtotal, tax, total, currency, payment terms, line items
(quantity, unit price, description, cost code).

### Change-order fields extracted

Project name, change-order number, request date, requesting company,
description, reason for change, requested amount, schedule impact, approver,
status, related contract/PO, supporting documentation.

## Hard product rule

The system **never auto-approves** payments, contracts, or legally
significant decisions. A human always reviews and approves before data is
released downstream. This is an architectural constraint, not a feature that
can be toggled off — see AI.md §6 and the human-approval-gate rule.

## What we are explicitly not building yet

- Distributor purchase-order automation
- Property-management workflows
- RFP / security-questionnaire assistant
- Accounting document intake (beyond invoices/change orders)
- Support document assistant
- Email-to-workflow automation

These are documented in the master plan as future products the architecture
must not block, but none of them are in scope for the MVP.

## Success looks like (first pilot)

`[ASSUMPTION — confirm against a real pilot customer]` A pilot customer
processing at least 20–30 invoices/change orders per week can:

- Cut manual data-entry time on those documents by more than half.
- Catch at least one error (duplicate invoice, missing approval, mismatched
  total) that would otherwise have gone through unnoticed.
- Trust the audit trail enough to use it in a vendor dispute.

## Why this customer, why now

Construction is a large, underserved market for this kind of automation:
paper-heavy, deadline-driven, and painful enough that a narrow, reliable tool
beats a broad, generic one. Winning a narrow niche first (invoices + change
orders for construction) is deliberately chosen over a horizontal "AI
document processor" positioning, because a specific customer can be found,
understood, and sold to — a generic one can't.
