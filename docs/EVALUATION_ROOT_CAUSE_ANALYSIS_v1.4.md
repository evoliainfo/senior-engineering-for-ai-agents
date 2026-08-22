# SEF v1.4 Evaluation Root-Cause Analysis

Status: research baseline, no runtime change

Baseline under analysis: `v1.4.0-beta`

Runtime SHA-256:

`31e3dfc1b1a173c83f0a85e2aad6fe4080f33899f328261aa2129a060f5ac68e`

Repository baseline commit after merging the expanded DEV scenarios:

`ade7c737501c50babec51a8454abeb3522758d4f`

## 1. Purpose

This document explains the reproducible failure signatures currently exposed by the deterministic SEF v1.4 evaluation harness.

It is intentionally a **root-cause document, not a fix proposal**. The objective is to avoid treating each failing scenario as an isolated keyword patch. A candidate runtime change should only be implemented after its causal hypothesis is falsifiable and replayable against the frozen benchmark.

Current materialized DEV baseline:

- 28 executed scenarios total;
- 18 PASS;
- 10 FAIL;
- 0 HARNESS_ERROR;
- 1 critical false negative (`AUTH-002`).

The arithmetic pass ratio is not a product-quality score. Severity, failure class and safety consequence dominate simple percentages.

## 2. Executive finding

The 10 observed failures can be explained by **four root mechanisms**:

| Root cause | Failure mechanism | Scenarios explained |
|---|---|---|
| RC-1 | Flat lexical trigger routing is too brittle to generalize across ordinary semantic/morphological variants and some missing task concepts | `AUTH-002`, `DATA-004`, `DATA-005`, `EXT-003`, `EXT-005`, `PROP-004` |
| RC-2 | Request trigger detection is polarity-blind; prohibited/non-goal language can activate the very governance route it negates | `DIFF-004` |
| RC-3 | Broad project-level heuristic inference can become a blocking task decision even when the inferred context is not material to the current task | `WEB-001` |
| RC-4 | Verification state is too coarse and too last-result-oriented; it neither models flaky history nor distinguishes unavailable evidence from ordinary command failure | `EVID-003`, `REL-004` |

These four mechanisms explain all currently materialized failures without requiring ten independent bug theories.

## 3. Evidence standard

A root-cause assignment is marked **confirmed** only when all three are available:

1. the scenario has a reproducible observed failure;
2. the relevant v1.4 decision path can be identified in the runtime;
3. the implementation mechanism directly explains the observed output.

Where a failure could have multiple contributing factors, the primary mechanism is recorded and secondary factors are noted.

No candidate is considered validated merely because it makes the DEV suite green. It must also preserve negative controls and later survive CHALLENGE replay.

---

## 4. RC-1 — Flat lexical trigger routing is semantically brittle

**Confidence: HIGH / confirmed**

### 4.1 Mechanism

The request classifier currently relies heavily on direct regular-expression `hit(...)` checks over request text. These checks are useful and deterministic, but many semantic concepts are represented by finite literal forms rather than a normalized concept layer.

Representative v1.4 examples include:

```python
if hit(r"\b(permission|permissions|rôle|rôles|role|roles|rbac|authori[sz]|autorisation|admin|propriétaire|owner|contrôle d.access|access control)\b"):
    add("AUTHZ_CHANGED", "authorization/role semantics in request")
```

```python
if hit(r"\b(webhook|callback|endpoint de rappel|callback endpoint)\b"):
    add("INBOUND_WEBHOOK_ADDED", "inbound webhook/callback requested", ["INBOUND_WEBHOOK", "PUBLIC_API"])
```

```python
if hit(r"\b(migration|schéma|schema|colonne|column|table|base de données|database change|backfill|rattrapage de données)\b"):
    add("DATABASE_SCHEMA_CHANGED", "database/schema change requested", ["DATABASE"])
```

The SEO request scope is likewise activated from a finite vocabulary including terms such as `seo`, `search engine optimization`, `organic search`, `indexation`, `crawl`, `sitemap`, `robots.txt`, `canonical`, `schema.org`, `structured data`, `search console` and `core web vitals`.

There is no general normalization step that first maps ordinary surface forms to stable engineering concepts such as:

