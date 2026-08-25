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

## Agent-native entry point

When operating inside an active Codex project session, use `tools/delivery_mission.py` as the normal M5 hand-off instead of manually fabricating execution-result JSON.

The CLI commands are:

- `prepare`: compute the current M5 decision and, only when it is `READY_FOR_AGENT`, freeze the exact decision + execution plan into a new run workspace;
- `register`: snapshot one real evidence file into that run workspace and let SEF compute its SHA-256 and enforce any exact M4 slot/surface binding;
- `attach-pack`: bind a registered observation document to an Expert Pack that is active in the exact decision;
- `finalize`: build the sealed execution-result after required slots/pack observations are present;
- `accept`: submit the finalized result to the canonical M5 evidence gate, persist the receipt and advance Project State by at most one state on `PASS`;
- `status`: read the integrity-checked run manifest.

The active Codex session remains the executor. This CLI does not launch another Codex/model session, does not own provider credentials and does not grant new authorization.

Detailed command examples and trust boundary: `docs/M5_AGENT_NATIVE_LIVE_LOOP.md`.

## Mission loop

1. Initialize or validate Project State.
2. Discover the current Codex tool inventory through the active harness and pass the explicit snapshot to M4 when the next action needs tools.
3. Compile or refresh required JIT capsules from current authoritative evidence.
4. Call `tools/delivery_mission.py prepare` with the mission spec, current Project State, explicit M4 inventory and required capsule files. Stop if it returns blocked or complete.
5. Read the generated `plan.json` from the new run workspace.
6. Load only the Project State domains listed by the plan and verify their context digest.
7. Load the exact JIT capsules listed by id and SHA-256. Do not substitute a capsule with the same id but different content.
8. Load only the Stable Expert Packs listed by the plan and use their declared observation contracts.
9. Use only the M4 capability/surface bindings copied into the plan. The plan does not grant new authorization and cannot replace a selected surface.
10. Execute the action using Codex-native tools, plugins/MCP and repository tooling.
11. For every required plan slot and evidence-bearing tool output, call `tools/delivery_mission.py register` so the bytes are copied into the run workspace and hashed by SEF with exact capability/surface provenance.
12. Build active pack observation documents under the plan's evidence namespace, register them, then call `attach-pack` once for every active pack. The observation JSON may be assembled by the agent or harness, but evidence-bearing references must point to tool-produced artifacts.
13. Call `finalize` to seal the execution-result envelope using the exact result contract carried by the plan.
14. Call `accept` with the current Project State file.
15. Let SEF verify artifact bytes, M4 provenance, active Expert Pack evaluators and mission-specific observation scope.
16. If the evidence receipt is `PASS`, Project State advances exactly one state. If it fails, keep Project State unchanged.
17. Start a fresh `prepare` call from the resulting Project State.

Repeat until `POST_DEPLOY_VERIFIED` or until a real blocker requires user input or external access.

## Execution-plan semantics

The Codex execution plan is a deterministic hand-off, not a second orchestrator and not a permission document.

It binds:

- the exact mission decision SHA-256;
- the exact input Project State SHA-256;
- the bounded Project State context domains and context SHA-256;
- each approved JIT capsule by stable id and exact content SHA-256;
- each M4 requirement to the exact selected surface, access, sensitivity and authorization state;
- the required M1 primary evidence kind;
- minimum tool-support artifacts;
- active Expert Pack skill/evaluator references, observation schema and mission scope;
- the exact execution-result contract to return.

The plan is recomputable from the decision. Rehashing a modified plan does not make a substituted tool surface, access level, pack scope, evaluator, artifact role or JIT capsule acceptable.

A tool-bound plan also has a freshness boundary. If the M4 snapshot has expired by the time the plan is generated, obtain a fresh inventory and decision instead of executing stale bindings.

## Agent-native run workspace

