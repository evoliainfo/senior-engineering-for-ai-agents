# RC-1 Candidate Architecture — Deterministic Task-Concept Normalization

Status: DESIGN CANDIDATE — NOT IMPLEMENTED

Baseline: SEF `v1.4.0-beta` runtime remains unchanged.

Decision target: RC-1 only — brittle request routing caused by direct surface-text-to-trigger matching.

This document is a design gate. It does not authorize or implement a runtime change.

## 1. Problem statement

SEF v1.4 currently maps request text directly to routing triggers through regular-expression matches. That design is deterministic and auditable, but the semantic boundary is too close to surface wording.

The locked benchmark and the independent root-cause probes demonstrate that semantically equivalent requests can route differently because of morphology, lexical choice or ordinary user phrasing. Confirmed examples include authorization, data migration, webhook/event intake, external suppliers, background work and search discoverability.

RC-1 is therefore not simply "missing synonyms". The architectural defect is the absence of a stable intermediate representation between user language and governance policy.

The desired change is:

```text
raw request
    ↓
deterministic lexical normalization
    ↓
canonical task concepts + evidence
    ↓
explicit compatibility/policy mapping
    ↓
existing triggers / contexts
    ↓
existing packs / risk / procedures
```

The governance decision must remain deterministic, explainable and fail-safe.

## 2. Goals

The RC-1 candidate MUST:

1. recognize materially equivalent task intent across safe lexical and morphological variants;
2. create a stable canonical concept boundary before risk/policy routing;
3. preserve deterministic and inspectable policy decisions;
4. emit evidence explaining why each concept was detected;
5. preserve current trigger/context/pack semantics unless a separately reviewed policy change is required;
6. preserve the independent actual-diff reassessment path;
7. avoid introducing network calls, model calls or nondeterministic dependencies;
8. support English and French at least to the level already claimed by current routing;
9. avoid broad stemming/fuzzy matching that materially increases over-routing;
10. remain compatible with the single-file SEF distribution/bootstrap invariant.

## 3. Non-goals

This candidate does NOT attempt to solve:

- RC-2 polarity or negation handling;
- RC-3 task-materiality of project-level context;
- RC-4 evidence history/state semantics;
- free-form LLM semantic classification;
- automatic policy learning;
- probabilistic security decisions;
- renaming all existing triggers/packs;
- rewriting the current governance engine;
- changing the immutable `v1.4.0-beta` release/tag.

RC-2 is intentionally separated. During the first RC-1 implementation, a concept found inside negated text is still detectable; no suppression rule is introduced. That preserves experimental isolation.

## 4. Architectural options considered

### Option A — Append more alternatives to current routing regexes

Example: add `authorization`, `authorized`, `webhooks`, `migrate`, `vendor`, `queue worker`, and similar terms directly to each existing regex.

**Rejected as the architecture.**

It may fix individual failures but keeps lexical knowledge coupled to policy routing. Future variants continue to require editing governance logic, testability remains fragmented, and probe-specific hard-coding becomes difficult to distinguish from genuine generalization.

### Option B — Generic stemming/fuzzy text matching

**Rejected for the first candidate.**

Aggressive stemming, edit-distance or substring matching can produce unsafe false positives, especially across English/French morphology and short security-sensitive terms. It also weakens explainability.

### Option C — LLM/NLP classifier before policy routing

**Rejected for the deterministic core candidate.**

It can improve semantic recall but introduces model/version drift, latency, cost, external dependency and probabilistic behavior at the safety-routing boundary. A future optional advisory layer may be evaluated separately, but it must never silently replace deterministic hard-gate logic.

### Option D — Deterministic canonical concept normalization

**Selected candidate.**

A small, explicit semantic-normalization layer converts bounded lexical/compositional evidence into canonical task concepts. A separate mapping translates concepts into the current SEF triggers and execution contexts. Policy/risk logic stays downstream and explicit.

## 5. Proposed components

### 5.1 Text normalization

A pure deterministic preprocessor produces a normalized view of the request while retaining offsets back to the original text.

Allowed operations:

- Unicode normalization (NFKC);
- case-folding;
- whitespace normalization;
- punctuation normalization where semantics are not lost;
- tokenization with stable offsets;
- safe normalization of selected hyphen/space forms.

Not allowed in the first candidate:

- uncontrolled stemming;
- fuzzy edit-distance matching;
- embeddings;
- external NLP libraries;
- model inference.

### 5.2 Canonical task-concept registry

Concepts are named semantic units independent of packs and procedures.

Initial RC-1 scope is intentionally limited to concepts demonstrated by the probes:

| Canonical concept | Meaning | Compatibility target |
| --- | --- | --- |
| `AUTHORIZATION_CHANGE` | role/permission/object-access semantics | `AUTHZ_CHANGED` |
| `DATABASE_STATE_MIGRATION` | migration/backfill/transformation of stored state | database migration routing |
| `INBOUND_PROVIDER_EVENT` | externally initiated callback/webhook/event reception | `INBOUND_WEBHOOK_ADDED` |
| `EXTERNAL_SERVICE_DEPENDENCY` | new or material third-party/SaaS/vendor dependency | external supplier governance |
| `BACKGROUND_PROCESSING` | queue/worker/consumer/background execution semantics | `BACKGROUND_JOB` execution context |
| `SEARCH_DISCOVERABILITY` | intent that public content be discoverable through search engines | `SEO_WEB_DISCOVERABILITY` |

The registry is semantic infrastructure, not a list of benchmark sentences.

Each concept definition may contain:

1. **direct lexemes** for highly specific terms;
2. **safe morphological families** where the transformation is unambiguous;
3. **compositional rules** requiring multiple cues within a bounded token window;
4. **language variants** where English/French equivalence is intentional;
5. **rule identifiers** used in evidence and tests.

Example concept logic, illustrative only:

```text
SEARCH_DISCOVERABILITY
  direct: seo, search discoverability
  compositional:
    FIND/BE_FOUND + SEARCH_ENGINE
    VISIBLE/DISCOVERABLE + GOOGLE/SEARCH_ENGINE
```

This is materially different from a single giant routing regex: lexical evidence is normalized into a concept first; policy mapping is separate.

### 5.3 Concept evidence

Every emitted concept MUST carry inspectable evidence.

Proposed logical record:

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

`strength` is categorical and deterministic, not a probabilistic confidence score. Candidate values may be `DIRECT` and `COMPOSITE`.

The exact serialized shape is an implementation detail, but equivalent traceability is mandatory.

### 5.4 Concept-to-policy compatibility adapter

Canonical concepts MUST NOT directly choose specialist packs.

Instead, a small explicit compatibility table maps concepts to existing request triggers and/or execution contexts.

Illustrative form:

```text
AUTHORIZATION_CHANGE
  -> trigger AUTHZ_CHANGED

INBOUND_PROVIDER_EVENT
  -> trigger INBOUND_WEBHOOK_ADDED
  -> contexts INBOUND_WEBHOOK, PUBLIC_API

SEARCH_DISCOVERABILITY
  -> context SEO_WEB_DISCOVERABILITY
```

This boundary preserves the existing governance engine and makes future trigger renames or policy evolution independent from language normalization.

If a concept cannot be faithfully mapped to an existing trigger without changing policy semantics, implementation MUST stop and surface an architecture/policy decision instead of silently inventing a route.

### 5.5 Existing governance engine

After compatibility mapping, the current pack/risk/procedure logic remains authoritative.

The RC-1 candidate MUST NOT introduce a second policy engine.

The current downstream properties remain valuable:

- deterministic pack selection;
- explicit route-to-skill mapping;
- risk/action-class logic;
- authoritative-context gates;
- Definition-of-Done augmentation;
- release and evidence gates.

### 5.6 Actual-diff isolation

Actual Git diff reassessment remains an independent safety channel.

Required invariant:

```text
request-language normalization
        │
        ├── request concepts → request routing
        │
actual diff analysis ───────────────→ independent diff routing
```

A failure, omission, future negation rule, or ambiguity in request-text normalization MUST NOT suppress a sensitive trigger discovered from changed files or actual diff semantics.

