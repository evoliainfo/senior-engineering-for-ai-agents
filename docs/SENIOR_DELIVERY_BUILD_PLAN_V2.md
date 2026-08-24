# SEF Senior Delivery Build Plan v2

Status: authoritative roadmap for capability-system work after C2
Date: 2026-08-24
Supersedes: C3-C9 sequencing in `CAPABILITY_BUILD_PLAN.md`
Product contract: `SENIOR_DELIVERY_CONTRACT.md`

## North-star outcome

SEF must let a non-expert/vibe coder describe a product or change and have the coding agent execute the professional engineering lifecycle from reflection to verified deployment with senior-level methods, while asking the user only for decisions that genuinely require product/business/risk authority.

The system is successful only if it improves real engineering outcomes. Skill count is not a success metric.

## What C2 established

C2 merged six foundation capabilities:

1. `repository-discovery`
2. `requirements-to-acceptance`
3. `implementation-planning`
4. `tdd-bug-reproduction`
5. `systematic-debugging`
6. `verification-before-completion`

They cover core reasoning, evidence and brownfield execution methods, but do not yet close the full greenfield-to-production lifecycle.

## Roadmap design principle

Two constraints must hold simultaneously:

1. **Complete the senior delivery spine** — no critical lifecycle stage may remain ownerless before release.
2. **Do not build an unproven catalog** — pause expansion after the first 12 capabilities and measure real value before adding the delivery-completion tranche.

This produces a staged proof program instead of a race to hundreds of skills.

---

# C3 — Senior inception and implementation tranche

Add six capabilities, bringing the measured core to 12.

## 7. `product-problem-framing`

Purpose:

- turn an idea into a clear user/problem/outcome frame;
- identify users/actors, success signals, material non-goals and feasibility constraints;
- distinguish product assumptions from engineering facts;
- prevent building a technically correct solution to the wrong problem.

Must remain proportionate for small changes.

## 8. `solution-architecture-stack-selection`

Purpose:

- choose defensible system boundaries and stack choices for greenfield work;
- reuse existing stack constraints for brownfield work;
- compare options using requirements, team/user constraints, operations, ecosystem maturity, security, maintainability and deployment reality;
- document material trade-offs without forcing every choice into an ADR.

The agent chooses ordinary technical details when evidence is clear; the user decides material product/cost/policy trade-offs.

## 9. `project-bootstrap-foundations`

Purpose:

- create a maintainable initial project structure from the selected architecture;
- establish repository-native formatting, tests, build/type/lint surfaces, configuration patterns and basic documentation;
- avoid framework-generated clutter and unused infrastructure;
- create the minimum engineering foundation needed for subsequent feature delivery.

Bootstrap must be stack-adaptive and must not imply one universal JavaScript/Python stack.

## 10. `environment-secrets-configuration`

Purpose:

- separate local/test/staging/production configuration appropriately;
- define required environment variables and safe defaults;
- keep secrets out of source/logs;
- validate missing/invalid configuration early;
- document configuration contracts without exposing secret values.

This capability owns ordinary configuration hygiene. Material secret/production access remains subject to harness/user approval.

## 11. `architecture-conformant-implementation`

Purpose:

- implement features within established boundaries and repository patterns;
- select abstractions proportionate to the change;
- preserve contracts outside scope;
- handle relevant failure paths;
- avoid speculative generic architecture.

This is the main implementation-method capability, not a replacement for language/framework expertise.

## 12. `code-review-diff-review`

Purpose:

- review the actual diff for correctness, hidden coupling, regressions, security/data implications, accidental scope growth and maintainability;
- prioritize behavior/invariants over style disputes already handled by tooling;
- distinguish blocker, important issue, optional improvement and preference;
- feed newly discovered material scope back into verification/guardrails.

## C3 acceptance

Each capability requires:

- portable `SKILL.md`;
- deterministic metadata;
- at least three DEV contract cases;
- context-budget/proportionality design;
- failure modes;
- evidence contract;
- no mandatory provider/API call;
- no universal stack/tooling prescription;
- clean composition with C2 capabilities;
- exact generated manifest.

