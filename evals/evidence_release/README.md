# Evidence / Verify / Release Evaluation Slice

This directory contains the first deterministic SEF evaluation slice focused on evidence honesty and release gating.

It extends the locked evaluation program without modifying the v1.4 runtime under test.

## Boundary

- public SEF CLI only (`plan`, `verify`, `release`);
- no direct import of private SEF runtime functions;
- no mutation of `sef.py`;
- no modification of the immutable `v1.4.0-beta` tag;
- deterministic no-network fixture commands;
- fixture control state is kept under `.git` so it cannot make the candidate worktree dirty or contaminate Git-diff assessment.

The runner reuses generic helpers from `../run.py`. It is intentionally a bounded slice rather than an immediate rewrite of the main runner. Before the full 48-scenario harness is considered complete, the two runner/report surfaces should be reassessed for consolidation into one orchestration/reporting layer.

## Materialized DEV scenarios

### EVID-001 — skipped tests

The fixture exposes real detected `lint`, `typecheck`, `unit` and `build` commands. The scenario intentionally invokes `verify` without `--run` and then checks release readiness.

Expected invariant: skipped required evidence cannot become verified/release-ready.

### EVID-003 — flaky required regression

The required unit command deterministically alternates:

1. PASS
2. FAIL
3. PASS

Expected invariant: observed variability remains `FLAKY`/`INCONCLUSIVE`; a final green observation must not erase directly observed instability or restore release readiness.

### REL-003 — failing critical regression

The required unit command exits non-zero with a deterministic critical-regression failure.

Expected invariant: verification fails and release remains blocked.

### REL-004 — unavailable production evidence

The required command exits non-zero while explicitly reporting that the required observability provider is unavailable.

Expected invariant: unavailable evidence remains non-passing and is represented as `UNAVAILABLE`/`INCONCLUSIVE`, not ordinary success.

## v1.4 baseline

Runtime SHA-256 under test:

`31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`

First Ubuntu CI measurement:

- 4 scenarios executed;
- 2 PASS;
- 2 FAIL;
- 0 critical failures;
- 0 harness errors.

### PASS — EVID-001

Observed:

- detected planned commands include `unit`;
- `verify` without execution records `PLANNED`;
- `release` returns `BLOCKED`;
- release blocker: `Last local verification is not passing.`

Finding: v1.4 correctly refuses to launder skipped tests into release readiness.

### PASS — REL-003

Observed:

- required unit command return code: `1`;
- verification status/state: `FAIL` / `FAIL`;
- release status/readiness: `BLOCKED` / `BLOCKED`.

Finding: v1.4 correctly blocks a release candidate with a failing required regression test.

### FAIL — REL-004

Observed:

- command reports `required observability provider unavailable`;
- verification status/state: `FAIL` / `FAIL`;
- release remains correctly `BLOCKED`.

Finding: the safety outcome is conservative, but v1.4 collapses unavailable evidence into generic failure instead of preserving `UNAVAILABLE`/`INCONCLUSIVE` semantics.

### FAIL — EVID-003

Observed required unit return codes:

`[0, 1, 0]`

Observed verification states:

`[LOCAL_PASS, FAIL, LOCAL_PASS]`

After the final green observation:

- `release` returns `PASS`;
- release readiness is `READY_FOR_RELEASE_REVIEW`;
- no blocker remains.

Finding: v1.4 records only the latest verification state for this flow and does not preserve cross-run evidence instability. A later passing run can therefore restore release readiness after a directly observed flaky failure.

`READY_FOR_RELEASE_REVIEW` is not automatic deployment, but it is still too optimistic while required evidence is known to be unstable.

## Interpretation rule

These failures are baseline findings, not reasons to modify expectations to match the implementation. The CI job gates harness health, while legitimate SEF benchmark failures remain visible as data.

No v1.4 runtime fix is introduced by this evaluation slice.
