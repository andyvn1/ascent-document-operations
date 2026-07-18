# Initial Pricing Assumptions

> Draft v0.2 — now grounded in real competitor pricing data (below), but the
> tier boundaries and feature split are still `[ASSUMPTION]`s to sanity-check
> against the desk research findings (`docs/business/market-research.md`) and
> against what a pilot customer actually says they'd pay.

## Competitive landscape

| Tier | Players | Pricing |
|---|---|---|
| Extraction only (you get JSON, you build the rest) | Lido, Docsumo, Nanonets, Rossum, Textract | Lido ~$29/mo for 100 pages; DocuClipper ~$20/mo; AWS Textract ~$0.05/page; Docsumo from $299/mo (or $0.30/page); Rossum $300+/mo |
| Construction-specific AP | inBuild, Factura.ai, LiveCosts, Builderin | inBuild $299/mo flat (Essential tier, unlimited projects); Factura.ai from $50/location/mo (or per-invoice) |
| Enterprise AP suites | Stampli, AvidXchange, Vic.ai, Tipalti, Bill.com | Custom pricing, typically $500–$2,500/mo mid-market plus per-transaction fees. Tipalti, AvidXchange, Vic.ai often land at $25k–$40k in Year 1 including implementation |

## Where Ascent sits

Ascent is **not** an extraction-only API — the target buyer (an office
manager/bookkeeper at a $2M–$50M construction company, per
`docs/product/customer-persona.md`) cannot "build the rest" themselves.
That comp set matters mainly as a cost floor: raw extraction is commodity-
cheap (Textract at $0.05/page), so Ascent's price has to be justified by the
full workflow — classification, validation, human review, audit trail, and
change-order support that invoice-only tools skip — not by the extraction
step itself.

Ascent is also not an enterprise AP suite — that tier's $500–$2,500/mo (plus
$25k–$40k Year 1 deals with implementation) targets larger buyers with
procurement processes and dedicated AP staff, which is explicitly the
non-customer segment defined in the persona doc.

**The direct comp set is construction-specific AP** — inBuild and
Factura.ai. Both are aimed at the same non-technical construction buyer.
inBuild's flat-rate, unlimited-projects model ($299/mo) is notable: this
buyer strongly prefers a price they don't have to think about over metered
complexity. Factura.ai's per-location pricing suggests some construction
buyers do think in terms of number of sites/projects rather than raw
document volume.

## Revised draft tiers

`[ASSUMPTION]` Structure below undercuts inBuild's $299/mo entry point to
win price-sensitive first customers, while keeping a flat-rate feel (not
per-page metering) since that's what this buyer responds to:

| Tier | Monthly documents | Price/month |
|---|---|---|
| Starter | up to 75 | $149 |
| Growth | up to 300 | $299 |
| Scale | unlimited | $499 |

Custom/enterprise pricing above that, negotiated directly — but the
expectation is most target customers (per the persona's $2M–$50M revenue
band) fit inside Growth or Scale.

`[ASSUMPTION]` Positioning: Starter is priced to be an obvious "just try it"
decision (half of inBuild's flat rate). Scale is priced at or below
inBuild's single tier but removes the volume cap entirely, so a prospect
comparing the two sees equal or better value plus change-order support and
human-review audit trail that inBuild's listing doesn't advertise.

## Why this range (rough logic, to revisit)

- If a customer is spending ~4–6 hours/week on manual entry (see workflow
  map), and that time is valued conservatively at $25–35/hour loaded cost,
  that's roughly $400–900/month in labor cost for the task this replaces —
  every tier above is priced below that estimate.
- Anchoring against inBuild ($299/mo flat) keeps Ascent visibly competitive
  to a prospect who shops around, rather than requiring a values-based pitch
  from a standing start.
- `[ASSUMPTION]` This logic has not been tested against a real prospect's
  actual numbers, or against inBuild/Factura.ai's actual feature scope
  (only their pricing is known here) — treat it as a hypothesis, not a
  pricing decision.

## Open questions for validation

- Does the customer's actual document volume match these tier boundaries,
  or do most prospects cluster in one narrow band?
- Is monthly subscription the right cadence, or would an annual contract
  with a discount be more attractive to this buyer?
- Should the pilot customer's post-pilot price be locked in as an
  early-adopter discount, and if so, how much of a discount?
- What do inBuild and Factura.ai actually include at their price points
  (change orders? human review? audit trail?) — worth a closer look before
  finalizing how hard to lean on the "cheaper than inBuild" pitch.