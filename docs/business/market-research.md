# Market Research — Ascent Document Operations

> Draft v0.2. Replaces the live-interview approach from v0.1 with desk
> research: published industry statistics, competitor reviews, and case
> studies. This is deliberately not a substitute for talking to a real
> prospect — it's what's used instead, for now. Where research didn't
> settle a question, it's listed as still open, not blocking.

## End-to-end manual workflow (current state, still a model)

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
   email or call around to chase down the missing piece. Published
   research backs this up as a major friction point (see change-order
   findings below), though the exact ranking of "biggest" time sink for a
   specific company is still a modeling choice, not a measured fact.
6. **Approval** — A project manager or owner signs off, often verbally or
   via a forwarded email rather than a logged approval.
7. **Posting** — Final numbers are keyed into the accounting/ERP system.
8. **Filing** — The source document is filed (physical folder or a shared
   drive), frequently disconnected from the data that was entered from it.

## Workflow & pain points (sourced)

- 86% of small and midsize businesses still manually enter invoice data.
- In construction specifically, 57% of invoice data is still manually
  entered from paper documents.
- 56% of respondents spend more than 10 hours/week processing invoices and
  administering supplier payments; manual processing runs roughly 12–15
  minutes per invoice once every task (receiving, entry, approval routing,
  filing) is counted, at a clip rate of about 5 invoices/hour for the entry
  step alone.
- Nearly 60% of workers estimate they could save six or more hours/week if
  repetitive data-entry tasks were automated; McKinsey estimates ~69%
  automation potential for data-processing tasks generally.
- Change orders: manual, fragmented processes (paper forms, scattered email
  threads, no audit trail) are consistently cited as the driver of approval
  delays and disputes. Common failure modes: unclear or incomplete change
  order requests, unauthorized work performed before formal approval, and
  disputes over scope/pricing when documentation is thin.
- Duplicate invoices: industry-wide, about 1.29% of processed invoices are
  duplicates, averaging ~$2,034 each; duplicate/erroneous disbursements run
  roughly 0.8–2% of annual spend across companies generally.

## Competitor signal (sourced)

**inBuild** (Capterra reviews): well-liked for ease of use and QuickBooks
Online integration. Used by office managers, project managers,
coordinators, bookkeepers, and finance leads at small/mid-size *cost-plus
builders* — this matches the target persona in
`docs/product/customer-persona.md` closely, which is a useful signal that
the persona is a real, already-served segment rather than an invented one.
Complaints: occasional site lag/reliability issues, and the AI extraction
sometimes pulls the wrong information from emails or fails to populate
invoice fields accurately.

**Factura.ai** (G2 + company site): markets 90% coding accuracy without
human intervention and sub-1-minute processing per invoice; per-location or
per-invoice pricing with no per-seat charges. Praised for ease of use and
support; main complaint is an upfront learning curve/setup time to train
the system per vendor's invoice format.

## What this confirms or changes vs. the original assumptions

- **Confirms** the core problem: manual invoice/change-order handling is a
  large, well-documented burden industry-wide, not a niche complaint.
- **Confirms** the persona: inBuild's own reviewed customer base (office
  managers/bookkeepers/PMs at small-mid cost-plus builders) matches
  `docs/product/customer-persona.md`'s target almost exactly.
- **Sharpens** the differentiation angle: inBuild's reviews show real users
  hitting AI-accuracy problems with no clear mention of a confidence-scored,
  mandatory human-review step. That's a concrete, evidenced gap Ascent's
  hard product rule (never auto-approve) can point to directly, not just a
  hypothetical advantage.
- **Adds a second pricing pattern to consider**: Factura.ai's no-per-seat,
  per-location/per-invoice model is a real alternative to inBuild's flat
  rate. `docs/business/pricing.md` currently anchors mainly on inBuild;
  worth keeping Factura.ai's model in view if a prospect pushes back on
  flat-rate pricing.

## Still open (desk research can't resolve these)

- Exact document-volume distribution for the target company size band —
  published stats are industry-wide, not segmented by the $2M–$50M revenue
  range specifically.
- What accounting/ERP systems are most common among companies that do
  *not* yet have automation (inBuild's reviewed customers are already
  QuickBooks-integrated, which may not represent the harder, less-tooled
  segment Ascent is targeting).
- Actual willingness to pay at Ascent's specific price points — industry
  stats establish the problem is real and costly, not what a given prospect
  would actually pay to solve it.

These stay open until a real pilot conversation happens organically — they
are not a blocker to continuing MVP work.

## Sources

- [59 Accounts Payable Statistics for 2026 — DocuClipper](https://www.docuclipper.com/blog/accounts-payable-statistics/)
- [True Cost of Manual Data Entry in 2026 — Parsli](https://parsli.co/blog/true-cost-manual-data-entry-2026)
- [Manual Data Entry Costs U.S. Companies $28,500 Per Employee Each Year — Parseur](https://parseur.com/blog/manual-data-entry-report)
- [13 Invoice Processing Stats: Manual vs. Automation — Resolve](https://resolvepay.com/blog/13-statistics-that-quantify-cost-per-invoice-in-manual-vs-automated-flows)
- [How to manage accounts payable in construction: Complete guide — ApprovalMax](https://blog.approvalmax.com/accounts-payable-in-construction)
- [5 steps to keep change orders from becoming disputes — Construction Dive](https://www.constructiondive.com/news/5-tips-prevent-change-orders-become-disputes-construction/653271/)
- [The Ultimate Guide to Construction Change Orders — Siteline](https://www.siteline.com/blog/the-ultimate-guide-to-construction-change-orders)
- [Why Specialty Contractor Change Orders Take So Long to Get Paid — ClearStory](https://www.clearstory.build/construction-blog/specialty-contractor-change-order-payment-delays)
- [Avoid Duplicate Payments in Accounts Payable — AvidXchange](https://www.avidxchange.com/blog/duplicate-payments-ap-processing-guide/)
- [Duplicate Invoices: What They Are & How to Prevent Them — Ramp](https://ramp.com/blog/accounts-payable/duplicate-invoices)
- [inBuild Reviews — Capterra](https://www.capterra.com/p/266078/inBuild/reviews/)
- [Factura.ai Reviews — G2](https://www.g2.com/products/factura-ai/reviews)
- [Best Invoice Processing Software for Construction Companies — Factura.ai](https://factura.ai/invoice-processing-software-construction-companies/)
