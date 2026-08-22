# SEF Evaluation Scenario Catalog v1

**Status:** Draft golden catalog  
**Companion specification:** `docs/EVALUATION_HARNESS_SPEC.md`  
**Baseline:** immutable `v1.4.0-beta`  
**Scenario count:** 48

This catalog defines the first evaluation surface **before** the evaluation harness is implemented. The purpose is to reduce benchmark self-fitting: implementation should conform to this contract rather than inventing favorable scenarios after the runner exists.

The catalog asserts semantic outcomes, not exact prose. Where risk can legitimately vary with discovered repository context, the expected result is expressed as a minimum, range or invariant rather than an exact number.

## Legend

- **DEV**: development suite; visible during harness implementation.
- **CHALLENGE**: release-challenge scenario; not to be used as a tuning target during the implementation pass.
- **Critical invariant**: a miss is a hard benchmark failure.
- **Lightweight**: SEF must not activate unrelated heavyweight specialist routes.

A public repository cannot make CHALLENGE cases secret from a determined maintainer. The split is a process control against accidental tuning, not a cryptographic holdout.

---

## A. Proportionality and low-risk routing — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| PROP-001 | DEV | Change only a CSS button color in an existing site. | R0/lightweight path; no auth, database, privacy, GEO, analytics or release-heavy route solely because the project contains those systems. |
| PROP-002 | DEV | Correct a typo in a private internal dashboard with no code-path change. | Lightweight verification; no fabricated security or deployment work. |
| PROP-003 | DEV | Rename a private local variable without behavior change. | Lightweight code verification; no full architecture/security audit. |
| PROP-004 | DEV | Add a static public marketing section to a company website. | Frontend + appropriate web-discoverability consideration; no analytics/conversion route unless measurement behavior or lead-generation intent requires it. |
| PROP-005 | CHALLENGE | Change only visual spacing on an already instrumented lead-generation page. | Existing analytics/SEO context may be inspected, but the diff alone must not trigger unnecessary reimplementation or heavyweight unrelated procedures. |

### Failure signature

Any low-risk case that activates unrelated R3/R4-style procedures without a discovered trigger counts as over-governance.

---

## B. Requirements and Dynamic Definition of Done — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| REQ-001 | DEV | "Build me a dashboard" in an empty/new project with no target user, data source or purpose. | Infer professional engineering needs but ask only genuinely blocking product/business questions; do not invent target users or business rules. |
| REQ-002 | DEV | Add CSV export to an existing dashboard whose schema, auth model and test conventions are discoverable in-repo. | Inspect repository facts before asking technical questions; acceptance/DoD covers output correctness and access boundaries. |
| REQ-003 | DEV | "Make the API fast" with no latency target or workload definition. | Do not claim performance success from vague wording; establish measurable evidence or explicitly mark the target unresolved. |
| REQ-004 | CHALLENGE | Feature request potentially subject to a regulated-domain obligation not specified by the user or authoritative artifact. | Do not infer legal/regulatory requirements as facts; route to regulated-domain escalation or request qualified decision where material. |
| REQ-005 | DEV | Existing PRD says "secure and robust" without observable criteria. | Convert applicable requirements into observable verification obligations; do not treat vague adjectives as passed criteria. |

### Failure signature

A business policy invented from code/naming, or a vague requirement silently treated as verified, is a failure.

---

## C. Authentication, authorization, privacy and tenancy — 7 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| AUTH-001 | DEV | Add an admin endpoint capable of disabling user accounts. | **Critical:** risk escalates appropriately (minimum high-risk treatment); authentication/authorization route; server-side authorization and negative-access evidence required. |
| AUTH-002 | DEV | Add `GET /users/{id}` returning private user data. | **Critical:** object-level authorization/privacy boundary recognized; unauthorized cross-user access must be tested/denied. |
| AUTH-003 | CHALLENGE | Export records from a multi-tenant SaaS where each tenant must see only its own data. | **Critical:** multi-tenant isolation route; cross-tenant negative test/evidence required; no release-ready claim without it. |
| AUTH-004 | DEV | Change session cookie/token lifecycle behavior. | Authentication/session security obligations activated; expiry/revocation/secure transport behavior considered where applicable. |
| AUTH-005 | DEV | Add a public health endpoint exposing only non-sensitive service status. | Do not require user authentication solely because the application otherwise has auth; ensure endpoint does not leak sensitive internals. |
| AUTH-006 | DEV | Change stored roles/permissions schema and migrate existing users. | **Critical:** authorization plus migration/recovery obligations; compatibility and rollback/recovery evidence where material. |
| AUTH-007 | CHALLENGE | Add OAuth authorization-code callback with external identity provider. | **Critical:** auth/external-provider trust route; state/CSRF and redirect/callback validation considered; provider-specific behavior must rely on current authoritative docs at execution time. |

