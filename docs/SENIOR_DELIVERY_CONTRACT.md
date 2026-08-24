# SEF Senior Delivery Contract

Status: product contract
Date: 2026-08-24
Applies to: SEF capability-system vNext

## North-star user

SEF is designed for a user who can describe the product or outcome they want but may not know the professional engineering steps required to deliver it safely and credibly.

The user should not need to know in advance that a project needs acceptance criteria, architecture boundaries, migration planning, negative tests, environment separation, release evidence, rollback planning, deployment verification, or observability.

SEF and the coding agent must surface those requirements when materially applicable.

The user remains responsible for product, business, legal/policy, destructive, budget, credential, and approval decisions that cannot be responsibly inferred.

## Product promise

> From idea to verified deployment, SEF should give the coding agent the methods and evidence discipline needed to operate like a strong senior software engineer while preserving implementation flexibility and proportionality.

This is an engineering-system objective, not a claim that the model becomes infallible or literally replaces a qualified human in every domain.

## Required delivery spine

A release candidate cannot be considered lifecycle-complete while a material stage below has no capability/workflow coverage.

### Stage 0 — Problem and outcome framing

The system must be able to establish:

- who the user/customer/system actor is;
- the problem or desired outcome;
- success signals and important non-goals;
- material product/business uncertainties;
- constraints that affect feasibility.

For a tiny change this can be implicit. For a new product it must be explicit enough to prevent building the wrong thing correctly.

### Stage 1 — Requirements and acceptance

The system must convert intent into observable acceptance criteria while distinguishing:

- explicit user requirements;
- repository/platform-derived requirements;
- professional engineering inferences;
- assumptions;
- user decisions;
- optional improvements.

Every committed criterion should have a plausible evidence path.

### Stage 2 — Project/repository understanding

For brownfield work:

- discover the existing architecture, conventions, test surfaces, dependencies and smallest change surface.

For greenfield work:

- establish the intended boundaries, stack constraints, repository structure and foundational conventions before large-scale implementation.

Repository/project reality should outrank generic framework preference.

### Stage 3 — Solution architecture and technical decisions

Material projects require a defensible technical approach covering, as applicable:

- system boundaries;
- data ownership and contracts;
- client/server/service responsibilities;
- persistence;
- integration boundaries;
- security/trust boundaries;
- operational model;
- deployment constraints;
- major trade-offs and ADR-worthy decisions.

The agent should choose ordinary technical details when evidence provides a clear answer and ask the user only for genuine product/business/risk trade-offs.

### Stage 4 — Implementation planning

The system must create the smallest credible execution path:

- dependency-aware sequencing;
- explicit scope boundaries;
- verification attached to material steps;
- uncertainty made visible;
- replanning triggers when evidence changes the problem.

Plans must shrink for simple tasks and expand only when complexity/risk justifies it.

### Stage 5 — Implementation

Implementation must:

- follow project-native patterns where appropriate;
- preserve existing contracts outside scope;
- use maintainable abstractions proportionate to the problem;
- handle material failure paths;
- avoid speculative architecture and unrelated refactoring;
- keep code, configuration, data changes and documentation coherent.

SEF should augment the agent's engineering methods without prescribing one framework/library when the project should decide.

### Stage 6 — Test, debug and quality verification

The system must establish evidence appropriate to the changed behavior:

- reproduction for defects when practical;
- focused behavioral tests;
- integration/E2E evidence when boundaries require it;
- systematic root-cause debugging for non-obvious failures;
- static/build/type/lint checks where relevant;
- negative/boundary cases proportionate to risk;
- actual-diff inspection;
- truthful states for checks that did not or could not run.

A generic green command is not enough if it does not observe the requested behavior.

### Stage 7 — Security, data and operational review

Before release, materially applicable concerns must be evaluated, including:

- authentication and authorization;
- secrets and environment configuration;
- sensitive data/privacy;
- untrusted input/file/external boundaries;
- database schema/data migration and recovery;
- dependencies/supply chain;
- concurrency/idempotency/retries;
- performance/capacity/cost;
- logs/metrics/traces and operational diagnostics;
- accessibility/compatibility for user-facing systems;
- regulated/high-impact escalation where necessary.

These should be targeted capabilities/guardrails, not one giant checklist applied to every task.

### Stage 8 — Code/diff review and release readiness

The system must review what actually changed and establish, when applicable:

