# ECC Capability Benchmark v2

Status: strategic benchmark
Date: 2026-08-24
Purpose: compare user-facing engineering capability, not only governance coverage.

## Executive conclusion

The first SEF/ECC benchmark over-weighted governance and routing correctness. That produced valuable evaluation infrastructure, brownfield controls and safety evidence, but it did not answer the most important product question:

> Does SEF make a coding agent materially more capable at real software engineering work?

ECC currently has the stronger capability surface. It packages a large modular skill catalog, specialized agents, commands, hooks, rules, memory/learning mechanisms and harness-native adapters. SEF currently has the stronger evidence discipline, brownfield adoption model, actual-diff reassessment and holdout methodology, but too much of that value is expressed as control rather than capability augmentation.

The strategic response is not to copy ECC's catalog. SEF should use its evaluation rigor to build a smaller set of deeper, composable and empirically validated senior-engineering capabilities.

## Scope and evidence reviewed

ECC evidence sampled from the current repository on 2026-08-24:

- `README.md`
- `.codex-plugin/plugin.json`
- `docs/SKILL-DEVELOPMENT-GUIDE.md`
- `skills/agentic-engineering/SKILL.md`
- `skills/tdd-workflow/SKILL.md`
- `skills/security-review/SKILL.md`
- `skills/verification-loop/SKILL.md`
- `agents/`
- `hooks/`
- `rules/`
- Codex/Claude/other harness integration surfaces

SEF evidence sampled from current `main`:

- `README.md`
- `docs/CAPABILITIES.md`
- `sef.py`
- `semantic_v2/`
- current regression, challenge, brownfield and release-gate evidence

ECC count caveat: the README currently advertises 286 skills while the Codex plugin manifest describes 281. Counts are therefore treated as approximate inventory indicators, not as a quality metric.

## Product-level comparison

Scoring scale: 1 = weak, 3 = credible, 5 = strong. The weighted score is a directional architecture benchmark, not an empirical task-success result. The empirical comparison is defined separately in `BROWNFIELD_COMPARATIVE_EVAL_PLAN.md`.

| Dimension | Weight | ECC | SEF current | Assessment |
|---|---:|---:|---:|---|
| Capability breadth | 12 | 5 | 2 | ECC exposes a much broader toolbox. SEF has 8 broad execution playbooks plus governance packs. |
| Capability depth/actionability | 12 | 4 | 3 | ECC quality is heterogeneous but leading skills are operational. SEF playbooks contain useful depth but are not first-class reusable skills. |
| Modularity/extensibility | 8 | 5 | 1 | ECC skills are independent modules. SEF remains heavily concentrated in `sef.py`. |
| Composition/orchestration | 8 | 5 | 3 | ECC combines skills, agents, commands and hooks. SEF routes playbooks/packs but primarily through governance logic. |
| Brownfield/project awareness | 10 | 3 | 5 | SEF explicitly adopts existing repositories, preserves reality and reassesses the actual diff. |
| Verification/evidence integrity | 10 | 4 | 5 | Both verify. SEF has stronger explicit evidence states and unsupported-claim discipline. |
| Evaluation rigor | 10 | 3 | 5 | SEF has independent challenges, immutable consumed holdouts and regression separation. |
| Harness portability | 5 | 5 | 2 | ECC has multiple harness-native surfaces. SEF currently centers Codex and Claude Code. |
| Installation/user experience | 5 | 5 | 2 | ECC has plugin/package surfaces. SEF still asks the user/agent to operate a Python runtime. |
| Memory/continuous learning | 5 | 5 | 1 | ECC includes persistence/learning mechanisms. SEF does not yet expose a comparable capability. |
| Agent flexibility/low friction | 8 | 4 | 2 | ECC primarily augments. SEF's recent direction risks excessive pre-execution governance. |
| Targeted safety | 4 | 4 | 5 | SEF has strong specialist gates and evidence discipline; this should become targeted rather than dominant. |
| Marginal provider cost | 3 | 5 | 5 | Both can operate without a separate mandatory LLM API call. Experimental Semantic Routing is excluded from the production architecture score. |

Directional weighted score:

- ECC: approximately 85/100
- SEF current: approximately 64/100

This score does not mean ECC produces better code. It means ECC currently exposes a stronger capability product architecture. The comparative brownfield benchmark must decide actual task performance.

## Where ECC is structurally ahead

### 1. Skills are first-class product units

ECC defines a skill as a context-activated knowledge/workflow module with a clear activation description. A skill can contain methods, examples, anti-patterns, decision trees, verification and references. This is substantially easier to discover, compose, improve and test than a monolithic control catalog.

### 2. It gives the agent useful methods before adding constraints

Representative examples include TDD, security review, verification, architecture, agentic engineering, framework patterns and domain-specific guidance. This directly increases what the agent knows how to do.

### 3. It has multiple runtime surfaces

ECC distinguishes:

- skills: contextual knowledge/workflow
- agents: delegated specialists
- commands: explicit user entry points
- hooks: event automation
- rules: persistent standards

SEF currently compresses too many concerns into one runtime lifecycle.

### 4. It is harness-native

