# SEF Evaluation Harness

This directory implements the deterministic evaluation, regression and holdout surfaces used to qualify the current SEF candidate.

Primary contracts:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`
- `docs/B3_REGRESSION_CLOSEOUT.md`
- `evals/release_candidate_manifest.json`

## Current candidate state

Canonical runtime SHA-256:

`c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`

Current deterministic evidence on this exact runtime:

- unified DEV closure: **38/38 PASS**
- B1 semantic-materiality acceptance: **10/10 PASS**
- B2 composition/generalization acceptance: **10/10 PASS**
- calibrated RC-8 postmortem controls: **14/14 PASS**
- first CHALLENGE replay: **10/10 PASS** as regression only
- final-cycle positive/negative controls: **12/12 PASS**
- CHALLENGE v2 replay: **10/10 PASS** as regression only

Both historical holdouts are evidence class **`CONSUMED_REGRESSION_ONLY`** after their failures were used for remediation. Passing them now proves known defects remain closed; it does not prove unseen generalization.

Historical independent results:

- CHALLENGE #1: **3/10 PASS, 7/10 FAIL** against commit `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837`, runtime `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`.
- CHALLENGE v2: **4/10 PASS, 6/10 FAIL** against commit `4132711f9d0ad74ff41b26deff7b9966d6e54e94`, runtime `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`, official run `32650180190`.

The single final deterministic remediation cycle is complete. The next fresh independent holdout is **CHALLENGE v3**. Its scenario content must not be materialized or inspected until the exact current candidate has been merged to `main` and rebound to a new freeze commit.

Real external-agent L2 status remains:

- Codex: `NOT_RUN`
- Claude: `NOT_RUN`

## Evaluation partition

The original 48-scenario catalog remains accounted for as:

- **38 DEV** scenarios in the deterministic closure gate;
- **10 original CHALLENGE** scenarios retained outside DEV discovery.

The original challenge partition may still be described as `SEALED` for discovery isolation. That does not imply statistical independence. The explicit independent-holdout state of CHALLENGE #1 and CHALLENGE v2 is consumed.

No CHALLENGE v3 scenario or answer key may exist under `evals/` before the new freeze.

## Unified DEV gate

`evals/run_dev_closure_all.py` aggregates four deterministic surfaces against one exact `sef.py` source:

1. general routing / proportionality;
2. evidence and release semantics;
3. semantic requirement closure;
4. stateful and brownfield behavior.

It enforces exact scenario accounting, rejects duplicate/missing IDs, rejects `HARNESS_ERROR`, records one runtime SHA-256 across results and never discovers CHALLENGE scenarios.

```bash
python3 evals/run_dev_closure_all.py --sef sef.py --output dev-closure-all.json
```

## B1, B2, RC-8 and final-cycle controls

B1, B2, RC-8 and final generalization controls are deterministic research/regression surfaces. They may be used for tuning and must never be presented as independent holdout evidence.

```bash
python3 evals/run_b1_acceptance.py --sef sef.py --output b1-acceptance.json
python3 evals/run_b2_acceptance.py --sef sef.py --output b2-acceptance.json
python3 evals/run_rc8_controls_round2_candidate.py --sef sef.py --output rc8-round2.json
python3 evals/run_final_generalization_controls.py --sef sef.py --output final-generalization.json
```

The B2 control history preserves the initial calibration failure. Four negative controls were ambiguous because they independently activated legitimate existing rules; their calibration is documented in `docs/B2_CONTROL_CALIBRATION.md`.

## Consumed holdout regressions

Historical challenge scenarios may be replayed only as explicit regression evidence. They must preserve:

- evidence class `CONSUMED_REGRESSION_ONLY`;
- `independent_holdout_claim: false`;
- exact runtime identity;
- complete scenario accounting.

Passing those cases is not a fresh generalization claim.

## Aggregate release-candidate gate

```bash
python3 evals/run_release_candidate_gate.py --sef sef.py --output release-candidate-gate.json
```

The aggregate gate checks:

- exact runtime/checksum identity;
- 38/38 DEV;
- 10/10 B1;
- 10/10 B2;
- 14/14 calibrated RC-8;
- 10/10 consumed first-challenge regression;
- immutable identity of the first historical CHALLENGE manifest;
- explicit consumed semantics for CHALLENGE v2;
- absence of materialized CHALLENGE v3 content before freeze;
- consistency between machine-readable manifests and this evaluation status.

A PASS means **freeze-ready deterministic evidence**, not final release approval.

## Actual-diff scenarios

For `phase: verify` cases the harness works in an isolated temporary Git fixture:

1. copy a fresh fixture;
2. initialize SEF and create required Git checkpoints;
3. save the task plan;
4. apply only the scenario-declared mutation;
5. execute `sef.py verify --base HEAD`;
6. grade planned versus actual-diff behavior against predeclared expectations.

This lets the suite detect destructive migrations, unexpected authorization changes, release/supply-chain expansion and infrastructure exposure without contaminating the source repository.

## Historical remediation helpers

Files named `apply_b1_*`, `apply_b2_*` and `apply_final_generalization*` are retained as audit/build provenance for how validated candidates were constructed. They are not alternate runtimes and are not release entry points.

The only canonical runtime is root-level `sef.py`, controlled by `SHA256SUMS` and `evals/release_candidate_manifest.json`.

## Interpretation rules

- exit code `2` / `HARNESS_ERROR` means the measurement is invalid;
- a benchmark failure is never silently converted to PASS;
- unavailable evidence remains unavailable rather than inferred successful;
- regression evidence and independent holdout evidence are labeled separately;
- future holdout expectations must not be exposed before candidate freeze;
- a green deterministic closeout does not replace real external-agent L2 trials.

## Next transition

Merge the exact current candidate to `main` without runtime mutation. Bind the resulting main commit and SHA-256 `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee` as the new freeze identity. Only then materialize **CHALLENGE v3** and execute it once as fresh independent evidence.

If CHALLENGE v3 passes **10/10**, deterministic tuning stops and the next gate is the real Codex L2 brownfield trial. If v3 contains structural critical failures, deterministic tuning also stops and the project moves to an architecture/release-scope decision rather than creating CHALLENGE v4.
