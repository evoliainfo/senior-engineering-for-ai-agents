# RC-1 pre-implementation frozen gates

This directory freezes candidate-specific evaluation inputs **before any RC-1 runtime implementation**.

- `negative_controls/`: 12 R0/R1 lexical near-miss controls covering all six proposed concept families. Every control forbids all six RC-1 specialist outputs (`AUTHORIZATION`, `DATABASE_MIGRATION`, `WEBHOOK_TRUST`, `EXTERNAL_SUPPLIER`, `BACKGROUND_JOB`, `SEO_WEB_DISCOVERABILITY`) so a candidate cannot appear to improve by moving an over-route into another RC-1 family.
- `metamorphic/`: 12 intent-preserving variants, arranged as six pairs. Each pair expresses the same governed concept using a specialist/explicit form and an ordinary morphological/compositional form. For supplier and background-processing concepts, both v1.4 variants may fail because the current runtime lacks a reliable positive lexical anchor; these pairs test concept recall/equivalence rather than only morphology.

## Pre-freeze validity review

The 24 contracts were reviewed before runtime implementation and before final freeze.

Two issues were corrected at the contract level:

1. `NEG-003` originally contained a negated stored-data statement (`Do not change stored data`), which mixed RC-1 lexical discrimination with the separately confirmed RC-2 negation defect. It was rewritten as a pure content/layout move without database language.
2. Negative controls originally forbade only the family-specific target output. They were strengthened to forbid all six RC-1 outputs, matching the accepted architecture's over-routing budget and preventing cross-family false positives from escaping the gate.

No metamorphic request/expectation required semantic correction. All six pairs remain intent-equivalent for the governed concept they target.

These are visible development gates, not held-out CHALLENGE evidence. They must not be rewritten to accommodate candidate behavior. If a contract is later found invalid, reclassification requires a separate documented review before candidate results are interpreted.

No file in this directory changes SEF behavior.
