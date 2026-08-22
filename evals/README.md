# SEF Evaluation Harness

This directory implements the benchmark contract defined in:

- `docs/EVALUATION_HARNESS_SPEC.md`
- `docs/EVALUATION_SCENARIO_CATALOG.md`

## Current implementation scope

The first implementation is intentionally narrow:

- black-box execution of the public `sef.py` CLI;
- zero third-party Python dependencies;
- deterministic L0/L1 scenario validation and plan-routing evaluation;
- isolated temporary fixture repository for every scenario;
- exact SHA-256 identity for the tested `sef.py` and fixture tree;
- machine-readable scenario/result records;
- no modification of the runtime under test.

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

CI bootstrap self-test:

```bash
python3 evals/run.py self-test --ids PROP-001,AUTH-001,DATA-002,WEB-001
```

A non-zero exit means at least one selected scenario failed, was inconclusive, or the harness itself failed.

## Design rule

The harness grades observable SEF outcomes. It must never infer missing fields as passing values or weaken a scenario to match the current implementation.
