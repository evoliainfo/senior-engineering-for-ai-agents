# CHALLENGE pre-run lock — candidate 7302914e

Recorded before the first CHALLENGE execution.

## Frozen candidate
- commit: `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837`
- `sef.py` SHA-256: `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`
- DEV baseline: 38/38 deterministic PASS

## Holdout contract
Exactly 10 scenarios are admitted: `PROP-005`, `REQ-004`, `AUTH-003`, `AUTH-007`, `DATA-003`, `EXT-004`, `REL-002`, `WEB-004`, `DIFF-003`, `EVID-002`.

Six are critical: `AUTH-003`, `AUTH-007`, `DATA-003`, `EXT-004`, `DIFF-003`, `EVID-002`.

## Final static audit before execution
- runtime mutation: forbidden; workflow checks `sef.py` and `SHA256SUMS` against the frozen candidate;
- scenario accounting: 9 standard + 1 stateful = exactly 10;
- canonical procedure IDs checked against the frozen runtime route registry;
- `REL-002` static wiring corrected from non-canonical `docker-containers` to canonical `container-docker-engineering` before any candidate observation;
- `DIFF-003` predeclared initial `maximum: R1` is explicitly enforced by the one-shot challenge grader before execution;
- semantic obligations are graded across the public plan evidence surface rather than exact prose;
- harness failure (exit 2) invalidates the measurement and is not a candidate failure;
- a valid benchmark failure (exit 1) is the official candidate outcome and is preserved before any diagnosis.

## Reuse rule
The first valid harness execution is the official holdout result for this candidate. Once executed, these scenarios are contaminated for tuning a later candidate. Any runtime change after observing the result requires a rotated challenge set or an explicit contaminated-holdout limitation.

## Separate evidence class
Real L2 external-agent evidence remains `Codex: NOT_RUN`, `Claude: NOT_RUN`; reference-harness solvability is not counted as agent evidence.
