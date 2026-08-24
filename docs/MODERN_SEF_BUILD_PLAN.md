# Modern SEF Build Plan

Status: proposed successor roadmap after 2026 native-capability review
Date: 2026-08-24

## North-star

SEF should let a non-expert/vibe coder move from an outcome to a genuinely shipped, verified software system by supplying expert knowledge, connected execution and evidence that the base coding agent does not reliably provide by itself.

The product is not a library of reminders.

## Phase M0 — Native overlap pruning

Before expanding the current 12-item primitive set:

- run the native-overlap/ablation plan;
- classify each primitive KEEP_SELECTIVE / INTERNAL_ONLY / MERGE_INTO_PACK / REMOVE;
- measure token/process friction;
- stop treating primitive count as roadmap progress.

No user-facing superiority claim.

## Phase M1 — Expert Pack contract

Define a package contract capable of carrying more than prose.

An Expert Pack should support:

- `SKILL.md` or standard agent-skill entry point;
- pack metadata/version;
- tool requirements expressed abstractly;
- optional executable scripts;
- references/resources with integrity hashes;
- fixtures/examples;
- evidence collectors;
- evals;
- recovery/failure semantics;
- optional adapters for harness/provider-specific tooling.

### Required properties

- progressive loading;
- no mandatory SEF-owned LLM/API call;
- provider/harness neutrality at the contract level;
- explicit tool/permission requirements;
- no embedded secrets;
- deterministic manifest/integrity support;
- executable verification where meaningful.

## Phase M2 — First deep expert packs

Build only a small set that covers high-value production failure surfaces.

Recommended first five:

1. `identity-access-production`
2. `data-lifecycle-production`
3. `external-integration-production`
4. `web-experience-visual-quality`
5. `production-delivery-operations`

Do not add more until these are evaluated deeply.

### Why these five

Together they cover a large portion of the gap between "Codex built an app" and "a non-expert can responsibly ship it":

- who can access what;
- whether data changes survive reality;
- whether third-party integrations fail safely;
- whether the user-facing product actually works in a real browser;
- whether the system can be deployed, observed and recovered.

## Phase M3 — Tool capability resolution

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
external_provider_sandbox
observability
secrets_store
```

For each capability, the runtime/mission should be able to determine:

- available / unavailable;
- authenticated / unauthenticated;
- read-only / write-capable;
- production-sensitive / safe sandbox;
- evidence obtainable.

The first implementation should integrate naturally with Codex native tools/plugins/MCP instead of building a parallel tool ecosystem.

## Phase M4 — First Delivery Mission

Build one end-to-end mission only:

### `launch-production-web-product`

Input can be an outcome-level request from a non-expert.

The mission should be able to:

1. establish product outcome and first delivery;
2. derive acceptance without asking unnecessary technical questions;
3. design the product flow and architecture;
4. create/modify the application;
5. use appropriate expert packs dynamically;
6. create and verify auth/data/integration surfaces if required;
7. exercise the product in a real browser;
8. perform visual/accessibility/responsive checks appropriate to scope;
9. produce a preview deployment when tooling/authorization permits;
10. run release/security/data checks proportionate to the actual surface;
11. deploy to the authorized target or state exactly why production deployment is blocked;
12. run post-deploy smoke/critical-journey checks;
13. return the highest delivery state actually supported by evidence.

### Non-goal

Do not build generic support for every cloud/provider before one mission works deeply.

## Phase M5 — Mission benchmark

Compare:

A. current Codex native
B. current Codex + ECC snapshot
C. current Codex + SEF mission architecture

Use outcome-level prompts, not technical implementation specs.

At least part of the benchmark must require:

- a real running app;
- browser-observed behavior;
- connected integration or realistic sandbox;
- deployment/preview evidence;
- post-deploy verification.

### Core metrics

- successful end-user journey;
- completeness from idea to claimed delivery state;
- architecture/maintainability;
- security/data correctness;
- real browser quality;
- deployment success;
- post-deploy verification;
- unsupported claims;
- number of technical questions pushed onto the non-expert;
- total intervention count;
- token/tool/runtime cost.

### Continuation rule

If SEF does not create clear net value over native Codex, stop and redesign before adding more packs or missions.

## Phase M6 — Expand only from measured gaps

Only after the first mission proves value, add missions such as:

- `ship-brownfield-feature`;
- `integrate-production-service`;
- `ship-production-data-change`;
- `ship-ai-feature`;
- `incident-to-recovery`.

Add new Expert Packs only when a measured failure class cannot be solved adequately by native agent behavior plus existing packs.

## Phase M7 — Packaging

Package the proven system using current agent-native distribution surfaces.

For Codex/OpenAI this can include:

- Agent Skills-compatible assets;
- plugin packaging when connected tools/apps are needed;
- MCP integration where appropriate;
- repository-local project instructions/adapters;
- no duplicate installation paths.

Cross-harness packaging follows after the Codex path is proven, not before.

## Phase M8 — Release claim

A release may claim senior delivery assistance only for the delivery surfaces actually proven by benchmark evidence.

Possible staged claims:

- `FOUNDATION_PRIMITIVES_EXPERIMENTAL`
- `WEB_PRODUCT_DELIVERY_BETA`
- `PRODUCTION_DELIVERY_VERIFIED`

Do not claim "any project, idea to production" until heterogeneous project classes and deployment environments are independently demonstrated.

## Definition of Done for the first meaningful beta

A meaningful beta is not reached by having N skills.

It requires:

- primitive ablation completed;
- Expert Pack contract implemented;
- five initial deep packs evaluated;
- tool-capability resolution implemented for the first mission;
- `launch-production-web-product` operational;
- real browser evidence;
- real preview/staging deployment evidence;
- post-deploy verification evidence;
- Codex-native vs ECC vs SEF comparative benchmark;
- no critical safety/data regression;
- user-question burden measured;
- cost/context overhead measured;
- truthful scope-limited release claim.