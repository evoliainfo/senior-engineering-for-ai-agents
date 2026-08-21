# Validation

SEF is developed with a regression-oriented validation model. These tests do not prove that an AI coding agent or every application built with SEF can never fail. They verify that SEF routes representative engineering situations to the intended risks, controls, procedures and gates, and that missing evidence is not silently converted into success.

## v1.4 beta baseline

- **212 Core controls**
- **326 specialist controls**
- **17 specialist governance packs**
- **538 atomic controls represented**
- **8 execution playbooks**
- historical policy regression: **30/30 PASS**

## v1.4 web discoverability & measurement validation

v1.4 adds three task-scoped execution playbooks while keeping the canonical governance catalog unchanged:

- SEO & Web Discoverability Engineering
- GEO / AI Discoverability Engineering
- Analytics & Conversion Instrumentation

Local candidate validation before publication produced:

| Suite | Result |
|---|---:|
| Python syntax / runtime compilation | PASS |
| Embedded policy self-test | PASS |
| Historical policy regression | 30/30 PASS |
| Specialist-pack validator | 17 packs / 326 specialist controls PASS |
| Web/GEO/analytics routing red-team | 18/18 PASS |
| Project-first + actual-diff integration | 9/9 PASS |
| v1.3 → v1.4 preservation | 11/11 PASS |
| Three new playbooks embedded | PASS |
| Eight execution playbooks present | PASS |

Representative routing assertions:

- public lead-generation site → Frontend + SEO + Analytics;
- explicit GEO/AEO/ChatGPT Search → SEO + GEO/AI Discoverability;
- GEO does not masquerade as an AI/LLM application;
- pure CSS/color website edit remains lightweight;
- an actual diff introducing canonical or analytics behavior can surface newly required procedures and force another verification cycle.

## Evidence separation added in v1.4

```text
SEO implementation ≠ indexation ≠ ranking outcome
AI crawl readiness ≠ AI citation / placement
analytics implementation ≠ transport ≠ ingestion ≠ valid conversion
```

Provider-specific behavior is time-sensitive, so the execution playbooks require current primary documentation to be re-checked when provider-specific decisions are made.

## Verification philosophy

A policy or prompt being present is not enough. SEF separates:

```text
documented
≠ automated
≠ enforced
≠ executed
≠ independently evidenced
≠ production-proven
```

Evidence/control states include `PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N_A`, `WAIVED`, and `BLOCKED`.

## Hard-stop examples

Representative conditions that must not be reported as production-ready include:

- required critical test/build/security failure;
- authentication/authorization bypass;
- exposed secret;
- uncontrolled destructive migration;
- unresolved material data-loss risk;
- critical requirement not verified;
- known regression;
- unexplained out-of-scope changes;
- absent required recovery/rollback evidence;
- tenant-isolation violation or unverified high-risk path;
- release artifact/revision not tied to verified source;
- missing independent/human approval where required;
- hard gate skipped, unavailable or silently treated as N/A.

## What the results mean

The validation results mean **SEF's own candidate routing and lifecycle passed the documented regression scenarios**. They do not mean every future application is automatically secure, correct, scalable, compliant, highly ranked, cited by AI systems or accurately attributed.

Real-project pilots, CI evidence, deployment evidence and adversarial testing remain necessary.
