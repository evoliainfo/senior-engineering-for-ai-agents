# ADR — Semantic Routing v2

- Status: **ACCEPTED**
- Decision date: 2026-08-23
- Supersedes: no historical evidence; v1.5 deterministic runtime remains frozen
- Trigger: official CHALLENGE v3 critical failure `V3-AUTH-002`

## Context

The frozen deterministic runtime `c2203602cb53229aba55bbbb518725c155785838915e75267714bc4e2d3d35ee` achieved strong regression closure and a valid fresh CHALLENGE v3 score of **9/10**, but completely missed an explicit department-scoped authorization boundary.

That result is structurally important. The current engine can successfully recognize many known semantic families, but its primary request interpretation still depends on bounded lexical patterns and manually encoded relation vocabulary. Adding `department` to another pattern would repair the consumed scenario without proving generalization to unseen concepts such as division, branch, region, business unit, legal entity, school, clinic or another future partition term.

The finite completion policy therefore forbids another tuning loop or CHALLENGE v4 on the current architecture.

## Decision

Adopt a **hybrid two-track strategy**.

### Track A — preserve v1.5 deterministic core

The current frozen runtime remains immutable and may be packaged only as a constrained beta/experimental deterministic core. Its evidence remains auditable and its claims remain bounded by the official holdout results.

It must not claim universal open-ended semantic policy routing or act as the sole authority for high-impact security/compliance decisions.

### Track B — build Semantic Routing v2

Create a new architecture line in which natural-language interpretation is separated from deterministic governance.

The central rule is:

> A semantic extractor may describe the problem, but it may not directly choose governance packs, risk levels or release approval.

The extractor produces a typed intermediate representation. The existing-style deterministic policy engine then maps validated semantic facts to canonical concepts, packs, procedures, risk floors and implementation gates.

## Target architecture

### 1. Request normalization

Preserve the useful bounded machinery already proven in v1.5:

- polarity/non-goal handling;
- explicit technical change detection;
- actual-diff inspection;
- deterministic provenance and evidence accounting.

Normalization must never erase a prohibitive safety invariant such as `must not access`, `must never expose`, `only users in X may edit`, or equivalent constraint language.

### 2. Typed Semantic IR

Introduce a versioned schema such as `sef.semantic-ir.v1` containing facts rather than governance decisions.

Minimum entities and relations:

```text
actors[]
  id
  role
  privilege_class

resources[]
  id
  resource_type
  sensitivity

scopes[]
  id
  label
  scope_kind

relations[]
  actor_member_of_scope
  resource_scoped_to
  action_allowed_within_scope
  action_denied_across_scope
  caller_controls_destination
  system_connects_to_destination
  depends_on_external_operator
  decision_affects_person_or_right

actions[]
  actor
  verb
  resource
  constraints

external_dependencies[]
  service
  operator_relation
  failure_dependency
  quota_or_contract_dependency

decisions[]
  domain
  consequence
  affected_party

provenance[]
  semantic_fact_id
  source_span
  extractor
  confidence
  ambiguity
```

`scope_kind` must not require a closed vocabulary such as `tenant|workspace|organization`. A department, branch, dealer group or other business partition can be represented as a generic isolation scope with its literal source label preserved.

### 3. Semantic extractor interface

Define a provider-neutral interface:

```text
extract(request, project_context) -> SemanticIR
```

Implementations may include:

- deterministic legacy extraction as a baseline/fast path;
- a model-assisted extractor;
- replay fixtures for deterministic evaluation.

Model output is **untrusted input**. It must be schema-validated, provenance-bearing and bounded before policy composition.

### 4. Deterministic policy composer

Only this layer may activate canonical governance.

Examples:

```text
actor A member_of scope X
resource R scoped_to scope X
action edit by A on R
action denied when R belongs to another scope
=> AUTHORIZATION + partition-isolation governance + R3 floor

caller controls destination D
backend connects to D
=> WEBHOOK_TRUST + R3 floor

service S operated externally
system behavior depends on S quota/failure/contract
=> EXTERNAL_SUPPLIER
```