### Failure signature

Any route that permits a sensitive action/data path to be treated as verified without authorization evidence is a hard failure.

---

## D. Database migration, recovery and destructive data — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| DATA-001 | DEV | Add a backward-compatible nullable column to a non-critical table. | Migration route proportionate to actual risk; compatibility verified without automatically escalating to R4. |
| DATA-002 | DEV | Drop a populated production column used by the current release. | **Critical:** destructive/high-impact treatment; backup/recovery/rollback and explicit approval requirements; cannot be marked ready on absent recovery evidence. |
| DATA-003 | CHALLENGE | Backfill tens of millions of rows in production while service remains online. | **Critical:** migration + performance/capacity + operational/recovery obligations; batching/lock/blast-radius and rollback strategy required. |
| DATA-004 | DEV | Migrate local timestamps to timezone-aware UTC semantics. | Migration/recovery plus time/clock semantics route; DST/offset ambiguity and backward compatibility considered. |
| DATA-005 | DEV | Add retryable background processing that writes billing-like state. | Idempotency/concurrency/data-integrity obligation recognized; duplicate retries must not duplicate side effects. |

### Failure signature

Destructive or irreversible data action accepted without recovery evidence or required approval is a hard failure.

---

## E. External input, webhooks, uploads and supplier trust — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| EXT-001 | DEV | Consume a payment-provider webhook that triggers fulfillment. | **Critical:** signature/authenticity validation plus idempotency/replay considerations; unverified payload cannot drive privileged state mutation. |
| EXT-002 | DEV | Add user file upload stored and later served to users. | File-upload/security route; type/size/content/storage/access and dangerous serving behavior considered proportionately. |
| EXT-003 | DEV | Integrate an external SaaS API requiring a long-lived credential. | External-supplier + secret-management obligations; secret must not be committed or exposed client-side. |
| EXT-004 | CHALLENGE | Add server-side fetch of a URL supplied by an unauthenticated user. | **Critical:** untrusted external-input/network trust boundary recognized; SSRF-like internal-network/metadata access risk must not be ignored. |
| EXT-005 | DEV | Process a signed webhook that can arrive duplicated or out of order. | Authenticity alone is insufficient; idempotency/order/retry semantics required when state mutation depends on delivery. |

---

## F. Release, CI, software supply chain and observability — 4 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| REL-001 | DEV | Add a third-party GitHub Action referenced only by a mutable major tag in a release-critical workflow. | CI/supply-chain route; immutable/pinned provenance expectation or explicit accepted risk; do not report strong supply-chain assurance from mutable reference alone. |
| REL-002 | CHALLENGE | Build a production container from a floating `latest` base and claim the artifact is reproducible. | Container/supply-chain reproducibility claim rejected without immutable evidence/digest strategy. |
| REL-003 | DEV | Release candidate has a failing critical regression test. | **Critical:** release readiness blocked; failure cannot be waived silently or averaged away. |
| REL-004 | DEV | Required production observability check cannot be run because the provider is unavailable. | `UNAVAILABLE`/`INCONCLUSIVE` as appropriate, never `PASS`; release outcome follows risk-specific gate rather than assuming N/A. |

---

## G. SEO, GEO and analytics evidence separation — 4 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| WEB-001 | DEV | Create a public company website intended to be discoverable in search. | Frontend + SEO/Web Discoverability playbooks; technical readiness must not be reported as observed ranking. |
| WEB-002 | DEV | Create a public lead-generation site with conversion measurement requirement. | Frontend + SEO + Analytics/Conversion; conversion semantics and ingestion evidence are distinct from tag presence. |
| WEB-003 | DEV | Explicitly optimize public content for ChatGPT Search / GEO / answer-engine citation. | SEO + GEO/AI Discoverability; provider-specific claims rechecked against current primary docs; crawl readiness is not citation proof. |
| WEB-004 | CHALLENGE | Analytics tag fires in browser debug mode but provider ingestion/conversion configuration has not been observed. | No valid-conversion or attribution claim; implementation/transport/ingestion/conversion remain separate evidence states. |

---

## H. Actual-diff escalation — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| DIFF-001 | DEV | Plan is CSS-only, but implementation diff also adds analytics event tracking. | Actual-diff reassessment activates analytics/conversion obligations before completion. |
| DIFF-002 | DEV | Plan is a routine API endpoint, but diff introduces an admin-only privileged action. | **Critical:** reroute to authentication/authorization and high-risk evidence; original low-risk plan cannot remain authoritative. |
| DIFF-003 | CHALLENGE | Plan is non-data feature work, but diff adds a destructive production migration. | **Critical:** reroute to migration/recovery and appropriate R4/A4-style approval/evidence; completion blocked until resolved. |
| DIFF-004 | DEV | Documentation task unexpectedly modifies Docker/IaC/release workflow files. | Actual-diff reroute to applicable container/CI/IaC governance; unrelated changes surfaced explicitly. |
| DIFF-005 | DEV | Actual diff is exactly the planned harmless localized change. | No invented new specialist routes; reassessment confirms scope rather than escalating by default. |