No concept-normalization state is allowed to downgrade actual-diff risk.

## 6. Concept-rule design rules

To avoid recreating the current problem in a new file, every concept rule MUST satisfy all applicable rules below.

### 6.1 Prefer semantic families over probe phrases

Invalid approach:

```text
if text == "people should be able to find this page in a search engine": ...
```

Valid direction:

```text
FINDABILITY cue + SEARCH_ENGINE cue -> SEARCH_DISCOVERABILITY
```

### 6.2 Use safe morphology only

Regular singular/plural or controlled noun/verb variants may be normalized when ambiguity is low.

Examples appropriate for explicit handling:

- webhook / webhooks;
- permission / permissions;
- role / roles;
- migration / migrate / migrating where the database/state context is present.

Generic suffix stripping is not acceptable as a security-routing primitive.

### 6.3 Require composition for broad words

Broad terms such as `find`, `worker`, `vendor`, `change`, `service`, `admin` or `Google` MUST NOT independently activate high-impact concepts unless they are already sufficiently specific.

Use bounded co-occurrence or phrase structures instead.

### 6.4 Deterministic rule precedence

Rule evaluation order, deduplication and aggregation MUST be deterministic. Reordering concept definitions must not unpredictably change routing.

### 6.5 No policy meaning inside lexical rules

A lexical/concept rule answers:

> What task concept is expressed?

It does not answer:

> Which pack is required, what risk level applies, or whether implementation is allowed?

Those remain policy decisions downstream.

## 7. Proposed execution flow

```text
1. Receive request + project context
2. Preserve raw request
3. Build normalized request representation
4. Detect canonical task concepts
5. Record concept evidence
6. Map concepts to legacy/current triggers + task execution contexts
7. Merge with existing deterministic request signals
8. Run current pack/risk/procedure engine
9. Later, independently reassess actual diff
10. Never let request normalization downgrade actual-diff findings
```

For the first candidate, existing direct request regexes should not be deleted wholesale in the same patch. Migration must be incremental so equivalence can be measured.

## 8. Incremental migration strategy

### Stage 1 — Shadow observation

Preferred if implementation cost remains small:

- compute canonical concepts;
- record them in diagnostic output;
- keep v1.4 routing authoritative;
- compare concept-derived compatibility triggers with legacy triggers.

Purpose: detect unexpected over/under-recognition before behavior changes.

If the current CLI/output contract makes shadow observation disproportionately invasive, this stage may be simulated in tests rather than exposed in public output.

### Stage 2 — RC-1 concept-derived additions

Allow concept mapping to add missing request triggers/contexts, but never remove a legacy trigger.

This is the safest first behavioral candidate because it addresses RC-1 recall while preventing accidental policy suppression.

Expected property:

```text
candidate_routes ⊇ legacy_request_routes
```

for RC-1 implementation only.

Because additions can create over-governance, R0/R1 and positive-control regression checks remain mandatory.

### Stage 3 — Legacy lexical de-duplication

Only after measured equivalence and challenge/pilot evidence may duplicated direct regex logic be removed or simplified.

This is explicitly not part of the first RC-1 implementation candidate.

## 9. Interaction with RC-2, RC-3 and RC-4

### RC-2 polarity

The concept representation SHOULD leave a future extension point for polarity metadata, but RC-1 MUST NOT implement suppression based on negation.

Reason: fixing RC-1 and RC-2 simultaneously would prevent causal attribution and could create security regressions.

### RC-3 materiality

Concept detection is task-language evidence, not proof that every project-level uncertainty is task-material. RC-3 retains a separate future decision layer.

### RC-4 evidence history

No interaction. Verification history and release readiness remain unchanged during RC-1 work.

## 10. Failure behavior

The concept layer MUST fail safely and observably.

- malformed internal registry: self-test/validation failure;
- duplicate concept/rule IDs: validation failure;
- unsupported concept-to-policy mapping: validation failure, not silent ignore for required mappings;
- ambiguous ordinary language: do not invent a high-impact concept solely from weak cues;
- detector exception: preserve existing routing and surface diagnostic failure; do not silently return an empty route set;
- actual-diff sensitive finding: always preserved regardless of request detector outcome.

