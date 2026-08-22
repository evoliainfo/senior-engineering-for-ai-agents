# SEF Evaluation Harness

This directory implements the benchmark contract defined in:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`

## Current implementation scope

The first implementation is intentionally bounded:

- black-box execution of the public `sef.py` CLI;
- zero third-party Python dependencies;
- deterministic L0/L1 scenario validation and plan-routing evaluation;
- isolated temporary fixture repository for every scenario;
- exact SHA-256 identity for the tested `sef.py` and fixture tree;
- machine-readable scenario/result records;
- no modification of the runtime under test.

The current materialized DEV slice contains 11 plan-level scenarios covering:

- low-risk proportionality;
- authentication and authorization;
- authorization + migration interaction;
- destructive migration/recovery;
- webhook trust;
- file upload security;
- CI/software-supply-chain routing;
- SEO/web discoverability;
- lead-generation analytics/conversion routing;
- GEO/AI discoverability without accidental AI-runtime routing.

It does **not** yet claim the full 48-scenario catalog is executable. Actual-diff, verification/release evidence, repeated Codex/Claude trials and real-project pilots are added in later bounded increments.

## Commands

Validate scenario contracts:

```bash
python3 evals/run.py validate
```

Run all currently materialized DEV scenarios:

```bash
python3 evals/run.py run --set DEV
```

Run selected scenarios:

```bash
python3 evals/run.py run --ids PROP-001,AUTH-001
```

A non-zero exit from `run` means at least one selected benchmark scenario failed or was inconclusive. That is a **benchmark result**, not automatically a harness defect.

CI separately gates harness health: malformed scenarios, missing results and `HARNESS_ERROR` outcomes fail CI, while legitimate SEF baseline failures are recorded without being laundered into PASS.

## Bootstrap baseline observation

Against the exact v1.4 runtime SHA-256
`31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`,
the 11-scenario plan-level bootstrap currently records **10 PASS / 1 FAIL**.

The observed failure is `WEB-001`: a public company website is correctly routed to frontend + SEO, but implementation is blocked by an inferred material context. This is retained as baseline evidence rather than weakened to make v1.4 score green.

This is a partial bootstrap measurement, not the final 48-scenario v1.4 benchmark score.

## Design rule

The harness grades observable SEF outcomes. It must never infer missing fields as passing values, hide a legitimate baseline failure, or weaken a scenario merely to match the current implementation.