- `authorized` -> authorization boundary;
- `migrate` -> migration;
- `webhooks` -> webhook trust boundary;
- `discoverable in search` -> search discoverability;
- `background worker` / retryable job -> asynchronous execution;
- `external SaaS API + long-lived token` -> external supplier dependency / credential boundary.

### 4.2 Scenario mapping

#### `AUTH-002` — critical

Request semantics explicitly state that only the target user or an authorized administrator may access a private record and that cross-user access must be denied.

Observed v1.4:

- risk `R1`;
- no `AUTHORIZATION` pack;
- no authentication/authorization specialist procedure.

Why the current regex misses it:

- `authorized` does not match the bounded literal `authori[sz]` because the regex expects a word boundary immediately after `z`/`s`;
- `administrator` does not match bounded `admin`;
- access denial semantics are not independently normalized into an object-authorization concept.

This is a **critical false negative**, not merely a wording preference.

#### `DATA-004`

Request says `Migrate stored local timestamps to timezone-aware UTC...`.

Observed v1.4:

- `TIME_SEMANTICS` is recognized;
- `DATABASE_MIGRATION` is not.

`migrate` is an ordinary morphological variant of `migration`, but the schema-change trigger contains `migration`, not a normalized migrate/migration concept family.

#### `DATA-005`

Request describes a retryable background worker writing ledger-like database state where reprocessing must not duplicate a side effect.

Observed v1.4:

- no `BACKGROUND_JOB` execution context;
- no `DATABASE` execution context;
- no backend/reliability procedures.

The runtime contains downstream behavior for `BACKGROUND_JOB` once that context exists, including retry/idempotency requirements and backend/reliability playbooks, but the request classifier has no equivalent robust lexical surface for `background worker`/worker semantics. The database trigger is also oriented toward schema-change vocabulary rather than ordinary stateful database-write semantics.

This is important: the missing behavior is not absence of downstream governance. The downstream governance exists; **the task does not reach it**.

#### `EXT-003`

Request introduces an external SaaS API and a long-lived server-side token.

Observed v1.4:

- no `EXTERNAL_SUPPLIER` pack;
- no external supplier/SaaS governance procedure.

SEF project discovery recognizes some integration wording as an `EXTERNAL_SAAS` design domain and infers concerns such as contract/versioning, timeouts/retries and supplier ownership. However, that discovery signal is not equivalent to a request-time `EXTERNAL_SUPPLIER` route. The specialist pack exists downstream, but this realistic task wording does not reliably activate it.

This is both a lexical coverage gap and a routing-layer disconnect: **discovery can know that an external dependency exists while task routing still fails to select supplier governance**.

#### `EXT-005`

Request uses the plural `webhooks` and explicitly describes duplicate/out-of-order delivery and idempotent state mutation.

Observed v1.4:

- risk remains `R1`;
- no `WEBHOOK_TRUST`;
- no `INBOUND_WEBHOOK` execution context.

The current bounded regex contains singular `webhook`. `webhooks` is therefore not guaranteed to match. Duplicate/out-of-order/idempotency semantics do not independently recover the intended webhook trust route.

#### `PROP-004`

Request requires a public marketing section to remain `discoverable in search`.

Observed v1.4:

- frontend route recognized;
- SEO route missed.

The phrase expresses the intended search-discoverability outcome, but it is outside the current explicit SEO vocabulary. Again, downstream SEO playbooks exist; the routing vocabulary does not generalize far enough.

### 4.3 Root-cause interpretation

The problem is broader than six missing synonyms.

A patch that adds only:

- `authorized`;
- `migrate`;
- `webhooks`;
- `discoverable in search`;
- `worker`;
- `external SaaS`;

would likely make the current DEV examples greener, but it would not demonstrate that the architecture generalizes to neighboring forms such as:

- `permitted administrator`;
- `move existing records to UTC`;
- `event notifications from the provider`;
- `search-visible`;
- `async consumer`;
- `third-party service credential`.

Therefore RC-1 should be tested as a **concept-normalization problem**, not accepted as a keyword-list problem.

### 4.4 Candidate experiment, not yet implementation

Before runtime change, define a deterministic concept layer that can map multiple surface forms into stable task concepts while preserving inspectability.

Candidate concept families:

- authorization boundary;
- authentication/session;
- database schema/data migration;
- stateful database write;
- asynchronous/background execution;
- inbound webhook/event callback;
- external supplier/SaaS dependency;
- search discoverability;
- release/deployment;
- destructive data change.

The first experiment should remain provider-independent and deterministic. An LLM classifier is **not** the default fix because it would introduce nondeterminism into the core governance gate before a simpler normalized classifier is shown insufficient.

Acceptance condition for RC-1 candidate:

- all six affected DEV scenarios improve or remain correctly classified;
- matched negative controls remain negative;
- neighboring paraphrase tests are added before tuning is declared successful;
- no critical false-positive increase from broad token matching.

---

## 5. RC-2 — Trigger detection does not model negation/polarity

**Confidence: HIGH / confirmed**

### 5.1 Mechanism

`DIFF-004` starts with a deliberately narrow plan:

`Update README documentation wording only; do not change runtime, deployment or infrastructure.`

The expected initial plan must not activate container, CI, IaC or release governance. Those domains are introduced later by the actual diff and must then be detected.

The request trigger logic includes:

```python
if hit(r"\b(release|livraison|déployer|deployer|deploy|déploiement|deploiement|deployment|production|mise en production|go live)\b"):
    add("RELEASE_PREPARED", "release/deployment requested")
```

The classifier sees the token `deployment` but does not represent the local polarity of `do not change deployment`.

Observed result:

- the initial plan incorrectly activates release engineering;
- the later actual diff correctly recognizes Docker/CI/IaC changes.

### 5.2 Why this is a distinct root cause

Adding or removing synonyms cannot solve this class. The same token may be positive or negative depending on the clause:

- `deploy this to production` -> activate release governance;
- `do not deploy this` -> do not interpret as requested deployment;
- `deployment is explicitly out of scope` -> do not activate requested deployment;
- actual diff modifies deployment files anyway -> activate from **observed diff**, regardless of the planned negation.

The fix therefore needs to preserve the distinction between:

1. user-requested scope;
2. explicit non-goals/prohibitions;
3. actual changed surface.

Negation handling must never be allowed to suppress an actual-diff escalation.

### 5.3 Candidate experiment, not yet implementation

Introduce polarity-aware request concept extraction with bounded local negation/non-goal handling.

Acceptance conditions:

- `DIFF-004` initial plan no longer routes release engineering;
- actual diff still routes Docker/CI/IaC and any genuinely observed release changes;
- positive deployment requests continue routing release governance;
- ambiguous sentences are not silently treated as negative when polarity cannot be established.

---

## 6. RC-3 — Project-level candidate inference can over-block unrelated tasks

**Confidence: HIGH / confirmed**

### 6.1 Mechanism

`WEB-001` has project brief:

`A public company website.`

and request:

`Create a public company website with SEO so it is discoverable in search.`

Expected behavior:

- frontend + SEO;
- no analytics by default;
- implementation may proceed;
- the word `company` alone must not create an unrelated multi-tenant blocking decision.

SEF discovery currently contains:

```python
if hit(r"\b(b2b|entreprise|entreprises|company|companies|organisation|organization|workspace|équipe|team)\b"):
    sig("B2B_ORGANIZATIONS", "organization/team usage in brief")
    candidates.append("MULTI_TENANT")
```

`MULTI_TENANT` belongs to `MATERIAL_CONFIRMATIONS`.

During planning, unresolved material candidates from the project profile/baseline are converted into `human_decisions_needed`. Any such decision causes:

```python
"implementation_gate": "BLOCKED_PENDING_AUTHORITATIVE_CONTEXT"
"implementation_allowed": False
```

This means a broad project-level heuristic (`company` -> possible multi-tenant context) can block a task even when the current task is a straightforward public marketing website and multi-tenancy is not material to the requested work.

### 6.2 Why the inference itself is not necessarily wrong

The useful part should be preserved:

- organization/team language can be a legitimate signal that a SaaS product may need tenant-boundary clarification.

The defect is the promotion rule:

`possible project context` -> `blocking current task decision`

without sufficient task-materiality evidence.

This is an over-governance problem, not a reason to remove project discovery.

### 6.3 Candidate experiment, not yet implementation