ECC has dedicated Codex and Claude/plugin surfaces and adapters for multiple other harnesses. The user installs capabilities into the environment the agent already uses.

### 5. It treats memory and learning as capabilities

ECC includes memory persistence and continuous-learning paths. SEF currently verifies a session well but does not yet turn repeated project-specific wins into reusable project capability.

## Where SEF is structurally ahead

### 1. Brownfield discipline

SEF's adoption model is a real differentiator. It starts from the actual repository, preserves existing architecture and scopes work against the current code rather than assuming greenfield conventions.

### 2. Actual-diff reassessment

SEF does not trust the plan alone. It can compare what was intended with what actually changed and surface newly introduced risk or verification requirements.

### 3. Evidence semantics

SEF distinguishes `PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N_A`, `WAIVED` and `BLOCKED` instead of collapsing everything into "done".

### 4. Evaluation integrity

The challenge program established useful norms:

- freeze before holdout creation;
- never tune against an independent holdout and continue calling it independent;
- preserve failed evidence;
- distinguish regression evidence from fresh generalization evidence;
- stop deterministic tuning when the architecture is the limiting factor.

This should become the quality system for capabilities.

### 5. Proportional safety kernel

SEF has strong logic for authorization, migrations, multi-tenancy, external trust, release, privacy and other high-risk changes. The mistake was making routing/governance too central, not building these controls.

## Key weakness discovered in ECC

Breadth is not the same as quality. Sampled ECC skills range from concise guidance to large prescriptive checklists. Some contain fixed technology assumptions or generic thresholds that may not fit every repository.

This creates SEF's opportunity:

> Do not win by having more skills. Win by proving that each important capability improves real task outcomes without unnecessary constraints.

## Revised SEF competitive thesis

SEF vNext should be:

> A capability system that gives coding agents reusable senior-engineering methods, composes the right methods for the task, adapts them to the real repository, verifies outcomes, and activates hard guardrails only when the operation materially requires them.

The hierarchy changes from:

```text
governance -> routing -> playbook -> agent
```

to:

```text
agent intent
  -> project context
  -> capabilities
  -> composed workflow
  -> implementation
  -> verification/evidence
  -> targeted guardrails only where material
```

## What is retained

The pivot does not delete the work since v1.4. The following become supporting infrastructure:

- `sef.py` deterministic governance baseline;
- specialist guardrail packs;
- brownfield adoption logic;
- actual-diff reassessment;
- evidence-state model;
- deterministic regression suites;
- challenge/holdout methodology;
- L2 brownfield harness;
- Semantic Routing v2 research evidence.

Semantic Routing v2 is paused as an experimental research branch of the architecture. It is not required for the vNext product path and must not become a mandatory external-API dependency.

## What is no longer the primary objective

The following are explicitly demoted:

- maximizing routing taxonomy coverage;
- perfecting an LLM semantic classifier before proving end-user capability value;
- applying heavyweight governance to ordinary implementation tasks;
- treating number of controls as a proxy for product quality.

## Capability priorities

### P0: foundational senior-engineering capabilities

1. Repository Discovery & Brownfield Mapping
2. Requirements to Acceptance Criteria
3. Implementation Planning & Scope Control
4. TDD / Bug Reproduction
5. Systematic Debugging & Root-Cause Analysis
6. Architecture-Conformant Implementation
7. Code Review & Diff Review
8. Verification Before Completion
9. Refactoring with Behavioral Preservation
10. API / External Integration Engineering
11. Database Change & Migration Engineering
12. Release / Rollback / Operational Readiness

### P1: high-frequency specialist capabilities

13. Authentication & Authorization Engineering
14. Secure Input / File Handling
15. Frontend Feature Engineering
16. Accessibility Engineering
17. Performance Investigation
18. Observability & Incident Diagnostics
19. CI / Build Repair
20. Dependency & Supply-Chain Maintenance
21. Test Strategy for Legacy Code
22. Data Backfill / Batch Processing
23. Webhook / Async Integration Engineering
24. Technical Documentation / ADR Production

### P2: expansion after measured value

Framework-, language- and domain-specific capabilities should be added only where benchmark evidence shows a recurring gap. Catalog size is not a target metric.

## Build-vs-adopt rule

For every planned SEF capability, compare against existing ECC content and other established engineering references:

- `ADOPT`: concept is already strong; implement compatible capability semantics without copying protected content.
- `ADAPT`: use the same category but improve project-awareness, verification or portability.
- `DIFFERENTIATE`: build where SEF's brownfield/eval strengths can create a measurable advantage.
- `DEFER`: low-frequency capability with no current benchmark signal.
- `REJECT`: capability adds complexity without measurable user value.

## Strategic success criterion

SEF vNext is not successful because it has 24 skills.

It is successful only if, under controlled brownfield evaluation:

1. Codex + SEF materially outperforms Codex alone;
2. Codex + SEF is competitive with or better than Codex + ECC;
3. the improvement comes without unacceptable context/token/time overhead;
4. ordinary tasks remain flexible;
5. high-risk tasks retain strong evidence and guardrails.

The empirical protocol is defined in `docs/BROWNFIELD_COMPARATIVE_EVAL_PLAN.md`.
