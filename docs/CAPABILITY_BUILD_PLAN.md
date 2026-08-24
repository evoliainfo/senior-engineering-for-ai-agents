# Capability System Build Plan

Status: proposed execution plan
Date: 2026-08-24
Architecture: `ADR_CAPABILITY_SYSTEM_VNEXT.md`

## Goal

Build and validate a capability-first SEF that makes Codex materially better at real brownfield engineering while retaining SEF's strongest evidence and safety assets.

The plan is intentionally finite. Catalog expansion is blocked until measured capability value exists.

## Definition of Done

A vNext capability release candidate is not complete until all of the following are true:

- a modular capability format exists;
- Codex can discover/use capabilities natively;
- no mandatory SEF-owned LLM API call exists in the normal path;
- at least 12 foundational capabilities meet their individual eval contracts;
- capabilities compose into common engineering workflows;
- existing repository instructions are preserved;
- `sef.py` deterministic beta runtime remains regression-green while migration is in progress;
- targeted guardrails can be invoked without dominating ordinary tasks;
- the brownfield pilot demonstrates a material delta vs Codex alone;
- a fresh comparative benchmark is run against ECC before any superiority claim;
- installation, upgrade and uninstall paths are documented and tested;
- release documentation clearly separates proven behavior from planned behavior.

## C0 — Strategic reset and benchmark

Deliverables:

- `ECC_CAPABILITY_BENCHMARK_V2.md`
- `ADR_CAPABILITY_SYSTEM_VNEXT.md`
- `CAPABILITY_BUILD_PLAN.md`
- `BROWNFIELD_COMPARATIVE_EVAL_PLAN.md`

Gate:

- no runtime mutation;
- Semantic Routing v2 promotion remains paused;
- PR #46 remains unmerged/superseded;
- current main regression integrity unchanged.

## C1 — Capability contract and registry

Build:

- canonical capability metadata schema;
- directory convention, initially `capabilities/<id>/SKILL.md`;
- capability manifest/registry generated from source metadata;
- validation tooling for duplicate IDs, invalid metadata, broken references and cycles;
- capability version field;
- optional `references/` and `examples/` assets;
- eval linkage metadata.

Important design requirement:

The source format should be compatible with harness-native skills where practical, but SEF-specific metadata must not make the skill unusable outside SEF.

C1 controls:

1. valid capability loads;
2. malformed metadata fails validation;
3. duplicate IDs fail;
4. missing referenced capability fails;
5. optional references do not load by default;
6. registry ordering is deterministic;
7. capability source contains no provider credential/config requirement;
8. existing `sef.py` checksum unchanged.

C1 exit gate: 8/8 deterministic controls.

## C2 — Foundation capability tranche A

Implement the first six capabilities:

1. `repository-discovery`
2. `requirements-to-acceptance`
3. `implementation-planning`
4. `tdd-bug-reproduction`
5. `systematic-debugging`
6. `verification-before-completion`

Each capability requires:

- activation contract;
- method;
- repository adaptation rules;
- failure/anti-pattern section;
- evidence/verification contract;
- context-budget design;
- at least 3 focused deterministic/replay eval cases;
- at least one brownfield outcome task reserved for pilot use.

No capability is accepted merely because its Markdown validates.

## C3 — Foundation capability tranche B

Implement:

7. `architecture-conformant-implementation`
8. `code-review-diff-review`
9. `behavior-preserving-refactor`
10. `external-api-integration`
11. `database-change-migration`
12. `release-operational-readiness`

Same acceptance standard as C2.

Additional requirement:

Capabilities 10–12 must demonstrate clean handoff to targeted guardrails when the actual task becomes materially risky.

## C4 — Composition and workflow skeletons

Create lightweight workflow composition for:

- feature delivery;
- bug resolution;
- refactor;
- external integration;
- data/migration change;
- release/production change.

Rules:

- workflows recommend a sequence, not a rigid state machine for every task;
- trivial tasks can skip unnecessary phases;
- capability handoff must be explicit and auditable;
- no central model API classifier;
- agent can discover related capabilities through metadata;
- cycles/recursive capability loading are bounded.

C4 evals include deliberately small tasks to prove that the system does not over-activate.

