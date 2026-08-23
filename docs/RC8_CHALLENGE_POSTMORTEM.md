# RC-8 — First CHALLENGE postmortem

Status: **RESEARCH ONLY — runtime mutation forbidden**

## Purpose

Explain the seven failures from the first valid 10-scenario CHALLENGE for frozen candidate `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837` before any runtime remediation.

Official first-holdout result: **3/10 PASS, 7/10 FAIL**. Harness integrity passed and the holdout is now contaminated for future tuning. These ten cases may become regression evidence for later candidates, but they may never again be represented as an independent holdout after remediation.

This RC does **not** change `sef.py`, `SHA256SUMS`, routing rules, risk rules, procedures, graders, or CHALLENGE expectations.

## Observed failure signatures

| Scenario | What worked | Missing behavior |
| --- | --- | --- |
| `AUTH-003` | `MULTI_TENANT`, R3, tenant negative-evidence obligations | `AUTHORIZATION` and `security-authentication-authorization` co-routing |
| `AUTH-007` | R3, `AUTH_PROTOCOL`, auth procedure, privacy/trust routing | `EXTERNAL_SUPPLIER`, supplier procedure, explicit state/CSRF and redirect/callback obligations |
| `DATA-003` | R3, `DATABASE_MIGRATION`, `RELEASE_ENGINEERING`, migration/release obligations | `PERFORMANCE_CAPACITY_COST`, capacity procedure, explicit batch/backfill obligation |
| `DIFF-003` | actual diff overrides harmless R1 plan, detects destructive migration, raises R1→R3, routes `DATABASE_MIGRATION` | `RELEASE_ENGINEERING` on the actual-diff path |
| `EXT-004` | basic backend plan only | remains R1; no external-input trust/SSRF route or network-trust obligations |
| `REL-002` | R3, `CONTAINER_ENGINEERING`, `RELEASE_ENGINEERING`, immutable-image obligation | `CI_SUPPLY_CHAIN` and supply-chain procedure |
| `REQ-004` | blocks implementation pending `REGULATED_DOMAIN` authoritative context | remains R1; no `REGULATED_DOMAIN` pack; no qualified-authority obligation in plan |

## Causal model — hypotheses, not conclusions

### H1 — Plan-time composition closure is incomplete

**Candidate scope:** `AUTH-003`, `AUTH-007`, `DATA-003`, `REL-002`.

The primary semantic domain is recognized, but a second domain that is materially implied by the interaction is not co-routed. The defect may be in routing composition rather than initial recognition.

Examples:
- multi-tenant data access implies authorization semantics in addition to tenant isolation;
- external OAuth identity implies external-supplier/provider governance in addition to auth protocol;
- online large backfill implies capacity/load governance in addition to migration/release;
- production container reproducibility with a floating base implies supply-chain governance in addition to container/release.

**Falsifier:** if neighboring cases containing the same semantic interactions already co-route reliably without lexical overlap, H1 is too broad or wrong and the failures may be narrower trigger defects.

### H2 — Untrusted server-side network destinations are not promoted as a trust boundary

**Candidate scope:** `EXT-004`; possibly contributes to `AUTH-007` but must not be assumed.

The public unauthenticated endpoint accepts an arbitrary caller-controlled URL and causes the server to make an outbound request, yet planning remains R1 with no `WEBHOOK_TRUST` route. The current trust surface appears better at webhook/inbound-integrity patterns than at generic attacker-controlled outbound network destinations.

**Falsifier:** if semantically equivalent server-side fetch cases with different wording already produce R3 + trust routing, the defect is lexical/coverage-specific rather than structural trust-boundary reasoning.

### H3 — Material regulated context can block implementation without promoting risk/pack obligations

**Candidate scope:** `REQ-004`.

SEF correctly asks for authoritative `REGULATED_DOMAIN` context and blocks implementation, proving that the regulated uncertainty is detected somewhere. But the same material fact is not reflected in risk (`R1`) or routed packs, and the plan omits qualified-authority obligations.

This suggests a split between **human-decision detection** and **risk/pack promotion**.

**Falsifier:** if other unresolved material regulated cases consistently promote to R3 + `REGULATED_DOMAIN`, then this may instead be a specific classifier gap around clinical recommendation semantics.

### H4 — Actual-diff escalation and plan-time composition do not share the same secondary-routing closure

**Candidate scope:** `DIFF-003`.

The verify path correctly detects a destructive migration and raises R1→R3, but only adds `DATABASE_MIGRATION`; it does not add `RELEASE_ENGINEERING`. This may share conceptual semantics with H1, but it executes after an actual Git diff and may be implemented through a distinct trigger→pack path.

