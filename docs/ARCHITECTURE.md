# Architecture

SEF is an agent-operated Project Engineering OS. The coding agent remains responsible for understanding and editing the actual project; SEF provides engineering governance, task-scoped execution playbooks, an evidence model and release gates around that work.

## High-level model

```text
USER / PRODUCT INTENT
        ↓
CODING AGENT
(Codex or Claude Code)
        ↓
SEF PROJECT ENGINEERING OS
        ↓
┌────────────────────────────────────────────┐
│ Project Engineering Baseline               │
│ Risk & action classification               │
│ Core + specialist policy routing           │
│ Task-scoped execution playbooks            │
│ Dynamic Definition of Done                 │
│ Verification & evidence                    │
│ Release readiness gate                     │
└────────────────────────────────────────────┘
        ↓
ACTUAL REPOSITORY / CI / RUNTIME / WEB
```

## Project lifecycle

```text
PROJECT INTAKE
→ ENGINEERING BASELINE
→ TASK PLAN / DYNAMIC DOD
→ IMPLEMENTATION
→ ACTUAL-DIFF RECLASSIFICATION
→ VERIFICATION / EVIDENCE
→ RELEASE READINESS
→ DEPLOYMENT THROUGH THE PROJECT'S NORMAL TOOLING
→ POST-DEPLOY VERIFICATION
→ OBSERVE / MAINTAIN / RECOVER / LEARN
```

SEF's `release` command is a readiness gate. It does not itself mean that production has been deployed.

## Core policy model

### Risk

- `R0` trivial
- `R1` standard
- `R2` significant
- `R3` critical/high-risk
- `R4` mission-critical or irreversible

Risk considers data sensitivity, privilege, blast radius, reversibility, side effects, availability, architectural impact and uncertainty.

### Action class

- `A0` read-only
- `A1` reversible local write
- `A2` external but reversible side effect
- `A3` privileged/destructive/shared-resource action
- `A4` production/irreversible/high-impact action

Change risk and action class are independent axes.

### Evidence states

SEF distinguishes `PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N_A`, `WAIVED`, and `BLOCKED`. Missing evidence is not converted into success.

## Evidence chain

```text
Requirement
→ Risk
→ Control
→ Procedure
→ Verification
→ Evidence
→ Gate
→ DONE
```

## Governance vs execution

SEF intentionally separates two layers:

- **17 specialist governance packs** decide what controls, risks and evidence obligations apply.
- **8 execution playbooks** tell the coding agent how to perform task-scoped engineering work.

v1.4 adds SEO/Web Discoverability, GEO/AI Discoverability and Analytics/Conversion as execution playbooks. It does not inflate the canonical governance catalog, which remains 538 controls.

## Web discoverability and measurement routing

The new playbooks are selected proportionately from product intent, task language and actual Git diff.

```text
public website
→ frontend + SEO/web discoverability

lead-generation website
→ frontend + SEO/web discoverability + analytics/conversion

GEO / ChatGPT Search task
→ SEO/web discoverability + GEO/AI discoverability

CSS color-only change
→ lightweight frontend path
```

The actual diff is reassessed after implementation. New canonical, crawler-policy, structured-data or analytics behavior can introduce new required procedures even when absent from the original request.

## Project instruction adapters

SEF v1.4 supports:

- `AGENTS.md` for Codex
- `CLAUDE.md` for Claude Code

Existing user instructions are preserved. Both adapters point to the same underlying SEF lifecycle and policy.

## Embedded distribution

The beta is distributed as a compact `sef.py`. Internal policies, specialist packs and execution playbooks are embedded in the runtime so the end user does not receive dozens of framework files.

The public repository documents the internal architecture; compact distribution is not a trust-by-obscurity mechanism.

## Stack and provider boundary

SEF is deliberately stack-agnostic and, for web discovery/measurement, provider-aware without pretending provider behavior is stable. Framework, database, cloud, search-engine, AI-search and analytics-provider specifics must be checked against current primary documentation when executed.

SEF does not treat technical SEO readiness as proof of indexation/ranking, AI crawl readiness as proof of citation, or an analytics tag firing as proof of a valid conversion.
