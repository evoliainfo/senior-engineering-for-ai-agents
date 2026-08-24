# ADR — Delivery Missions, Expert Packs and Tool Adapters

Status: proposed architecture
Date: 2026-08-24

## Decision

SEF will no longer treat a flat catalog of generic engineering skills as its primary product architecture.

The user-facing architecture becomes a layered delivery system:

```text
User outcome
   ↓
Delivery Mission
   ↓
Expert Packs + native agent abilities
   ↓
Tool Adapters / connected plugins / MCP / local tools
   ↓
Real implementation + real environment
   ↓
Executable evidence + post-deploy verification
```

The existing C2/C3-style planning/debugging/review material is reclassified as **engineering primitives**. Primitives may be loaded selectively or used inside evaluators, but they are not differentiated product capabilities by themselves.

## Why

Current frontier coding agents already plan, inspect repositories, write tests, debug, review diffs, use browsers, call tools and execute long tasks. Repeating generic advice can consume context and reduce flexibility without creating enough value.

ECC also establishes a high baseline for breadth: a large specialist toolbox, agents, hooks, memory and production-oriented skills.

SEF therefore needs to add something harder to reproduce with ordinary prompting: composed expert systems that take a non-expert from an outcome to a verified shipped system.

## Layer 0 — Native agent capabilities

SEF should use, not recreate, capabilities supplied by the harness/model:

- general reasoning and coding;
- repository navigation;
- shell and patching;
- browser/computer use;
- image generation/vision where available;
- multi-agent/subagent parallelism;
- worktrees;
- code review primitives;
- connected tools/plugins/MCP;
- memory and long-running task facilities.

SEF must remain replaceable across harnesses where possible, but it should exploit strong native features when present.

## Layer 1 — Engineering primitives

Examples:

- requirements-to-acceptance;
- repository-discovery;
- implementation-planning;
- debugging method;
- diff review;
- verification discipline.

Properties:

- small;
- selectively loaded;
- no product-value claim on their own;
- removable if ablation shows no improvement;
- no duplicate prompting when the harness already handles the behavior well.

## Layer 2 — Expert Packs

An Expert Pack is a deep specialty package, not a checklist.

It can contain:

- `SKILL.md` orchestration guidance;
- executable scripts/tools;
- provider/platform adapters;
- schemas and validation logic;
- test fixtures and adversarial cases;
- current reference pointers;
- implementation templates only when validated and adaptable;
- evidence collectors;
- failure/recovery procedures;
- focused evaluators.

Candidate expert packs include:

### Identity and access

- authentication flows;
- sessions/tokens/cookies;
- OAuth/OIDC integration;
- RBAC/ABAC/tenant isolation;
- account recovery;
- server-side authorization verification;
- E2E permission tests.

### Data lifecycle

- schema design;
- migrations/backfills;
- backup/recovery;
- rollback strategy;
- production-sized rehearsal;
- indexing/query performance;
- tenancy/data ownership;
- integrity verification.

### External integrations and webhooks

- live documentation discovery;
- auth setup;
- rate limits;
- retries/timeouts;
- idempotency;
- webhook signature/replay/out-of-order handling;
- sandbox/live separation;
- observability and failure injection.

### Billing and entitlements

- checkout/subscriptions;
- webhook-driven state;
- entitlement synchronization;
- duplicate/out-of-order event handling;
- test/live mode separation;
- billing portal/recovery paths;
- end-to-end sandbox verification.

### Web experience and visual quality

- product flow to UI implementation;
- responsive behavior;
- accessibility;
- generated/curated assets where useful;
- browser automation;
- screenshot/appshot comparison;
- loading/error/empty states;
- performance/SEO where relevant;
- real preview verification.

### Production delivery and operations

- deployment-target discovery;
- CI/CD setup;
- environment/secrets integration;
- preview/staging/production workflows;
- health checks;
- logs/metrics/traces;
- smoke tests;
- rollback;
- post-deploy verification;
- incident/recovery workflows.

### AI feature engineering

- model/tool selection;
- eval design;
- prompt/tool contracts;
- RAG/retrieval where justified;
- latency/cost budgets;
- safety/tool-abuse controls;
- observability;
- regression evals before release.

## Layer 3 — Tool Adapters

Expertise without execution is not enough.

SEF will describe tool needs abstractly, for example:

```text
browser
visual_capture
git_host
hosting
database
auth_provider
billing_provider
observability
secrets_store
```

A harness-specific adapter resolves those needs to available mechanisms:

- native Codex tools;
- installed plugins;
- MCP servers;
- CLI tools already authenticated by the user;
- repository scripts;
- enterprise-connected services.

### Rules

- SEF does not require its own OpenAI API key for normal agent-native use.
- User/provider credentials remain in the user's connected environment.
- Tool absence produces an explicit capability gap or a reduced-evidence path, not a fabricated success.
- Adapters expose capability and permission, not secret values.

## Layer 4 — Delivery Missions

A Delivery Mission is the main user-facing unit.

The user describes an outcome. The mission composes native agent abilities, expert packs and tools into a complete delivery path.

Initial mission candidates:

### `launch-production-web-product`

From rough idea to a deployed and post-deploy-verified web product slice.

Potential composition:

- product framing;
- UX/visual product flow;
- architecture;
- identity/data as needed;
- implementation;
- browser/appshot QA;
- security/release evidence;
- preview/staging deployment;
- production deployment when authorized;
- smoke and post-deploy verification.

### `ship-brownfield-feature`

From outcome request to merged/deployable feature in an existing repository, preserving project architecture and verifying actual diff behavior.

### `integrate-production-service`

Connect a payment, messaging, CRM, storage, AI, or other external service using live provider contracts, sandbox verification, failure handling and production observability.

### `ship-production-data-change`

Execute a schema/data evolution with rehearsal, backup/recovery, migration evidence, rollback and post-change verification.

### `ship-ai-feature`

Build an AI-powered feature with evals, tool/data contracts, cost/latency budgets, safety and production observability rather than just an API call.

### `incident-to-recovery`

Use runtime evidence to diagnose, mitigate, rollback/fix and verify recovery while preserving a usable incident artifact.

## Mission contract

Every material Delivery Mission must produce an evidence graph covering the stages it claims.

A mission cannot claim `DEPLOYED` merely because local tests pass.

Example states:

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

The mission must report the highest state supported by evidence.

## Multi-agent policy

SEF should exploit native multi-agent/subagent execution when it improves throughput or review independence.

Examples:

- implementation and test-design workstreams in parallel after contract lock;
- separate fresh-context reviewer;
- UI/browser QA agent against a preview while another agent inspects server/runtime evidence;
- specialist security/data review only when the change surface requires it.

SEF must not create multi-agent theater. Parallelism is used only when workstreams are meaningfully separable.

## Context policy

Progressive disclosure is mandatory.

A mission should not load all expert packs up front.

Example:

- no billing pack if no money flow exists;
- no Kubernetes pack for a Vercel-hosted app;
- no migration pack if schema is unchanged;
- no AI engineering pack for ordinary deterministic features.

This protects agent flexibility and context quality.

## Product success criterion

SEF succeeds only if Delivery Missions produce measurably better shipped outcomes than the same current agent without SEF, while keeping user expertise requirements and process friction acceptably low.

Skill count is not a product metric.