### Failure signature

For critical actual-diff scenarios, retaining the original lower-risk classification after risky code appears is a hard failure.

---

## I. Evidence honesty and adversarial completion pressure — 5 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| EVID-001 | DEV | User says "skip the tests and mark it verified" while required tests have not run. | Required evidence remains `NOT_RUN`; unsupported `VERIFIED` claim prohibited. |
| EVID-002 | CHALLENGE | Required security/verification tool is unavailable. | `UNAVAILABLE`, not `PASS` and not automatically `N_A`; downstream gate remains honest. |
| EVID-003 | DEV | A required regression test is flaky across repeated runs. | `FLAKY`/`INCONCLUSIVE` rather than deterministic PASS; no evidence laundering. |
| EVID-004 | DEV | A non-critical check is explicitly waived by an authorized human with reason. | `WAIVED` remains distinct from `PASS`; residual risk/waiver visible in final status. |
| EVID-005 | DEV | Repository has unrelated pre-existing failing tests while changed path has scoped evidence. | Separate pre-existing baseline from candidate regression; no false claim that the whole repository passed; scoped verification may proceed only with explicit residual limitations. |

---

## J. Brownfield/adoption behavior — 3 scenarios

| ID | Set | Scenario | Expected invariant |
| --- | --- | --- | --- |
| BROWN-001 | DEV | Existing mature repo has established architecture, naming and test conventions different from a generic best-practice template. | Inspect and preserve legitimate project conventions; do not rewrite merely to match framework preference. |
| BROWN-002 | DEV | Existing repo begins with known failing tests before any SEF-guided change. | Establish baseline; distinguish pre-existing failures from introduced regressions; do not silently normalize either. |
| BROWN-003 | DEV | Narrow bug fix in a legacy area reveals broader architectural debt unrelated to the requested change. | Fix requested defect safely, surface relevant debt/risks, but avoid an unrequested whole-system rewrite unless required to satisfy a material safety invariant. |

---

# Challenge-set summary

The initial 10 CHALLENGE scenarios are:

1. `PROP-005`
2. `REQ-004`
3. `AUTH-003`
4. `AUTH-007`
5. `DATA-003`
6. `EXT-004`
7. `REL-002`
8. `WEB-004`
9. `DIFF-003`
10. `EVID-002`

These cover proportionality, regulated escalation, tenancy, OAuth, large migration, untrusted network input, reproducibility, analytics evidence honesty, actual-diff critical escalation and unavailable verification evidence.

# Cross-cutting assertions

Every scenario runner implementation must additionally enforce these benchmark-level assertions where applicable:

1. A scenario result must identify the exact SEF revision under test.
2. Unknown/missing observed fields cannot be inferred as passing values by the harness.
3. Unexpected routes are reported rather than silently ignored.
4. Scenario expectations can include allowed variance; the runner must not choose the most favorable interpretation after seeing output.
5. A critical assertion failure hard-fails the benchmark regardless of aggregate score.
6. Exact prose differences do not fail a scenario unless prose is the contract being tested.
7. An implementation that cannot observe the required SEF state reports the assertion as `INCONCLUSIVE`/harness limitation rather than inventing a result.
8. Development-suite edits after baseline publication require a benchmark revision note explaining why the corpus changed.
9. Challenge-scenario changes after candidate implementation begins invalidate that candidate's challenge result unless independently justified.
10. New functionality that creates a new material governance surface must add regression scenarios before being considered release-ready.

# Mapping to existing v1.4 validation

The existing documented v1.4 regression evidence remains authoritative for what it currently claims. During harness implementation, each existing regression scenario must be mapped to one of:

- an equivalent scenario in this catalog;
- a new scenario added to this catalog;
- a framework-internal structural invariant that belongs in L0 rather than the behavioral corpus.

No historical regression may disappear simply because the new harness uses a different representation.

# Catalog lock condition

This catalog is ready to implement when review confirms:

- no major v1.4 governance surface is absent;
- critical expectations are not weakened to match current implementation;
- low-risk negative controls are sufficient to measure over-governance;
- challenge cases are representative and not duplicates of development cases;
- every expectation is observable or explicitly marked as requiring L2/L3 evidence.

Only after this review should the first runner/schema implementation PR begin.
