# Semantic Routing v2 — S5 Semantic DEV Qualification

## Purpose

S5 qualifies relation extraction and deterministic policy composition on a broader **development** corpus before any v2 freeze.

It is not an independent holdout. No S5 result may be represented as `SEMANTIC-HOLDOUT-1` evidence.

The frozen v1.5 root runtime remains canonical and unchanged throughout S5.

## Evidence layers

S5 deliberately separates two evidence classes.

### 1. Replay DEV qualification

`evals/run_semantic_v2_s5.py --provider replay` validates:

- corpus integrity and development-only labeling;
- exact Semantic IR relation graphs for resolved controls;
- zero-material-fact negative controls;
- ambiguity fail-closed behavior;
- deterministic policy composition;
- metamorphic invariance across changed domain labels;
- consumed holdout handling;
- no corpus-specific noun whitelist in the live provider adapter.

Replay mode proves the evaluation contract and semantic-policy pipeline. It **does not** prove model quality and always reports `live_provider_quality_validated = false`.

### 2. Live OpenAI DEV qualification

`evals/run_semantic_v2_s5.py --provider openai` sends the same 35 DEV cases through `OpenAIResponsesSemanticProvider`, then through the existing untrusted-provider wrapper and deterministic composer.

The adapter uses structured JSON output but retains no policy authority. The model may emit only semantic facts, uncertainty and completeness. `ModelAssistedExtractor` still validates and normalizes its output before S3 composition.

A live PASS is valid only when:

- every one of the 35 DEV cases passes its semantic and policy expectations;
- all metamorphic groups are invariant;
- all negative controls avoid material over-classification;
- all ambiguity controls return `SEMANTIC_REVIEW_REQUIRED`;
- the exact requested and observed model identity is recorded;
- provider response IDs and usage metadata are preserved in the artifact;
- the job actually executed with a real credential.

If no credential is available, the workflow records `NOT_RUN`; it must never silently substitute replay evidence.

## Corpus design

The corpus contains 35 cases across:

- business-partition authorization;
- object authorization;
- authorization negatives;
- server-side destination trust;
- trust negatives;
- external operational suppliers;
- supplier negatives;
- consequential human-impact decisions;
- regulated-sector arithmetic negatives;
- large live-data transformations;
- non-live data negatives;
- external authentication composition;
- material semantic ambiguity.

### Metamorphic groups

The same underlying relation graph is expressed with different labels and domain surfaces:

- `AUTH-PARTITION`: 8 variants;
- `AUTH-NEGATIVE`: 3 variants;
- `TRUST-DESTINATION`: 4 variants;
- `TRUST-NEGATIVE`: 2 variants;
- `REG-DECISION`: 3 variants;
- `REG-ARITHMETIC-NEGATIVE`: 3 variants;
- `DATA-LIVE`: 2 variants.

A label change must not change the normalized semantic-policy result when the relation graph is the same.

## Consumed CHALLENGE v3 regression

`V3-AUTH-002` is copied into S5 only as a **consumed regression probe**.

The exact project brief and request are protected by source digest:

`f47cf769e78c97e9898a4a4a38cc726d435374069903ae74ce36936490e62743`

It retains the label `consumed_regression = V3-AUTH-002` and cannot be used as fresh independent evidence.

## Exact graph rule

For resolved DEV controls, S5 requires the material fact graph to equal the expected fact set, not merely contain it.

This intentionally catches both classes of model error:

1. **under-classification** — a required relation is missing;
2. **over-classification** — the model invents an additional material relation.

Pure negative controls additionally impose `max_material_facts = 0`.

## Ambiguity rule

Material ambiguity must not be guessed through.

The three ambiguity controls require:

- `review_state = SEMANTIC_REVIEW_REQUIRED`;
- final policy `risk = null`;
- implementation blocked;
- no independent-release claim.

## OpenAI provider adapter

`semantic_v2/openai_responses_provider.py` is one replaceable implementation of the provider-neutral S2 contract.

It:

- calls the OpenAI Responses API;
- requests schema-constrained semantic output;
- defines typed semantic relations by meaning rather than corpus noun lists;
- preserves open-vocabulary labels in semantic attributes;
- records provider response identity and usage;
- never emits or decides packs, risk, procedures, implementation approval or release status.

No API key is committed or logged.

## S5 acceptance states

### `PASS` replay + `PASS` live

S5 semantic DEV qualification is complete and S6 freeze planning may begin, subject to all legacy deterministic gates remaining green.

### `PASS` replay + `NOT_RUN` live

S5 infrastructure and deterministic DEV corpus are integrated, but **S5 is not complete for provider qualification**. Do not freeze a provider-qualified v2 candidate yet.

### replay or live `FAIL`

S5 remains open. Diagnose relation-level causes. Do not fix failures by adding a noun/synonym whitelist.

## Anti-loop rule

A proposal that amounts to “add the failed word to a keyword list” fails architecture review.

DEV failures may improve relation definitions, provider instructions, uncertainty handling or typed composition because S5 is a development corpus. After S6 freeze, the independent program is created fresh and cannot be used for tuning the frozen candidate.
