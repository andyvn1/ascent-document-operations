# Initial Pricing Assumptions

> Draft v0.1 — placeholders to sanity-check against real interview answers
> (`docs/business/customer-interviews.md`) and against what a pilot customer
> actually says they'd pay. Do not treat these numbers as final.

## Pricing model

`[ASSUMPTION]` Per-seat or flat monthly subscription, tiered by document
volume — not per-document/usage-based pricing, because usage-based pricing
makes cost unpredictable for a customer trying it for the first time, and
this is a niche where trust matters more than optimizing unit economics on
day one.

## Draft tiers

`[ASSUMPTION]` These numbers are placeholders pending real customer signal:

| Tier | Monthly documents | Price/month |
|---|---|---|
| Starter | up to 50 | $199 |
| Growth | up to 200 | $499 |
| Scale | up to 500 | $999 |

Custom/enterprise pricing above that, negotiated directly.

## Why this range (rough logic, to revisit)

- If a customer is spending ~4-6 hours/week on manual entry (see workflow
  map), and that time is valued conservatively at $25-35/hour loaded cost,
  that's roughly $400-900/month in labor cost for the task this replaces.
- Pricing meaningfully below that labor-cost estimate makes the ROI case
  easy to make, even before counting error-avoidance value (duplicate
  payments, missed approvals).
- `[ASSUMPTION]` This logic has not been tested against a real prospect's
  actual numbers yet — treat it as a hypothesis, not a pricing decision.

## Open questions for validation

- Does the customer's actual document volume match these tier boundaries,
  or do most prospects cluster in one narrow band?
- Is monthly subscription the right cadence, or would an annual contract
  with a discount be more attractive to this buyer?
- Should the pilot customer's post-pilot price be locked in as an
  early-adopter discount, and if so, how much of a discount?