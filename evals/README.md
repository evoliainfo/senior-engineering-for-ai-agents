# SEF Evaluation Harness

This directory implements the deterministic evaluation, regression and holdout surfaces used to qualify the current SEF candidate.

Primary contracts:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`
- `docs/B3_REGRESSION_CLOSEOUT.md`
- `docs/CHALLENGE_V3_VERDICT.md`
- `evals/release_candidate_manifest.json`

## Current candidate state

Frozen runtime SHA-256:

`c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`

Frozen code commit:

`3630f563f24b3577ad1e6a0a05e66a86615dabca`

Current release decision:

**`ARCHITECTURE_DECISION_REQUIRED`**

The runtime remains frozen and is **not release-eligible under the original full-generalization claim** because the final fresh independent holdout produced one critical structural failure.

## Deterministic regression evidence

On the exact frozen runtime:

- unified DEV closure: **38/38 PASS**
- B1 semantic-materiality acceptance: **10/10 PASS**
- B2 composition/generalization acceptance: **10/10 PASS**
- calibrated RC-8 postmortem controls: **14/14 PASS**
- first CHALLENGE replay: **10/10 PASS** as regression only
- final-cycle positive/negative controls: **12/12 PASS**
- CHALLENGE v2 replay: **10/10 PASS** as regression only

These green regressions show that known defects remain closed. They are not independent generalization evidence.

## Independent holdout history

- CHALLENGE #1: **3/10 PASS, 7/10 FAIL** against commit `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837`, runtime `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`.
- CHALLENGE v2: **4/10 PASS, 6/10 FAIL** against commit `4132711f9d0ad74ff41b26deff7b9966d6e54e94`, runtime `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`, official run `32650180190`.
- CHALLENGE v3: **9/10 PASS, 1/10 FAIL**, harness integrity **PASS**, against frozen commit `3630f563f24b3577ad1e6a0a05e66a86615dabca` and runtime `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`.

CHALLENGE v3 official evidence:

- run: `32657568114`
- catalog SHA-256: `acf2d37f2c5692a05acca90b7116b3fd66c10ed1ba103e288596d310d564bacb`
- artifact: `9497844102`
- artifact digest: `sha256:702e855db549d229e4b186dda522c77dccbc37e318db86cdde1de60469a4ca0d`
- critical failure: **`V3-AUTH-002`**
- official decision: **`STOP_DETERMINISTIC_TUNING_ARCHITECTURE_DECISION`**

The v3 evaluator PR was closed without merge after the first valid run. Its branch and immutable workflow artifact preserve the original scenarios and verdict without placing holdout answer material on the release branch.

All executed holdouts are now **`CONSUMED_REGRESSION_ONLY`** for future use. No CHALLENGE v4 is permitted on this deterministic architecture line.

## Why `V3-AUTH-002` matters

The request described an operator assigned to one department who may edit work items only for that department and explicitly required that passing another department identifier must never expose or modify the other department's items.

The runtime returned:

- risk `R1`;
- no `AUTHORIZATION` pack;
- no partition-isolation pack;
- only core planning/review/test procedures.

There is a reasonable ontology question over whether an internal department should map to the canonical `MULTI_TENANT` pack. That ambiguity does **not** invalidate the failure: the runtime also missed the explicit authorization boundary entirely. The result therefore remains a genuine critical signal that open-ended business-partition semantics can escape the current deterministic lexical/relation layer.

## Evaluation partition

The original 48-scenario catalog remains accounted for as:

- **38 DEV** scenarios in the deterministic closure gate;
- **10 original CHALLENGE** scenarios retained outside DEV discovery.

The original challenge partition may still be described as `SEALED` for discovery isolation. That does not imply statistical independence after results have been used for remediation.

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

B1, B2, RC-8 and final generalization controls are deterministic research/regression surfaces. They may be used for regression proof but must never be presented as independent holdout evidence.

```bash
python3 evals/run_b1_acceptance.py --sef sef.py --output b1-acceptance.json
python3 evals/run_b2_acceptance.py --sef sef.py --output b2-acceptance.json
python3 evals/run_rc8_controls_round2_candidate.py --sef sef.py --output rc8-round2.json
python3 evals/run_final_generalization_controls.py --sef sef.py --output final-generalization.json
```

## Aggregate evidence-consistency gate

```bash
python3 evals/run_release_candidate_gate.py --sef sef.py --output release-candidate-gate.json
```

A PASS from this gate now means:

- the frozen runtime/checksum identity is intact;
- deterministic regression suites remain green;
- historical holdout identities and verdicts are recorded consistently;
- the terminal finite-completion policy is respected;
- no CHALLENGE v4 material exists.

It **does not mean release approval**. `release_eligible=false` and `ARCHITECTURE_DECISION_REQUIRED` remain authoritative until an explicit product/architecture decision changes the release scope.

## Actual-diff scenarios

For `phase: verify` cases the harness works in an isolated temporary Git fixture:

1. copy a fresh fixture;
2. initialize SEF and create required Git checkpoints;
3. save the task plan;
4. apply only the scenario-declared mutation;
5. execute `sef.py verify --base HEAD`;
6. grade planned versus actual-diff behavior against predeclared expectations.

## Historical remediation helpers

Files named `apply_b1_*`, `apply_b2_*` and `apply_final_generalization*` are retained as audit/build provenance for how validated candidates were constructed. They are not alternate runtimes and are not release entry points.

The only canonical runtime is root-level `sef.py`, controlled by `SHA256SUMS` and `evals/release_candidate_manifest.json`.

## Interpretation rules

- exit code `2` / `HARNESS_ERROR` means the measurement is invalid;
- a benchmark failure is never silently converted to PASS;
- unavailable evidence remains unavailable rather than inferred successful;
- regression evidence and independent holdout evidence are labeled separately;
- a green deterministic regression closeout does not override a failed independent holdout;
- real-agent L2 evidence cannot erase the official CHALLENGE v3 result.

## Next transition

Do **not** patch `V3-AUTH-002`, do not mutate the frozen runtime and do not create CHALLENGE v4.

The next step is an architecture/release-scope decision:

1. redesign semantic boundary classification for stronger open-ended generalization; or
2. ship the current deterministic core only as a constrained beta/experimental release with the lexical business-partition limitation explicitly documented.

Codex L2 remains `NOT_RUN`. It may be used as exploratory evidence after the release-scope decision, but not as a substitute for the failed independent deterministic gate.
