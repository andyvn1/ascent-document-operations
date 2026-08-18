Synthetic invoices for evaluating extraction quality (TASK-019/020).

Each case is a pair of files sharing a basename:

- `<name>.txt` — synthetic invoice text, standing in for what a
  document's text-extraction/OCR step would produce. `extract_invoice`
  takes this as `document_text` directly.
- `<name>.expected.json` — ground truth: the fields an `InvoiceData`
  extraction of that text *should* produce, keyed identically to
  `InvoiceData`'s fields. Reflects what the document literally prints,
  even when the printed numbers don't reconcile (see
  `inconsistent-totals`) -- extraction should be faithful to the
  document, not "fix" it. Catching that mismatch is `validation.py`'s
  job, not extraction's.

Cases:

- `clean-full` — every field present, numbers reconcile.
- `missing-optional-fields` — only the required fields are on the
  document; everything else should extract as `null`.
- `inconsistent-totals` — subtotal + tax does not equal the printed
  total; exercises `numeric_inconsistencies`.
- `duplicate-a` / `duplicate-b` — the same invoice (vendor, invoice
  number, total) submitted twice with different formatting; exercises
  `find_duplicate`.