**Falsifier:** if actual-diff cases for other material changes already perform transitive/secondary routing, H4 collapses into a narrower destructive-migration mapping defect. If not, actual-diff closure deserves independent remediation.

## Why seven lexical patches are forbidden

The failed CHALLENGE is now visible to us. Adding direct phrase mappings such as `tenant export → AUTHORIZATION`, `python:latest → CI_SUPPLY_CHAIN`, or `medication dose → REGULATED_DOMAIN` could make the consumed cases green without demonstrating generalization.

A remediation may be promoted only if it:
1. is justified by a semantic invariant broader than the failed wording;
2. passes positive controls that vary vocabulary and fixture shape;
3. passes negative controls that must **not** over-route;
4. passes metamorphic variants that preserve meaning while changing phrasing;
5. preserves the existing 38/38 DEV baseline;
6. makes the consumed CHALLENGE cases regression tests, not a new holdout claim.

## RC-8 experimental gates

### Gate A — Positive controls

A hypothesis must predict correct routing on neighboring cases that are not literal paraphrases of the consumed CHALLENGE.

- H1 authorization composition: tenant-scoped object access must co-route tenant isolation + authorization.
- H1 supplier composition: externally delegated identity/session behavior must co-route auth protocol + supplier/provider governance when correctness depends on an external provider contract.
- H1 capacity composition: large online data transformation must route migration + operational capacity/load + release/recovery as material.
- H1 supply-chain composition: production artifact provenance/reproducibility must include supply-chain governance when mutable dependencies can alter the resulting artifact.
- H2 trust boundary: caller-controlled destinations used by a privileged/server-side network client must route external-input trust and elevated risk.
- H3 regulated context: implementation decisions that can materially affect regulated outcomes without authoritative policy must promote risk, pack, human decision, and qualified-authority obligations coherently.
- H4 actual diff: a destructive production migration introduced in the diff must route both migration/recovery and release governance regardless of the initial plan.

### Gate B — Negative controls

The remediation must avoid broad false positives.

- single-tenant data access must not invent `MULTI_TENANT`;
- local/internal auth code with no external provider contract must not invent `EXTERNAL_SUPPLIER`;
- small offline/dev-only data changes must not automatically require production capacity/release governance;
- a pinned immutable base used only for local development must not automatically become a production release/supply-chain hard gate;
- a browser/client-side URL preview that does not cause privileged server-side fetching must not be classified as server-side SSRF solely because a URL is user-controlled;
- ordinary arithmetic/unit conversion must not route `REGULATED_DOMAIN`;
- a documentation-only actual diff must remain low-risk and must not acquire migration/release packs.

### Gate C — Metamorphic controls

For each promoted invariant, vary nouns, verbs, ordering, endpoint names, provider names, deployment language, and explicit security vocabulary. Meaning-preserving rewrites should retain the same material routing outcome.

### Gate D — Regression preservation

Before any runtime promotion:
- exact existing DEV baseline remains 38/38;
- RC-1..RC-7 regression gates remain green;
- no prior PASS→FAIL is accepted without explicit architectural review;
- the seven failed CHALLENGE cases may be added to regression accounting only after the causal fix is specified.

## Promotion order

Do not patch all hypotheses simultaneously.

1. Measure H1 controls and isolate plan-time composition behavior.
2. Measure H2 independently because trust-boundary over-routing has high false-positive risk.
3. Measure H3 independently because regulated-domain promotion affects implementation blocking and risk semantics.
4. Measure H4 on the actual-diff path independently from plan-time H1.
5. Promote one validated mechanism at a time, re-running all existing regression gates after each promotion.

## CHALLENGE v2 contamination boundary

Do **not** materialize concrete CHALLENGE v2 scenarios during RC-8 remediation. Doing so would expose the future holdout to the tuning process.

Only the holdout protocol may be specified in advance:
- new scenario IDs and contents are generated after the remediated candidate is frozen;
- no direct paraphrases of the ten consumed CHALLENGE scenarios;
- same high-level capability surface may be sampled, but with different interactions/fixtures and independently written expectations;
- candidate runtime hash is frozen before scenario execution;
- first valid execution is the official verdict;
- any subsequent runtime tuning consumes that holdout for later candidates.

## Definition of Done for RC-8 research

RC-8 research is complete only when:
- all seven failures are assigned to explicit hypotheses with competing explanations;
- each hypothesis has positive, negative, and metamorphic controls capable of falsifying it;
- control observations are recorded before runtime modification;
- no `sef.py`/`SHA256SUMS` mutation occurs in the research PR;
- a remediation order is justified by expected leverage and false-positive risk;
- concrete CHALLENGE v2 content remains unmaterialized.

Only then may a separate runtime-integration PR begin.