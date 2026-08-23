# B3 Regression Closeout and Freeze Preparation

## Purpose

B3 is the final deterministic closeout before candidate freeze. It is **not** a runtime-remediation phase.

The canonical B2 runtime entering B3 is:

- source `main` commit: `4ba20e299786eb61b718b855df5d397e48090ac1`
- `sef.py` SHA-256: `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`

B3 must not modify `sef.py` or `SHA256SUMS`.

## Why B3 exists

B1 and B2 closed the known deterministic semantic/composition gaps, but a release candidate is not ready to freeze merely because the latest tests are green. The repository must also have one coherent evidence state, no misleading stale benchmark documentation, explicit holdout contamination semantics, and a reproducible aggregate gate.

B3 therefore closes four classes of release risk:

1. **Regression drift**: all deterministic suites must still execute the same runtime and remain green.
2. **Evidence drift**: documentation and machine-readable manifests must describe the same candidate and counts.
3. **Evaluator leakage**: the consumed first CHALLENGE must never be relabeled as independent evidence, and CHALLENGE v2 must remain unmaterialized during B3.
4. **Provenance ambiguity**: B1/B2 patch/build helpers may remain for auditability, but `sef.py` is the only canonical runtime under test.

## Required gates

B3 is promotable only when the exact B2 runtime passes all of the following:

| Surface | Required result | Evidence class |
| --- | ---: | --- |
| Unified DEV closure | 38/38 PASS | deterministic DEV |
| B1 acceptance | 10/10 PASS | deterministic regression/generalization controls |
| B2 acceptance | 10/10 PASS | deterministic regression/generalization controls |
| RC-8 calibrated controls | 14/14 PASS | postmortem falsification/regression controls |
| First CHALLENGE cases | 10/10 PASS | **CONSUMED_REGRESSION_ONLY** |

The final row is deliberately not independent holdout evidence. The official first-CHALLENGE verdict remains the immutable 3/10 result obtained by candidate `7302914e…` before remediation.

## Holdout isolation

During B3:

- no CHALLENGE v2 scenario, ID, expectation or answer key may be materialized under `evals/`;
- no runtime tuning may use future holdout information;
- the future holdout must be created only after an exact candidate freeze;
- the first CHALLENGE remains available only as regression evidence because its failures were used during remediation.

This means B3 can establish **freeze readiness**, not independent generalization.

## Documentation closeout

`evals/README.md` must describe the current deterministic state rather than historical partial baselines. Historical baseline artifacts and one-shot patchers remain valid provenance, but they must be labeled as historical rather than presented as the current candidate state.

The original `evals/challenge_manifest.json` is preserved as immutable historical evidence for the first holdout. Current release-candidate state lives in `evals/release_candidate_manifest.json`.

## Definition of Done

B3 is complete when all of these conditions are true:

- `sef.py` and `SHA256SUMS` are byte-identical to B2 at branch start;
- runtime SHA-256 is `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`;
- DEV is 38/38 PASS;
- B1 is 10/10 PASS;
- B2 is 10/10 PASS;
- RC-8 calibrated controls are 14/14 PASS;
- consumed first-CHALLENGE regression is 10/10 PASS with `independent_holdout_claim=false`;
- no CHALLENGE v2 evaluation content is materialized;
- current evaluation documentation and machine manifests agree on the candidate state;
- known L2 work remains explicit: Codex `NOT_RUN`, Claude `NOT_RUN`;
- the aggregate release-candidate gate reports `freeze_ready=true`.

If any item fails, B3 is **not** complete. Runtime changes are not permitted inside B3; a genuine runtime defect would reopen remediation instead of being patched during closeout.

## After B3

The next phase is **FREEZE**:

1. take the exact B3-merged repository commit;
2. re-run the aggregate deterministic gate against `main`;
3. record the exact repository commit + `sef.py` SHA-256 as frozen candidate identity;
4. prohibit runtime changes for that candidate;
5. only then materialize and seal a fresh CHALLENGE v2 under evaluator separation.

Real external-agent L2 trials remain a later gate after deterministic independent evaluation, unless the release protocol explicitly orders them otherwise.