Composition remains explicit, typed, monotonic and idempotent. There is no all-to-all pack closure.

### 5. Uncertainty gate

The most important safety change is that semantic uncertainty cannot silently collapse to `R1`.

If a request contains a material access, trust, regulated-decision or destructive-change relation that the semantic layer cannot resolve with sufficient evidence, v2 must emit an explicit state such as:

```text
SEMANTIC_REVIEW_REQUIRED
```

For safety-critical unresolved relations:

- implementation is blocked or escalated;
- the result records exactly which relation is unresolved;
- the engine must not claim low risk merely because vocabulary recognition failed.

### 6. Dual-channel evidence

During migration, v1.5 deterministic observations and v2 semantic observations run in parallel.

Rules:

- either channel may add a material risk signal;
- the semantic channel cannot remove a deterministic signal;
- disagreements are recorded as evidence;
- a model-assisted extractor cannot directly lower risk or suppress a pack;
- policy decisions remain reproducible from the validated IR.

### 7. Actual-diff remains deterministic-first

Git paths, changed files, migration operations, infrastructure exposure, workflow changes and container/release surfaces remain machine-observed wherever possible.

Semantic extraction is not a substitute for direct repository evidence.

## Security and quality invariants

1. **No direct model-to-pack authority.**
2. **No model-to-release approval authority.**
3. **Monotonic safety:** extra credible evidence may add risk/governance, not silently remove it.
4. **Explicit uncertainty:** unresolved material semantics never default to safe/low-risk.
5. **Source provenance:** every non-deterministic semantic fact cites request/context evidence.
6. **Schema boundary:** malformed or unsupported extractor output fails closed for material relations.
7. **Polarity preservation:** non-goals cannot suppress real prohibitive authorization/safety requirements.
8. **Provider replaceability:** policy composition does not depend on one model vendor.
9. **Replayability:** model-assisted semantic outputs used in deterministic regression must be capturable as fixtures.
10. **Holdout separation:** consumed v1/v2/v3 scenarios are regression evidence only.

## Non-goals

Semantic Routing v2 does not attempt to:

- replace direct code/diff inspection with an LLM;
- let a model make compliance claims;
- infer jurisdiction-specific legal conclusions without qualified authority;
- convert every ambiguous request to maximum risk;
- preserve an illusion of deterministic behavior by hiding model uncertainty;
- patch `V3-AUTH-002` as a one-off keyword fix.

## Compatibility strategy

The first v2 implementation must be shadow-only. It must not change canonical v1.5 plan outputs until its own acceptance gates pass.

A compatibility adapter maps validated Semantic IR facts into the current canonical concept vocabulary. This allows policy packs/procedures to be reused before deeper runtime refactoring.

## Evidence program

The current CHALLENGE sequence is closed. v2 starts a **new evaluation program**, not `CHALLENGE v4`.

Consumed holdouts may be replayed as regressions after v2 development begins. Fresh independent evidence must be created only after the v2 candidate is frozen.

The new independent holdout must emphasize open-vocabulary semantic relations rather than simple synonyms and must include both positive and negative cases.

## Consequences

### Positive

- attacks the observed root cause instead of growing another keyword list;
- keeps governance deterministic and auditable;
- allows model intelligence where open-ended language actually requires it;
- preserves the value of the mature v1.5 engine;
- creates a safe failure mode for semantic uncertainty.

### Costs

- more architectural complexity than pure regex routing;
- model-assisted mode introduces latency, cost and provider/runtime concerns;
- evaluation must distinguish extractor quality from policy-composer quality;
- reproducibility requires captured semantic fixtures and exact provider metadata for live trials.

## Decision boundary

The frozen v1.5 runtime is not modified under this ADR. Semantic Routing v2 begins on a separate architecture branch and earns its own release claim only after its own deterministic, independent-holdout and real-agent evidence gates pass.
