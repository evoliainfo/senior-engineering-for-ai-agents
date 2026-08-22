# RC-1 Candidate Architecture — Deterministic Task-Concept Normalization

Status: DESIGN CANDIDATE — REVIEWED, PRE-IMPLEMENTATION GATE

Baseline: SEF `v1.4.0-beta` runtime remains unchanged.

Decision target: RC-1 only — brittle request routing caused by direct surface-text-to-trigger matching.

This document is a design gate. It does not authorize or implement a runtime change.

## 1. Problem statement

SEF v1.4 currently maps request text directly to routing triggers through regular-expression matches. That design is deterministic and auditable, but the semantic boundary is too close to surface wording.

The locked benchmark and independent root-cause probes demonstrate that semantically equivalent requests can route differently because of morphology, lexical choice or ordinary user phrasing. Confirmed examples include authorization, data migration, webhook/event intake, external suppliers, background work and search discoverability.

RC-1 is therefore not simply "missing synonyms". The architectural defect is the absence of a stable intermediate representation between user language and governance policy.

Desired flow:

```text
raw request
    ↓
deterministic lexical normalization
    ↓
canonical task concepts + evidence
    ↓
explicit compatibility mapping
    ↓
existing triggers / task contexts
    ↓
existing packs / risk / procedures
```

Governance decisions remain deterministic, explainable and fail-safe.

## 2. Goals and invariants

The RC-1 candidate MUST:

1. recognize materially equivalent task intent across bounded lexical and morphological variants;
2. create a stable canonical concept boundary before risk/policy routing;
3. preserve deterministic and inspectable policy decisions;
4. emit evidence explaining every concept detection;
5. preserve current trigger/context/pack semantics unless separately reviewed;
6. preserve independent actual-diff reassessment;
7. avoid network calls, model calls and nondeterministic dependencies;
8. support English and French at least to the level already claimed by current routing;
9. avoid broad stemming/fuzzy matching that materially increases over-routing;
10. remain compatible with the single-file SEF distribution/bootstrap invariant;
11. make registry validity machine-checkable at self-test/CI time;
12. define deterministic merge/deduplication semantics between legacy and concept-derived routes.

## 3. Non-goals

This candidate does NOT solve:

- RC-2 polarity/negation;
- RC-3 task-materiality of project-level context;
- RC-4 evidence history/state semantics;
- free-form LLM semantic classification;
- automatic policy learning;
- probabilistic security decisions;
- wholesale trigger/pack renaming;
- governance-engine rewrite;
- changes to immutable `v1.4.0-beta`.

RC-2 remains isolated: a concept inside negated text may still be detected during RC-1. No suppression rule is introduced in this patch family.

## 4. Options considered

### A. Add alternatives to existing routing regexes

Rejected as the architecture. It fixes sentences while preserving lexical-policy coupling and encourages benchmark-specific hard-coding.

### B. Generic stemming/fuzzy matching

Rejected for the first candidate. Broad suffix stripping/edit distance/substrings increase false positives and weaken explainability.

### C. LLM/NLP classifier before hard policy routing

Rejected for the deterministic core. Model/version drift, latency, external dependency and probabilistic behavior are inappropriate for the hard safety-routing boundary. A future advisory layer could be evaluated separately but cannot silently replace deterministic routing.

### D. Deterministic canonical task-concept normalization

Selected. Bounded lexical/compositional evidence maps to canonical concepts; a separate compatibility adapter maps concepts to existing triggers/contexts; existing policy remains downstream.

## 5. Proposed components

### 5.1 Deterministic text normalization

Pure preprocessing retains offsets to raw text and may perform:

- Unicode NFKC normalization;
- case-folding;
- stable whitespace normalization;
- semantics-preserving punctuation normalization;
- tokenization with offsets;
- selected hyphen/space normalization.

Not allowed initially: uncontrolled stemming, fuzzy edit distance, embeddings, external NLP libraries or model inference.

### 5.2 Canonical concept registry

Initial scope is limited to six demonstrated families:

| Concept | Meaning | Compatibility target |
| --- | --- | --- |
| `AUTHORIZATION_CHANGE` | role/permission/object-access semantics | `AUTHZ_CHANGED` |
| `DATABASE_STATE_MIGRATION` | migration/backfill/transformation of stored state | database migration routing |
| `INBOUND_PROVIDER_EVENT` | externally initiated callback/webhook/event reception | `INBOUND_WEBHOOK_ADDED` |
| `EXTERNAL_SERVICE_DEPENDENCY` | new/material third-party/SaaS/vendor dependency | external supplier governance |
| `BACKGROUND_PROCESSING` | queue/worker/consumer/background execution | `BACKGROUND_JOB` task context |
| `SEARCH_DISCOVERABILITY` | public content intended to be found through search engines | `SEO_WEB_DISCOVERABILITY` task context |

A concept definition may contain direct lexemes, explicitly safe morphology, bounded compositional rules, English/French variants and stable rule IDs.

Broad words such as `find`, `worker`, `vendor`, `service`, `admin`, `change` or `Google` MUST NOT independently activate a high-impact concept unless independently specific. Broad cues require composition.

### 5.3 Machine-checkable registry schema

The implementation MUST represent registry entries with a validated internal schema. The concrete Python representation may vary, but every concept definition MUST expose equivalent fields to:

```text
concept_id        stable unique identifier
rules[]           non-empty list of lexical/compositional rules
rule_id           globally unique stable identifier
rule_kind         DIRECT | MORPHOLOGY | COMPOSITE
language          EN | FR | BOTH
strength          DIRECT | COMPOSITE
policy_mapping    NOT ALLOWED HERE
```

Registry validation MUST fail self-test/CI for:

- duplicate concept IDs;
- duplicate rule IDs;
- unknown rule kinds/languages;
- empty rule definitions;
- unsupported normalization operators;
- embedded pack names, risk levels, procedure names or release decisions inside lexical rules;
- compatibility mappings targeting unknown triggers/contexts.

The lexical registry answers only **what concept is expressed**. Policy semantics belong exclusively to the compatibility/policy layer.

### 5.4 Concept evidence

Every emitted concept MUST carry inspectable evidence equivalent to:

```json
{
  "concept": "AUTHORIZATION_CHANGE",
  "rule_id": "authz.permission-role.v1",
  "source": "request",
  "matched_text": "...",
  "start": 42,
  "end": 61,
  "strength": "DIRECT"
}
```

`strength` is categorical/deterministic, not probabilistic confidence.

### 5.5 Compatibility adapter

Concepts MUST NOT choose specialist packs directly. A small explicit adapter maps canonical concepts to existing request triggers and/or task execution contexts.

Example:

```text
AUTHORIZATION_CHANGE -> trigger AUTHZ_CHANGED
INBOUND_PROVIDER_EVENT -> trigger INBOUND_WEBHOOK_ADDED + contexts INBOUND_WEBHOOK,PUBLIC_API
SEARCH_DISCOVERABILITY -> context SEO_WEB_DISCOVERABILITY
```

If faithful mapping requires a policy-semantic change, implementation stops and raises a separate architecture/policy decision.

### 5.6 Deterministic merge and deduplication contract

During the additive migration, legacy request routing and concept-derived routing coexist. Their merge semantics MUST be explicit:

1. evaluate legacy request routing and concept routing independently from the same raw request;
2. preserve source attribution for every emitted trigger/context;
3. union trigger IDs and task-context IDs by canonical identifier;
4. duplicate emission MUST NOT duplicate downstream packs/procedures or inflate risk merely because two detectors found the same semantic route;
5. concept-derived routes may ADD a missing request route but may not REMOVE or downgrade a legacy route;
6. if two routes imply different downstream controls, existing governance aggregation remains authoritative;
7. ordering of registry definitions or detector execution MUST NOT change the final canonical route set;
8. actual-diff findings are merged through their existing independent path and can never be suppressed by request-route deduplication.

Required first-candidate property:

```text
candidate_request_routes ⊇ legacy_request_routes
```

This is a migration invariant, not a permanent requirement after later separately-reviewed de-duplication.

### 5.7 Existing governance engine

After compatibility mapping/merge, current pack/risk/procedure logic remains authoritative. RC-1 MUST NOT create a second policy engine.

### 5.8 Actual-diff isolation

