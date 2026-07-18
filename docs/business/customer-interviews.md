# Customer Workflow Map & Interview Questions

> Draft v0.1. The workflow map below refines the first-pass version from
> `docs/product/customer-persona.md` — treat every `[ASSUMPTION]` as something
> to confirm or correct during the actual interview, not a fact.

## End-to-end manual workflow (current state)

1. **Arrival** — Invoice or change order arrives by email attachment,
   fax/scan, or physical mail.
2. **Triage** — Someone (office manager/bookkeeper) opens it, identifies
   which project/PO it belongs to, and decides who needs to see it.
3. **Manual entry** — The person retypes vendor, amounts, dates, and line
   items into a spreadsheet or the accounting system's entry screen.
4. **Cross-check** — They compare the document against the original PO or
   contract, often by searching email threads or a shared drive folder.
5. **Exception handling** — If something doesn't match (missing PO number,
   total doesn't reconcile, change order has no approver signature), they
   email or call around to chase down the missing piece. `[ASSUMPTION]`
   This step is the single biggest time sink and the most common source of
   payment delays.
6. **Approval** — A project manager or owner signs off, often verbally or
   via a forwarded email rather than a logged approval.
7. **Posting** — Final numbers are keyed into the accounting/ERP system.
8. **Filing** — The source document is filed (physical folder or a shared
   drive), frequently disconnected from the data that was entered from it.

## Expected business savings (to validate, not assume)

`[ASSUMPTION]` Based on the workflow above, a company processing 20–30
documents/week at roughly 8–12 minutes of manual entry + exception-handling
time per document is spending on the order of 3–6 hours/week on this task
alone, concentrated in one or two people.

`[ASSUMPTION]` The bigger cost may not be the data-entry time itself but the
downstream cost of errors: duplicate payments, missed change-order
approvals, and disputed invoices that take far longer to resolve than the
original entry would have taken.

These are placeholders — replace with real numbers from the interview below.

## Interview questions

### Warm-up / context
1. Walk me through what happens, step by step, from the moment an invoice or
   change order lands in your inbox to the moment it's fully processed.
2. Roughly how many invoices and change orders do you handle in a typical
   week?
3. Who actually does the data entry today? Is it always the same person?

### Pain points
4. What's the most annoying or time-consuming part of that process?
5. Can you remember the last time something went wrong — a duplicate
   payment, a missed approval, a disputed total? What happened?
6. How do you currently catch (or fail to catch) duplicate invoices?
7. When a change order is missing an approval or supporting document, what
   happens next?

### Value / willingness to pay
8. If this process took half as long, what would that change for your team?
9. Have you looked at any tools to help with this before? What happened?
10. What would make you trust a system enough to rely on its output instead
    of double-checking everything by hand?

### Pilot fit
11. Would you be open to trying this on a subset of your real documents
    before committing to anything long-term?
12. What accounting or project-management software do you currently use?
    (Determines export/integration priority.)
13. Who would need to sign off internally before adopting something like
    this?

## What to do with the answers

After the interview, update:
- The workflow map above (replace assumptions with what was actually said).
- `docs/business/pricing.md` savings estimate.
- `docs/product/customer-persona.md` if the target segment needs correcting.
