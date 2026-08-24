# Semantic Routing v2 — S6 Promotion and Freeze Boundary

## Purpose

S6 promotes Semantic Routing v2 out of shadow-only execution and then freezes one exact candidate for the new independent evaluation program.

This phase does **not** mutate the frozen root-level v1.5 runtime and does **not** create fresh holdout cases.

## Promotion model

Semantic v2 becomes the canonical **semantic-policy** channel through `ActiveSemanticRouter`.

The frozen deterministic v1.5 assessment remains a monotonic safety floor:

- known v1.5 risk may not be reduced by v2;
- known v1.5 packs/procedures may not disappear from the active result;
- a v1.5 implementation block remains a block;
- semantic v2 may add or strengthen governance;
- unresolved or invalid semantic output fails closed;
- a model/provider never emits canonical packs, risk, implementation approval or release approval directly;
- direct repository/diff evidence remains deterministic-first.

The active integration mode is `ACTIVE_V2_HYBRID` and the output schema is `sef.semantic-routing.v2`.

## Release authority

S6 promotion is not release approval. Active routing emits `release_eligible = false` and `release_decision = NOT_RELEASE_AUTHORITY`.

Release-grade claims remain blocked until the fresh post-freeze semantic holdout and real Codex L2 gates pass.

## S5 evidence carried into freeze

The pre-freeze live Semantic DEV qualification used the OpenAI Responses provider with:

- requested model alias: `gpt-5.6`;
- observed model: `gpt-5.6-sol`;
- reasoning effort: `medium`;
- live responses: 35/35;
- case expectations: 35/35 PASS;
- aggregate S5 controls: 47 PASS / 0 FAIL;
- live run: `32675385581`;
- live artifact: `9502550871`;
- live artifact digest: `sha256:d2cdbf0bd8d1f1c1c580ec4f53c5d0977cf635b2c15c8159f49ac0e91afdae85`.

This is DEV evidence only. It is explicitly **not** an independent holdout.

## Freeze procedure

1. S6 promotion controls and all prior deterministic/semantic gates must be green.
2. Merge the promotion PR to `main`.
3. The resulting exact merge commit becomes the v2 frozen candidate.
4. Create an immutable candidate ref named from that commit.
5. Record exact candidate commit, Semantic v2 tree identity, extractor/provider configuration, frozen v1.5 runtime hash and S5 evidence in a freeze manifest.
6. Run a dedicated freeze workflow that verifies the candidate ref and replays deterministic readiness.
7. After freeze, candidate mutation is forbidden.
8. Only then may `SEMANTIC-HOLDOUT-1` be materialized.

## Anti-loop rule

No post-freeze mutation is allowed in response to `SEMANTIC-HOLDOUT-1`. A critical structural failure triggers an architecture/release decision rather than synonym tuning or a hidden replacement candidate.
