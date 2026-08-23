# RC-7 — Explicit waiver semantics

Target: `EVID-004`.

## Contract

SEF may record an authorized waiver only for a **known optional/non-critical check** on the current exact Git revision.

A waiver must be:
- explicit (`WAIVED`, never normalized to `PASS`);
- revision-bound;
- check-bound;
- reasoned (non-empty human reason);
- attributed (`authorized_by` recorded);
- visible in machine-readable output and persisted state.

## Safety boundaries

- Required checks cannot be waived through this interface.
- A waiver never changes raw command/evidence observations into PASS.
- A waiver for an old revision does not apply to a new revision.
- Unknown checks cannot be waived before they exist as optional evidence.
- `authorized_by` is recorded operator-supplied provenance; SEF does not claim cryptographic identity verification.
- Release remains blocked whenever required evidence is not PASS.
- RC-1 through RC-6 semantics remain unchanged.
- CHALLENGE remains sealed.

## Public interface

Proposed bounded command:

`sef.py waive-evidence <repo> <check_id> --reason <text> --authorized-by <identity>`

The command succeeds only if the current revision already contains the check in revision-bound evidence and that check is explicitly optional.

## Admission gates

1. `EVID-004` exercises the public interface and observes `WAIVED` distinct from `PASS` with reason/authorization visible.
2. Attempt to waive a required check is BLOCKED.
3. Attempt to waive an unknown check is BLOCKED.
4. Missing reason or authorization is BLOCKED.
5. Waiver does not survive revision change as active evidence.
6. Full 38-scenario DEV = 38/38 with zero critical failures and CHALLENGE still sealed.
7. RC-1..RC-6 and runtime validation remain green.
