---
name: requirements-to-acceptance
description: Turn user intent and repository context into testable acceptance criteria, separating explicit requirements, justified engineering inferences, assumptions, and decisions that genuinely require the user.
---

# Requirements to Acceptance

## Purpose

Convert an imprecise request into a **small, testable contract for success** without forcing the user to know every engineering requirement in advance.

The output should clarify what must be true when the task is complete while preserving implementation freedom.

## When to use

Use this capability when:

- the user describes an outcome but not exact behavior;
- multiple interpretations could produce materially different results;
- a feature, bug fix, integration, or refactor needs explicit completion criteria;
- professional requirements can be inferred from repository/context but should be distinguished from user requirements.

Skip a formal acceptance contract for trivial, fully specified changes where success is already obvious and directly observable.

## Core principle

**Infer engineering details; escalate product decisions.**

Do not make the user specify technical requirements that a competent engineer can derive from the repository, platform, existing behavior, or ordinary professional practice. But do not silently invent product policy, destructive trade-offs, legal/business decisions, or user-visible behavior when plausible alternatives matter.

## Requirement classes

Keep these classes distinct:

1. **Explicit** — stated by the user or authoritative task source.
2. **Repository-derived** — required by existing interfaces, conventions, tests, schemas, or compatibility commitments.
3. **Professional inference** — a proportionate engineering requirement needed for the requested outcome to be credible, such as preserving existing behavior outside scope or handling an obvious failure path.
4. **Assumption** — a temporary interpretation used because evidence is incomplete; it must be visible and revisable.
5. **Decision required** — a choice that materially changes product/business behavior and cannot be responsibly inferred.
6. **Optional improvement** — useful but not necessary for the requested outcome; keep it outside the committed scope unless adopted.

Never present an optional improvement as though the user requested it.

## Method

### 1. Define the outcome boundary

Identify:

- actor/user/system involved;
- desired observable outcome;
- current behavior if known;
- behavior explicitly out of scope;
- compatibility or preservation expectations implied by an existing system.

Use repository evidence from `repository-discovery` when the task is brownfield.

### 2. Extract explicit requirements verbatim in meaning

Preserve the user's intent. Normalize wording only enough to make it testable; do not quietly broaden the requirement.

Example:

> "Managers can export their team's report as CSV."

Becomes an acceptance statement about who can export, what report is exported, and the observable CSV result. It does not automatically authorize redesigning reporting or permissions across the application.

### 3. Add only material inferred requirements

Ask: **what could make the implementation look complete while failing the actual outcome?**

Possible inference categories:

- preservation of existing behavior outside the intended scope;
- failure/error behavior that is inherent to the requested interaction;
- data/interface compatibility already enforced by the repository;
- accessibility, security, reliability, or performance only when materially applicable;
- verification obligations needed to support the completion claim.

Do not add generic non-functional requirements by reflex.

### 4. Resolve ambiguity by evidence first

Before asking the user:

1. inspect nearby behavior and tests;
2. inspect documented product conventions;
3. inspect schemas/interfaces/configuration;
4. choose the established local behavior when it clearly answers the question and does not contradict the request.

Ask the user only if different plausible choices remain materially user-visible, risky, destructive, costly, or policy-sensitive.

### 5. Write observable acceptance criteria

Prefer statements that can be demonstrated by tests, runtime observation, a diff, or another concrete artifact.

Good:

- "An authenticated manager exporting Team A receives a CSV containing only rows visible in the existing Team A report."
- "An upstream timeout returns the repository's established recoverable error behavior and does not persist a partial record."

Weak:

- "Export works correctly."
- "The code is robust."
- "Use best practices."

Avoid encoding implementation choices in acceptance criteria unless the choice itself is a requirement.

### 6. Define negative and preservation criteria where they matter

For behavior with boundaries, include the most material things that **must not** happen.

Examples:

- unauthorized actor cannot perform the new action;
- unrelated existing endpoint behavior remains unchanged;
- failed operation does not commit partial state;
- refactor does not change public behavior.

Do not create an exhaustive negative checklist for low-risk changes.

### 7. Establish evidence for each criterion

Every committed criterion should have a plausible verification path:

- automated test;
- existing regression suite;
- build/type/lint result;
- deterministic artifact inspection;
- runtime/manual evidence where automation is not practical.

If a criterion cannot currently be verified, mark the evidence gap instead of pretending it is testable.

## Expected output

For material tasks, a compact contract is enough:

```text
ACCEPTANCE CONTRACT
Explicit:
- ...

Inferred from repository/professional practice:
- ...

Preservation / negative criteria:
- ...

Assumptions:
- ...

Decision required from user:
- ...

Optional, not committed:
- ...

Evidence map:
AC-1 -> test/observation
AC-2 -> test/observation
```

Omit empty sections.

## Decision points

### Requirement vs implementation detail

If changing the implementation while preserving observable behavior would still satisfy the task, the detail normally belongs in the plan, not the acceptance contract.

### Inference vs user question

Infer when repository evidence or ordinary engineering responsibility yields a clear, reversible, non-product-specific choice.

Ask when the choice defines business policy, user-visible semantics, irreversible data behavior, cost commitment, compliance posture, or another materially different outcome.

### Acceptance vs optional improvement

A criterion is committed only if it is necessary to satisfy explicit intent, preserve an existing contract, or prevent a material failure inherent to the task.

## Failure modes and anti-patterns

- Asking the user to design the technical solution.
- Expanding a small request into a generic enterprise checklist.
- Hiding assumptions inside declarative requirements.
- Treating inferred engineering requirements as explicit user instructions.
- Writing criteria that cannot be observed or tested.
- Encoding preferred libraries or architectures as acceptance criteria.
- Ignoring important negative behavior for authorization, destructive state changes, or similar boundaries.
- Adding optional polish and then declaring the original task incomplete without it.

## Verification of requirement quality

Before handoff, check:

- each acceptance criterion maps to the requested outcome;
- each material inference has a reason grounded in repository/context or a clear engineering failure mode;
- assumptions and user decisions are visible;
- implementation freedom remains where possible;
- criteria have evidence paths;
- scope has not silently expanded.

## Handoff

Use `implementation-planning` to turn the accepted contract into a repository-aware sequence.

Use `repository-discovery` first when the repository itself may answer open requirements.

Use targeted guardrails only if the accepted behavior actually involves a material protected operation.
