---
name: repository-discovery
description: Map an unfamiliar or materially relevant existing repository before changing it, finding the smallest architecture, conventions, tests, and change surface needed for the task.
---

# Repository Discovery

## Purpose

Understand the real codebase before proposing material changes. Build the **smallest useful repository map** that explains where the requested behavior lives, how nearby code is structured, how it is tested, and which local constraints must be preserved.

This is brownfield discovery, not a request to read the whole repository.

## When to use

Use this capability when:

- implementing or debugging behavior in a repository you do not already understand;
- the task may cross package, service, data, build, or deployment boundaries;
- the user points to an outcome but not the responsible files;
- repository conventions or existing patterns should determine the implementation approach.

Keep it lightweight when the change is obviously local and the responsible code, tests, and conventions are already known.

## Core principle

**Repository reality outranks generic preference.**

Do not prescribe a new framework, folder structure, library, abstraction, or testing style until you have checked what the project already uses and whether it can satisfy the task.

## Method

### 1. Establish the task boundary

Restate the requested outcome in one or two sentences. Separate:

- what the user explicitly wants changed;
- what must remain unchanged;
- any named files, modules, services, routes, screens, commands, or data involved.

Do not turn discovery into product requirements analysis. Hand unresolved behavior questions to `requirements-to-acceptance` when needed.

### 2. Read instruction surfaces first

Before material edits, identify applicable repository or harness instructions such as project documentation, contributor guidance, package-level conventions, agent instructions, formatting/testing commands, and generated-file warnings.

Respect narrower local instructions when they legitimately apply to a subtree. Preserve user-owned instructions rather than replacing them with generic SEF preferences.

### 3. Build a structural map, progressively

Start broad and narrow quickly:

1. inspect the top-level tree and workspace/package boundaries;
2. identify languages, package managers, build systems, test systems, and CI entry points relevant to the task;
3. locate the likely runtime entry point or feature boundary;
4. trace only the dependency/data/control path needed to explain the requested behavior;
5. find one or more analogous existing implementations before inventing a new pattern.

Prefer evidence from actual manifests, imports, routes, schemas, tests, configuration, and call sites over assumptions based on directory names.

### 4. Find the local engineering contract

For the relevant area, identify:

- public interfaces and boundaries;
- state/data ownership;
- error-handling conventions;
- validation/authentication boundaries when applicable;
- naming and abstraction patterns;
- existing test level and fixture style;
- build/type/lint/test commands that provide meaningful evidence;
- generated or vendored files that should not be edited directly.

The goal is not to catalogue everything. Capture only constraints that can change the implementation decision or its verification.

### 5. Define the likely change surface

Produce a **change-surface hypothesis**, not fake certainty:

- files/modules likely to change;
- tests likely to change or be added;
- interfaces that should remain stable;
- adjacent systems that may be affected;
- unknowns that could expand the scope.

Mark unverified guesses explicitly. If the first implementation step disproves the map, update it rather than forcing the code to fit the original plan.

### 6. Stop when the map is sufficient

Discovery is sufficient when you can explain:

- where the behavior currently lives;
- what existing pattern should normally be followed;
- what the smallest plausible change surface is;
- how the change can be verified;
- which important uncertainty remains, if any.

Do not keep reading files merely to make the map feel comprehensive.

## Expected output

Use a compact repository map when it helps the task:

```text
REPOSITORY MAP
Task boundary:
Relevant architecture:
Existing analogue(s):
Likely change surface:
Relevant tests/verification:
Local invariants to preserve:
Open uncertainties:
```

For a tiny task, this may be only a few bullets and need not be shown to the user unless useful.

## Decision points

### Existing pattern vs new abstraction

Prefer the existing pattern when it satisfies the requirement without creating a known defect. Introduce a new abstraction only when evidence shows duplication, coupling, correctness, extensibility, or maintainability makes it worthwhile for this task.

### Targeted reading vs broad exploration

Broaden exploration only when a dependency boundary, hidden call path, generated artifact, shared schema, cross-package contract, or unexplained test failure indicates the current map is insufficient.

### Ask the user vs infer locally

Do **not** ask the user to choose technical details that the repository already answers. Ask only when a product/business decision, destructive trade-off, unavailable credential/context, or genuinely ambiguous required behavior cannot be responsibly inferred.

## Failure modes and anti-patterns

- Reading the entire repository before touching a localized task.
- Assuming a folder name proves architecture or data ownership.
- Replacing existing patterns because another framework is generally preferred.
- Creating a parallel service/helper/abstraction without checking for an existing analogue.
- Treating the initial file list as guaranteed scope.
- Ignoring repository instructions or generated-file ownership.
- Asking the user questions that source code, tests, manifests, or docs already answer.
- Claiming architecture understanding without tracing the relevant runtime/test path.

## Verification of discovery quality

Before handing off, check that:

- every material architectural claim is grounded in a file, manifest, import, test, config, or observed command;
- at least one existing analogue was sought when the repository is non-trivial;
- the proposed change surface is smaller than an indiscriminate repository scan;
- verification commands/tests are repository-native rather than invented defaults;
- unknowns are explicitly separated from facts.

## Handoff

Use `requirements-to-acceptance` when required behavior is underspecified.

Use `implementation-planning` once repository reality and acceptance criteria are sufficient to sequence the change.

Do not activate a hard guardrail merely because discovery observes a broad domain word; material operations are handled separately by targeted guardrails.
