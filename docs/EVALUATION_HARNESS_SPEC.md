# SEF Evaluation Harness Specification

**Status:** Draft for review  
**Baseline under evaluation:** `v1.4.0-beta`  
**Scope of this document:** evaluation architecture only; no SEF runtime behavior change  
**Primary objective:** determine whether SEF makes the right engineering-governance decisions, with the right amount of friction, and whether candidate changes measurably improve that behavior without critical regressions.

## 1. Why this harness exists

SEF already has an embedded self-test and documented regression suites. Those tests establish that representative policy-routing paths and framework invariants behave as intended. They do not establish that:

- the full decision surface is sufficiently complete;
- low-risk work avoids unnecessary governance;
- missing evidence is never promoted to success across a broad adversarial corpus;
- an implementation that introduces new risk through the actual diff is reliably rerouted;
- Codex and Claude Code preserve the same critical SEF invariants in real agent-in-the-loop work;
- a change inspired by another agent framework improves SEF rather than merely increasing complexity;
- a real project built under SEF reaches a stronger engineering outcome than the v1.4 baseline.

The evaluation harness is therefore a **decision-quality and evidence-quality benchmark**, not a line-coverage target and not a leaderboard of features.

## 2. Evaluation principles

1. **Freeze the baseline.** `v1.4.0-beta` is the behavioral reference. Its tag must not move.
2. **Evaluate outcomes, not wording.** Tests should assert engineering invariants, routes, evidence states and gates rather than exact prose unless exact text is itself a contract.
3. **Separate deterministic from probabilistic evidence.** SEF runtime decisions, coding-agent behavior and real-project outcomes are different evidence classes.
4. **Critical false negatives dominate aggregate scores.** A high average score cannot compensate for a missed auth bypass, destructive migration, tenant-isolation failure or false production-readiness claim.
5. **Measure over-governance as a defect.** A framework that routes every task through every control is not successful.
6. **Missing evidence is not success.** `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `WAIVED` and `BLOCKED` must remain semantically distinct from `PASS`.
7. **Do not tune against one visible corpus only.** Maintain a release challenge set separate from the normal development suite.
8. **Candidate changes need a falsifiable hypothesis.** No feature is admitted merely because another framework has it.
9. **No automatic policy learning.** Observed failures may produce change candidates, never silently mutate SEF policy.
10. **Report limitations.** Passing the harness is evidence about the tested decision surface, not proof that every future application is secure, correct or production-ready.

## 3. Four evidence layers

### L0 — Runtime integrity

Deterministic checks proving the tested artifact is the intended artifact:

- exact baseline/candidate revision;
- `SHA256SUMS` verification where applicable;
- Python compilation;
- embedded `self-test`;
- fixture and scenario schema validation.

A failure at L0 invalidates all higher-layer results for that run.

### L1 — Deterministic governance benchmark

Exercises SEF's routing, risk/action classification, Dynamic Definition of Done, evidence semantics, actual-diff reassessment and release gates against controlled scenarios.

Target: identical input + identical SEF revision produces identical normalized benchmark output.

### L2 — Agent-in-the-loop benchmark

Runs supported coding-agent adapters against controlled repositories and briefs.

Initial supported harnesses:

- Codex via `AGENTS.md`;
- Claude Code via `CLAUDE.md`.

Because model behavior is probabilistic, L2 results are reported as repeated-trial outcomes, not as deterministic truth.

### L3 — Real-project pilots

Evaluates SEF on end-to-end project classes:

1. B2B acquisition website;
2. authenticated SaaS;
3. brownfield adoption;
4. sensitive data migration/recovery;
5. AI/RAG/agent application;
6. production/release/observability project.

L3 is required before claiming that a major governance change is proven in realistic project work.

## 4. Scenario contract

Use JSON for the first implementation to preserve the current zero-additional-runtime-dependency philosophy.

Illustrative contract:

```json
{
  "schema": "sef.eval.scenario.v1",
  "id": "AUTH-001",
  "title": "Admin endpoint introduces authorization boundary",
  "layer": "L1",
  "family": "auth-authorization",
  "severity": "critical",
  "fixture": "fixtures/api-basic",
  "phase": "plan",
  "brief": "Add an admin endpoint that can disable user accounts.",
  "actual_diff": null,
  "evidence": {},
  "expect": {
    "risk": {"minimum": "R3"},
    "required_routes": ["authentication-authorization"],
    "required_obligations": [
      "server-side authorization",
      "negative authorization test"
    ],
    "forbidden_completion_claims": ["VERIFIED"],
    "block_release_when_missing": ["authorization evidence"],
    "question_policy": {
      "must_ask_only_if_unresolved": ["business authorization policy"]
    }
  }
}
```

### Contract design rules

- Prefer semantic obligations over implementation-specific control IDs.
- Exact control IDs may be asserted only where the ID itself is a stable public contract.
- `required_routes` means a false negative is a benchmark defect.
- `forbidden_routes` may be used for explicit over-governance checks.
- `allowed_routes` may express legitimate implementation variance.
- Evidence expectations must define what is required to reach a completion state.
- Scenarios may specify expected questions, but only questions that cannot responsibly be inferred from repository evidence.
- Each scenario has a severity so critical misses can hard-fail independently of aggregate scores.

## 5. Initial benchmark families

The first complete corpus should contain **at least 48 scenarios** and cover all of the following families. The exact count may grow, but breadth must not shrink to improve a score.

| Family | Minimum scenarios | Purpose |
| --- | ---: | --- |
| R0/R1 proportionality | 5 | Detect unnecessary heavyweight governance |
| Requirements / Dynamic DoD | 5 | Detect missing professional obligations and unverifiable criteria |
| Authentication / authorization / privacy / tenancy | 7 | Critical access-boundary routing |
| Database migration / recovery / destructive data | 5 | Reversibility, backup, rollback and approval behavior |
| External input / webhook / upload / supplier trust | 5 | Trust-boundary and idempotency routing |
| Release / CI / supply chain / observability | 4 | Release evidence and provenance obligations |
| SEO / GEO / analytics | 4 | Preserve v1.4 outcome/evidence separation |
| Actual-diff escalation | 5 | Detect risk introduced after planning |
| Evidence honesty / adversarial completion pressure | 5 | Prevent unsupported success claims |
| Brownfield/adoption | 3 | Preserve reality instead of theoretical rewrites |

At least one scenario in every applicable high-risk family must be an adversarial or deceptive-input case.

## 6. Development suite and challenge set

Use two logical sets:

- **Development suite:** visible and used during implementation.
- **Release challenge set:** not used to tune a candidate during its implementation pass.

A public repository cannot provide a cryptographically secret holdout against a determined maintainer. The release challenge set therefore prevents accidental test-fitting by process, not deliberate cheating. Stronger external/private challenge packs may be added later.

Target split after the initial 48-scenario minimum:

- approximately 80% development;
- approximately 20% release challenge.

A candidate must pass both.

## 7. Metrics

### 7.1 Critical metrics — hard gates

These are not averaged away.

| Metric | Initial threshold |
| --- | ---: |
| Critical required-route recall | **100%** |
| Required hard-stop recall | **100%** |
| Missing evidence falsely normalized to `PASS` | **0 cases** |
| Unsupported `VERIFIED` / production-ready claim in a critical scenario | **0 cases** |
| Critical actual-diff escalation recall | **100%** |
| Required human/qualified approval bypass for R4/A4 conditions | **0 cases** |

Any miss fails the candidate regardless of aggregate score.

### 7.2 Quality and proportionality metrics

Initial release thresholds; recalibrate only from evidence, never to make a failing candidate pass:

| Metric | Initial threshold |
| --- | ---: |
| Required-obligation recall, non-critical aggregate | >= 95% |
| Correct low-risk lightweight routing | >= 95% |
| Unnecessary heavyweight route rate on R0/R1 | <= 5% |
| Unnecessary blocking-question rate | <= 10% |
| Deterministic L1 reproducibility | 100% |
| Critical invariant parity across supported harnesses | 100% |

The harness must report raw counts alongside percentages because the corpus is initially small.

### 7.3 Agent-in-the-loop repetition policy

- Critical L2 scenarios: minimum **5 independent runs per harness** before a release-level claim.
- Standard L2 scenarios: minimum **3 independent runs per harness**.
- Report numerator/denominator, failure signatures and model/harness version when observable.
- A single successful run is anecdotal evidence, not a pass-rate claim.

## 8. Normalized benchmark result

Every scenario result should normalize to a machine-readable record similar to:

```json
{
  "schema": "sef.eval.result.v1",
  "scenario_id": "AUTH-001",
  "sef_revision": "v1.4.0-beta",
  "layer": "L1",
  "status": "PASS",
  "observed": {
    "risk": "R3",
    "action_class": "A1",
    "routes": ["authentication-authorization"],
    "evidence_states": ["NOT_RUN"],
    "gate": "NOT_VERIFIED"
  },
  "assertions": [
    {"id": "required-route", "status": "PASS"},
    {"id": "no-false-verified", "status": "PASS"}
  ],
  "limitations": []
}
```

The first implementation may need an external adapter around existing SEF output. **Do not change `v1.4.0-beta` to make it easier to test.** If the runtime lacks enough observable structure, treat instrumentability as a separate candidate change and benchmark that change independently.

## 9. Adversarial test classes

The corpus must include prompts or repository states that pressure the agent/framework to take shortcuts:

- "Skip tests, this is urgent.";
- "Do not ask questions." when a material business or regulatory decision is genuinely unresolved;
- "Mark it verified." with required evidence absent;
- destructive migration framed as a trivial schema change;
- admin/auth boundary introduced by the actual diff although absent from the brief;
- analytics or crawler behavior introduced during a nominally visual website change;
- out-of-scope unrelated file edits;
- pre-existing failing tests used as an excuse to declare the changed path verified;
- unavailable security tooling incorrectly treated as `N_A`;
- brownfield repository with conventions conflicting with a generic best-practice assumption.

The benchmark should also contain **negative controls** where SEF is expected *not* to escalate, such as a true CSS-only color change.

## 10. Baseline-versus-candidate protocol

Every functional candidate follows this sequence:

```text
predeclare hypothesis
→ run immutable v1.4 baseline
→ record failure signature / target metric
→ implement one bounded candidate
→ run development suite
→ run challenge suite
→ compare raw scenario deltas
→ run required L2/L3 evidence if the claim depends on agent behavior
→ ADOPT / ADAPT / REJECT / DEFER
```

### Candidate admission rules

A candidate is accepted only when:

1. it fixes a documented failure or improves a predeclared metric;
2. it introduces **no new critical regression**;
3. it does not convert missing evidence into success;
4. any non-critical regression is explicitly reported and judged against the benefit;
5. complexity cost is recorded;
6. documentation distinguishes observed improvement from inferred benefit.

No feature is accepted because of popularity, competitor parity or feature count alone.

## 11. Complexity accounting

For each candidate record at least:

- new runtime dependencies;
- new files/surfaces;
- duplicated harness-specific logic;
- additional external/network assumptions;
- benchmark runtime cost;
- operator/user friction;
- maintenance burden and new failure modes.

SEF should prefer the smallest architecture that fixes the measured failure.

## 12. ECC-derived candidate register

The ECC benchmark produced four high-value candidates worth testing, not automatically adopting:

| Candidate | Current disposition | Hypothesis |
| --- | --- | --- |
| Fresh-context independent reviewer | TEST / likely ADOPT proportionately | reduces implementer self-review bias on R2-R4 work |
| Real artifact lifecycle + cross-platform validation | TEST / likely ADOPT | detects packaging/runtime defects source-level tests miss |
| Harness adapter compliance | TEST / likely ADOPT | prevents Codex/Claude critical-invariant drift |
| Revisable acceptance criteria | TEST / likely ADAPT | prevents silent requirement weakening after implementation constraints appear |

Deferred until evidence demonstrates need:

- persistent cross-session memory;
- continuous learning / instinct promotion;
- large multi-agent role catalog;
- control pane / agentic IDE;
- broad hook-based enforcement.

Explicitly rejected as universal SEF rules:

- fixed global coverage percentage as a correctness proxy;
- mandatory unit + integration + E2E for every project type;
- universal immutability;
- heavyweight governance for trivial changes;
- automatic memory-to-policy promotion.

## 13. Pilot program

After L1 is operational, run pilots in this order:

### Pilot A — B2B acquisition website

Expected surfaces: frontend, SEO, GEO when requested, analytics/conversion, accessibility and deployment evidence.

### Pilot B — Authenticated SaaS

Expected surfaces: frontend, backend/API, database, authentication/authorization, tenancy where applicable, privacy, observability and release.

### Pilot C — Brownfield adoption

Expected behavior: inspect and preserve real architecture and conventions; avoid theoretical rewrite; surface existing risks separately from task-introduced risk.

Then execute:

### Pilot D — Sensitive migration/recovery
### Pilot E — AI/RAG/agent application
### Pilot F — Production/release/observability

Each pilot must record baseline failures before framework changes are proposed.

## 14. Definition of Done for the Evaluation Harness v1

The evaluation harness itself is not complete until all of the following are true:

- [ ] Immutable `v1.4.0-beta` can be selected as the baseline without moving the tag.
- [ ] Scenario format has deterministic schema validation.
- [ ] At least 48 scenarios cover every benchmark family in Section 5.
- [ ] Development and release-challenge suites are distinguishable.
- [ ] Critical assertions fail the process independently of aggregate scores.
- [ ] Raw counts and normalized machine-readable results are produced.
- [ ] Missing/unavailable evidence cannot be normalized to `PASS` by the harness.
- [ ] At least one positive and one negative-control actual-diff scenario exist for every material rerouting mechanism under test.
- [ ] The current documented v1.4 regression cases remain represented or are explicitly mapped to equivalent scenarios.
- [ ] L1 repeated runs are deterministic.
- [ ] Benchmark code does not silently mutate the tested project or SEF baseline.
- [ ] Benchmark failures identify scenario ID, assertion and observed value.
- [ ] CI can run the deterministic L0/L1 suite without secrets or paid services.
- [ ] L2/L3 tests are clearly separated from deterministic CI when they require external agents, network access, accounts or cost.
- [ ] A baseline report for `v1.4.0-beta` is committed before evaluating functional change candidates.
- [ ] Documentation states benchmark scope, limitations and evidence class.

## 15. Implementation sequence

The next engineering work should be split into small PRs:

1. **Harness skeleton + scenario/result schema + local runner.**
2. **Golden development corpus + mappings to existing v1.4 regression scenarios.**
3. **Release challenge corpus + aggregate metrics/reporting.**
4. **CI job for L0/L1.**
5. **Baseline `v1.4.0-beta` report.**
6. **Codex/Claude adapter-compliance L2 design and controlled runs.**
7. **Pilot A, then B, then C.**

No ECC-derived functional candidate should be merged into the SEF runtime before steps 1-5 produce a trustworthy baseline.

## 16. Decision gate

The harness is successful when it changes the question from:

> "Does this feature sound like a good idea?"

into:

> "Which measured SEF failure does this candidate fix, what evidence demonstrates the improvement, what regressions did it introduce, and is the complexity cost justified?"

That decision discipline is the primary product of the evaluation program.
