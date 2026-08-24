# Semantic Routing v2 — Provider Stability Gate (S5R)

## Why this gate exists

S5 produced one accepted live 35/35 DEV qualification for the OpenAI semantic provider, but the attempted S6 promotion exposed that a single stochastic extraction was not reproducible enough to freeze as an active routing authority.

On S6 PR #44, all deterministic gates were green on head `2b69e16c8074a52d909576afbb1c4d3ac8e486e7`, including the dedicated S6 promotion workflow. The live S5 job nevertheless produced material over-classification. Exactly one diagnostic rerun was permitted without changing code, prompt, corpus, model request or policy rules. It also failed, with a different over-classification profile.

This is evidence of provider-output variance, not evidence that the S5 acceptance contract should be weakened.

## Recorded blocker evidence

- blocked S6 PR: `#44`, closed without merge;
- S6 deterministic workflow: `32704289827`;
- S6 deterministic artifact: `9511648096`, digest `sha256:b6bf2d7523fe7fae45869c9067399d444c2ae897b2dcd51e9e18139914aed4ae`;
- live S5 workflow: `32704289855`;
- first failed live artifact: `9511722508`, digest `sha256:c2cd2a0a0886ffd2074162282005c08c7187a5d2be0dcd8804549311dae75b94`;
- single diagnostic rerun artifact: `9516656933`, digest `sha256:e0cb38fe31c1969ce1c5a3bc245fb158b738698df87e2a7b623a4aede34d5e6a`;
- unchanged S5 replay artifact: `9511647585`, digest `sha256:a569a6a4ea386bcf6c761b8e7807836a949e10ff5d831513eb21f3d20d1a9c23`.

No required safety fact was missed in those two observed failures, but exact resolved fact graphs and negative over-classification controls were not stable. Therefore S6 freeze was correctly blocked.

## Decision

Add a bounded provider-neutral stability boundary before any new S6 promotion attempt.

For each request and project context:

1. run exactly **three independent** semantic extraction samples with the same provider configuration;
2. validate each sample through the existing S2 `ModelAssistedExtractor` boundary;
3. reduce each sample to the policy-relevant semantic view: `review_state` plus the set of material fact kinds;
4. require unanimity across the three policy-relevant views;
5. if the views disagree, emit a valid Semantic IR with material `CONFLICT` uncertainty and `SEMANTIC_REVIEW_REQUIRED`;
6. if a sample is unavailable or invalid, fail closed with review required;
7. only unanimous resolved material semantics may proceed as resolved input to the deterministic S3 composer.

The stability layer does not call the policy composer and cannot emit packs, risk, procedures, implementation approval or release status.

## Why not majority vote, intersection-only or union-only

A majority vote can silently erase a real safety relation if two samples miss it. A raw intersection can do the same. A raw union can convert one stochastic false positive into a permanent material escalation.

S5R therefore uses unanimity for the routing decision. The common material facts may be retained for audit and review, but any disagreement blocks autonomous implementation through the existing deterministic review gate.

## What counts as disagreement

The stability comparison includes only fields that can alter S3 governance today:

- semantic review state;
- material semantic fact kinds.

It intentionally ignores response IDs, fact IDs, provider wording, provenance ordering, notes and non-material facts. Those fields remain useful evidence but must not create routing variance when the deterministic composer does not consume them.

If future composer versions begin consuming additional relation attributes, the stability view must expand before those attributes gain policy authority.

## S5 acceptance remains unchanged

S5R reuses the existing 35-case S5 DEV corpus and its existing expectations:

- exact material fact graph for resolved cases;
- zero-material-fact ceilings for pure negatives;
- required and forbidden facts;
- expected risk and implementation behavior;
- metamorphic invariance;
- ambiguity fail-closed behavior.

A stability conflict does **not** turn a resolved S5 case into a pass. It returns semantic review, so the unchanged S5 expectation fails. This prevents the stability layer from becoming a post-hoc acceptance relaxation.

The single-sample live S5 workflow remains available only as a manual diagnostic. Pull-request promotion uses the three-sample S5R gate.

## Finite qualification policy

This remediation has one bounded live qualification attempt after its code and deterministic controls are complete.

- If the stabilized live S5R run passes the unchanged corpus completely, a new S6 promotion PR may be created from the accepted main state.
- If the stabilized live S5R run fails, do not rerun until pass and do not tune individual failed nouns. Stop provider qualification and make a provider/configuration architecture decision.

There is no S6 freeze and no `SEMANTIC-HOLDOUT-1` until S5R is accepted.

## Required deterministic controls

Before the live S5R run, all of the following must pass:

- frozen v1.5 `sef.py` and `SHA256SUMS` unchanged;
- S0-S4 regressions;
- unchanged S5 replay qualification;
- unanimous resolved samples remain resolved;
- added material fact in one sample -> `CONFLICT` review;
- missing material fact in one sample -> `CONFLICT` review;
- provider unavailable -> review required;
- invalid sample -> review required;
- unanimous ambiguity -> review required;
- sample ordering does not alter stabilized output digest;
- non-material variance does not alter policy-relevant routing;
- exactly three samples are required;
- no direct model or deterministic-composer dependency inside the stability reducer;
- unchanged S5 corpus passes through stabilized replay.

## Release claim

S5R is development qualification, not an independent holdout and not a release. Even a complete S5R pass only reopens S6. The fresh independent `SEMANTIC-HOLDOUT-1`, real Codex L2 and release documentation remain subsequent mandatory gates.
