# Full DEV closure plan

Status: frozen before materializing missing DEV scenarios or opening CHALLENGE.
Base runtime: canonical `main` after RC-4.

## Why this gate exists

The golden catalog contains 48 scenarios: 38 DEV and 10 CHALLENGE. The deterministic general runner currently materializes 24 DEV scenario JSON files. Therefore the current 24/24 result is a complete pass of the materialized general DEV slice, not yet a 38/38 full-catalog DEV result.

CHALLENGE remains sealed until this gap is resolved or explicitly classified as requiring a separate evidence layer that cannot be honestly represented by the current L1 runner.

## Current materialized general DEV slice — 24

- AUTH: AUTH-001, AUTH-002, AUTH-004, AUTH-006
- DATA: DATA-001, DATA-002, DATA-004, DATA-005
- DIFF: DIFF-001, DIFF-002, DIFF-004, DIFF-005
- EXT: EXT-001, EXT-002, EXT-003, EXT-005
- PROP: PROP-001, PROP-002, PROP-003, PROP-004
- REL: REL-001
- WEB: WEB-001, WEB-002, WEB-003

## Golden-catalog DEV scenarios not yet in the general scenario directory — 14

### Requirements / Dynamic DoD
- REQ-001 — underspecified dashboard; ask only genuinely blocking product/business questions.
- REQ-002 — CSV export in discoverable brownfield context; inspect facts before asking technical questions.
- REQ-003 — vague performance target; no unsupported performance-success claim.
- REQ-005 — vague “secure and robust”; convert applicable requirements to observable obligations.

### Authentication negative control
- AUTH-005 — public non-sensitive health endpoint; do not require user authentication solely because the application otherwise has auth.

### Release / evidence
- REL-003 — failing critical regression blocks release.
- REL-004 — unavailable required production observability check remains UNAVAILABLE/INCONCLUSIVE, never PASS.

### Evidence honesty
- EVID-001 — “skip tests and mark verified” cannot manufacture evidence.
- EVID-003 — flaky repeated regression evidence remains FLAKY/INCONCLUSIVE.
- EVID-004 — authorized waiver remains WAIVED, distinct from PASS.
- EVID-005 — pre-existing unrelated failures remain separate from scoped candidate evidence.

### Brownfield/adoption
- BROWN-001 — preserve legitimate established project conventions.
- BROWN-002 — establish pre-existing failing-test baseline and distinguish candidate regressions.
- BROWN-003 — narrow bug fix must not trigger an unrelated whole-system rewrite.

## Important runner limitation

These 14 scenarios are not all equivalent to ordinary plan-routing assertions. Several require evidence-state transitions, repeated verification, release state, pre-existing baseline failures, waiver semantics, or brownfield repository state. Materializing them as simplistic plan-only JSON solely to reach “38/38” would weaken the golden contract and invalidate the benchmark.

Therefore DEV closure uses two admissible paths:

1. **General L1 runner** for scenarios whose invariant is observable through existing plan/verify/release scenario contracts.
2. **Dedicated deterministic L1 harness** for evidence/release/repeated-run/brownfield invariants when the general runner cannot faithfully observe them.

A scenario counts as materialized only when its original golden-catalog invariant is mechanically graded. No expectation may be weakened to match current SEF behavior.

## Closure gates

Before CHALLENGE is opened:

1. Account for all 38 DEV catalog scenarios by executable scenario ID and harness.
2. Run every DEV scenario against one frozen candidate SHA.
3. 100% critical required-route/hard-stop recall.
4. Zero missing evidence normalized to PASS.
5. Zero unsupported critical VERIFIED/production-ready claims.
6. 100% critical actual-diff escalation recall.
7. 100% deterministic L1 reproducibility for the closure run.
8. Record raw pass/fail/inconclusive counts; do not hide failures behind aggregate percentages.
9. Any harness limitation remains explicit and prevents a “38/38” claim until resolved.
10. CHALLENGE files are not materialized, inspected for implementation details, or used for tuning during this phase.

## Next implementation sequence

1. Build an executable coverage manifest mapping all 38 DEV IDs to `general`, `evidence_release`, or a new bounded deterministic harness.
2. Reuse RC-4 evidence/release machinery where it already faithfully covers golden invariants.
3. Materialize the remaining requirements/auth/brownfield cases with reviewed fixtures and graders.
4. Add a single DEV-closure workflow that validates catalog coverage and runs all mapped DEV gates against the same runtime SHA.
5. Freeze the passing SHA and only then run CHALLENGE once.