Required invariant:

```text
request normalization -> request concepts -> request routing

actual diff analysis -----------------------> independent diff routing
```

Request normalization, future polarity rules, ambiguity or detector failure cannot downgrade a sensitive actual-diff finding.

## 6. Rule-design constraints

- Prefer semantic families over benchmark phrases.
- Use controlled morphology only when ambiguity is low.
- Require bounded composition for broad cues.
- Rule evaluation/deduplication is deterministic.
- No pack/risk/procedure meaning in lexical rules.
- No global fuzzy substring matching.
- No catastrophic regular expressions.

Examples appropriate for controlled handling include webhook/webhooks, permission/permissions, role/roles, and migration/migrate only with required state/database context where necessary.

## 7. Execution flow

```text
1. Receive request + project context
2. Preserve raw request
3. Build normalized request representation
4. Detect canonical task concepts
5. Record concept evidence
6. Map concepts to legacy/current triggers + task contexts
7. Merge/deduplicate with legacy request signals under the explicit contract
8. Run current pack/risk/procedure engine
9. Independently reassess actual diff later
10. Never let request normalization downgrade actual-diff findings
```

## 8. Migration stages

### Stage 1 — shadow observation

Preferred when implementation cost remains proportionate:

- compute concepts and compatibility routes;
- keep legacy routing behavior authoritative;
- compare legacy versus concept-derived route sets;
- expose comparison only through diagnostic/machine-readable evaluation output, not by changing normal CLI text.

### Stage 2 — additive behavior

Concept mapping may add missing request triggers/contexts but cannot remove legacy routes. This is the first behavioral candidate.

### Stage 3 — legacy lexical de-duplication

Only after separately reviewed evidence, including held-out/pilot evidence. Not part of first RC-1 implementation.

## 9. Shadow/additive telemetry compatibility contract

The implementation MUST make concept behavior observable without breaking the existing public CLI contract.

Preferred contract:

- default human-facing output remains backward-compatible;
- existing JSON keys retain their meaning;
- concept evidence is exposed through an opt-in diagnostic/debug field or existing machine-readable assessment envelope;
- diagnostic records distinguish `legacy_request`, `concept_request`, and `actual_diff` sources;
- shadow mode records `legacy_only`, `concept_only`, and `both` canonical route IDs;
- telemetry is local/deterministic and creates no network analytics dependency;
- absence of diagnostic mode MUST NOT change routing behavior;
- diagnostics MUST NOT contain secrets beyond request text already supplied to SEF; no additional environment/token capture is allowed.

A compatibility test MUST compare normal CLI/JSON behavior before and after shadow instrumentation and reject unintended public-output drift.

## 10. Interaction with RC-2/3/4

- RC-2: leave a future polarity extension point but do not suppress negated concepts in RC-1.
- RC-3: concept detection is task-language evidence, not proof that project-level uncertainty is task-material.
- RC-4: no change to verification history/release readiness.

## 11. Failure behavior

- malformed registry -> self-test/CI failure;
- unsupported concept mapping -> validation failure;
- detector exception -> preserve legacy routing, surface diagnostic failure, never silently replace routes with empty output;
- weak/ambiguous language -> do not invent high-impact concepts from broad cues alone;
- actual-diff sensitive finding -> always preserved.

## 12. Performance/dependency constraints

Initial candidate SHOULD remain Python-standard-library only, linear or near-linear over normal request length, with compiled static rules, no network access, no model download, no mutable external lexicon and deterministic output for identical input/version.

## 13. Observability contract

A maintainer MUST be able to answer:

1. which concepts were detected;
2. which rule/evidence caused each;
3. which trigger/context each concept produced;
4. whether the same route came from legacy request, concept request or actual diff;
5. which downstream pack/procedure/risk resulted.

## 14. Acceptance gates

The first behavioral implementation is acceptable only if ALL hard gates hold.

### 14.1 Integrity

- `sef.py` compiles;
- embedded self-test passes;
- integrity manifest changes only for intentional candidate runtime change;
- immutable `v1.4.0-beta` remains untouched;
- no CHALLENGE tuning.

### 14.2 RC-1 causal probes

