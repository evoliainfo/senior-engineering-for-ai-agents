# RC-1 pre-implementation frozen gates

This directory freezes candidate-specific evaluation inputs **before any RC-1 runtime implementation**.

- `negative_controls/`: 12 R0/R1 lexical near-miss controls covering all six proposed concept families. Candidate work must introduce no new specialist security/data/supplier route on these controls relative to the frozen v1.4 baseline.
- `metamorphic/`: 12 intent-preserving variants, arranged as six pairs. Each pair expresses the same governed concept using a currently explicit/specialist form and an ordinary morphological/compositional form.

These are visible development gates, not held-out CHALLENGE evidence. They must not be rewritten to accommodate candidate behavior. If a contract is later found invalid, reclassification requires a separate documented review before candidate results are interpreted.

No file in this directory changes SEF behavior.