C3 exit target: 12 total capabilities, all C1/C2/C3 gates green.

---

# C4 — Core value pilot before further expansion

Do **not** immediately build more skills after C3.

Freeze the 12-capability core and run a development-value pilot.

## Pilot arms

A. Codex alone
B. Codex + current ECC snapshot recorded at freeze
C. Codex + SEF 12-capability core

## Pilot mix

12 tasks total:

- 6 brownfield tasks;
- 6 greenfield/inception-to-implemented-slice tasks.

Greenfield tasks should begin from outcome-level user requests rather than prewritten technical specifications. They need not perform real production deployment yet because deployment capabilities are deliberately gated on pilot value.

## Pilot dimensions

- functional correctness;
- requirement coverage;
- architecture/project fit;
- regression rate;
- debugging quality;
- verification truthfulness;
- maintainability;
- unnecessary user questions;
- unnecessary process friction;
- token/tool-call overhead;
- unsupported completion claims.

## Continuation gate

Continue to lifecycle completion only if:

- SEF weighted outcome score improves vs Codex alone by at least 8 percentage points;
- functional success is not worse than Codex alone;
- no critical safety regression appears;
- median token overhead is <= 35% vs Codex alone;
- no systematic low-risk friction pattern appears;
- greenfield and brownfield subsets both show non-negative value.

ECC comparison is diagnostic at C4; public superiority claims remain prohibited.

If the gate fails, stop catalog expansion and fix capability architecture before adding delivery skills.

---

# C5 — Lifecycle completion tranche

Only after C4 passes, add the capabilities required to close the idea-to-production spine.

## 13. `behavior-preserving-refactor`

Own safe structural improvement while proving behavior preservation and limiting scope.

## 14. `external-api-integration`

Own API contract discovery, authentication integration, failure/retry behavior, timeouts, idempotency where applicable, versioning and integration evidence.

## 15. `database-change-migration`

Own schema/data evolution, compatibility, migration sequencing, backfill, recovery and verification.

## 16. `security-trust-boundary-review`

Own task-scoped security review across authentication/authorization, untrusted input, sensitive data, secrets, files, external callbacks and dependency/trust boundaries.

This is a capability layer. Existing deterministic SEF guardrails remain available for material protected operations.

## 17. `release-operational-readiness`

Own build/package/release readiness, compatibility, CI evidence, migration ordering, rollback/recovery expectations, operational dependencies and residual-risk declaration.

## 18. `deployment-execution`

Own platform-adaptive deployment execution:

- discover the project's real deployment mechanism;
- validate target environment/configuration;
- execute only within harness/user permissions;
- capture artifact/version/deployment evidence;
- distinguish configuration from actual deployment success;
- stop or roll back when release evidence contradicts expectations.

No single hosting platform is hard-coded as the universal path.

## 19. `post-deploy-verification-observability`

Own post-deployment proof:

- health/readiness;
- smoke/critical journey;
- logs/metrics/traces where available;
- error/regression signals;
- migration state;
- relevant downstream/provider effects;
- rollback triggers;
- truthful `POST_DEPLOY_VERIFIED` vs incomplete states.

## C5 exit gate

- 19 total capabilities;
- every Stage 0-11 item in `SENIOR_DELIVERY_CONTRACT.md` has at least one explicit capability/workflow owner;
- no lifecycle stage is satisfied only by a generic checklist claim;
- deployment and post-deployment remain distinct evidence states;
- all earlier gates remain green.

---

# C6 — Workflow composition

Compose capabilities into six primary workflows.

## 1. Greenfield product delivery

```text
product-problem-framing
→ requirements-to-acceptance
→ solution-architecture-stack-selection
→ project-bootstrap-foundations
→ environment-secrets-configuration
→ implementation-planning
→ architecture-conformant-implementation
→ tdd-bug-reproduction as applicable
→ code-review-diff-review
→ verification-before-completion
→ security-trust-boundary-review as applicable
→ release-operational-readiness
→ deployment-execution
→ post-deploy-verification-observability
```

## 2. Brownfield feature delivery

