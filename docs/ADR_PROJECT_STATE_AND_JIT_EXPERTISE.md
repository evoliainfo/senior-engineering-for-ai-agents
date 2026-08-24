# ADR — Project State Spine and Just-In-Time Expertise

Status: proposed architecture
Date: 2026-08-24

## Decision

SEF should not rely on a giant static catalog of expert skills to carry a project from idea to production.

Two additional architectural components are required:

1. **Project State Spine** — durable structured project state that survives sessions, agents and lifecycle stages.
2. **Just-In-Time Expertise (JIT Expertise)** — project-specific expertise capsules compiled from current authoritative sources, available tools and local project evidence only when a mission needs them.

These components sit between Delivery Missions and Expert Packs/Tool Adapters.

```text
User outcome
   ↓
Delivery Mission
   ↓
Project State Spine
   ↓
Native abilities + retained primitives
   ↓
JIT Expertise / stable Expert Packs
   ↓
Tool capability resolution
   ↓
Execution in real environment
   ↓
Evidence graph + updated project state
```

## Problem 1 — Static skills age quickly

A static skill about a framework, cloud platform, auth provider, billing provider or API can become stale while the agent/model and provider documentation evolve.

A large static catalog also creates:

- maintenance burden;
- context-selection problems;
- duplicated knowledge already available in current models;
- stale examples that look authoritative;
- incentive to optimize skill count rather than delivery outcomes.

## Problem 2 — Long projects lose engineering continuity

A vibe coder can already ask a frontier agent to build large chunks of software. The hard problem increasingly becomes continuity across time and surfaces:

- why the product exists;
- what was promised vs inferred;
- which architecture decisions are authoritative;
- current data ownership and trust boundaries;
- environments and deployment targets;
- integrations and credentials that exist without exposing their values;
- which migrations/releases have happened;
- which checks actually ran;
- what is deployed now;
- what remains risky or unfinished.

Chat history alone is not a reliable engineering source of truth.

## Project State Spine

SEF maintains a compact, repository-local or workspace-local structured state.

Suggested logical sections:

```text
product
requirements
architecture
interfaces
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

### Properties

- machine-readable canonical representation;
- human-readable rendering when useful;
- versioned with the project where appropriate;
- references evidence rather than copying large logs;
- contains no secret values;
- distinguishes fact, decision, assumption and unresolved question;
- records who/what has authority for user/business decisions;
- can be updated incrementally by missions;
- remains small enough to load selectively.

### Example state fragment

```json
{
  "delivery_state": "PREVIEW_VERIFIED",
  "deployment_target": {
    "kind": "hosting",
    "name": "configured-target",
    "production_authorized": false
  },
  "identity_access": {
    "status": "IMPLEMENTED_AND_E2E_VERIFIED",
    "evidence_refs": ["evidence/auth-e2e-2026-08-24.json"]
  },
  "open_decisions": [
    {
      "id": "DEC-014",
      "owner": "user",
      "question": "Enable paid subscriptions in first public release?"
    }
  ]
}
```

The actual schema will be defined separately and kept minimal.

## Delivery state is evidence-derived

Project state must never promote itself because an agent says a stage is complete.

Example state progression:

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

Transitions require referenced evidence appropriate to the project.

## Just-In-Time Expertise

JIT Expertise produces a small **Expertise Capsule** for a specific project need.

Example triggers:

- integrating Stripe subscriptions;
- adding Clerk/Auth0/Supabase auth;
- deploying a background worker to a selected platform;
- adopting a current framework feature;
- configuring an unfamiliar database migration mechanism;
- implementing an OpenAI/Anthropic/other provider feature whose API evolves quickly.

### Inputs

- mission need;
- project state;
- repository evidence;
- selected technology/provider;
- current authoritative documentation;
- installed/native tool capabilities.

### Outputs

A capsule can contain:

- task-specific constraints;
- authoritative API/contracts relevant to this project;
- current failure/retry/rate-limit/security requirements;
- exact tool surface available;
- required verification paths;
- citations/source metadata;
- freshness/version metadata;
- optional executable fixture or adapter references.

It should not contain a broad tutorial on the entire technology.

## Source policy

Prefer sources in this order:

1. repository-local authoritative code/contracts;
2. selected provider/framework official documentation;
3. installed plugin/MCP/tool schema;
4. standards/specifications;
5. trusted secondary material only when official sources are insufficient.

Community snippets are not treated as authoritative implementation contracts.

## Capsule provenance

Each capsule records enough provenance to answer:

- where did this requirement come from?
- when was the source observed?
- which provider/framework version or feature surface was relevant?
- which local project facts caused it to be selected?
- which parts remain uncertain?

A capsule can be invalidated when:

- provider version materially changes;
- project architecture changes;
- source freshness threshold expires;
- tool capability changes;
- the mission ends and the knowledge is not worth persisting.

## Stable Expert Pack vs JIT Expertise

Use a stable Expert Pack when the value is durable and executable, for example:

- migration rehearsal harness;
- visual QA evaluator;
- evidence collector;
- provider-neutral webhook adversarial fixture suite;
- security/data test harness.

Use JIT Expertise when the value depends heavily on current external contracts, for example:

- today's provider API syntax;
- deployment platform settings;
- current auth-provider flows;
- current model/tool parameters;
- provider-specific limitations.

The two mechanisms compose.

## Tool acquisition

JIT Expertise may identify that an installed/native tool is insufficient.

The mission may then:

- use an already installed plugin/MCP/CLI;
- ask the harness to discover an appropriate tool if supported;
- recommend/install a tool only through an authorized platform flow;
- fall back to a lower-evidence path;
- stop at an explicit capability gap.

SEF must not silently install arbitrary remote code or expose credentials.

## User interaction rule

JIT Expertise exists partly to reduce questions pushed onto the vibe coder.

The agent should research and decide ordinary technical facts itself.

Ask the user only when the answer controls:

- product/business behavior;
- material recurring cost;
- data/privacy/regulatory posture;
- irreversible/destructive action;
- production authorization;
- external account/credential ownership;
- a material trade-off with no objectively dominant engineering answer.

## Competitive implication

SEF's value is not "we know Stripe" or "we know Vercel" as static text.

The intended value is:

> SEF knows **how to acquire the right current expertise, bind it to this project, use the available tools, preserve the resulting decisions/evidence, and carry the project forward without forcing the non-expert to become the integration architect.**

## Evaluation requirements

JIT Expertise must be evaluated for:

- source freshness and authority;
- relevance/compactness;
- absence of invented provider contracts;
- project-specific selection;
- reduction in unnecessary user questions;
- real integration success;
- safe behavior when current sources/tools are unavailable;
- context/token overhead.

Project State Spine must be evaluated for:

- continuity across fresh agent sessions;
- correct fact/assumption/decision separation;
- evidence-backed state transitions;
- no secret leakage;
- resistance to stale-state drift;
- usefulness to deployment and incident missions.