A READY `prepare` call freezes `spec.json`, `state.before.json`, `decision.json`, `plan.json` and an integrity-sealed `run.json` beneath a new run directory. Never reuse a non-empty run directory for another execution attempt.

`register` copies the supplied evidence bytes into that run directory before hashing them. The original external/tool output may later change without changing the snapshotted evidence. If the snapshotted run artifact itself changes after registration/finalization, the downstream evidence gate rejects the SHA mismatch.

A successful finalization is not allowed while a required plan slot or an active pack observation is missing. A finalized run may be accepted only once.

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

The public M5 decision and execution plan bind each ready capsule by `capsule_id` plus `content_sha256`. The stable id alone is not version identity.

A changed observation timestamp alone is not a semantic tool-capability change; M4 owns tool-observation freshness.

## Stable Expert Packs

Load packs only when returned by the mission decision and execution plan. Initial mission integration uses:

- `web-experience-visual-quality` for browser/visual verification;
- `data-change-safety` only for material persistent-data changes;
- `production-evidence-operations` for deployed-runtime/post-deploy verification.

Pack metadata does not execute tools. The active harness collects raw evidence. After execution, SEF itself loads the current pack evaluator and recomputes the report from the observation document. Do not accept an agent-authored pack `PASS` as evidence.

Mission scope is stricter than a generic pack result. A local visual gate requires a local observation, preview/release gates require preview observations, and production operations verification requires a production release observation.

## Evidence semantics

Use the public mission evidence API through the agent-native CLI rather than manually calling `advance_delivery_state` after an action.

An execution result must be bound to:

- the exact mission and project;
- the exact pre-execution decision SHA-256;
- the exact input Project State SHA-256;
- the exact action.

Every declared evidence artifact must exist beneath the supplied artifact root and match its declared SHA-256. Evidence-bearing references used by the initial Stable Expert Packs must resolve to declared tool-produced artifacts.

A successful execution status alone is insufficient. The result must also provide the M1 evidence kind required for the next state, with action-appropriate provenance, and every active pack must pass when recomputed by SEF.

Receipts are immutable by default. A failed receipt is persisted for diagnosis and leaves Project State unchanged. A passing receipt is persisted, its file hash becomes M1 evidence, and M1 advances exactly one state.

## Trust boundary

SEF can verify the artifact bytes it receives, their hashes, their binding to the M4-selected surface, the exact JIT content identity placed in the execution plan, and the result of its own pack evaluators.

The execution plan itself performs no tool call, collects no evidence, advances no state and grants no authorization. The agent-native CLI makes the hand-off operational but still does not execute the selected provider/browser/hosting tool itself; the active Codex harness does.

Do not claim that artifact hashing alone cryptographically proves an external provider generated those bytes. Stronger provider provenance requires a signed receipt or equivalent authoritative mechanism exposed by that provider/harness.

## Current implementation boundary

The mission now provides four deterministic/agent-native layers:

1. pre-action orchestration: decide the next action, relevant context, JIT readiness, active packs, tool requirements and blockers;
2. Codex execution hand-off: compile a bounded plan with exact context, JIT, M4, M3 and evidence contracts;
3. agent-native run workspace/CLI: freeze the hand-off, snapshot/hash real evidence bytes, seal the result and submit it from the active Codex project session;
4. post-action evidence acceptance: verify artifacts, recompute active pack gates, persist an evidence receipt and advance M1 exactly one state on `PASS`.

The mission still does not itself:

- perform live browser/source-control/hosting/database/provider actions instead of the active Codex harness;
- discover Codex's effective tool inventory without an explicit harness snapshot;
- fetch JIT sources without the active agent/harness;
- create provider-authenticated provenance when the provider exposes none;
- claim M5 end-to-end completion merely because deterministic/process-boundary qualification passes.

End-to-end M5 completion requires at least one real Codex mission run with real browser evidence, real preview/staging or authorized deployment evidence, post-deploy evidence and fresh-session continuity evidence. These must come from the actual harness/tool execution, not deterministic fixtures.
