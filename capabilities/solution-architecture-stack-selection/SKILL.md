---
name: solution-architecture-stack-selection
description: Choose proportionate system boundaries and technology stack from product requirements, project constraints, operational reality, ecosystem maturity, and deployment needs rather than habit or trend.
---

# Solution Architecture and Stack Selection

Use this capability when a greenfield product or material architecture change needs a defensible technical shape before implementation.

## Core Principle

> Choose the simplest architecture that credibly satisfies the product, operational, security, and evolution constraints.

Do not select a framework, database, cloud, queue, vector store, microservice architecture, or AI layer merely because it is familiar or fashionable.

## 1. Establish Decision Inputs

Use the accepted product/requirement evidence:

- critical user journeys;
- data and state needs;
- trust/auth boundaries;
- integration requirements;
- latency/availability constraints when material;
- expected deployment/operating environment;
- budget/vendor restrictions;
- team/user constraints that genuinely matter;
- existing stack for brownfield systems.

Do not ask a non-expert user to choose ordinary implementation technology when engineering evidence can decide it.

## 2. Define System Boundaries Before Products

Identify the minimum meaningful components and ownership boundaries:

- client/UI;
- application/backend responsibility;
- persistence/data ownership;
- external providers;
- asynchronous processing if actually needed;
- authentication/authorization boundary;
- deployment/runtime units.

Start with one deployable application/service when it can satisfy the requirements. Add distributed components only for a demonstrated boundary, scaling, isolation, integration, ownership, or operational reason.

## 3. Identify Architecture Drivers

Rank only the drivers that can change the decision, such as:

- simplicity/time-to-value;
- maintainability;
- ecosystem/library maturity;
- deployment compatibility;
- type/runtime guarantees;
- data consistency needs;
- portability/vendor lock-in;
- performance/capacity;
- availability/recovery;
- compliance/data residency;
- cost profile;
- observability/operations.

Avoid scoring dozens of generic qualities that are irrelevant to the project.

## 4. Generate a Small Option Set

When the right answer is not obvious, compare 2-3 realistic options.

For each option, state:

```text
Option:
Why it fits:
Material drawbacks:
Operational/deployment implications:
Migration/reversibility:
Decision-changing unknowns:
```

Do not create fake alternatives when repository constraints or platform requirements already determine the answer.

## 5. Prefer Boring, Supported Technology Unless Requirements Disagree

Prefer technologies that have:

- stable maintenance and security posture;
- mature documentation/ecosystem;
- deployment support in the target environment;
- adequate libraries for required integrations;
- understandable failure/operational characteristics.

Use newer/specialized technology when it creates a clear project-specific advantage worth its operational and maintenance cost.

## 6. Design Data and Interface Ownership

Before implementation, define enough to prevent accidental coupling:

- source of truth for material entities/state;
- API/module boundaries;
- synchronous vs asynchronous interactions;
- transaction/consistency expectations;
- external-system ownership assumptions;
- public/stable interfaces that should not leak implementation detail.

Do not design every table or endpoint here. Detailed design belongs nearer implementation.

## 7. Include Deployment Reality in Architecture

Architecture is incomplete if it ignores how the system will run.

Check:

- target deployment model/platform constraints;
- build/runtime compatibility;
- environment/configuration needs;
- persistent storage/networking requirements;
- background job/webhook support;
- preview/staging/production separation where relevant;
- logs/health/operational observability;
- rollback/recovery implications.

Do not treat deployment as an afterthought to be solved after the application is finished.

## 8. Distinguish Engineering Choice from User Decision

The agent should normally choose ordinary technical details such as framework/library versions or internal structure based on evidence and current authoritative documentation.

Escalate when the alternatives materially change:

- product behavior;
- recurring cost/business commitment;
- vendor ownership/lock-in that matters to the user;
- data/privacy/compliance posture;
- deployment geography;
- performance/availability promise;
- irreversible migration path.

Explain the trade-off in non-technical terms when user input is needed.

## 9. Record Only Material Decisions

Create a compact architecture decision summary:

```text
SOLUTION ARCHITECTURE
Drivers:
System boundaries:
Data/source-of-truth:
Selected stack:
Why this option:
Rejected material alternative(s), if any:
Deployment model:
Security/trust boundaries:
Material assumptions:
User decisions required:
Risks/revisit triggers:
```

Use a formal ADR only when the decision is durable, non-obvious, costly to reverse, or important for future maintainers.

## Brownfield Adaptation

For an existing repository:

- existing architecture and stack are strong constraints;
- prefer conformant extension over platform migration;
- introduce new technology only when the existing stack cannot responsibly satisfy a material requirement;
- identify compatibility/migration cost before recommending replacement.

Use `repository-discovery` first when architecture reality is not known.

## Context Budget

Load only:

1. product/acceptance frame;
2. relevant repository architecture for brownfield work;
3. current authoritative documentation for genuinely decision-sensitive external technology;
4. deployment/environment constraints.

Do not perform encyclopedic technology research after the decision is already clear.

## Anti-Patterns

Avoid:

- "use X because it is modern/popular";
- asking the user to pick framework/database/cloud without a material reason;
- microservices by default;
- adding queues/caches/search/vector databases before a requirement exists;
- selecting technology without considering deployment support;
- premature abstraction for hypothetical scale;
- rewriting an existing stack for personal preference;
- architecture diagrams with no ownership or runtime implications;
- treating cost, secrets, migration, recovery, or observability as later concerns;
- creating a giant ADR for ordinary reversible choices.

## Evidence Contract

A material architecture choice should be explainable by evidence:

1. Which requirements/drivers determined the architecture?
2. What are the system/data/trust boundaries?
3. Why is the selected stack adequate and proportionate?
4. What material alternative was rejected and why, if choice was non-obvious?
5. How will the system build, run, deploy, and be observed?
6. What assumptions could force a revisit?
7. Which decisions genuinely required user authority?

## Handoff

For greenfield work use `project-bootstrap-foundations` to turn the architecture into a minimal maintainable repository.

Use `environment-secrets-configuration` for configuration contracts.

Use `implementation-planning` once the architecture is sufficiently established.