## 11. Performance and dependency constraints

The initial candidate SHOULD remain Python-standard-library only.

Target characteristics:

- linear or near-linear processing over normal request length;
- compiled static patterns/rules;
- no catastrophic-regex patterns;
- no network access;
- no runtime model download;
- no mutable external lexicon;
- deterministic output for identical input and SEF version.

## 12. Observability / explainability contract

A developer evaluating a route MUST be able to answer:

1. which canonical concepts were detected;
2. which rule/evidence caused each detection;
3. which trigger/context each concept produced;
4. which downstream pack/procedure/risk decision resulted;
5. which findings came from request text versus actual diff.

The user-facing CLI does not need to print all internals by default, but machine-readable/debug evidence must remain obtainable for evaluation and maintenance.

## 13. Candidate acceptance gates

The first behavioral implementation of this architecture is acceptable only if ALL hard gates below hold.

### 13.1 Integrity gates

- `sef.py` compiles;
- embedded self-test passes;
- integrity manifest is intentionally updated only when a candidate runtime is intentionally changed;
- no change to immutable `v1.4.0-beta` tag;
- no CHALLENGE tuning.

### 13.2 RC-1 causal gates

On the visible RC-1 diagnostic family:

- `RC1-AUTH-001`: PASS;
- all other RC-1 treatment probes: PASS;
- RC-1 positive controls remain PASS;
- no `HARNESS_ERROR`.

This is necessary but not sufficient because the probes are visible tuning data.

### 13.3 Official DEV regression gates

- zero new critical DEV failures;
- existing critical routing successes remain successes;
- actual-diff escalation scenarios remain unchanged or improve;
- no evidence/release regression attributable to RC-1;
- no material increase in unnecessary heavyweight routing on R0/R1 tasks.

### 13.4 Metamorphic generalization gates

Before CHALLENGE, add deterministic metamorphic checks that transform wording without changing intent, for example:

- singular ↔ plural where semantically safe;
- noun ↔ controlled verb form;
- English ↔ already-supported French equivalent;
- explicit specialist term ↔ ordinary-language compositional form.

The candidate must preserve the same canonical concept under these transformations where the semantic contract is unchanged.

These tests validate the normalization mechanism rather than memorizing the 19 probe sentences.

### 13.5 Held-out gate

Only after the candidate stabilizes on official DEV + probes + metamorphic checks:

- execute the predeclared CHALLENGE set once as the held-out gate;
- do not tune repeatedly on CHALLENGE;
- any new critical false negative blocks promotion.

## 14. Rejected shortcuts during implementation

The following changes should cause review rejection unless separately justified by new evidence:

- adding one regex alternative per failing sentence while retaining direct policy coupling;
- introducing fuzzy substring matching globally;
- adding an LLM call to decide hard safety routes;
- changing RC-2 negation behavior in the same patch;
- weakening existing actual-diff escalation;
- disabling or relaxing a positive control to improve probe totals;
- changing benchmark expectations to match candidate behavior;
- editing held-out CHALLENGE scenarios during tuning;
- declaring success only from aggregate pass percentage.

## 15. Implementation boundary proposal

The future RC-1 implementation PR SHOULD be narrow:

1. add deterministic normalization helpers;
2. add the six initial canonical concept definitions;
3. add concept-evidence representation;
4. add concept-to-current-trigger/context compatibility mapping;
5. integrate additive concept-derived routing into the request path;
6. add unit/metamorphic tests;
7. replay official DEV + probes;
8. update checksum only because the runtime candidate changed;
9. leave RC-2/3/4 behavior untouched.

If preserving the single-file distribution requires source-generation changes, packaging work must be scoped explicitly and must not become an unrelated framework refactor.

## 16. Decision record

**Recommended:** proceed with Option D, deterministic canonical task-concept normalization, using an additive first behavioral candidate.

**Why:** it addresses the demonstrated RC-1 cause at the correct abstraction boundary while preserving SEF's strongest property: deterministic, auditable governance decisions.

**Do not implement yet:** this document must be reviewed as the architecture gate before any `sef.py` modification.
