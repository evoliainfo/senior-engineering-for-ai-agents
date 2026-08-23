# Semantic Routing v2 — S4 Shadow Integration

## Purpose

S4 runs frozen v1.5 and Semantic Routing v2 in parallel while preserving v1.5 as the only canonical policy authority.

S4 does **not** promote v2, does not change `sef.py`, and does not qualify a live semantic provider. Its purpose is to make disagreements observable and promotion-blocking before any switch-over is considered.

The first real S4 run intentionally remained red when it exposed safety/parity gaps. Its findings and structural remediation are preserved in `docs/SEMANTIC_ROUTING_V2_S4_POSTMORTEM.md`; expectations were not weakened to make the gate pass.

## Shadow record

For each request S4 records:

- the canonical v1.5 observation;
- the exact canonical-output digest;
- Semantic IR and its digest;
- deterministic v2 policy and composition digest;
- risk, pack, governed-procedure and implementation differences;
- classification of the disagreement;
- provenance and semantic uncertainty;
- a promotion-block decision;
- an overall shadow-evidence digest.

## Canonical authority invariant

The canonical result is deep-copied before v2 execution and its digest is checked after v2 execution. A mutation is a runtime error.

`canonical_output_changed` must remain `false` and `v2_policy_authority` must remain `false` throughout S4.

## Disagreement classes

### `AGREEMENT`

Known comparable governance is equivalent.

### `V2_STRONGER_OR_BROADER`

V2 raises risk, adds a governance pack/procedure or blocks implementation more conservatively without losing a known v1.5 safety obligation. This is observable but is not a safety downgrade.

### `SAFETY_DOWNGRADE`

V2 does at least one of the following:

- lowers known v1.5 risk;
- loses a v1.5 governance pack;
- loses a governed v1.5 procedure;
- allows implementation where v1.5 blocks it.

Any such result blocks promotion. S4 contains no automatic waiver mechanism.

### `SEMANTIC_REVIEW_BLOCK`

V2 has material unresolved semantics, or otherwise cannot emit a final comparable risk. It is not silently called a safety downgrade, but promotion is blocked.

### `INVALID_V2_BLOCK`

Semantic IR is invalid. Promotion is blocked.

### `NON_SAFETY_DIVERGENCE`

A difference exists that is not currently classified as a safety downgrade or stronger/broader governance. It remains visible for S5 analysis.

## Procedure comparison boundary

V1.5 may emit baseline procedures that do not yet correspond to a Semantic IR fact family. S4 preserves them in canonical evidence but only compares procedures owned by current S3 deterministic rules. This prevents false downgrade claims from unrelated baseline procedure noise.

A future semantic fact family must extend the deterministic composer before its procedure becomes comparable.

## Authoritative-context parity

S4 showed that matching packs and risk is insufficient if v2 permits implementation where v1.5 blocks pending authoritative context.

S3 therefore now preserves a separate deterministic implementation gate. Access-control boundaries, partition isolation, live-data transformations and the external-authentication composition remain deny-by-default until a future trusted-context mechanism supplies auditable non-provider authority. A semantic model cannot clear this gate itself.

## S4 acceptance

The S4 gate:

1. proves root `sef.py` remains SHA-256 `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee`;
2. replays S0/S1, S2 and S3;
3. runs six real v1.5 black-box plan executions and v2 shadow evaluations on the same requests;
4. requires the known covered relation families to agree on comparable policy;
5. proves canonical v1.5 observations are unchanged;
6. proves provenance is present and shadow evidence is deterministic;
7. injects risk, pack, procedure and implementation downgrades and requires all to block promotion;
8. injects semantic-review and invalid-IR states and requires fail-closed promotion blocking;
9. proves stronger v2 governance is observable without being mislabeled as a safety downgrade;
10. proves aggregate shadow summaries block on any downgrade or unresolved semantic state using an order-independent synthetic control.

## Evidence boundary

S4 uses scripted semantic facts after executing real v1.5 requests. It therefore validates **parallel integration and disagreement governance**, not the semantic quality of an OpenAI or other live provider.

`live_provider_quality_validated` remains `false`.

Live semantic quality belongs to S5 and the later post-freeze independent evaluation program.

## Exit criterion

S4 is complete when its acceptance gate passes on the exact proposed head, all legacy regression gates remain green, and the frozen v1.5 runtime is unchanged.

Only then may S5 build the broader semantic DEV qualification corpus.
