# ADR: Evidence-Matrix Semantic Provider for Semantic Routing v2

Status: PROPOSED_FOR_QUALIFICATION  
Date: 2026-08-24  
Base main: `9244c7e20b7eadf25acfcfa77d5dfa8bb4b5aa09`

## Context

Semantic Routing v2 deliberately separates semantic extraction from deterministic governance composition. The provider may identify semantic relations, but only deterministic code may choose packs, risk, implementation gates, or release status.

S5 previously produced one valid 35/35 live OpenAI qualification on `gpt-5.6` (observed `gpt-5.6-sol`). During attempted S6 promotion, subsequent unchanged live executions were not exactly reproducible. PR #45 therefore introduced a pre-registered three-sample unanimity reducer and one bounded S5R qualification.

PR #45 official S5R evidence:

- head: `43476380cc252677009348647f1d345b55e13281`
- workflow run: `32718870098`
- deterministic job: `97405831150` SUCCESS
- live job: `97405900837` FAILURE
- live artifact: `9517158994`
- live artifact digest: `sha256:e18fc7dba8e5b67cc2826f1acfc19f98d056d1e70d098349c26b296ef522408a`
- deterministic artifact: `9516966567`
- deterministic artifact digest: `sha256:2ff921ba0f048e9e33d85ab26c281251f0f8e561e92c1ff5f31e83a9b80ab287`
- requested model: `gpt-5.6`
- observed model: `gpt-5.6-sol`
- 35 cases, 3 samples per case, 105/105 live responses
- 32/35 semantic cases satisfied the unchanged S5 expectation
- three cases produced material disagreement between samples
- no provider outage, no missing credential, no corpus change, no policy-rule change, no frozen v1.5 runtime change

The disagreements were conservative over-classifications rather than missed required protections:

1. `S5-AUTH-OBJECT`: all samples found `ACCESS_CONTROL_BOUNDARY`; two additionally emitted `PARTITION_ISOLATION`.
2. `S5-TRUST-TENANT-PROXY`: all samples found `SERVER_DESTINATION_TRUST`; one additionally emitted `PARTITION_ISOLATION`.
3. `S5-TRUST-NEG-FIXED-INTERNAL`: two samples emitted no material fact; one additionally emitted `ACCESS_CONTROL_BOUNDARY`.

The S5R reducer behaved safely by returning `SEMANTIC_REVIEW_REQUIRED`, but the provider/configuration failed the pre-registered exact-resolved reproducibility contract. PR #45 was therefore closed unmerged. S6 freeze and `SEMANTIC-HOLDOUT-1` remain blocked.

## Problem statement

The current provider contract asks a generative model to return an open list of semantic facts. Even with strict JSON schema, the model must decide both:

1. which ontology relations to consider; and
2. which considered relations to emit.

This permits semantically plausible secondary facts to appear intermittently. Repeating the same free-list extraction three times detects the variability, but does not address its source.

The architecture needs a more explicit, auditable decision boundary without returning to business-noun whitelists or allowing a model to choose governance outcomes.

## Decision

Introduce a provider-level **evidence matrix** over the existing closed semantic fact ontology.

Instead of asking the provider to freely list whatever facts it notices, the provider must assess **every supported semantic fact kind** using a fixed tri-state decision:

- `PRESENT`
- `ABSENT`
- `UNCERTAIN`

Each row must also contain provenance/evidence derived from the request or project context. Literal business labels remain open vocabulary and are preserved as evidence/attributes; they are not routing keys.

The evidence-matrix adapter then deterministically converts provider rows into the existing `sef.semantic-ir.v1` representation:

- `PRESENT` -> semantic fact
- `ABSENT` -> no fact
- `UNCERTAIN` -> material semantic uncertainty when the relation can affect governance
- malformed/incomplete matrix -> fail closed

The existing deterministic S3 policy composer remains the only authority for governance packs, risk, procedures, implementation gates, and release status.

## Why this is not keyword tuning

The ontology fact kinds are intentionally closed engineering concepts. The rejected failure mode was a bounded list of business nouns such as department, branch, region, or tenant deciding policy.

The evidence matrix does not enumerate business vocabulary. It asks the provider to evaluate stable semantic relations such as access-control boundary, partition isolation, server-destination trust, consequential decision, or live-data transformation regardless of the literal names used in the brief.

## Provider output contract v2

Conceptual row shape:

```json
{
  "kind": "PARTITION_ISOLATION",
  "decision": "PRESENT | ABSENT | UNCERTAIN",
  "material": true,
  "subject": "... or null",
  "object": "... or null",
  "evidence": [
    {
      "source_kind": "request | project_context",
      "locator": "...",
      "support": "concise source-grounded explanation"
    }
  ],
  "labels": [],
  "notes": []
}
```

