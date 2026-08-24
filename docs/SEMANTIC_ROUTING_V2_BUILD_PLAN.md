# Semantic Routing v2 — Finite Build Plan

## Goal

Replace open-ended noun matching with typed semantic relations while keeping governance deterministic and auditable. This is a new architecture line, not a patch to the frozen v1.5 runtime and not CHALLENGE v4.

## Definition of Done

One frozen v2 candidate must satisfy all of these gates:

1. legacy DEV 38/38, B1 10/10, B2 10/10 and RC-8 14/14 remain green;
2. consumed holdouts remain regression-only and pass as regressions;
3. Semantic IR schema and invariants pass completely;
4. open-vocabulary semantic DEV and negative controls pass completely;
5. ambiguity/provider-failure controls fail closed rather than defaulting to low risk;
6. one new post-freeze independent semantic holdout passes its first valid run;
7. real Codex L2 passes the existing brownfield grader for all required trials;
8. release limitations and evaluated provider/model configuration are documented.

## S0 — Contracts before code

Define `sef.semantic-ir.v1`, extractor interface, provenance, uncertainty states and deterministic composer contract. Extractor output must contain semantic facts only; it cannot emit packs, risk or release approval.

## S1 — Deterministic bridge

Convert proven v1.5 observations into Semantic IR in shadow mode. Preserve outputs and evidence exactly. No canonical routing change is allowed yet.

## S2 — Open-vocabulary extractor

Implement `extract(request, project_context) -> SemanticIR` behind a provider-neutral interface.

It must infer relations such as actor-to-scope membership, resource scoping, cross-scope denial, caller-controlled destinations, external operational dependencies and consequential decisions without requiring every domain noun to exist in a governance keyword list.

Invalid or unavailable extraction must be explicit. A material unresolved relation produces `SEMANTIC_REVIEW_REQUIRED`, not an invented R1 result.

## S3 — Deterministic policy composer

Map validated relations to canonical governance. The composer must be deterministic, idempotent, monotonic for safety evidence and independently testable without a live model.

Initial relation families:

- actor/resource scope + cross-scope denial -> authorization and partition isolation;
- caller-controlled server destination -> trust governance;
- independently operated service dependency -> supplier governance;
- consequential person/right decision -> regulated escalation;
- large live data transformation -> migration, capacity and release composition.

## S4 — Shadow integration

Run v1.5 and v2 in parallel and record legacy observations, Semantic IR, v2 governance, disagreements, provenance and uncertainty. Any unexplained safety downgrade blocks promotion.

## S5 — Semantic DEV qualification

Build relation-focused DEV controls with positive, negative and metamorphic variants. Vary domain labels while preserving the relation graph. A department, branch, region or another unseen partition label should not change the expected authorization semantics merely because the noun changes.

`V3-AUTH-002` becomes a consumed regression probe here, never a fresh holdout.

## S5R — Provider stability qualification

Before promotion, a stochastic model-assisted provider must pass a bounded stability gate. Run exactly three independent semantic extractions per DEV case using the same provider configuration. Compare the policy-relevant semantic view: review state and material fact kinds.

- unanimous resolved views may proceed as resolved Semantic IR;
- any material disagreement becomes `CONFLICT` + `SEMANTIC_REVIEW_REQUIRED`;
- unavailable or invalid samples fail closed;
- no majority vote, raw intersection or raw union may silently resolve a disagreement;
- the existing S5 corpus and acceptance expectations remain unchanged.

S5R has one fresh live qualification attempt after implementation and deterministic controls are complete. If it fails, stop rerunning/tuning individual cases and make a provider/configuration architecture decision before another qualification program.

The single-sample S5 live workflow remains diagnostic only after S5R is introduced. It cannot authorize S6 promotion.

## S6 — Freeze v2

Only after all deterministic and semantic DEV gates, including S5R, are green, promote out of shadow mode and freeze one exact candidate, extractor configuration and runtime identity. No candidate mutation is allowed after this point.

## S7 — New independent program

Start a new program such as `SEMANTIC-HOLDOUT-1`; do not call it CHALLENGE v4.

Materialize it only after the v2 freeze. Recommended scope: 12 new cases, at least 6 critical, covering unseen partition labels, object authorization, semantic negatives, trust, supplier dependence, consequential decisions, actual diff and uncertainty/fail-closed behavior.

Target: 12/12 PASS, zero harness errors, first valid run official. A critical structural failure stops tuning of that frozen architecture and triggers another architecture/release decision.

## S8 — Real Codex L2

Use existing `evals/run_l2_brownfield.py` on `BROWN-001` and `BROWN-003`. Both require at least 3 trials.

Release-grade acceptance:

- all required tests and behavior probes pass in every accepted trial;
- required files change and no disallowed application files change;
- protected framework/project files remain unchanged;
- forbidden dependency manifests remain unchanged;
- exact SEF revision, model and agent version are recorded.

The deterministic reference adapter validates only the harness and never counts as real L2 evidence.

## S9 — Release

A stronger non-beta claim requires deterministic closure, the fresh semantic holdout pass, real Codex L2 pass, documented limitations and exact release identity. Otherwise retain the constrained beta claim.

## Anti-loop rule

Any proposed v2 fix that reduces to “add more synonyms until this test passes” fails architecture review before implementation.
