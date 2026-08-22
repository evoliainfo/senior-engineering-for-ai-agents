# RC-1 shadow invariants

1. Shadow observations are non-authoritative.
2. `routing_effect` is always `NONE` in this phase.
3. No shadow output is imported by `sef.py`.
4. Existing policy payload and `SHA256SUMS` remain unchanged.
5. Frozen negative/metamorphic contracts are not edited to fit detector behavior.
6. A visible-corpus PASS does not imply general semantic correctness.
7. Promotion requires a separate activation review and regression gate.