Separate at least three states:

1. **candidate context**: plausible from project discovery;
2. **task-material context**: relevant to the current requested change;
3. **blocking authoritative decision**: cannot safely proceed without an answer.

A candidate should only block when the current task materially depends on the unknown fact.

Acceptance conditions:

- `WEB-001` becomes implementation-allowed while retaining frontend + SEO routing;
- genuine multi-tenant tasks still block or escalate where tenant boundaries are undecided;
- project-level hints remain visible as non-blocking context when not task-material;
- no material business/world fact is silently invented.

---

## 7. RC-4 — Verification evidence state model is too coarse and last-result-oriented

**Confidence: HIGH / confirmed**

This root mechanism explains two different symptoms with the same underlying state model.

### 7.1 Current runtime behavior

During local verification, SEF records individual command runs and computes:

```python
failures = [r for r in runs if r["returncode"] != 0]
if failures:
    state = "FAIL"
elif not runs:
    state = "INCOMPLETE_NO_PROJECT_COMMANDS"
...
else:
    state = "LOCAL_PASS"
```

The runtime then stores a single `last_verification` record for the project state.

Release readiness consults that last record and accepts only selected local-pass states.

Two limitations follow:

1. all nonzero command exits collapse into `FAIL` unless handled elsewhere;
2. repeated verification history is not synthesized into a stability state such as `FLAKY`/`INCONCLUSIVE`.

### 7.2 `EVID-003` — flaky required test

Evaluation sequence:

- run 1 passes;
- run 2 fails;
- run 3 passes.

Expected evidence semantics:

- recognize `FLAKY` or `INCONCLUSIVE`;
- do not become release-ready merely because the latest run passed.

Observed v1.4:

- recorded states are effectively `LOCAL_PASS`, `FAIL`, `LOCAL_PASS`;
- latest pass wins for release-readiness purposes;
- release becomes `READY_FOR_RELEASE_REVIEW`.

This is not a test-runner problem. The harness is exposing that SEF lacks a temporal evidence aggregation model for contradictory recent observations.

### 7.3 `REL-004` — required provider unavailable

The verification command returns a nonzero exit and explicitly reports that a required observability provider is unavailable.

Expected evidence semantics:

- `UNAVAILABLE` or `INCONCLUSIVE`;
- release blocked;
- never claim PASS.

Observed v1.4:

- verification state becomes `FAIL` because all nonzero results are treated equivalently;
- release is correctly blocked, but the evidence classification is wrong.

This distinction matters operationally:

- `FAIL`: the observed system behavior violated the check;
- `UNAVAILABLE`: the required evidence source could not be obtained;
- `INCONCLUSIVE`: evidence exists but cannot establish the proposition;
- `FLAKY`: contradictory repeated observations make the current reliability claim unstable.

These states should remain distinct even when all of them block a release.

### 7.4 Candidate experiment, not yet implementation

Define an evidence ledger/state machine with at least:

- `PLANNED`;
- `NOT_RUN`;
- `PASS` / `LOCAL_PASS`;
- `FAIL`;
- `UNAVAILABLE`;
- `INCONCLUSIVE`;
- `FLAKY`;
- `WAIVED` where explicitly authorized and permitted;
- specialist-evidence-outstanding states where applicable.

Do not infer `UNAVAILABLE` from arbitrary stderr text alone as a universal rule. The experiment must define an explicit machine-readable contract for command/evidence adapters so absence is distinguishable from assertion failure.

For repeated required checks, release readiness must consider relevant evidence history rather than only the final successful sample where flakiness has been observed and not resolved.

Acceptance conditions:

- `EVID-003` does not reach release-ready after pass/fail/pass without an explicit stability resolution rule;
- `REL-004` is classified `UNAVAILABLE` or `INCONCLUSIVE`, not ordinary `FAIL`;
- `REL-003` genuine critical regression remains `FAIL` and blocks release;
- `EVID-001` skipped tests remain non-passing evidence;
- state transitions are deterministic and auditable.

---

## 8. Failure-to-root mapping