The matrix must contain exactly one row for every supported semantic fact kind. Duplicate, omitted, unknown, or policy-authority fields invalidate the provider output.

## Invariants

1. No model-to-pack path.
2. No model-to-risk path.
3. No model-to-release path.
4. `sef.py` and the frozen v1.5 checksum remain unchanged during provider qualification.
5. Open-vocabulary literal scope labels remain allowed.
6. No S5 case noun may be added as a routing synonym or special case.
7. Provider output is untrusted and schema validated.
8. Missing/duplicate ontology rows fail closed.
9. `UNCERTAIN` on a material relation cannot silently become READY.
10. Provider/model metadata changes cannot alter deterministic policy composition for the same validated Semantic IR.
11. S5 is now development/regression evidence only; it cannot become a fresh independent holdout.
12. The official S5R failure remains immutable and is never relabeled as PASS.

## Qualification plan

### E0 — contract controls

Deterministically prove:

- exact ontology coverage;
- no duplicate/missing rows;
- forbidden policy-authority injection rejection;
- evidence/provenance validation;
- malformed provider output fails closed;
- conversion to `sef.semantic-ir.v1` is deterministic;
- row ordering does not affect the IR digest;
- literal business labels do not affect relation dispatch;
- `ABSENT` cannot become a fact;
- `UNCERTAIN` cannot become READY.

### E1 — unchanged S5 replay

Use the existing 35-case S5 corpus as consumed development evidence. Do not alter its cases or expected semantic relations to fit new outputs.

The matrix implementation must preserve required protections and negative controls. Any behavioral change must be explained at the architecture level, not by adding case-specific vocabulary.

### E2 — bounded live development qualification

Only after E0/E1 pass, run one pre-registered live qualification using the evidence-matrix provider. Record:

- exact requested and observed model;
- exact provider schema/version;
- exact prompt/instruction digest;
- exact case count;
- response count;
- required-fact misses;
- forbidden/negative false positives;
- `UNCERTAIN`/review count;
- invalid-provider-output count;
- artifact digest.

Do not rerun until green.

### E3 — S6 freeze candidate

S6 promotion may be reconsidered only if the evidence-matrix provider passes its pre-registered development gate and all deterministic S0-S5 regressions remain green.

### E4 — fresh independent semantic holdout

Only after S6 freeze create a new independent holdout. It must not reuse S5 cases or the consumed deterministic challenge catalogs.

## Acceptance philosophy

The objective is not to force a stochastic model to emit byte-identical prose. The objective is to make the **policy-relevant semantic decision surface explicit and measurable**.

A valid production architecture may intentionally return `SEMANTIC_REVIEW_REQUIRED` for genuinely unresolved material relations. However, review behavior must be pre-registered and bounded before a fresh holdout; a failed historical contract may not be retroactively weakened to manufacture a pass.

## Rejected alternatives

### Keep rerunning three free-list samples until all agree

Rejected. This creates qualification-by-luck and violates the finite evaluation policy.

### Majority vote over three free-list samples

Rejected. A 2/3 vote can silently discard a real material relation or silently accept a spurious one without an explicit evidence model.

### Union of all sampled facts

Rejected. Safe in one narrow sense but can create unbounded over-classification and unusable review/risk inflation.

### Intersection of sampled facts

Rejected. Can remove a material relation seen by only one sample and therefore under-classify risk.

### Add nouns from failed S5 cases to the prompt

Rejected. That recreates the lexical brittleness Semantic Routing v2 was designed to replace.

### Change S5 expectations after observing the failures

Rejected. S5 and S5R are consumed development evidence. Historical verdicts remain immutable.

## Consequences

Positive:

- every ontology relation is explicitly considered;
- positive, negative, and uncertain judgments become symmetric;
- provider behavior is easier to audit and compare between models;
- secondary fact additions are visible as row-level decision changes;
- no business-noun whitelist is introduced;
- deterministic governance authority remains intact.

Costs:

- larger structured outputs;
- potentially higher token cost;
- more provider contract code and tests;
- live evaluation must be requalified before S6.

## Current release state

- `main`: remains at the qualified S5/shadow state; no #44 or #45 promotion code merged.
- frozen v1.5 deterministic runtime: unchanged.
- S6 freeze: blocked.
- `SEMANTIC-HOLDOUT-1`: not created/not consumed.
- real Codex L2: not yet release-qualifying.
- release: not eligible yet.
