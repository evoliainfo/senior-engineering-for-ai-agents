# ADR: SEF Capability System vNext

Status: proposed for merge
Date: 2026-08-24
Decision type: product and architecture reset
Supersedes as primary direction: Semantic Routing v2 promotion path

## Context

SEF v1.4 and the post-v1.4 challenge program produced strong governance, evidence and evaluation infrastructure. The Semantic Routing v2 experiment then attempted to solve open-vocabulary routing limitations by introducing a model-assisted semantic layer.

The experiment produced useful research evidence, including a 35/35 live DEV run, but subsequent reproducibility tests showed that a model can produce materially different semantic fact sets for the same request. More importantly, the product discussion exposed a deeper issue: optimizing routing and governance does not by itself make the coding agent more capable.

ECC provides a stronger immediate user value proposition by installing reusable skills, agents, workflows, hooks and rules into the harness. SEF must therefore re-center on capability augmentation.

## Decision

SEF vNext will be a **capability-first senior-engineering system**.

The product hierarchy is:

```text
CAPABILITIES
    ↓
COMPOSED WORKFLOWS
    ↓
PROJECT-AWARE EXECUTION
    ↓
VERIFICATION + EVIDENCE
    ↓
TARGETED GUARDRAILS WHEN MATERIAL
```

Governance is a supporting kernel, not the main user experience.

## Product principle

> SEF should make the agent more capable before it makes the agent more constrained.

A capability should increase the agent's ability to solve a class of engineering problems. A guardrail should constrain behavior only when a material failure mode justifies the constraint.

## Non-goals

SEF vNext will not:

- create or train a new AI model;
- require a separate OpenAI API call for normal operation;
- force every task through a semantic classifier;
- block ordinary low-risk implementation with heavyweight governance;
- maximize skill count as a success metric;
- copy ECC content;
- claim superiority over ECC before controlled comparative evidence exists.

## Architecture

### Layer 1: Harness adapter

Purpose: expose SEF natively inside the coding environment.

Initial target: Codex-first.

Required properties:

- native skill discovery where the harness supports it;
- project instructions integrated without destroying user-owned instructions;
- no separate LLM credential required;
- no mandatory Python interaction in the normal user path after installation;
- portable capability source format so Claude Code and other harness adapters can follow.

### Layer 2: Capability registry

Capabilities are independent modules with stable identifiers and metadata.

Minimum capability contract:

```yaml
id: brownfield-repository-discovery
version: 1
purpose: Map an existing repository before material change.
activate_when:
  - feature work in an unfamiliar repository
  - bug fix with uncertain architecture
inputs:
  - user intent
  - repository state
outputs:
  - architecture map
  - relevant files
  - constraints
  - unresolved questions
related_capabilities:
  - implementation-planning
  - architecture-conformant-implementation
guardrail_hooks: []
evals:
  - CAP-BROWN-001
```

Each capability must include:

1. purpose and activation criteria;
2. expected inputs and outputs;
3. method/workflow;
4. decision points;
5. project-context adaptation rules;
6. anti-patterns/failure modes;
7. verification/evidence expectations;
8. handoff/composition rules;
9. optional targeted guardrail hooks;
10. eval coverage.

### Layer 3: Capability selection and composition

Normal mode is agent-native selection using capability metadata and current repository/task context.

The system must not require an extra classifier model call.

Composition rules should be lightweight and explicit. Example:

```text
"Add Stripe subscriptions"
  -> repository-discovery
  -> implementation-planning
  -> external-api-integration
  -> webhook-async-integration
  -> database-change
  -> verification-before-completion
```

Capabilities can recommend or hand off to related capabilities, but no single capability becomes a universal controller.

### Layer 4: Project intelligence

This retains and generalizes one of SEF's strongest assets.

Responsibilities:

- adopt the actual repository rather than a theoretical architecture;
- identify stack, test system, conventions and boundaries;
- find existing implementation patterns;
- preserve local project instructions;
- identify the smallest relevant file/context set;
- distinguish task intent from repository reality;
- reassess the actual diff after implementation.

### Layer 5: Workflow composition

A small number of reusable workflow skeletons compose capabilities:

1. Feature delivery
2. Bug / incident resolution
3. Refactor / architecture change
4. Integration / dependency change
5. Data / migration change
6. Release / production change

Typical feature workflow:

```text
understand -> plan -> implement -> test -> review -> verify
```

The workflow can skip irrelevant phases for trivial tasks. Proportionality is mandatory.

### Layer 6: Guardrail kernel

The current deterministic SEF governance logic is repositioned as a targeted kernel.

Guardrails should activate for material operations such as:

- destructive or live-data changes;
- authentication/authorization changes;
- tenant or partition isolation;
- secrets and sensitive data;
- untrusted files or external input;
- release/rollback-critical changes;
- production infrastructure;
- high-impact regulated decisions.

Ordinary coding tasks should not be blocked solely because a broad domain word appears.

Default behavior for non-material tasks is guidance + verification, not blocking.

