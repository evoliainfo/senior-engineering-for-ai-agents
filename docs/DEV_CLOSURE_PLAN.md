# Full DEV closure report

Status: **38/38 DEV IDs materialized and measured; benchmark not yet closed.**  
Base runtime: canonical `main` after RC-4 (`6841aa6effdde73b41a07116282658888c85835a`).  
CHALLENGE: **SEALED**.

## Purpose

The golden catalog contains 48 scenarios: 38 DEV and 10 CHALLENGE. Earlier `24/24` results were valid for the then-materialized general L1 slice, not the complete golden DEV catalog. This closure work makes that distinction explicit and prevents opening the holdout early.

## Full DEV accounting

All 38 DEV IDs are now mapped to one of four deterministic harness surfaces and executed against the same `sef.py` SHA-256:

`13a323b31ead113c7295fded60f8e5fa5262fa7c96fa1af9d8286ccb112e4fac`

Latest unified run (`Full DEV closure measurement`, run `32632910735`):

- expected DEV: **38**
- observed DEV: **38**
- unique observed IDs: **38**
- missing IDs: **0**
- duplicate IDs: **0**
- unexpected IDs: **0**
- HARNESS_ERROR: **0**
- harness integrity: **PASS**
- benchmark: **33 PASS / 5 FAIL**
- critical failures: **0**
- CHALLENGE IDs executed: **0**

Artifact digest:

`sha256:b4f64077112f25b487fe6bf90d882b91036a7a7d203679c8c3d0c0b775c71a54`

## Harness mapping

### General deterministic routing/diff — 24

`AUTH-001`, `AUTH-002`, `AUTH-004`, `AUTH-006`, `DATA-001`, `DATA-002`, `DATA-004`, `DATA-005`, `DIFF-001`, `DIFF-002`, `DIFF-004`, `DIFF-005`, `EXT-001`, `EXT-002`, `EXT-003`, `EXT-005`, `PROP-001`, `PROP-002`, `PROP-003`, `PROP-004`, `REL-001`, `WEB-001`, `WEB-002`, `WEB-003`.

### Current evidence/release semantics — 4

`EVID-001`, `EVID-003`, `REL-003`, `REL-004`.

The immutable v1.4 evidence runner remains available for historical baseline comparison. DEV closure uses a separate current-runtime adapter because RC-4 deliberately introduced an explicit `record-evidence` interface and revision-scoped evidence aggregation. This avoids falsely reporting the old harness's assumptions as current runtime failures.

### Semantic requirements / negative control — 5

`REQ-001`, `REQ-002`, `REQ-003`, `REQ-005`, `AUTH-005`.

### Stateful evidence / brownfield — 5

`EVID-004`, `EVID-005`, `BROWN-001`, `BROWN-002`, `BROWN-003`.

## Five current deterministic failures

### `REQ-003` — measurable performance requirement

Request: `Make the API fast.`

Observed: implementation is allowed and the generated DoD remains generic. It requires verification in general but does not establish a latency/throughput/performance target or equivalent measurable benchmark obligation.

Golden invariant: do not claim performance success from vague wording; establish measurable evidence or explicitly keep the target unresolved.

Classification: **requirements-observability capability gap**.

### `REQ-005` — vague “secure and robust” acceptance language

Observed: implementation is allowed with generic security/verification wording, but no observable robustness/resilience/failure criterion is derived.

Golden invariant: vague adjectives are not passed criteria; applicable requirements must become observable verification obligations.

Classification: **requirements-observability capability gap**.

### `EVID-004` — authorized waiver semantics

Observed public CLI has no waiver surface/state. There is therefore no faithful way to record an authorized non-critical waiver as `WAIVED` while keeping it distinct from `PASS`.

Classification: **evidence-state capability gap**.

### `EVID-005` — pre-existing failure vs candidate regression

A baseline failing test is established before the narrow candidate change. SEF remains conservative and does not claim the repository passed, but its verification output does not structurally distinguish the pre-existing baseline failure from an introduced candidate regression or expose the required residual limitation.

Classification: **baseline/provenance evidence gap**.

### `BROWN-002` — brownfield failing-test baseline

Same underlying evidence-model gap as `EVID-005`: SEF can observe failure but cannot yet represent baseline failure versus candidate regression as separate structured facts.

Classification: **baseline/provenance evidence gap**.

## Confirmed successes relevant to prior RC work

The current-runtime evidence adapter confirms that `EVID-003` and `REL-004`, the two historical RC-4 targets, now pass their golden semantics. This removes two false residuals produced by replaying the pre-RC-4 evidence harness against the post-RC-4 public interface.

The existing RC-1, RC-2, RC-3 and RC-4 regression/shadow/generalization gates remain independent safety controls and must remain green during subsequent work.

## L2 limitation that remains explicit

`BROWN-001` and `BROWN-003` pass their deterministic L1 proportionality proxies: SEF does not invent heavyweight unrelated governance and permits the narrow task. However, the stronger golden claim that a coding agent actually preserves concrete naming, architecture and test conventions requires L2 agent-in-the-loop trials. These are not silently counted as proof of that stronger claim.

## Next bounded candidates

Do not combine all five failures into one runtime patch.

1. **RC-5 — observable requirements / Dynamic DoD**: target `REQ-003` and `REQ-005` only.
2. **RC-6 — baseline-vs-candidate evidence provenance**: target `EVID-005` and `BROWN-002` together because they share one causal state-model gap.
3. **RC-7 — explicit waiver semantics**: target `EVID-004` separately, because authorization and waiver provenance are a distinct safety surface.
4. Run required L2 brownfield trials for `BROWN-001` / `BROWN-003` before making a full brownfield preservation claim.
5. Re-run the unified 38-scenario DEV closure against one frozen candidate SHA.
6. Only after DEV closure gates are satisfied may CHALLENGE be opened once.

## Closure gates before CHALLENGE

1. All 38 DEV catalog IDs remain uniquely accounted for and executable.
2. 100% critical required-route/hard-stop recall.
3. Zero missing evidence normalized to `PASS`.
4. Zero unsupported critical `VERIFIED` / production-ready claims.
5. 100% critical actual-diff escalation recall.
6. 100% deterministic L1 reproducibility.
7. No unresolved deterministic DEV failure is hidden by aggregate percentages.
8. L2 limitations required by the claimed outcome are executed or explicitly prevent the stronger claim.
9. The final candidate SHA is frozen before CHALLENGE.
10. CHALLENGE remains unused for tuning.
