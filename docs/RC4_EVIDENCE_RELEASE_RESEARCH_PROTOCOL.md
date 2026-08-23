# RC-4 Evidence / Release research protocol

Status: frozen before any canonical runtime change.
Base: `main@443a8a0c0fc1d55049f413d51c8a7e68cfcd6c8c`

## Correction note
The first draft of this protocol misstated the two residual RC-4 failures. The canonical root-cause analysis is authoritative. This revision corrects the protocol before any runtime candidate is integrated.

The actual residuals are:

- `EVID-003`: a required regression check produces contradictory repeated observations (`PASS -> FAIL -> PASS`). The current runtime stores only the latest verification state, so the final pass can launder a flaky history into release readiness.
- `REL-004`: a required production observability check cannot run because its provider is unavailable. The current runtime collapses every non-zero command exit into ordinary `FAIL`, losing the operational distinction between assertion failure and unavailable/inconclusive evidence.

## Objective
Define and test a deterministic evidence-state model that preserves evidence honesty across repeated verification attempts and distinguishes evidence-source unavailability from genuine assertion failure, without weakening conservative release safety.

## Architectural boundary
RC-4 concerns evidence aggregation and release interpretation only. It MUST NOT change:

- RC-1 request/diff routing semantics;
- RC-2 request-polarity semantics;
- RC-3 task-materiality / `MULTI_TENANT` planning semantics;
- release blocking for genuinely unresolved material confirmations;
- release blocking when required verification has not run;
- project facts or project-profile confirmation state;
- CHALLENGE scenarios or expectations.

## Current mechanism under test
The current runtime computes one local state per invocation and persists a single `last_verification` record. Any non-zero command exit becomes `FAIL`; release consults only that latest record. Therefore contradictory recent observations are not aggregated and provider unavailability is not represented explicitly.

## Frozen hypotheses

### H1 — revision-scoped evidence ledger
Required verification observations should be appendable and attributable to an exact repository revision and check identity. Release should reason over relevant evidence for the current revision rather than only the last sample.

### H2 — contradiction is first-class
For the same required check and same revision, contradictory `PASS` and `FAIL` observations must aggregate to `FLAKY`/`INCONCLUSIVE`; a later pass alone must not erase the contradiction.

### H3 — machine-readable evidence outcome
`UNAVAILABLE`/`INCONCLUSIVE` must come from an explicit adapter/evidence contract, not arbitrary stderr keyword matching. In the absence of such a signal, a non-zero command remains an ordinary `FAIL`.

### H4 — conservative freshness
Evidence from another revision must not satisfy the current revision's release gate.

### H5 — explicit resolution boundary
Flaky evidence may become passing only after a new revision or another explicit, auditable stability-resolution event. Re-running the unchanged revision until it happens to pass is not sufficient.

## Candidate state vocabulary
At minimum:

- `NOT_RUN`
- `PASS`
- `FAIL`
- `UNAVAILABLE`
- `INCONCLUSIVE`
- `FLAKY`
- `WAIVED` when explicitly authorized and policy-permitted

Existing specialist-evidence-outstanding states remain separate runtime concerns and must not be weakened by RC-4.

## Frozen behavioral gates

### Treatments
1. `PASS -> FAIL -> PASS` for the same required check and revision aggregates to `FLAKY` (or equivalently blocking `INCONCLUSIVE`), not `PASS`.
2. A required provider-unavailable observation supplied through an explicit machine-readable adapter contract aggregates to `UNAVAILABLE` or `INCONCLUSIVE`, not ordinary `FAIL`.
3. A genuine failed critical regression remains `FAIL`.
4. Evidence on a new revision does not inherit a prior revision's flaky/pass state as proof.
5. Release remains blocked for `FLAKY`, `UNAVAILABLE`, `INCONCLUSIVE`, `FAIL`, and `NOT_RUN` required evidence unless an explicit policy-authorized waiver applies.

### Controls
1. A simple required check with only passing observations remains `PASS`.
2. Arbitrary stderr text containing words such as "unavailable" cannot by itself create `UNAVAILABLE`.
3. `release` before required verification remains blocked.
4. Unresolved material confirmations remain blocking regardless of evidence state.
5. A non-critical explicitly authorized waiver remains `WAIVED`, never silently converted to `PASS`.
6. Existing RC-1, RC-2 and RC-3 regression suites must show zero `PASS -> FAIL` regressions.
7. Official DEV must remain 24/24 before any runtime promotion.

## Research sequence
1. Reproduce the current latest-result and generic-nonzero behaviors on the exact base commit.
2. Build an isolated deterministic evidence reducer outside canonical `sef.py`.
3. Freeze treatment, negative-control, stale-evidence and metamorphic cases before tuning.
4. Run the isolated reducer in CI and publish observations as artifacts.
5. Compare against RC-1/RC-2/RC-3 regression gates and official DEV.
6. Only if all gates pass: design a separate runtime-integration PR with state-schema migration/backward-compatibility review.
7. CHALLENGE remains sealed until RC-4 is merged and post-merge gates are green.

## Decision thresholds
Promote only with:

- 100% treatment pass;
- 100% frozen safety-control pass;
- deterministic repeated results;
- zero `PASS -> FAIL` on prior RC suites;
- DEV = 24/24;
- explicit revision-freshness protection demonstrated;
- explicit no-stderr-guessing behavior demonstrated;
- no CHALLENGE inspection or tuning.
