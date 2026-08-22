# SEF Evaluation Harness

This directory implements the benchmark contract defined in:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`

## Current implementation scope

The implementation remains intentionally bounded:

- black-box execution of the public `sef.py` CLI;
- zero third-party Python dependencies;
- deterministic L1 plan-routing evaluation;
- deterministic L1 actual-Git-diff reassessment;
- isolated temporary fixture repository for every scenario;
- exact SHA-256 identity for the tested `sef.py` and fixture tree;
- machine-readable scenario/result records;
- no modification of the runtime under test.

The current materialized DEV slice contains **15 scenarios**:

- 11 plan-level routing/proportionality scenarios;
- 4 actual-diff scenarios: `DIFF-001`, `DIFF-002`, `DIFF-004`, `DIFF-005`.

`DIFF-003` remains in the CHALLENGE set and is intentionally not materialized during this tuning pass.

It does **not** yet claim the full 48-scenario catalog is executable. Evidence/release behavior, repeated Codex/Claude trials and real-project pilots remain later bounded increments.

## How actual-diff scenarios work

For a `phase: verify` scenario the harness:

1. creates a fresh temporary copy of the fixture;
2. initializes SEF and records a clean Git checkpoint;
3. saves the original task plan and records a second checkpoint;
4. applies only the scenario-declared mutation;
5. runs `sef.py verify --base HEAD`;
6. grades the actual observed diff against the predeclared expectations.

This keeps the saved SEF task state out of the candidate implementation diff and makes the tested mutation reproducible.

## Commands

Validate scenario contracts:

```bash
python3 evals/run.py validate
```

Run all materialized DEV scenarios:

```bash
python3 evals/run.py run --set DEV
```

Run selected scenarios:

```bash
python3 evals/run.py run --ids DIFF-001,DIFF-002
```

A non-zero exit from `run` means at least one selected benchmark scenario failed or was inconclusive. That is a **benchmark result**, not automatically a harness defect.

CI separately gates harness health: malformed scenarios, missing results and `HARNESS_ERROR` outcomes fail CI, while legitimate SEF baseline failures are recorded without being laundered into PASS.

## Current baseline

Against the exact v1.4 runtime SHA-256
`31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`,
the original 11-scenario plan-level slice records **10 PASS / 1 FAIL**.

The retained plan-level failure is `WEB-001`, an over-governance case already documented in the PR that introduced the harness.

The first actual-diff baseline is measured in CI for this increment and should be recorded here only after the runner itself has passed harness-health review.

This is a partial measurement, not the final 48-scenario v1.4 benchmark score.

## Design rule

The harness grades observable SEF outcomes. It must never infer missing fields as passing values, hide a legitimate baseline failure, or weaken a scenario merely to match the current implementation.
