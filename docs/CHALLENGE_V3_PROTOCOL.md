# CHALLENGE v3 Protocol

CHALLENGE v3 is the final fresh deterministic holdout for the current SEF architecture.

## Frozen candidate

- candidate ref: `candidate/frozen-3630f563`
- candidate commit: `3630f563f24b3577ad1e6a0a05e66a86615dabca`
- canonical runtime SHA-256: `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`
- runtime mutation after freeze: **forbidden**

## Holdout identity

- 10 scenarios
- catalog SHA-256: `acf2d37f2c5692a05acca90b7116b3fd66c10ed1ba103e288596d310d564bacb`
- scenario expectations were written before any v3 execution
- CHALLENGE #1 and CHALLENGE v2 are consumed regression evidence and are not part of this independent verdict

## Execution rule

The first run that satisfies all harness-integrity conditions is the official independent CHALLENGE v3 verdict, regardless of benchmark outcome. A benchmark failure must never be retried as a fresh independent result.

A run is valid only if:

1. the frozen candidate ref resolves to the declared candidate commit;
2. the extracted `sef.py` SHA-256 exactly matches the declared runtime hash;
3. the 10 scenario IDs are unique, complete and match the sealed manifest;
4. the canonicalized scenario catalog hash matches the sealed catalog hash;
5. all 10 scenarios execute exactly once;
6. there are no `HARNESS_ERROR` results;
7. every result reports the exact frozen runtime SHA-256.

## Decision rule

- **10/10 PASS**: deterministic tuning stops; proceed to the real Codex L2 brownfield trial.
- **Any structural critical failure**: deterministic tuning also stops. No CHALLENGE v4 is created. The next step is an architecture-level or constrained-release decision.
- Non-critical failures are recorded as the official verdict and assessed against release scope; they are not silently tuned away under the same architecture without an explicit architecture decision.

After the first valid run, CHALLENGE v3 becomes consumed and may only be replayed as regression evidence.
