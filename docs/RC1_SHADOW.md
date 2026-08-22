# RC-1 concept normalization — shadow phase

## Purpose

Observe whether a concept-level detector can recognize the six accepted RC-1 concept families without changing authoritative SEF behavior.

## Hard boundary

`rc1_shadow.py` is observational only. Its output MUST NOT be consumed by `sef.py`, the embedded policy runtime, risk classification, required packs, execution contexts, or release decisions during this phase.

The detector emits:

- normalized request text;
- concept observations;
- candidate output IDs;
- exact matched evidence and spans;
- `routing_effect: NONE`.

## Six candidate concepts

1. `AUTHORIZATION` → candidate pack `AUTHORIZATION`
2. `DATABASE_MIGRATION` → candidate pack `DATABASE_MIGRATION`
3. `WEBHOOK_TRUST` → candidate pack `WEBHOOK_TRUST`
4. `EXTERNAL_SUPPLIER` → candidate pack `EXTERNAL_SUPPLIER`
5. `BACKGROUND_JOB` → candidate execution context `BACKGROUND_JOB`
6. `SEO_WEB_DISCOVERABILITY` → candidate execution context `SEO_WEB_DISCOVERABILITY`

## Shadow acceptance gate

Against the contracts frozen before runtime implementation:

- all 12 metamorphic scenarios must emit their intended concept;
- all 12 negative controls must emit zero RC-1 concepts;
- the existing `SHA256SUMS` integrity check and `sef.py self-test` must still pass;
- authoritative v1.4 candidate results remain measurements and are not rewritten by the shadow detector.

Passing this gate is necessary but not sufficient for promotion. Activation into routing requires a separate reviewed PR/change with regression comparison against the frozen baseline.