## C5 — Codex-native delivery surface

Goal: make capability value available where the user already works.

Deliverables:

- Codex-native plugin/skill packaging compatible with current Codex conventions;
- installation instructions;
- project-local and user-level installation modes where supported;
- preservation of existing `AGENTS.md` content;
- upgrade path;
- uninstall/reset path;
- capability listing/diagnostic command or equivalent native discovery surface;
- no duplicate install behavior.

Do not generalize to every harness before Codex proof.

## C6 — Brownfield pilot

Protocol defined in `BROWNFIELD_COMPARATIVE_EVAL_PLAN.md`.

Pilot purpose:

> Establish whether the first 12 capabilities create measurable user value before we build more.

Pilot arms:

A. Codex alone
B. Codex + ECC
C. Codex + SEF capability system

Pilot uses 12 development tasks and is considered development evidence, not final competitive proof.

Minimum continuation gate:

- SEF arm improves weighted outcome score vs Codex alone by at least 8 percentage points; and
- functional success is not worse than baseline; and
- median token overhead vs Codex alone is <= 35%; and
- no systematic low-risk friction pattern is observed; and
- any catastrophic safety regression blocks continuation regardless of aggregate score.

If this gate fails, stop catalog expansion and diagnose capability design before adding specialist skills.

## C7 — Specialist expansion

Only after C6 passes, implement a prioritized subset of P1 based on pilot failure signatures:

- authentication/authorization;
- secure input/file handling;
- frontend feature engineering;
- accessibility;
- performance investigation;
- observability/incident diagnostics;
- CI/build repair;
- dependency/supply-chain;
- legacy test strategy;
- data backfill;
- webhook/async integration;
- technical documentation/ADR.

Priority is empirical. A capability with no recurring failure signal can be deferred even if it sounds useful.

## C8 — Fresh comparative benchmark

Freeze the capability candidate before fresh benchmark task creation/finalization.

Run the full controlled protocol against:

- Codex alone;
- Codex + current ECC version recorded at freeze time;
- Codex + frozen SEF candidate.

No benchmark-specific capability patch may be made while retaining a claim that the benchmark is fresh.

Outcome classes:

- `SUPERIOR`: SEF meets superiority thresholds;
- `COMPETITIVE`: SEF is statistically/practically comparable and has documented differentiated strengths;
- `INFERIOR`: SEF underperforms materially;
- `INCONCLUSIVE`: variance/sample prevents a supported claim.

Only `SUPERIOR` supports a public "outperforms ECC" claim.

## C9 — Real L2 / release candidate

After C8:

- run real Codex L2 on frozen candidate;
- verify install/use/uninstall on a clean environment;
- run security review of capability/plugin surfaces;
- confirm no mandatory provider API dependency;
- verify provenance/licensing of original content;
- update README/product positioning;
- decide version/tag.

## Capability quality rubric

Each capability is scored 0–4 on:

1. activation precision;
2. method clarity;
3. repository adaptation;
4. technical correctness;
5. flexibility;
6. verification quality;
7. composition quality;
8. context efficiency;
9. failure-mode coverage;
10. observable task-value delta.

Acceptance before pilot:

- no dimension below 2;
- mean >= 3.0;
- technical correctness and flexibility >= 3;
- task-value delta may remain provisional until brownfield pilot.

## Anti-patterns prohibited by architecture review

- one giant always-loaded skill;
- copying ECC skills into SEF;
- hard-coding a framework/library where repository discovery should decide;
- adding a capability because a benchmark case mentions one noun;
- mandatory three-model consensus in production;
- separate LLM classification call for every task;
- unconditional 80% coverage rule across all repositories;
- blocking implementation without a material repository/user/safety reason;
- treating skill count as a KPI;
- rerunning a competitive holdout until the desired result appears.

## Finite iteration policy

For each tranche:

1. define capability contract;
2. define DEV evals;
3. implement;
4. run DEV;
5. allow at most one structural remediation round for known DEV failures before pilot;
6. run pilot/fresh benchmark only after freeze;
7. preserve failures;
8. do not tune on a fresh benchmark while keeping it "fresh".

This applies the strongest lesson from the post-v1.4 challenge program to capability engineering.
