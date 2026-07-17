# Customer Persona — Ascent Document Operations

> Draft v0.1. Assumptions below are marked `[ASSUMPTION]` — confirm or correct
> before this feeds Day 2 (customer interviews) or any architecture decision.

## Who

**Small to midsize construction companies and subcontractors** who receive a
steady stream of paper/PDF invoices and change orders from vendors, suppliers,
and subs, and currently process them by hand.

`[ASSUMPTION]` Target segment: general contractors and subcontractors in the
$2M–$50M annual revenue range, with no dedicated document-processing software
already in place (they use email, spreadsheets, and their accounting package's
manual entry screen).

`[ASSUMPTION]` Primary buyer/user: an office manager, bookkeeper, or project
coordinator — not the owner, and not a professional accountant. This person is
non-technical, time-constrained, and evaluated on accuracy and speed, not on
technology adoption.

## Current manual workflow (first pass — validate on Day 2)

1. Invoice or change order arrives by email attachment or physical mail/scan.
2. A person opens the PDF, reads it, and manually types the key fields into a
   spreadsheet or accounting system.
3. They cross-check the amount against the original PO or contract, often by
   searching email or a shared drive.
4. If something looks wrong (missing PO number, mismatched total, no
   approver signature on a change order), they email around to chase it down.
5. Once satisfied, they key the final numbers into the accounting/ERP system
   and file the source document.

`[ASSUMPTION]` This is done multiple times per day across a stack of
documents that arrive in bursts (e.g., end of week, end of month), not evenly
throughout the day — meaning backlogs and rushed data entry are common
failure points.

## Problems this persona has today

**Invoice processing:**
- Manual data entry from PDFs is slow and error-prone (wrong totals, wrong
  vendor, transposed numbers).
- No consistent audit trail of who approved what and when.
- Duplicate invoices from the same vendor go undetected until a double
  payment is caught (or isn't).

**Change orders:**
- Change orders arrive in inconsistent formats from different subs/vendors.
- Missing approvals or missing schedule-impact information isn't caught
  until it becomes a dispute later.
- No single place to see a change order's status (requested → approved →
  applied to contract).

## What this persona is buying

Per the master plan: not "AI," but outcomes —

- Less manual data entry
- Fewer costly mistakes (wrong totals, duplicate payments)
- Faster turnaround so approvals don't bottleneck a project
- An audit trail they can point to if a vendor disputes a payment

## Non-customers (explicitly out of scope for now)

`[ASSUMPTION]` Enterprise general contractors with existing ERP-integrated
document processing (e.g., Procore, Sage 300 CRE add-ons) are not the initial
target — they already have tooling and longer sales cycles. The initial
wedge is companies with **no existing automation**, where the alternative is
a human retyping a PDF.

---

## Open questions for Day 2 customer interviews

- Is the $2M–$50M revenue band correct, or does the pain look different at a
  smaller/larger scale?
- Who actually keys in the data today — is it always an office
  manager/bookkeeper, or does it vary by company size?
- How many invoices/change orders per week is typical? This determines
  whether the ROI story is "saves an hour a day" or "saves a full-time role."
- What accounting/ERP system(s) do they already use? This affects the export
  integration priority list.