- correctness against acceptance criteria;
- unintended behavior/scope changes;
- migration compatibility;
- configuration/environment readiness;
- CI/build/package readiness;
- release ordering;
- rollback/recovery plan;
- operational ownership and known residual risks.

"Tests passed" and "ready to release" are different claims.

### Stage 9 — Deployment execution

When deployment is in scope, the system must follow the project's/platform's real deployment mechanism rather than inventing one.

It must distinguish:

- deployment configured;
- deployment attempted;
- deployment succeeded;
- artifact/version actually active in the target environment.

Credentials, production approvals and irreversible actions remain subject to the harness/user approval model.

### Stage 10 — Post-deployment verification

A production delivery is not fully verified until the relevant deployed behavior is observed.

Depending on the project, this can include:

- health/readiness;
- smoke/critical user journey;
- logs/metrics/traces;
- error rate;
- migration state;
- external provider/downstream effect;
- analytics/event ingestion;
- performance sanity;
- rollback trigger monitoring.

Do not infer production success from local evidence alone.

### Stage 11 — Handoff and maintainability

For non-trivial projects the delivered state should leave enough information for future work:

- relevant documentation/ADR updates;
- configuration/environment expectations;
- migration/recovery notes where applicable;
- tests as executable contracts;
- known limitations/residual risks;
- operational or support notes when needed.

Documentation should be proportional and should not duplicate self-explanatory code.

## Greenfield and brownfield paths

SEF must support both.

### Greenfield

```text
idea
-> problem/outcome framing
-> requirements/acceptance
-> architecture + stack/project bootstrap
-> implementation plan
-> implementation
-> test/debug/review
-> security/operational readiness
-> deploy
-> post-deploy verify
-> handoff
```

### Brownfield

```text
requested change
-> repository discovery
-> requirements/acceptance
-> change architecture/plan
-> implementation
-> test/debug/review
-> release readiness when applicable
-> deploy when applicable
-> post-deploy verify when applicable
```

A small brownfield change can legitimately skip most lifecycle ceremony. A new production product cannot.

## Senior-engineering quality properties

Across the lifecycle, SEF should teach/enforce these behaviors:

1. **Evidence before certainty** — distinguish facts, hypotheses and assumptions.
2. **Repository/project adaptation** — do not force generic stacks or rituals.
3. **Proportionality** — effort and controls match complexity and risk.
4. **Boundary awareness** — interfaces, data, trust and deployment boundaries are explicit.
5. **Failure-path thinking** — material negative paths are designed and tested.
6. **Maintainability** — minimize accidental complexity and hidden coupling.
7. **Reversibility** — prefer changes and release paths that can be safely corrected.
8. **Actual-change review** — reassess the real diff, not only the original plan.
9. **Operational reality** — deployment/runtime evidence is different from local evidence.
10. **Truthful completion claims** — never claim more than was observed.

## User interaction contract

The coding agent should **not** ask a non-expert user to make ordinary technical decisions the repository, platform documentation, evidence, or professional engineering judgment can answer.

Ask the user when a choice materially affects:

- product behavior;
- business policy;
- destructive/irreversible data behavior;
- material cost;
- legal/compliance posture;
- production approval;
- credentials/access not available to the agent;
- a genuinely unresolved trade-off with different user outcomes.

## Capability-system acceptance rule

The capability catalog is not lifecycle-complete until every material stage in this document has:

1. a named capability or composed workflow owner;
2. activation/proportionality rules;
3. an evidence contract;
4. at least one development eval;
5. outcome-level brownfield or greenfield evidence before release claims.

No number of specialist skills compensates for a missing lifecycle stage.

## Current coverage status

At C2:

- repository discovery: implemented in tranche A;
- requirements/acceptance: implemented in tranche A;
- implementation planning: implemented in tranche A;
- defect reproduction/testing: implemented in tranche A;
- systematic debugging: implemented in tranche A;
- verification/completion claims: implemented in tranche A;
- architecture-conformant implementation, diff review, data/integrations and release readiness: planned in tranche B;
- product/problem framing, greenfield solution architecture/stack selection, project bootstrap, environments/secrets, deployment execution and post-deployment verification require explicit lifecycle coverage in subsequent tranches.

This gap is intentional and visible. SEF must not claim full idea-to-production lifecycle coverage until those stages are implemented and evaluated.
