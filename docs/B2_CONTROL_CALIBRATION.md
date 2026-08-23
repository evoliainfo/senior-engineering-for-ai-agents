# B2 acceptance-control calibration

The first isolated B2 candidate run (`32645588198`) preserved DEV 38/38 and B1 10/10. Six B2 positive controls passed. Four negative controls failed for reasons attributable to the control contracts rather than the B2 composition rules.

No runtime or B2 patcher change is made by this calibration.

## Round-1 evidence

- workflow run: `32645588198`
- candidate SHA-256: `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`
- artifact: `9494778073`
- artifact digest: `sha256:889b957d1489e0610b57b3c14d9af7a812e978dc8b45a052c5fdb4d162b96339`
- DEV: 38/38 PASS
- B1: 10/10 PASS
- B2 round 1: 6 PASS / 4 FAIL

## Calibrations

### `B2-DATA-N1`

The request itself contained `no production database or live traffic`, which introduced production/release vocabulary into a control whose intended invariant is simply that a tiny local fixture rewrite must not acquire online-data capacity/release governance. The calibrated request states only the positive local-fixture task. The forbidden packs are unchanged.

### `B2-SUPPLY-N1`

The request explicitly said `do not publish or release it`. This unnecessarily exercised legacy release/polarity behavior instead of the intended B2 invariant: an immutable, local development image should not acquire supply-chain/release governance merely from image semantics. The calibrated request removes the explicit release non-goal. The forbidden packs are unchanged.

### `B2-TRUST-N1`

The request included `the server must never request the destination`, which placed both `server` and a server-fetch verb in the same request and therefore tested a new negation-language variant rather than the intended browser-only boundary. The calibrated request describes the browser-only navigation positively; the project brief still states there is no server-side fetching capability. `WEBHOOK_TRUST` remains forbidden.

### `B2-DIFF-N1`

The initial request mentioned an account-settings page and legitimately routed unrelated UI governance at R2, while the documentation-only actual diff was correctly R0. Exact risk values were not material to the B2 invariant. The calibrated control retains only the requirements that neither initial plan nor actual diff acquire database/release governance and that the actual diff not acquire `DESTRUCTIVE_DATA_CHANGE`.

## Methodological status

Round 1 remains immutable evidence. The calibrated Round 2 does not relax any B2 pack-boundary requirement and does not alter the candidate runtime. It removes incidental assertions that were outside the B2 hypothesis under test.
