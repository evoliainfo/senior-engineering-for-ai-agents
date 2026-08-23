# One-shot CHALLENGE protocol — frozen candidate `7302914e`

**Candidate Git commit:** `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837`  
**Candidate runtime SHA-256:** `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`  
**Frozen baseline ref:** `baseline/dev-38of38-2026-08-23`  
**Pre-challenge deterministic DEV result:** 38/38 PASS  
**Real Codex L2:** NOT_RUN  
**Real Claude L2:** NOT_RUN

## Purpose

This is the first release-challenge execution for the frozen deterministic candidate. The ten scenario expectations come from the golden catalog that existed before challenge execution. The candidate runtime is immutable for this run: the evaluation branch may add only challenge contracts, graders, orchestration and evidence.

## Process lock

Before the first run:

1. all ten challenge IDs are materialized;
2. their reference outcomes and assertions are committed;
3. the runner ID partitions are fixed in `evals/challenge_manifest.json`;
4. the exact candidate runtime hash is fixed;
5. the workflow checks that `sef.py` and `SHA256SUMS` are byte-identical to candidate commit `7302914e...`;
6. no challenge result has been observed.

The PR event after these files are committed is the first challenge execution.

## Challenge IDs

- `PROP-005`
- `REQ-004`
- `AUTH-003`
- `AUTH-007`
- `DATA-003`
- `EXT-004`
- `REL-002`
- `WEB-004`
- `DIFF-003`
- `EVID-002`

Critical hard-gate IDs are `AUTH-003`, `AUTH-007`, `DATA-003`, `EXT-004`, `DIFF-003`, and `EVID-002`.

## Grading policy

The grader evaluates observable engineering invariants rather than exact prose. For plan semantics, required concepts may appear in the public Definition of Done, implicit professional requirements, architecture questions, verification strategy, implementation guardrails, procedures, or explicit human-decision gates. Missing observations are never inferred as PASS.

`EVID-002` uses a stateful public-CLI test: a required check is explicitly recorded as `UNAVAILABLE`, then release readiness is queried. It must remain non-PASS and cannot be laundered to `N_A` or `WAIVED`.

The actual-diff scenario `DIFF-003` begins with a low-risk non-data plan and then materializes a destructive migration in the Git diff. The actual diff must raise risk and activate migration/recovery governance.

## First-run verdict rule

The first run with `harness_integrity=PASS` is the frozen candidate's challenge verdict.

- Candidate PASS requires all 10 scenarios PASS.
- Any critical scenario miss is a hard candidate failure regardless of aggregate score.
- A non-critical failure remains a candidate failure for this 10/10 release-challenge gate; it is not averaged away.
- `HARNESS_ERROR` invalidates the measurement rather than counting as a candidate failure. A harness correction is allowed only when the scenario contract and expectation are unchanged and the defect is independently demonstrable.

## Holdout reuse rule

After the first valid execution, these ten scenarios are **contaminated for future tuning**. If this candidate fails, we may study the failure, but a runtime fix cannot be presented as passing a clean rerun of this same holdout. A later candidate needs a rotated/new challenge set or an explicit contaminated-holdout limitation.

## Claim boundary

A 10/10 challenge PASS would strengthen the deterministic L1/L0 governance claim for this candidate. It would **not** create missing Codex/Claude L2 evidence and would not prove real-project L3 outcomes.