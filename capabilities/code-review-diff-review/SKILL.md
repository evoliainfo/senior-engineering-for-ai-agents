---
name: code-review-diff-review
description: Review the actual repository diff like a skeptical senior engineer, checking correctness, architecture fit, regressions, scope, maintainability, and evidence before a change is treated as release-ready.
---

# Code and Diff Review

## Purpose

Review **what actually changed**, not what the plan intended to change.

A senior review asks whether the diff satisfies the requested outcome, fits the system, preserves important contracts, introduces hidden risk, and has enough evidence to justify the completion claim. It should find meaningful defects without turning every review into stylistic churn.

This capability is deliberately technology-neutral and evidence-driven.

## When to use

Use this capability when:

- a material implementation is complete enough to inspect as a coherent diff;
- a feature/fix/refactor is about to be declared done or handed toward release;
- the actual changed files may differ from the original plan;
- a non-expert user relies on the agent to catch engineering problems they would not know to ask about.

For a trivial, obvious one-line change, perform a compact review rather than producing a long report.

## Core principles

### Review the actual diff first

Do not review from memory, the user prompt, or the implementation plan alone. Inspect the changed files, changed contracts, tests, configuration, migrations, generated artifacts, and relevant surrounding code.

### Correctness before style

Prioritize issues that can make the product wrong, unsafe, fragile, incompatible, unmaintainable, or undeployable. Do not bury a real defect under dozens of naming preferences.

### Findings need evidence

A review finding should identify:

- what is wrong or materially risky;
- where it occurs;
- why it matters for this project/task;
- what evidence supports the concern;
- the smallest credible direction for resolution when useful.

Avoid speculative “could maybe” comments with no plausible failure path.

### Review proportionally

A CSS copy edit and a data migration do not require the same review depth. Expand review according to actual diff impact, not generic ceremony.

## Method

### 1. Establish review scope from the diff

Inspect:

- changed and deleted files;
- new dependencies/configuration;
- schema/API/interface changes;
- tests added/changed/removed;
- migration/deployment/CI changes;
- generated files or lockfiles;
- unexpected files outside the planned surface.

Compare the actual diff with acceptance criteria and the implementation plan. Record material scope drift rather than assuming it is valid.

### 2. Verify the requested behavior is represented

For each committed acceptance criterion, identify where the diff implements or proves it.

Ask:

- is the main path implemented at the correct boundary?
- are important negative/preservation criteria represented?
- did implementation accidentally narrow or broaden the requirement?
- is a product decision being silently made in code?

If acceptance cannot be traced to code/evidence, flag the gap rather than inferring success.

### 3. Review architecture and ownership

Check whether the diff:

- changes the authoritative layer for the behavior;
- follows repository or selected greenfield architecture;
- duplicates an existing source of truth;
- creates an unnecessary parallel abstraction/service/store/helper;
- crosses package/service boundaries in a way that breaks ownership;
- introduces coupling that makes future changes harder without a task-driven reason.

Do not reject a deviation merely because it is new. Reject or question it when the deviation lacks evidence or degrades the system relative to the requirement.

### 4. Review correctness and failure behavior

Look for failure modes created by the actual change, such as:

- invalid/missing input handling;
- partial state writes;
- stale or inconsistent state;
- incorrect ordering/concurrency assumptions;
- wrong error propagation;
- missing idempotency/retry behavior when the operation genuinely requires it;
- serialization/schema mismatches;
- resource lifecycle/leak issues;
- timezone/locale/precision/boundary errors only where relevant.

Avoid a universal checklist. Trace the changed behavior and ask what can realistically fail.

### 5. Review security/data boundaries where materially affected

When the diff touches identity, authorization, untrusted input, secrets, files, external destinations, sensitive data, or destructive operations, inspect the relevant boundary explicitly.

Examples:

- authorization enforced server-side at the established boundary;
- secret not exposed to client/log/source;
- untrusted input validated before authoritative use;
- tenant/user data isolation preserved;
- destructive operation has the required authorization/recovery path.

Do not activate security bureaucracy for unrelated low-risk changes.

### 6. Review tests as evidence, not decoration

Check whether tests:

- observe the real behavior rather than implementation trivia;
- would have failed for the defect/change being addressed when applicable;
- cover the material boundary/negative behavior introduced by the diff;
- use the repository's appropriate test layer;
- avoid excessive mocking of the actual failure mechanism;
- were not weakened, deleted, skipped, or rewritten merely to obtain green status.

A large number of tests is not automatically strong evidence.

### 7. Review maintainability and scope discipline

Ask:

- did the diff introduce unnecessary dependency or abstraction cost?
- is new complexity proportional to current requirements?
- are names/contracts understandable in the local context?
- is duplicated logic likely to diverge?
- did temporary debug code, flags, comments, test data, TODOs, or local config leak into the change?
- did drive-by cleanup make review/risk unnecessarily broad?

Prefer concrete maintainability concerns over taste-based rewrites.

### 8. Review deployability signals

When relevant, inspect whether the diff introduces:

- new environment variables/secrets;
- migration/order requirements;
- build/runtime assumptions;
- dependency/lockfile changes;
- background jobs/queues/webhooks;
- health/observability needs;
- rollout/rollback concerns.

Do not claim deployability merely because code and unit tests pass locally.

### 9. Classify findings by severity and confidence

Use a small scale:

- **BLOCKER** — likely correctness/security/data/release failure that prevents safe completion;
- **MAJOR** — material defect or design issue that should be fixed before completion;
- **MINOR** — bounded maintainability/evidence issue worth fixing if proportionate;
- **NOTE** — observation/question, not a defect.

For each finding include confidence: high / medium / low.

Low-confidence speculative notes should not block delivery without additional evidence.

### 10. Re-review after material fixes

After correcting blockers/majors, inspect the resulting diff again. A review fix can introduce new behavior or scope.

Do not mechanically repeat the entire repository scan; re-review changed areas plus relevant interactions.

## Expected output

For material reviews:

```text
DIFF REVIEW
Scope observed:
Acceptance trace:

Findings:
- [BLOCKER|MAJOR|MINOR] location — issue — evidence — impact

Architecture/scope assessment:
Test/evidence assessment:
Deployability implications:
Residual uncertainty:
Verdict: CHANGES_REQUIRED | REVIEW_CLEAN_WITH_NOTES | READY_FOR_FINAL_VERIFICATION
```

If there are no meaningful findings, say so clearly rather than inventing comments to appear thorough.

## Decision points

### Defect vs preference

A defect has a plausible project-specific impact on correctness, safety, compatibility, maintainability, operability, or acceptance. A personal preference without material impact should not block the change.

### Fix in this diff vs follow-up

Fix now when the issue is introduced by the current change or is required for its safe operation. Defer unrelated pre-existing debt unless the current task materially worsens it or cannot be completed correctly without addressing it.

### Ask the user vs resolve technically

Resolve technical review findings using repository evidence where possible. Ask the user only when resolving the finding requires a product/business decision, irreversible trade-off, inaccessible permission/credential, or changed user-visible semantics.

## Failure modes and anti-patterns

- Reviewing the plan instead of the actual diff.
- Commenting on every style choice while missing correctness issues.
- Inventing generic security/performance concerns unrelated to changed paths.
- Recommending rewrites without demonstrating why existing architecture fails the task.
- Treating test count/coverage percentage as proof by itself.
- Missing removed/weakened tests or configuration changes.
- Ignoring migration/deployment implications because local tests pass.
- Requiring cleanup of unrelated legacy debt before allowing a focused change.
- Reporting speculative low-confidence issues as blockers.
- Claiming review passed without inspecting all material changed files.

## Verification of capability use

Before handoff:

- every material changed file/category was inspected;
- acceptance criteria can be traced to implementation/evidence or gaps are explicit;
- architecture and source-of-truth ownership were reviewed;
- realistic failure/security/data/deployment implications were considered where applicable;
- test changes were reviewed as evidence;
- findings are prioritized by impact rather than taste;
- the final verdict matches unresolved findings.

## Handoff

Use `verification-before-completion` after the diff is review-clean enough to prove the final completion status.

Future release/deployment capabilities should own production-readiness and deployment execution; this review only identifies their implications.