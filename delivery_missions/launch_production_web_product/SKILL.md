---
name: launch-production-web-product
description: Orchestrate a production web-product delivery through SEF Project State, JIT Expertise, Stable Expert Packs and Codex tool-capability resolution. Use when a non-expert provides an outcome and expects the agent to progress only as far as real evidence supports.
---

# Launch Production Web Product

Use this Delivery Mission for one end-to-end web-product launch. The mission composes existing SEF contracts; it is not a replacement for Codex or for the project repository.

## Operating rule

Treat Project State as the canonical delivery truth.

Never claim a higher delivery state because the model believes work is complete. A transition is valid only through the M1 Project State API with the evidence kind required for that target state.

## Inputs the agent structures

From the user's outcome, prepare the mission spec with:

- one concrete first-delivery outcome;
- blocking acceptance criteria;
- explicit technical failure surfaces actually present: persistent data, material data change, identity/access, billing and external integrations;
- JIT Expertise needs only for selected current/provider/framework contracts that materially affect the mission.

Do not ask the user to choose ordinary technical implementation details when repository evidence, authoritative documentation and engineering judgment can resolve them.

## Mission loop

1. Initialize or validate Project State.
2. Read only the state domains returned for the next action.
3. Discover the current Codex tool inventory through the active harness and pass the explicit snapshot to M4.
4. Resolve the tool requirements for the next action.
5. Compile or refresh any required JIT capsules from current authoritative evidence.
6. Load only the Stable Expert Packs returned as active for the current failure surface.
7. Execute the next action using Codex-native tools, plugins/MCP and repository tooling.
8. Persist tool/system outputs as execution artifacts with their observed hashes and M4 capability/surface provenance.
9. Build an execution-result envelope bound to the exact mission decision and input Project State digest.
10. Pass the envelope and artifact root to the public M5 evidence API.
11. Let SEF verify artifact bytes, recompute active Expert Pack evaluators, and enforce mission-specific observation scope.
12. If the evidence receipt is `PASS`, persist it and advance Project State exactly one state. If it fails, keep Project State unchanged.
13. Re-run the mission decision from the resulting state.

Repeat until `POST_DEPLOY_VERIFIED` or until a real blocker requires user input or external access.

## Human questions

Ask the user only when the unresolved point is materially user-authoritative, such as:

- product/business behavior;
- material cost or commercial commitment;
- data/privacy/regulatory posture;
- irreversible or destructive action;
- production authorization;
- external account/credential ownership;
- a material trade-off with no objectively dominant engineering answer.

Do not push routine framework, database, test, deployment or code-structure choices onto a non-expert merely because they were not specified.

## Tool semantics

The existence of a concrete tool does not prove SEF may use it.

Use the M4 result:

- `READY` means the selected surface meets the technical and authorization contract;
- `AUTHORIZATION_REQUIRED` is a blocker until the required authorization is actually evidenced;
- `UNAUTHENTICATED`, `UNAVAILABLE`, `INSUFFICIENT_*`, `UNKNOWN` and `CONFLICT` remain blockers.

Never infer production authorization from write capability.

When execution returns evidence, a `TOOL` artifact must name the exact capability and surface selected by the pre-execution M4 decision. Evidence from an unselected surface does not support the transition.

## JIT semantics

A selected provider/framework contract must use a matching JIT capsule when the mission spec declares an expertise need. Refresh the capsule when its selected project context, semantic tool capability or authoritative source freshness no longer supports the previous capsule.

A changed observation timestamp alone is not a semantic tool-capability change; M4 owns tool-observation freshness.

## Stable Expert Packs

Load packs only when returned by the mission decision. Initial mission integration uses:

- `web-experience-visual-quality` for browser/visual verification;
- `data-change-safety` only for material persistent-data changes;
- `production-evidence-operations` for deployed-runtime/post-deploy verification.

Pack metadata does not execute tools. The active harness collects raw evidence. After execution, SEF itself loads the current pack evaluator and recomputes the report from the observation document. Do not accept an agent-authored pack `PASS` as evidence.

Mission scope is stricter than a generic pack result. A local visual gate requires a local observation, preview/release gates require preview observations, and production operations verification requires a production release observation.

## Evidence semantics

Use the public mission evidence API rather than manually calling `advance_delivery_state` after an action.

An execution result must be bound to:

- the exact mission and project;
- the exact pre-execution decision SHA-256;
- the exact input Project State SHA-256;
- the exact action.

Every declared evidence artifact must exist beneath the supplied artifact root and match its declared SHA-256. Evidence-bearing references used by the initial Stable Expert Packs must resolve to declared tool-produced artifacts.

A successful execution status alone is insufficient. The result must also provide the M1 evidence kind required for the next state, with action-appropriate provenance, and every active pack must pass when recomputed by SEF.

Receipts are immutable by default. A failed receipt is persisted for diagnosis and leaves Project State unchanged. A passing receipt is persisted, its file hash becomes M1 evidence, and M1 advances exactly one state.

## Trust boundary

SEF can verify the artifact bytes it receives, their hashes, their binding to the M4-selected surface, and the result of its own pack evaluators.

Do not claim that this alone cryptographically proves an external provider generated those bytes. Stronger provider provenance requires a signed receipt or equivalent authoritative mechanism exposed by that provider/harness.

## Current implementation boundary

The mission now provides two qualified deterministic layers:

1. pre-action orchestration: decide the next action, relevant context, JIT readiness, active packs, tool requirements and blockers;
2. post-action evidence acceptance: verify artifacts, recompute active pack gates, persist an evidence receipt and advance M1 exactly one state on `PASS`.

The mission still does not itself:

- perform live browser/source-control/hosting/database/provider actions;
- discover Codex's effective tool inventory without an explicit harness snapshot;
- fetch JIT sources without the active agent/harness;
- create provider-authenticated provenance when the provider exposes none;
- claim M5 end-to-end completion merely because deterministic fixture qualification passes.

Live Codex execution must produce the evidence envelopes/artifacts consumed by this API. End-to-end M5 completion requires real browser, preview, production/post-deploy and fresh-session evidence, not fixtures alone.
