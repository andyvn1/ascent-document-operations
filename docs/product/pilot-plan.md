# Pilot Plan — Ascent Document Operations

> Draft v0.1 — a strawman offer to bring into the first customer
> conversation and adjust based on their reaction, not a final term sheet.

## Goal of the pilot

Prove, on a real customer's real documents, that automated extraction +
human review is faster and more reliable than their current manual process
— without asking them to commit to anything long-term or risk their live
accounting workflow.

## What the pilot customer gets

- Processing of their real invoices and change orders (a defined batch or a
  fixed time window — see scope below) through the system.
- A human-reviewed, corrected, approved output for every document — nothing
  is auto-approved or auto-posted to their systems.
- A CSV export of the approved data they can compare against what they'd
  have entered manually.
- A short report at the end: documents processed, time saved (estimated),
  errors caught (if any).

## Scope

`[ASSUMPTION]` Pilot duration: 2–4 weeks.
`[ASSUMPTION]` Volume: up to 50 documents (invoices + change orders
combined), enough to be meaningful without requiring production-grade scale
yet.
`[ASSUMPTION]` Document intake: manual upload to start (email intake is a
later milestone per the roadmap), so the pilot doesn't depend on features
that don't exist yet.

## What the pilot customer needs to do

- Provide a batch of real (or recent historical) invoices/change orders,
  with personally/commercially sensitive data redacted if needed.
- Have one person available to review and approve extracted results in the
  dashboard.
- Give feedback at the end on accuracy and whether the time savings felt
  real.

## What "success" looks like

- Extraction accuracy on required fields is high enough that review time is
  clearly less than the current manual entry time.
- At least one exception (missing approval, potential duplicate, mismatched
  total) is caught that the customer confirms would have otherwise been
  easy to miss.
- The customer would be willing to pay for this going forward.

## Pricing during the pilot

`[ASSUMPTION]` Free or heavily discounted for the pilot window — the goal is
proof and feedback, not revenue, and asking for payment before the product
has proven itself to a first customer raises the bar for saying yes. See
`docs/business/pricing.md` for the intended post-pilot pricing.

## After the pilot

- If successful: convert to a paying customer at the standard (or
  early-adopter) pricing tier.
- If not successful: get specific feedback on what fell short (accuracy,
  missing features, workflow fit) and decide whether to iterate or look for
  a different pilot customer.