### Layer 7: Evidence and evaluation

Every capability is evaluated at two levels.

#### Capability-level eval

Tests whether the skill activates appropriately and applies the intended method.

#### Outcome-level brownfield eval

Tests whether using the capability improves the actual engineering result compared with an agent baseline.

SEF retains the following evaluation integrity rules from the challenge program:

- freeze before independent evaluation;
- consumed tests become regression-only;
- failed evidence is preserved;
- no tuning-to-green on fresh holdouts while preserving an independence claim;
- implementation claims must be supported by actual test/diff evidence.

## Capability design principles

### 1. Outcome-oriented

A skill is not a checklist dump. It exists to improve an observable engineering outcome.

### 2. Repository-aware

Guidance must first inspect project conventions before prescribing a framework, library or command.

### 3. Flexible implementation

Capabilities specify invariants and method, not unnecessary implementation details.

Bad:

> Always use library X.

Better:

> Reuse the repository's existing validated approach unless evidence shows it cannot satisfy the requirement.

### 4. Progressive disclosure

Do not load every capability into context. Load only what the task needs.

### 5. Composable

Capabilities expose clean handoffs and avoid duplicating whole workflows.

### 6. Verifiable

Every material recommendation should define how the agent can tell whether it worked.

### 7. Source-aware

Time-sensitive platform/framework claims should be checked against authoritative current documentation at execution time instead of being frozen as eternal facts in a skill.

### 8. Provider-neutral

A capability should work with any sufficiently capable coding agent. OpenAI-, Anthropic- or harness-specific behavior belongs in adapters.

## Initial capability portfolio

### Foundation set

1. `repository-discovery`
2. `requirements-to-acceptance`
3. `implementation-planning`
4. `tdd-bug-reproduction`
5. `systematic-debugging`
6. `architecture-conformant-implementation`
7. `code-review-diff-review`
8. `verification-before-completion`
9. `behavior-preserving-refactor`
10. `external-api-integration`
11. `database-change-migration`
12. `release-operational-readiness`

### Next specialist set

13. `authentication-authorization`
14. `secure-input-file-handling`
15. `frontend-feature-engineering`
16. `accessibility-engineering`
17. `performance-investigation`
18. `observability-incident-diagnostics`
19. `ci-build-repair`
20. `dependency-supply-chain`
21. `legacy-test-strategy`
22. `data-backfill-batch-processing`
23. `webhook-async-integration`
24. `technical-documentation-adr`

## Relationship to existing SEF assets

### `sef.py`

Retained as the deterministic beta governance/evidence kernel. No immediate rewrite is required.

### Semantic Routing v2

Status changes to **experimental research / paused**.

Its contracts, provider adapter, composer and evidence remain in the repository for research and regression history. It is no longer on the critical path to vNext and no S6 freeze or semantic holdout is required before capability-system work begins.

### Existing eight playbooks

They become source material for capability extraction. Useful methods should move into modular capability units over time. Existing playbooks remain intact until replacement capabilities are proven.

### Existing challenges and holdouts

Remain immutable historical evidence about the deterministic routing architecture. They do not become capability benchmarks.

## Freedom budget

A capability must justify every hard constraint it introduces.

Hard constraints are permitted only when one of the following is true:

1. repository invariant requires it;
2. user explicitly requires it;
3. deterministic safety kernel identifies a material irreversible/high-impact risk;
4. a test/build/release contract requires it.

Everything else should be recommendation, not prohibition.

## Context budget

Each capability should be designed for selective loading.

Initial target:

- concise core instructions;
- optional references/examples loaded only when needed;
- avoid duplicating generic rules across capabilities;
- measure capability-attributable input tokens in benchmark runs.

No hard token threshold is accepted until pilot data exists.

## Acceptance criteria for this architecture

The architecture is accepted only if implementation demonstrates:

1. capabilities can be independently installed/discovered;
2. capabilities can compose without a central LLM classifier;
3. normal use requires no SEF-owned model API call;
4. trivial tasks remain lightweight;
5. high-risk operations can still trigger the deterministic guardrail kernel;
6. capability usage is observable in evals;
7. Codex + SEF beats Codex alone on the pre-registered brownfield pilot before broad catalog expansion;
8. superiority claims over ECC require a fresh controlled comparative benchmark.

## Consequences

### Positive

- user value becomes direct and understandable;
- SEF augments agent competence rather than primarily policing it;
- existing evaluation work becomes a competitive quality system;
- no mandatory API-cost scaling problem;
- modular architecture improves contribution and portability;
- guardrails remain available where they matter.

### Negative

- significant refactoring away from monolithic `sef.py` will eventually be needed;
- capability quality requires domain-specific eval design;
- catalog growth must be deliberately slower than ECC's breadth;
- multi-harness packaging remains future work after Codex-first proof.

## Final decision rule

If capability-system experiments do not materially improve real Codex brownfield outcomes, do not continue expanding the catalog. Reassess the product thesis instead.
