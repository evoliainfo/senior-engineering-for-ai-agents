# Modern SEF Build Plan

Status: proposed successor roadmap after 2026 native-capability review
Date: 2026-08-24

## North-star

SEF should let a non-expert/vibe coder move from an outcome to a genuinely shipped, verified software system by supplying continuity, current expertise, connected execution and evidence that the base coding agent does not reliably provide by itself.

The product is not a library of reminders.

## Phase M0 — Native overlap pruning

Before expanding the current 12-item primitive set:

- run the native-overlap/ablation plan;
- classify each primitive KEEP_SELECTIVE / INTERNAL_ONLY / MERGE_INTO_PACK / REMOVE;
- measure token/process friction;
- stop treating primitive count as roadmap progress.

No user-facing superiority claim.

M0 blocks merging the 12-item candidate as a differentiated capability catalog, but does not block architecture work on the new mission/state/tool contracts.

## Phase M1 — Project State Spine

Implement the minimal durable project state required for long-running senior delivery.

Initial state domains:

```text
product
requirements
architecture
data
identity_access
integrations
environments
quality
security
release
deployments
observability
open_decisions
known_risks
evidence
```

Required properties:

- canonical machine-readable schema;
- no secret values;
- fact / decision / assumption / unresolved distinction;
- evidence references rather than copied logs;
- evidence-backed delivery-state transitions;
- selective loading;
- deterministic integrity/versioning;
- fresh-session replay tests.

The state is a project source of truth, not a replacement for repository code/configuration.

## Phase M2 — Just-In-Time Expertise contract

Define a compact project-specific Expertise Capsule.

The capsule must support:

- mission/project trigger;
- authoritative-source provenance;
- observed/freshness timestamps;
- provider/framework/version context when relevant;
- task-specific constraints only;
- tool/API surfaces actually available;
- required verification paths;
- uncertainty and invalidation conditions;
- optional executable fixture/adapter references.

### Source order

1. repository-local authoritative contracts;
2. official provider/framework docs;
3. installed plugin/MCP/tool schemas;
4. standards/specifications;
5. trusted secondary evidence only when necessary.

### Required JIT tests

- no invented provider contract;
- compact relevance;
- current-source preference;
- correct invalidation when source/project/tool state changes;
- reduced unnecessary user questions;
- truthful failure when source/tool access is unavailable.

## Phase M3 — Stable Expert Pack contract

Stable Expert Packs carry durable executable expertise rather than volatile provider instructions.

A pack can support:

- `SKILL.md` or standard agent-skill entry point;
- metadata/version;
- abstract tool requirements;
- executable scripts;
- resources with integrity hashes;
- fixtures/adversarial cases;
- evidence collectors;
- evaluators;
- failure/recovery semantics;
- optional harness adapters.

### Initial stable packs

Build only three first:

1. `web-experience-visual-quality`
   - browser/appshot evidence;
   - responsive/accessibility checks;
   - critical-state traversal;
   - visual discrepancy loop.

2. `data-change-safety`
   - migration/backfill rehearsal;
   - backup/recovery evidence;
   - rollback checks;
   - data-integrity fixtures.

3. `production-evidence-operations`
   - deployment evidence collection;
   - smoke/health verification;
   - logging/observability checks;
   - rollback/post-deploy evidence.

Provider-specific auth, billing, hosting and external-API details should primarily arrive through JIT Expertise unless a durable executable component justifies a stable pack.

## Phase M4 — Tool capability resolution

Create a harness-neutral tool capability layer.

Examples:

```text
browser
visual_capture
source_control
ci
hosting
database_admin
auth_admin
billing_admin
external_provider_sandbox
observability
secrets_store
```

For each capability determine:

- available / unavailable;
- authenticated / unauthenticated;
- read-only / write-capable;
- sandbox / production-sensitive;
- evidence obtainable;
- authorization still required.

The first implementation should exploit Codex native tools/plugins/MCP instead of building a parallel tool ecosystem.

SEF should not own provider credentials for ordinary agent-native use.

## Phase M5 — First Delivery Mission

Build one end-to-end mission only:

### `launch-production-web-product`

Input can be an outcome-level request from a non-expert.

The mission should be able to:

1. establish product outcome and first delivery;
2. initialize/update Project State Spine;
3. derive acceptance without unnecessary technical questions;
4. design product flow and architecture;
5. discover available tools;
6. compile JIT Expertise for selected frameworks/providers/integrations;
7. load stable Expert Packs only when their failure surface exists;
8. create/modify the application;
9. create and verify auth/data/integration surfaces if required;
10. exercise the product in a real browser;
11. perform visual/accessibility/responsive checks appropriate to scope;
12. produce a preview deployment when tooling/authorization permits;
13. run release/security/data checks proportionate to the actual surface;
14. deploy to the authorized target or state exactly why production deployment is blocked;
15. run post-deploy smoke/critical-journey checks;
16. persist evidence and update the project state;
17. return the highest delivery state actually supported by evidence.

### Delivery states

```text
FRAMED
ARCHITECTED
IMPLEMENTED
VERIFIED_LOCAL
PREVIEW_VERIFIED
RELEASE_READY
DEPLOYED
POST_DEPLOY_VERIFIED
```

No state transition from model assertion alone.

### Non-goals

- do not support every cloud/provider before one mission works deeply;
- do not generate a giant static integration catalog;
- do not ask the vibe coder to choose ordinary technical implementation details.

## Phase M6 — Mission benchmark

Compare:

A. current Codex native
B. current Codex + ECC snapshot
C. current Codex + SEF mission architecture

Use outcome-level prompts, not prewritten technical specifications.

At least part of the benchmark must require:

- a real running app;
- browser-observed behavior;
- connected integration or realistic sandbox;
- preview/staging or authorized deployment evidence;
- post-deploy verification;
- a fresh-session continuation that tests Project State Spine usefulness;
- at least one current external-provider contract acquired through JIT Expertise.

### Core metrics

- successful end-user journey;
- completeness from idea to claimed delivery state;
- architecture/maintainability;
- security/data correctness;
- real browser quality;
- deployment success;
- post-deploy verification;
- stale/invented provider assumptions;
- unsupported claims;
- number of technical questions pushed onto the non-expert;
- human intervention count;
- context/token/tool/runtime cost;
- continuity after fresh-session restart.

### Continuation rule

If SEF does not create clear net value over native Codex, stop and redesign before adding more packs or missions.

## Phase M7 — Expand only from measured gaps

Only after the first mission proves value, add missions such as:

- `ship-brownfield-feature`;
- `integrate-production-service`;
- `ship-production-data-change`;
- `ship-ai-feature`;
- `incident-to-recovery`.

Add a new stable Expert Pack only when a measured repeated failure class cannot be handled adequately by native behavior + JIT Expertise + existing packs.

## Phase M8 — Packaging

Package the proven system using current agent-native distribution surfaces.

For Codex/OpenAI this can include:

- Agent Skills-compatible mission/pack entry points;
- plugin packaging when connected tools/apps are needed;
- MCP integration where appropriate;
- repository-local project-state/evidence artifacts;
- no duplicate installation paths.

Cross-harness packaging follows after the Codex path is proven, not before.

## Phase M9 — Release claim

A release may claim senior delivery assistance only for delivery surfaces proven by benchmark evidence.

Possible staged claims:

- `FOUNDATION_PRIMITIVES_EXPERIMENTAL`
- `WEB_PRODUCT_DELIVERY_BETA`
- `PRODUCTION_DELIVERY_VERIFIED`

Do not claim "any project, idea to production" until heterogeneous project classes and deployment environments are independently demonstrated.

## Definition of Done for the first meaningful beta

A meaningful beta is not reached by having N skills.

It requires:

- primitive ablation completed;
- Project State Spine implemented and replay-tested;
- JIT Expertise contract implemented and freshness/provenance-tested;
- stable Expert Pack contract implemented;
- three initial executable packs evaluated;
- tool-capability resolution implemented for the first mission;
- `launch-production-web-product` operational;
- real browser evidence;
- real preview/staging or authorized deployment evidence;
- post-deploy verification evidence;
- fresh-session continuity evidence;
- Codex-native vs ECC vs SEF comparative benchmark;
- no critical safety/data regression;
- user-question burden measured;
- cost/context overhead measured;
- truthful scope-limited release claim.