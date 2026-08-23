# RC-4 Evidence / Release research protocol

Status: frozen before any canonical runtime change.
Base: `main@443a8a0c0fc1d55049f413d51c8a7e68cfcd6c8c`

## Objective
Resolve the two residual Evidence/Release failures identified by the v1.4 root-cause analysis without weakening conservative release safety:

- `EVID-003`: verification command exits successfully, but `verification.status` remains `NOT_RUN` because successful verification is not persisted.
- `REL-004`: local/no-project-command verification is represented as `INCOMPLETE_NO_PROJECT_COMMANDS`; release therefore cannot distinguish "verification was run and passed as far as the project permits" from "verification has not been run".

## Architectural boundary
RC-4 concerns evidence state and release interpretation only. It MUST NOT change:

- RC-1 diff-based routing semantics;
- RC-2 negative-evidence polarity semantics;
- RC-3 task-materiality / `MULTI_TENANT` planning semantics;
- release blocking for genuinely unresolved material confirmations;
- release blocking when verification has genuinely not run;
- project facts or project-profile confirmation state.

## Hypotheses to test

### H1 — durable successful verification evidence
A successful `verify` execution should persist a machine-readable verification record to project state, sufficient for a later `release` invocation to prove that verification ran on the current relevant state.

### H2 — explicit local-pass semantics
When all executable local checks pass but the repository exposes no project-level test/build/lint command, verification should be represented explicitly as a constrained success (for example `LOCAL_PASS` / equivalent structured state), not as an undifferentiated incomplete/not-run state.

### H3 — conservative freshness
Persisted verification evidence must not become a stale universal bypass. Release must reject or downgrade evidence that is not applicable to the current repository/runtime state.

## Frozen behavioral gates

### Treatments
1. Successful verification persists evidence; a subsequent release can observe it.
2. No-project-command verification that passes all available local checks is distinguishable from `NOT_RUN`.
3. `EVID-003` passes without manually editing state.
4. `REL-004` passes when its only missing proof is the no-project-command verification state.

### Controls
1. `release` before any verification remains blocked.
2. Failed verification remains blocked and must not be promoted to success.
3. Unresolved material confirmations remain blocking regardless of verification success.
4. A changed runtime/repository state cannot blindly reuse stale verification evidence.
5. Existing RC-1, RC-2 and RC-3 regression suites must show zero `PASS -> FAIL` regressions.
6. Official DEV must remain 24/24.

## Research sequence
1. Reproduce `EVID-003` and `REL-004` on the exact base commit.
2. Inspect current state schema and release/verify data flow.
3. Build an isolated candidate outside canonical `sef.py` or behind a non-canonical harness.
4. Run treatment + control + stale-evidence/metamorphic probes.
5. Compare against RC-1/RC-2/RC-3 and official DEV.
6. Only if all gates pass: open a separate runtime-integration PR.
7. CHALLENGE remains sealed until RC-4 is merged and post-merge gates are green.

## Decision thresholds
Promote only with:
- 100% treatment pass;
- 100% frozen safety-control pass;
- zero `PASS -> FAIL` on prior RC suites;
- DEV = 24/24;
- explicit stale-evidence protection demonstrated;
- no CHALLENGE inspection or tuning.
