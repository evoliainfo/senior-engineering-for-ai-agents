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
6. grades the original plan and actual observed diff against predeclared expectations.

A clean checkpoint with an existing `HEAD` is valid even if there is nothing new to commit. This keeps harness bookkeeping from becoming a false failure while preserving an exact Git base for `verify`.

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

## Current v1.4 baseline

Against exact runtime SHA-256:

`31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`

Latest Ubuntu CI measurement:

- **15 DEV scenarios executed**
- **13 PASS**
- **2 FAIL**
- **0 critical failures**
- **0 harness errors**

Retained failures:

1. `WEB-001` — public company website + SEO is routed correctly, but a broad `company` signal creates an unconfirmed multi-tenant candidate and unnecessarily blocks implementation.
2. `DIFF-004` — the actual Docker/CI/IaC diff is correctly detected and escalated to R3 with the expected packs, but the original documentation-only request already activates `RELEASE_ENGINEERING` because the negative phrase `do not change ... deployment` is matched as release intent.

Actual-diff observations:

- `DIFF-001`: PASS — analytics introduced outside a CSS-only plan is detected and adds analytics obligations.
- `DIFF-002`: PASS — privileged admin authorization introduced outside a routine API plan is detected at R3 with `AUTHORIZATION`.
- `DIFF-004`: FAIL overall — actual diff detection itself passes; the failure is the over-routed initial documentation plan described above.
- `DIFF-005`: PASS — a genuinely harmless localized CSS diff remains R0 without invented heavyweight routes.

This is a partial baseline, not the final 48-scenario v1.4 benchmark score.

## Design rule

The harness grades observable SEF outcomes. It must never infer missing fields as passing values, hide a legitimate baseline failure, or weaken a scenario merely to match the current implementation.
