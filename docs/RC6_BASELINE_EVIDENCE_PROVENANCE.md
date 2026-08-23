# RC-6 — Baseline vs candidate evidence provenance

Targets: `EVID-005` and `BROWN-002`.

## Problem
SEF can observe a failing required check, but before RC-6 it does not structurally distinguish a failure already observed on an ancestor baseline from a failure first observed on the candidate revision.

## Contract
For verification of a candidate diff (`verify --base <ref> --run`), SEF may use only revision-bound verification evidence from `<ref>` or its Git ancestors to build a comparison baseline.

The result must expose machine-readable fields that distinguish:
- `preexisting_failures`: required checks already non-passing on the nearest comparable ancestor evidence and still non-passing now;
- `candidate_regressions`: required checks newly non-passing on the candidate relative to that baseline;
- `resolved_baseline_failures`: baseline failures that are now passing/not present;
- `baseline_comparison`: exact baseline evidence revision and comparison-base revision;
- `residual_limitations`: explicit caveat that matching check identity does not prove identical failure cause.

## Safety boundaries
- No old evidence from a non-ancestor revision may be treated as candidate baseline.
- Absence of comparable ancestor evidence remains explicit; it must not imply a clean baseline.
- This classification does not turn a failing repository into PASS.
- Release semantics remain conservative and unchanged.
- RC-1 through RC-5 behavior must remain stable.
- CHALLENGE remains sealed.

## Admission gates
1. `EVID-005` PASS.
2. `BROWN-002` PASS.
3. Full DEV moves from 35/38 to at least 37/38 with only `EVID-004` remaining.
4. No new critical or prior PASS regression.
5. Runtime/self-test/checksum and RC-1..RC-5 gates remain green.
