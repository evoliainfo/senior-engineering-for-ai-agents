# SEF Evaluation Harness

This directory implements the deterministic evaluation and regression surfaces used to qualify the current SEF candidate.

Primary contracts:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`
- `docs/B3_REGRESSION_CLOSEOUT.md`
- `evals/release_candidate_manifest.json`

## Current candidate state

Canonical runtime SHA-256:

`bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`

Current deterministic release-candidate evidence:

- unified DEV closure: **38/38 PASS**
- B1 semantic-materiality acceptance: **10/10 PASS**
- B2 composition/generalization acceptance: **10/10 PASS**
- calibrated RC-8 postmortem controls: **14/14 PASS**
- first CHALLENGE scenarios replayed as regression: **10/10 PASS**

The last line is evidence class **`CONSUMED_REGRESSION_ONLY`**. It is not an independent holdout result.

The original first CHALLENGE remains historical experimental evidence. Its official one-shot result was **3/10 PASS, 7/10 FAIL** against frozen candidate commit `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837` with runtime SHA-256 `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`. Because those failures were later used for remediation, that holdout is permanently contaminated for future tuning claims.

A fresh **CHALLENGE v2** is therefore required after candidate freeze. B3 deliberately does not materialize, inspect or tune against that future holdout.

Real external-agent L2 status remains:

- Codex: `NOT_RUN`
- Claude: `NOT_RUN`

## Evaluation partition

The original 48-scenario catalog is accounted for as:

- **38 DEV** scenarios in the deterministic closure gate;
- **10 original CHALLENGE** scenarios retained outside DEV discovery.

`evals/dev_coverage_manifest.json` may still report the original challenge partition as `SEALED`. In the current repository this means those 10 IDs remain excluded from DEV discovery. It does **not** mean the first CHALLENGE remains statistically or methodologically independent; its explicit independent-holdout state is `CONSUMED`.

No CHALLENGE v2 scenario or answer key should exist under `evals/` during B3.

## What the unified DEV gate covers

`evals/run_dev_closure_all.py` aggregates four deterministic surfaces against one exact `sef.py` source:

1. general routing / proportionality;
2. evidence and release semantics;
3. semantic requirement closure;
4. stateful and brownfield behavior.

It enforces exact scenario accounting, rejects duplicate/missing IDs, rejects `HARNESS_ERROR`, and records the single runtime SHA-256 observed across all results. It never discovers or executes CHALLENGE scenarios.

Run it with:

```bash
python3 evals/run_dev_closure_all.py --sef sef.py --output dev-closure-all.json
```

## B1, B2 and RC-8 controls

B1 and B2 controls are deterministic DEV research/regression surfaces used to test semantic generalization and false-positive containment around the mechanisms introduced during remediation.

```bash
python3 evals/run_b1_acceptance.py --sef sef.py --output b1-acceptance.json
python3 evals/run_b2_acceptance.py --sef sef.py --output b2-acceptance.json
python3 evals/run_rc8_controls_round2_candidate.py --sef sef.py --output rc8-round2.json
```

The B2 control history intentionally preserves an initial failed calibration round. Four negative controls were ambiguous because they independently activated legitimate existing rules. Their calibration is documented in `docs/B2_CONTROL_CALIBRATION.md`; the runtime candidate was unchanged while those control fixtures were corrected.

## Consumed first-CHALLENGE regression

The original 10 CHALLENGE cases may now be executed only through the regression wrapper:

```bash
python3 evals/run_consumed_challenge_regression.py --sef sef.py --output consumed-challenge-regression.json
```

That runner must report:

- evidence class `CONSUMED_REGRESSION_ONLY`;
- `independent_holdout_claim: false`;
- exact candidate runtime identity;
- explicit accounting for all 10 historical cases.

Passing these cases proves that known failures remain closed. It does not prove unseen generalization.

## Aggregate B3 / release-candidate gate

B3 uses one aggregate runner to prevent evidence drift:

```bash
python3 evals/run_release_candidate_gate.py --sef sef.py --output release-candidate-gate.json
```

The aggregate gate checks:

- exact runtime/checksum identity;
- 38/38 DEV;
- 10/10 B1;
- 10/10 B2;
- 14/14 calibrated RC-8;
- 10/10 consumed challenge regression;
- immutable identity of the first historical CHALLENGE manifest;
- explicit consumed-holdout semantics;
- absence of materialized CHALLENGE v2 content during B3;
- consistency between machine-readable manifests and this evaluation status.

A PASS from this runner means **freeze-ready deterministic evidence**, not final release approval.

## Actual-diff scenarios

For `phase: verify` cases the harness works in an isolated temporary Git fixture:

1. copy a fresh fixture;
2. initialize SEF and create the required Git checkpoints;
3. save the task plan;
4. apply only the scenario-declared mutation;
5. execute `sef.py verify --base HEAD`;
6. grade planned versus actual-diff behavior against predeclared expectations.

This is how destructive migrations, unexpected authorization changes, web/analytics scope expansion and other implementation-time changes are evaluated without contaminating the source repository.

## Historical remediation helpers

Files named `apply_b1_*` and `apply_b2_composition.py` are retained as **audit/build provenance** for how validated candidates were constructed during remediation. They are not alternate runtimes and are not the release entry point.

The only canonical runtime is root-level `sef.py`, whose identity is controlled by `SHA256SUMS` and `evals/release_candidate_manifest.json`.

## Harness interpretation rules

- exit code `2` / `HARNESS_ERROR` means the measurement itself is invalid;
- a benchmark failure is never silently converted to PASS;
- unavailable evidence remains unavailable rather than being inferred as successful;
- regression evidence and independent holdout evidence are labeled separately;
- future holdout expectations must not be exposed before candidate freeze;
- a green deterministic closeout does not replace real external-agent L2 trials.

## Next transition

After B3 is merged, the repository can enter **FREEZE**. That phase must bind an exact repository commit to the same runtime hash without runtime tuning. Only after the frozen identity exists may a rotated CHALLENGE v2 be materialized and executed as fresh independent evidence.
