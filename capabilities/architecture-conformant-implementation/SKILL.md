---
name: architecture-conformant-implementation
description: Implement features and fixes through the repository's chosen architecture, preserving authoritative boundaries and contracts while making the smallest maintainable change that satisfies acceptance criteria.
---

# Architecture-Conformant Implementation

## Purpose

Turn an accepted plan into working code **without losing the architecture while coding**.

A senior implementation does more than make the happy path work. It changes the authoritative layer, preserves existing contracts, follows local conventions, handles the material failure paths created by the change, and keeps the diff proportionate to the requested outcome.

This capability gives the coding agent implementation discipline without dictating one framework, language, library, or pattern.

## When to use

Use this capability when:

- implementing a material feature or bug fix after repository/solution understanding exists;
- a change crosses domain, data, API, UI, integration, or configuration boundaries;
- a greenfield project has an explicit architecture that implementation must realize;
- there is meaningful risk of adding a parallel abstraction instead of extending the authoritative path.

For a tiny, obvious edit, apply the principles proportionally rather than producing an implementation ceremony.

## Core principles

### Change the authoritative layer

Find where the relevant business rule, state transition, interface, or data ownership actually belongs. Fix or extend it there when possible rather than compensating in several downstream consumers.

### Repository reality outranks personal preference

Use the project's established patterns when they satisfy the requirement. Do not introduce a new library, architecture style, state mechanism, ORM, validation stack, or directory convention merely because it is generally popular.

### Acceptance defines success, architecture constrains the path

Acceptance criteria describe what must become true. Architecture defines how responsibilities are divided. Implementation should satisfy both without encoding accidental implementation details into product requirements.

### Smallest maintainable change, not smallest textual diff

A one-line workaround can be worse than a focused multi-file correction when the workaround violates ownership or creates duplicated truth. Conversely, do not refactor broad areas merely to make a localized change aesthetically cleaner.

## Method

### 1. Reconfirm the implementation contract

Before editing, identify:

- acceptance criteria being implemented;
- authoritative module/service/component for the behavior;
- interfaces/contracts that must remain stable;
- relevant data ownership and state transitions;
- repository-native verification surfaces;
- material unknowns that could invalidate the plan.

If the repository disproves the assumed architecture, update the plan rather than forcing code into the wrong boundary.

### 2. Trace the end-to-end path only as far as needed

For the requested behavior, follow the real path such as:

```text
input/event -> validation -> domain/application decision -> persistence/integration -> output/UI
```

Not every task has every layer. The purpose is to identify where responsibility belongs and where contracts cross boundaries.

Use existing analogous behavior as evidence when available.

### 3. Implement from authoritative state outward

Prefer changing the source of truth first, then its adapters/consumers.

Examples:

- change the domain/application rule before patching multiple renderers;
- update the schema/serializer contract before adding consumer-specific coercions;
- place authorization at the established enforcement boundary rather than hiding checks in UI only;
- update the shared adapter only if evidence shows the shared contract itself must change.

Do not broaden a shared component merely because it is convenient if only one caller requires different semantics.

### 4. Preserve contracts deliberately

For every materially affected boundary, consider:

- inputs and validation;
- outputs and error semantics;
- API/schema compatibility;
- persistence/state invariants;
- caller expectations;
- configuration/environment differences;
- retries/idempotency/concurrency only when relevant;
- accessibility/security/performance only where the change actually creates those obligations.

Avoid generic checklists disconnected from the task.

### 5. Keep implementation choices evidence-based

When several technical approaches are viable, prefer the one that:

1. fits existing architecture;
2. introduces the fewest new concepts/dependencies;
3. is easiest to test at the real behavior boundary;
4. preserves reversibility and operational clarity;
5. avoids speculative scale or abstraction.

For greenfield projects, follow `solution-architecture-stack-selection` decisions unless new implementation evidence exposes a material flaw. If so, record the reason and re-evaluate rather than silently drifting.

### 6. Maintain evidence while coding

Use the nearest meaningful feedback loop:

- focused behavior test;
- type/build check;
- integration test;
- local runtime exercise;
- fixture/snapshot only when it observes the real contract.

For reproducible bugs or testable behavior changes, use `tdd-bug-reproduction` where useful.

