---
name: data-change-safety
description: Evaluate migration, backfill and data-transformation safety using rehearsal, integrity, execution-control, backup and recovery evidence. Use for material persistent-data changes before release progression.
---

# Data Change Safety

Use this pack when a mission materially changes persistent data, schema shape, existing records or recovery risk. Do not load it for read-only queries or ordinary application-code changes with no data mutation surface.

## What this pack does

It converts real rehearsal and recovery observations into a deterministic safety decision. It does not treat a migration file, ORM diff or model confidence as proof that the change is safe.

## Before evaluation

Record the planned change and the actual change reference. Classify the change as one of:

- `MIGRATION`
- `BACKFILL`
- `DATA_TRANSFORM`
- `DESTRUCTIVE_CLEANUP`

Declare whether the change is destructive and which execution controls are required for this change: `idempotency`, `resumability`, `chunking`, `compatibility`.

## Rehearse with real data tooling

Resolve `database_admin` through M4/tool resolution. Rehearse against a non-production surface with representative fixtures.

Collect:

- reviewed-plan and actual-change references;
- scope-match status;
- rehearsal execution and verification evidence;
- pre/post critical data invariants;
- evidence for every required execution control;
- recovery strategy and recovery exercise evidence;
- backup evidence when the change is destructive.

## Evaluate

Run `evaluators/evaluate.py` against the structured evidence document.

The evaluator returns:

- `PASS` only when the change scope matches, rehearsal passes, critical invariants pass, required controls pass with evidence, recovery is proven, and destructive changes have backup evidence;
- `FAIL` when observed evidence demonstrates a material safety defect or an explicitly unsafe recovery state;
- `INCOMPLETE` when evidence was not run, is missing or remains inconclusive.

Never reinterpret `NOT_RUN` as success.

## Recovery semantics

A data change must declare one of `ROLLBACK`, `RESTORE` or `FORWARD_FIX` as its recovery strategy. `NONE` cannot support a passing safety claim.

For a destructive change, backup evidence is mandatory. The backup reference is not itself proof that restore works: the recovery exercise must also pass with evidence.

## Scope boundary

This pack does not generate SQL, choose a database vendor strategy, execute production changes, own credentials or decide provider-specific migration syntax. Those details come from project context, JIT Expertise and resolved tools. It evaluates the durable safety evidence around the change.