- `RC1-AUTH-001` passes;
- all other visible RC-1 treatment probes pass;
- RC-1 positive controls remain pass;
- zero `HARNESS_ERROR`.

Necessary, not sufficient: visible probes are tuning data.

### 14.3 Official DEV regression gates

- zero new critical DEV false negatives;
- existing critical routing successes remain successes;
- actual-diff escalation remains unchanged or improves;
- evidence/release behavior has no RC-1 regression;
- benchmark expectations are never weakened to accommodate candidate behavior.

### 14.4 Frozen negative-control / over-routing budget

Before implementing behavior, create and freeze a dedicated R0/R1 negative-control set outside CHALLENGE. It MUST include lexical near-misses for each concept family, for example ordinary `admin` prose without access-control change, a `worker` as a person rather than background execution, vendor/business copy without new supplier dependency, search UI without search-engine discoverability, and migration language unrelated to stored-state migration.

Hard budget for the first candidate:

- **0 new critical false positives** versus v1.4 baseline;
- **0 new specialist security/data/supplier packs on the frozen negative controls** unless the control is independently reclassified before candidate execution;
- **0 regressions on existing R0 scenarios that currently remain R0**;
- any new R1 over-routing must be individually reviewed and justified; aggregate percentage alone cannot waive it.

This budget is intentionally stricter than a generic pass-rate threshold because additive routing naturally biases toward over-governance.

### 14.5 Metamorphic generalization gates

Before CHALLENGE, add deterministic intent-preserving transformations:

- safe singular/plural;
- controlled noun/verb morphology;
- English/already-supported French equivalents;
- specialist term/ordinary-language compositional equivalents.

Equivalent intent must preserve the same canonical concept where the semantic contract is unchanged.

### 14.6 Public-output compatibility gate

Shadow/additive instrumentation MUST have a regression test proving that default human-facing output and existing machine-readable contract do not drift unintentionally. New diagnostic fields must be additive/opt-in or otherwise explicitly versioned.

### 14.7 Held-out gate

Only after DEV + probes + negative controls + metamorphic checks stabilize:

- execute the predeclared CHALLENGE set once;
- do not repeatedly tune on CHALLENGE;
- any new critical false negative blocks promotion.

## 15. Rejected shortcuts

Reject unless separately justified by new evidence:

- one regex alternative per failing sentence while retaining direct policy coupling;
- global fuzzy substring matching;
- LLM hard-gate classification;
- RC-2/3/4 changes in the same patch;
- weakening actual-diff escalation;
- relaxing positive controls/benchmark expectations;
- editing CHALLENGE during tuning;
- declaring success from aggregate pass percentage alone.

## 16. Implementation boundary

Future RC-1 implementation PR SHOULD remain narrow:

1. add deterministic normalization helpers;
2. add six canonical concept definitions under the validated registry contract;
3. add concept-evidence representation;
4. add compatibility mapping;
5. add deterministic merge/deduplication;
6. add shadow diagnostics without public-output drift;
7. freeze negative controls before behavioral tuning;
8. add unit/metamorphic tests;
9. integrate additive concept-derived routing;
10. replay official DEV + probes + negative controls;
11. update checksum only for intentional runtime change;
12. leave RC-2/3/4 untouched.

## 17. Senior architecture review decision

**Decision: ACCEPT WITH CONDITIONS, conditions incorporated in this revision.**

Selected architecture remains Option D: deterministic canonical task-concept normalization with additive first migration.

The review identified four pre-implementation weaknesses in the initial draft and this revision closes them at design level:

1. registry schema/invariants are now machine-checkable;
2. legacy/concept merge and deduplication semantics are explicit;
3. over-routing has a frozen negative-control set and hard budget;
4. shadow/additive observability has a backward-compatibility contract.

Residual risks remain and are intentionally handled by gates rather than hidden:

- additive routing can over-govern;
- bounded deterministic semantics cannot understand arbitrary paraphrase;
- RC-2 negation remains unfixed by design;
- visible probes can be overfit, therefore metamorphic and held-out gates remain mandatory.

**Recommendation:** after CI/review of this document revision, merge this design gate. Then open a separate implementation branch/PR. Do not implement RC-1 on the design branch.