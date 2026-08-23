# RC-4 Runtime Integration Design

Status: implementation gate for RC-4 runtime work.
Base: `main@443a8a0c0fc1d55049f413d51c8a7e68cfcd6c8c`
Research precursor: draft PR #19 (`research/rc4-evidence-release`)

## Purpose
Integrate the validated RC-4 evidence semantics into canonical runtime without changing RC-1 request/diff routing, RC-2 polarity, RC-3 task materiality, or existing conservative release blockers.

The runtime defects addressed are:

1. `EVID-003`: latest-result-only persistence can turn contradictory same-revision `PASS -> FAIL -> PASS` observations into a final apparent pass.
2. `REL-004`: every non-zero command currently becomes `FAIL`, so explicit evidence-source unavailability/inconclusiveness cannot be represented independently from a genuine assertion failure.

## Compatibility constraints

- Existing `.sef/state.json` files may contain `last_verification` only.
- `last_verification` remains a compatibility summary/output field.
- New release decisions MUST NOT trust a legacy unbound `last_verification` as sufficient proof for the current revision.
- Existing verification states and `INCOMPLETE_NO_PROJECT_COMMANDS` behavior are not redefined by this change unless required for aggregation; RC-4 is not a project-command-discovery change.
- Existing unresolved material confirmations remain release blockers.
- Dirty worktree remains a release blocker.
- No stderr/stdout keyword parsing may manufacture `UNAVAILABLE` or `INCONCLUSIVE`.

## State model

Add a bounded append-only state field:

```json
{
  "verification_evidence": [
    {
      "revision": "<git HEAD sha>",
      "attempt_id": "<stable id for this verify invocation>",
      "recorded_at": "<UTC timestamp>",
      "check_id": "<stable check identity>",
      "required": true,
      "state": "PASS|FAIL|UNAVAILABLE|INCONCLUSIVE|NOT_RUN|WAIVED",
      "source": "command|adapter|runtime",
      "command": "<optional normalized command>",
      "returncode": 0,
      "detail": "<bounded diagnostic detail>"
    }
  ]
}
```

`FLAKY` is a derived aggregate, not a raw command observation.

### Bound and retention

Keep a bounded ledger (initially 256 observations) to prevent state-file growth. Eviction is oldest-first. The current-revision summary is materialized into `last_verification`, but release recomputes/validates from ledger evidence when ledger support is present.

## Revision identity

Use exact `git rev-parse HEAD`. If revision identity cannot be established, verification evidence cannot be considered release proof; release remains conservative.

A dirty worktree is already separately blocking. RC-4 does not attempt to hash all uncommitted files into evidence identity.

## Check identity

Each executed project/runtime check receives a deterministic `check_id` derived from its logical role plus normalized command. The same logical check on the same revision aggregates across verify attempts.

## Raw outcome normalization

For ordinary shell commands:

- return code `0` => `PASS`
- non-zero => `FAIL`
- not executed => `NOT_RUN`

`UNAVAILABLE` and `INCONCLUSIVE` require an explicit structured adapter/evidence result. Plain stderr/stdout text is never used for classification.

The initial runtime integration MAY expose the structured state normalization helper before any first-party provider adapter uses it. That preserves conservative behavior for all existing command execution while making REL-004 representable through a machine-readable contract.

## Aggregation

Scope evidence by exact revision and deterministic `check_id`.

For each required check on the current revision:

1. both `PASS` and `FAIL` observed => `FLAKY`
2. otherwise any `INCONCLUSIVE` => `INCONCLUSIVE`
3. otherwise any `UNAVAILABLE` => `UNAVAILABLE`
4. otherwise any `FAIL` => `FAIL`
5. otherwise all relevant concrete observations `PASS` => `PASS`
6. no evidence => `NOT_RUN`

A later same-revision pass does not erase an earlier contradictory fail.

A new revision is an explicit reset boundary because evidence from the previous revision does not satisfy current-revision release proof.

## Release semantics

Required evidence states:

- `PASS` => evidence gate may pass
- `NOT_RUN` => block
- `FAIL` => block
- `FLAKY` => block
- `UNAVAILABLE` => block
- `INCONCLUSIVE` => block

`WAIVED` is not silently equivalent to `PASS`; it is allowed only when an existing explicit policy says that the specific non-critical evidence is waivable. RC-4 introduces no broad waiver path.

Additional pre-existing release blockers remain additive.

## Legacy migration

When `verification_evidence` is absent:

- initialize it lazily on the next `verify` run;
- retain legacy `last_verification` for observability/backward-compatible display;
- release MUST require fresh revision-bound evidence before treating verification as passing.

This deliberately favors a one-time fresh verification over silently accepting unverifiable legacy evidence.

## Failure containment

If ledger persistence fails, the runtime must not report a stronger release-ready state than the evidence it can persist.

If aggregation sees an unknown state, treat it conservatively as `INCONCLUSIVE`/blocking rather than passing.

## Test gates before merge

1. same revision `PASS -> FAIL -> PASS` => derived `FLAKY`, release blocked;
2. explicit adapter `UNAVAILABLE` => release blocked and not rewritten to `FAIL`;
3. plain non-zero command with stderr containing "unavailable" => ordinary `FAIL`;
4. genuine regression => `FAIL`;
5. prior-revision evidence cannot satisfy current revision;
6. fresh all-pass current-revision evidence => pass;
7. unresolved material confirmations remain blocking;
8. dirty worktree remains blocking;
9. legacy state without ledger requires fresh verification;
10. ledger remains bounded;
11. RC-1, RC-2, RC-3 permanent/shadow regression gates remain green;
12. official DEV remains 24/24;
13. CHALLENGE remains sealed throughout implementation and validation.

## Promotion rule

Do not merge unless every frozen RC-4 treatment/control and all pre-existing RC regression gates pass on the exact integration HEAD with zero `PASS -> FAIL` regressions.
