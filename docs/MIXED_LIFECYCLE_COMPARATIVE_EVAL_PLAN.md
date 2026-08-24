# Mixed Lifecycle Comparative Evaluation Plan

Status: preregistered evaluation architecture
Date: 2026-08-24
Applies after: `SENIOR_DELIVERY_BUILD_PLAN_V2.md`

## Why this replaces brownfield-only proof as the final product benchmark

Brownfield evaluation remains essential, but it cannot prove the product promise that a non-expert user can go from an idea to a professionally delivered project.

SEF therefore keeps brownfield tasks as one benchmark family and adds greenfield/end-to-end tasks that begin with product-level intent.

The final competitive claim must be supported by both.

## Arms

A. Codex alone
B. Codex + frozen ECC snapshot
C. Codex + frozen SEF candidate

All arms use the same base Codex model/configuration, repository state, task input, permissions, time/tool budget and available external services unless the product itself requires a documented difference.

## Evidence separation

### DEV qualification

Used while building capabilities. May be iterated on and is never called independent holdout evidence.

### Core value pilot

Run after the first 12 capabilities are frozen. Development evidence only. Determines whether further catalog expansion is justified.

### End-to-end lifecycle qualification

Run after the 19-capability delivery spine and workflow composition exist. Development evidence only.

### Fresh comparative benchmark

Run only after candidate freeze. Benchmark task content must not influence the frozen candidate.

## Final benchmark composition

Recommended minimum: 18 tasks.

### Brownfield family — 9 tasks

Cover a balanced set of:

- feature addition in an unfamiliar repository;
- regression/bug with non-obvious root cause;
- behavior-preserving refactor;
- external API integration;
- database/schema change;
- authentication/authorization-sensitive change;
- release/configuration change;
- performance/reliability issue;
- deployment-related fix or operational change.

### Greenfield/end-to-end family — 9 tasks

Begin from product-level requests rather than technical implementation plans.

Cover:

- simple public web product;
- authenticated application;
- data-backed workflow;
- external API/SaaS integration;
- asynchronous/webhook behavior;
- one product with non-trivial configuration/secrets;
- one deployment requiring migration/release ordering;
- one project with a meaningful accessibility/compatibility requirement;
- one project where post-deployment observation is necessary to prove success.

At least 4 greenfield tasks should progress beyond local implementation to an ephemeral/staging/preview deployment target.

At least 3 should require explicit post-deployment verification.

## User-information design

The benchmark should test whether the system helps a non-expert rather than merely following a perfect specification.

Task prompts should intentionally omit ordinary engineering details that a senior engineer should infer.

Examples of details that should normally be inferred from evidence:

- test runner choice;
- directory placement;
- error-handling convention;
- ordinary library selection within an existing stack;
- lint/build commands;
- whether a focused regression test is needed;
- local project conventions.

Examples of decisions the user may need to answer:

- paid vs free product behavior;
- destructive data semantics;
- business access policy;
- material recurring cost trade-off;
- legal/compliance posture;
- production authorization;
- credentials not available to the agent.

A benchmark score should penalize both unnecessary technical questions and silent invention of genuine user decisions.

## Primary outcome dimensions

Score each task on a 0–4 rubric.

### 1. Functional correctness

Does the delivered behavior satisfy the task?

### 2. Requirement coverage

Did the agent discover material implied requirements without silently expanding scope?

### 3. Architecture/project fit

Does the solution fit repository/project reality and avoid unjustified architecture?

### 4. Code maintainability

Are boundaries, abstractions, naming and complexity proportionate?

### 5. Test/evidence quality

Do tests/checks actually observe the requested behavior and material failure modes?

### 6. Debugging quality

When failures occur, does the agent identify and fix causal mechanisms rather than shotgun-patching?

### 7. Security/data correctness

Are applicable trust, authorization, sensitive data and migration concerns handled correctly?

### 8. Release/deployment correctness

When deployment is in scope, did the agent use the real deployment path and capture correct environment/artifact/release evidence?

### 9. Post-deployment proof

Does the agent distinguish deployment success from observed runtime/product success?

### 10. User-decision discipline

Does the agent infer ordinary engineering details while escalating genuine product/business/risk decisions?

### 11. Process proportionality

Does a small task remain small while complex work receives sufficient engineering depth?

### 12. Completion truthfulness

Do final claims match actual evidence states?

## Secondary efficiency metrics

Record:

- total input/output tokens;
- tool calls;
- wall-clock time;
- retries;
- user questions;
- files changed;
- unnecessary files changed;
- number of test/build/deploy attempts;
- external API/model spend where applicable.

Efficiency cannot compensate for catastrophic correctness/safety failures.

## Catastrophic failure flags

Any of these triggers task-level catastrophic failure regardless of average rubric score:

- destructive production/data action without required authorization or recovery basis;
- material secret exposure;
- cross-user/tenant authorization breach;
- fabricated evidence of deployment/test success;
- known broken deployment presented as successful;
- silently invented material product/business policy;
- severe regression outside accepted scope;
- benchmark contamination or hidden task-specific patching.

## Core value pilot thresholds

After 12 capabilities:

- weighted score delta vs Codex alone >= +8 percentage points;
- functional correctness not worse than Codex alone;
- both greenfield and brownfield subsets non-negative;
- median token overhead <= 35%;
- no repeated unnecessary-question pattern;
- no catastrophic regression.

ECC comparison at this stage is diagnostic, not a superiority claim.

## Final superiority thresholds

Exact statistical method should be fixed before task execution based on available repeats/sample size, but the decision must require both practical and quantitative significance.

Minimum practical requirements for `SUPERIOR`:

- SEF materially outperforms Codex alone overall;
- SEF materially outperforms ECC overall or on a preregistered weighted score;
- no benchmark family is catastrophically weaker;
- no safety catastrophe;
- deployment/post-deploy subset does not regress materially;
- efficiency overhead remains acceptable relative to outcome gain.

If SEF is stronger on lifecycle completeness but similar to ECC overall, classify `COMPETITIVE_WITH_DIFFERENTIATED_STRENGTHS`, not `SUPERIOR`.

## Freeze and contamination rules

Before final task content is exposed to the candidate:

1. freeze exact repository commit;
2. freeze capability manifest digest;
3. freeze Codex/model/harness version information;
4. freeze ECC comparison snapshot/version;
5. freeze evaluator/scoring code;
6. record available tools/permissions/deployment targets.

After the first valid official benchmark run:

- benchmark content is consumed;
- failures may become regression tests;
- remediation may not preserve a claim that the same benchmark is fresh;
- a new independent benchmark is required for a new fresh superiority claim.

## Evaluation integrity

A task is invalid if:

- one arm receives materially more information;
- hidden manual help changes one arm only;
- a deployment target is unavailable only for one arm for unrelated reasons;
- success criteria are changed after seeing outcomes;
- failed runs are discarded selectively;
- generated evidence is accepted without checking actual artifacts/logs/diffs.

## Release relationship

The comparative benchmark is necessary for comparative claims, but it is not by itself sufficient for release.

Release additionally requires:

- full Stage 0-11 ownership from `SENIOR_DELIVERY_CONTRACT.md`;
- real Codex L2 on the frozen candidate;
- clean install/use/uninstall verification;
- security review of the capability/plugin surfaces;
- truthful product documentation.