```text
repository-discovery
→ requirements-to-acceptance
→ implementation-planning
→ architecture-conformant-implementation
→ focused testing/debugging
→ code-review-diff-review
→ verification-before-completion
→ release/deploy path when in scope
```

## 3. Bug/incident resolution

```text
repository-discovery
→ tdd-bug-reproduction
→ systematic-debugging
→ causal fix
→ code-review-diff-review
→ verification-before-completion
→ deploy/post-deploy when required
```

## 4. Refactor

Use behavior-preserving refactor + review + verification, with repository discovery proportional to uncertainty.

## 5. Integration/data change

Compose external API or database capabilities with security/release/deployment capabilities when material.

## 6. Release/production change

Release readiness → deployment execution → post-deploy verification, with guardrail escalation for destructive/live operations.

## Composition rules

- workflows are recommendations, not rigid state machines;
- trivial tasks skip irrelevant phases;
- the agent can re-enter earlier capabilities when evidence changes the problem;
- no separate classifier LLM call is required;
- no workflow may silently skip a material lifecycle owner;
- the user is not asked to manually select engineering phases.

---

# C7 — Codex-native product surface

Deliver the system where the vibe coder works.

Required:

- native Codex skill/plugin packaging compatible with current conventions;
- project-local and supported user-level installation modes;
- preservation of user `AGENTS.md`/project instructions;
- install/upgrade/uninstall verification;
- capability discovery/diagnostic surface;
- no duplicate installation behavior;
- no separate API key for normal SEF operation;
- a simple default prompt/entry path such as “build this project with SEF”.

The user should not need to invoke 19 skills manually.

---

# C8 — End-to-end lifecycle qualification

Before competitive freeze, run real end-to-end development qualification.

Minimum matrix:

- 3 greenfield project slices starting from product-level intent;
- 3 brownfield material changes;
- at least 2 scenarios include environment configuration + deployment to an ephemeral/staging/preview target;
- at least 2 require post-deployment verification;
- at least 2 include material failure/recovery behavior;
- at least 2 require a user product/business decision while ordinary technical decisions are inferred.

Evidence must measure the whole journey, including whether the agent asks unnecessary technical questions.

C8 is development evidence, not competitive holdout evidence.

---

# C9 — Freeze and fresh comparative benchmark

Freeze candidate identity before final benchmark scenario finalization.

Compare:

A. Codex alone
B. Codex + frozen ECC version
C. Codex + frozen SEF candidate

Benchmark must contain both:

- brownfield engineering tasks;
- greenfield/end-to-end delivery tasks.

No benchmark-specific patch may retain a “fresh” claim.

Only a supported statistical/practical superiority result permits a public “outperforms ECC” claim.

---

# C10 — Real Codex L2 and release decision

After C9:

- run real Codex L2 against the frozen candidate;
- verify clean installation and uninstall;
- run security review of plugin/capability surfaces;
- verify licensing/provenance;
- update README to match only proven coverage;
- confirm full Stage 0-11 ownership and evidence;
- make release/tag decision.

## Release Definition of Done

A capability-system release claiming idea-to-production support requires all of the following:

1. all Stage 0-11 lifecycle stages have evaluated owners;
2. greenfield and brownfield workflows both work end to end;
3. deployment execution has been exercised, not merely documented;
4. post-deployment verification has been exercised separately from deployment;
5. the user did not need to know or manually request ordinary senior-engineering phases;
6. material user decisions were not silently invented by the agent;
7. low-risk tasks remain proportionate;
8. no mandatory SEF-owned LLM API dependency exists;
9. core pilot showed measurable value before expansion;
10. fresh competitive evidence supports any public comparative claim;
11. real Codex L2 is completed on the frozen candidate;
12. failed and unavailable evidence remains truthfully represented.

## Explicit non-goals

SEF does not need to contain a separate skill for every framework, language or cloud provider before release. The coding model and project ecosystem provide broad implementation knowledge; SEF provides the senior engineering method, project adaptation, lifecycle composition and evidence discipline that make that knowledge deliverable.

Specialist skills should be added later when measured failure signatures justify them.
