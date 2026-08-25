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
8. Collect system/tool-observed evidence.
9. Run the relevant evaluator/gate.
10. Add validated evidence to Project State and advance exactly one state when M1 allows it.
11. Re-run the mission decision from the new state.

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

## JIT semantics

A selected provider/framework contract must use a matching JIT capsule when the mission spec declares an expertise need. Refresh the capsule when its selected project context, semantic tool capability or authoritative source freshness no longer supports the previous capsule.

A changed observation timestamp alone is not a semantic tool-capability change; M4 owns tool-observation freshness.

## Stable Expert Packs

Load packs only when returned by the mission decision. Initial mission integration uses:

- `web-experience-visual-quality` for browser/visual verification;
- `data-change-safety` only for material persistent-data changes;
- `production-evidence-operations` for deployed-runtime/post-deploy verification.

Pack metadata does not execute tools. The active harness collects the evidence; the pack evaluator grades it.

## Current implementation boundary

The deterministic mission core currently decides what should happen next and what blocks it. It does not itself:

- execute browser, source-control, hosting, database or provider tools;
- fetch JIT sources;
- deploy an application;
- run a Stable Expert Pack evaluator automatically;
- mutate Project State beyond explicit initialization;
- claim M5 end-to-end completion.

Those execution steps are added and qualified incrementally. Keep this boundary explicit in user-facing claims.
