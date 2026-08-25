# M3 Pack 2 — Data Change Safety

Status: experimental implementation candidate
Date: 2026-08-24
Parent contract: `STABLE_EXPERT_PACK_CONTRACT_M3.md`

## Purpose

`data-change-safety` is the second Stable Expert Pack in the Modern SEF roadmap.

Its durable value is not provider-specific migration syntax. It defines an executable evidence gate around material persistent-data changes so SEF can distinguish:

- a rehearsed, evidence-backed change;
- an observed unsafe change;
- a change whose safety has not yet been proven.

## Tool boundary

The pack declares one required abstract capability:

```text
database_admin
```

with `WRITE` access in a `SANDBOX` context.

The pack does not bind this to PostgreSQL, Supabase, Neon, RDS or any other provider. M4 Tool Capability Resolution will map the abstract requirement to the actual tool surface. Provider/version-specific behavior remains JIT Expertise.

## Observation contract

Input schema:

`sef.data-change-safety-observations.v1`

A document contains:

- `change` — intended and actual change identity, kind, target environment, destructiveness and scope-match result;
- `rehearsal` — non-production rehearsal status plus environment, fixture, execution and verification references;
- `recovery` — rollback/restore/forward-fix strategy, recovery exercise evidence and backup evidence;
- `invariants` — pre/post integrity claims and evidence;
- `controls` — the four durable execution-control classes.

### Change kinds

```text
MIGRATION
BACKFILL
DATA_TRANSFORM
DESTRUCTIVE_CLEANUP
```

`DESTRUCTIVE_CLEANUP` must always set `destructive=true`. Other change kinds may also be destructive when their real effect requires it.

## Non-production rehearsal

A rehearsal may only declare:

```text
SANDBOX
PREVIEW
```

Production may be the eventual target, but production execution is not accepted as rehearsal evidence by this pack.

A passing rehearsal requires references for:

- environment;
- representative fixture;
- execution;
- verification.

A green status with missing supporting references becomes `INCOMPLETE`, not `PASS`.

## Data invariants

At least one invariant is mandatory. Each invariant records:

- statement;
- criticality;
- pre-change status/reference;
- post-change status/reference.

A failed observed invariant causes `FAIL`. A missing/not-run/inconclusive invariant or a passing status without evidence causes `INCOMPLETE`.

## Durable execution controls

Every document must account for exactly:

```text
idempotency
resumability
chunking
compatibility
```

The pack does not require all four on every change. Instead each one must be explicit:

```text
required=true  → status/evidence must support it
required=false → status must be N_A and evidence must be absent
```

This prevents an agent from silently dropping a safety dimension from the record.

## Recovery semantics

Accepted strategies:

```text
ROLLBACK
RESTORE
FORWARD_FIX
NONE
```

`NONE` is representable so an unsafe/no-strategy state can be recorded truthfully, but it always blocks a passing decision. It must use `status=N_A` and no recovery evidence; contradictory `NONE + PASS` evidence is rejected structurally.

For non-`NONE` strategies, recovery must be exercised and evidenced to pass.

## Destructive changes and backup

When `destructive=true`:

- backup status must be `PASS`;
- backup evidence must exist;
- recovery exercise must independently pass with evidence.

A backup artifact alone does not prove recoverability.

## Decision semantics

### `PASS`

The actual scope matches the reviewed plan, rehearsal is proven, all invariants pass with evidence, every required execution control passes with evidence, a real recovery strategy is proven and destructive changes have backup evidence.

### `FAIL`

Observed evidence proves a material unsafe condition, including scope mismatch, rehearsal failure, invariant failure, required-control failure, recovery failure, missing recovery strategy or backup failure.

### `INCOMPLETE`

The safety claim cannot yet be supported because a required step is `NOT_RUN`/`INCONCLUSIVE` or supporting evidence is missing.

`FAIL` takes precedence over `INCOMPLETE` when both exist.

## Qualification

The deterministic pack gate covers 26 controls including:

- M3 pack-contract conformance;
- deterministic manifest inclusion alongside the first visual pack;
- passing non-destructive migration;
- passing destructive cleanup with backup/restore evidence;
- critical invariant failure;
- missing recovery evidence;
- plan/actual scope mismatch;
- rehearsal failure and missing rehearsal evidence;
- rejection of production rehearsal;
- exhaustive accounting of the four control classes;
- explicit N_A semantics;
- required-control failure/missing evidence;
- absent/contradictory recovery strategy;
- recovery failure/missing evidence;
- destructive backup failure/missing evidence;
- destructive-kind consistency;
- invariant evidence gaps;
- explicit non-claims;
- historical `sef.py` runtime integrity.

The qualification performs zero database, network or model calls. It tests durable decision semantics against controlled evidence fixtures.

## Explicit non-claims

This pack does not prove that SEF can already:

- connect to a live database;
- create backups;
- execute migrations/backfills;
- restore data;
- choose provider-specific SQL or migration syntax;
- authorize a production data change;
- outperform native Codex on real data migrations.

Those claims require M4 tool resolution, M5 mission integration and later outcome-level evaluation.