| Scenario | Severity | Observed failure | Root cause |
|---|---:|---|---|
| `AUTH-002` | critical | object authorization boundary missed | RC-1 |
| `DATA-004` | high | UTC/time semantics seen; data migration missed | RC-1 |
| `DATA-005` | high | async/background + DB/idempotency execution surface missed | RC-1 |
| `EXT-003` | high | external SaaS/supplier governance missed | RC-1 |
| `EXT-005` | high | plural webhook + delivery semantics missed | RC-1 |
| `PROP-004` | standard | search-discoverability intent missed | RC-1 |
| `DIFF-004` | high | negated deployment term activates release governance in initial plan | RC-2 |
| `WEB-001` | standard | `company` project heuristic creates unrelated multi-tenant blocker | RC-3 |
| `EVID-003` | high | pass/fail/pass history collapses to latest pass for release | RC-4 |
| `REL-004` | high | unavailable evidence collapses to generic FAIL | RC-4 |

## 9. What should **not** be done next

The current evidence argues against the following responses:

### 9.1 Do not patch ten scenarios independently

That would optimize for the visible DEV set and create a false sense of generalization.

### 9.2 Do not replace deterministic routing with an LLM classifier by default

That would trade known lexical brittleness for nondeterministic governance decisions, cost, provider coupling and harder regression diagnosis before proving a deterministic normalization layer insufficient.

### 9.3 Do not weaken the benchmark to make v1.4 appear healthier

The contract review already removed assertions that were stricter than the locked catalog. Remaining failures have direct causal support.

### 9.4 Do not let negation suppress actual-diff evidence

User-request polarity and observed repository changes are different evidence channels.

### 9.5 Do not treat every inferred project context as either irrelevant or blocking

The missing concept is task materiality, not the elimination of discovery.

### 9.6 Do not treat release blocking as sufficient evidence correctness

`REL-004` blocks release, but still classifies unavailable evidence incorrectly. Evidence honesty is itself a requirement.

## 10. Proposed experiment order

No runtime implementation should begin until the candidate tests below are specified.

### Experiment A — normalized task concepts

Targets RC-1.

Create DEV neighbor paraphrases and negative controls before implementation, then evaluate a deterministic concept-normalization candidate.

Priority: **highest**, because it includes the only current critical false negative.

### Experiment B — request polarity/non-goals

Targets RC-2.

Add positive, negative and ambiguous variants for release, auth, data deletion and infrastructure language. Confirm actual-diff escalation remains independent.

Priority: high.

### Experiment C — task-material context gating

Targets RC-3.

Compare:

- public company website;
- B2B marketing site;
- team SaaS with organization membership;
- explicit multi-tenant SaaS;
- unrelated task inside a multi-tenant repo.

Priority: high because over-blocking directly affects usability/proportionality.

### Experiment D — evidence ledger/state transitions

Targets RC-4.

Specify transition fixtures for:

- pass;
- fail;
- unavailable;
- pass/fail/pass;
- fail/pass/pass under an explicit stabilization policy;
- skipped/not-run;
- specialist evidence outstanding;
- authorized waiver where allowed.

Priority: high for release truthfulness.

## 11. Decision gate before modifying `sef.py`

A runtime candidate is allowed only when:

1. its target root cause is explicitly named;
2. new neighboring tests are written before or alongside the candidate, not after observing candidate output;
3. the frozen v1.4 baseline remains reproducible;
4. candidate results are compared against the same scenarios;
5. critical false negatives do not increase;
6. over-governance is re-measured, not ignored;
7. the candidate does not silently weaken evidence semantics;
8. CHALLENGE scenarios are not used as iterative tuning targets;
9. accepted changes have a simpler causal explanation than scenario-by-scenario exceptions.

## 12. Current conclusion

The expanded benchmark has already achieved its primary purpose: it changed the next engineering decision.

Before the benchmark, a reasonable temptation would have been to add more packs, skills or ECC-style agent capabilities.

The evidence now says the highest-value work is elsewhere:

1. make SEF's existing governance routes **recognize ordinary task meaning more robustly**;
2. distinguish requested scope from negated/non-goal scope;
3. make project discovery **task-material rather than globally blocking**;
4. make verification evidence **stateful, truthful and temporally aware**.

SEF does not currently need more governance breadth to address these failures. It needs a stronger decision layer connecting user/project evidence to the governance it already has.

No v1.5 or other release number is implied by this analysis.