Do not wait until the end to discover that the implementation cannot compile, serialize, migrate, or exercise its main path.

### 7. Handle failures at the right boundary

Add error handling only where the failure can actually occur and where the repository establishes responsibility.

Avoid:

- catch-all exception swallowing;
- arbitrary retries/timeouts;
- duplicated validation in unrelated layers;
- fake fallbacks that hide invalid state;
- returning success when a required side effect failed.

Make failure semantics consistent with the project's existing contract unless the requirement intentionally changes them.

### 8. Reassess the actual diff

Before calling implementation complete, inspect the changed files and ask:

- Did the diff remain within the intended architecture?
- Did a new dependency or abstraction appear that was not justified?
- Did the code duplicate an existing source of truth?
- Did implementation expose a hidden requirement or migration/release concern?
- Did any temporary/debug/generated artifact leak into the diff?

If the actual diff differs materially from the plan, update the reasoning and verification scope.

## Greenfield adaptation

For a new project:

- treat the selected architecture as the initial contract, not sacred doctrine;
- establish a thin vertical slice early enough to prove the architecture works end-to-end;
- avoid implementing every planned layer before one real user outcome runs;
- keep environment/config boundaries compatible with the intended deployment model;
- resist speculative abstractions for future features that are not yet required.

A greenfield project should become deployable incrementally rather than accumulating local-only code for weeks.

## Brownfield adaptation

For an existing project:

- extend established boundaries before creating parallel ones;
- preserve public behavior outside accepted scope;
- reuse repository-native utilities and conventions when appropriate;
- verify the smallest relevant regression surface first, then broaden according to actual impact;
- do not perform drive-by upgrades/refactors unless they are necessary to make the requested change safe.

## Expected evidence

For material work, the agent should be able to explain internally:

```text
IMPLEMENTATION EVIDENCE
Acceptance criteria addressed:
Authoritative boundary changed:
Existing pattern followed / justified deviation:
Material contracts preserved or changed:
Focused evidence:
Relevant regression evidence:
Actual diff surprises:
Residual uncertainty:
```

This need not be shown verbosely to the user unless useful.

## Decision points

### Existing abstraction vs new abstraction

Use the existing abstraction if it expresses the required behavior cleanly. Introduce a new abstraction only when the current structure creates real duplication, incorrect ownership, coupling, or inability to test/extend the requested behavior.

### Local workaround vs authoritative correction

Prefer authoritative correction when the problem is shared truth or invalid state. Use a localized adapter/workaround only when the underlying contract is intentionally unchanged or cannot responsibly be changed within scope.

### Refactor now vs later

Refactor during implementation only when it directly enables correctness, testability, or maintainability of the requested change. Otherwise keep unrelated cleanup separate.

### Ask the user vs choose technically

Choose ordinary technical details from project evidence. Ask the user only for materially user-visible behavior, irreversible/costly decisions, inaccessible credentials/permissions, or genuine product trade-offs.

## Failure modes and anti-patterns

- Coding directly from the prompt without repository/architecture grounding.
- Adding a parallel service/helper/store because the existing path was not inspected.
- Choosing a fashionable dependency where built-in/existing project capability is sufficient.
- Spreading one business rule across UI, API, and persistence layers.
- Making a broad refactor inseparable from a small feature.
- Ignoring error paths inherent to a new external/stateful operation.
- Overengineering speculative scale, multi-tenancy, queues, caching, or abstractions without evidence.
- Silently changing architecture when implementation becomes inconvenient.
- Treating local manual success as sufficient final verification.

## Verification of capability use

Before handoff:

- the implementation maps to explicit acceptance criteria;
- authoritative boundaries are respected or deviations are justified;
- repository/selected-architecture conventions are followed where suitable;
- no unnecessary framework/tool/dependency was imposed;
- material failure behavior is addressed proportionally;
- focused evidence passes;
- actual diff has been inspected for architectural drift and scope creep.

## Handoff

Use `code-review-diff-review` to review the completed change from the perspective of a skeptical senior reviewer.

Use `verification-before-completion` to prove the final completion claim against acceptance criteria and actual diff.

Use targeted guardrails only when the actual implementation introduces a materially protected operation.