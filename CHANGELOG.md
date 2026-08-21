# Changelog

All notable beta changes to SEF are recorded here.

## v1.4 — Web discoverability & measurement engineering

### Added

Three task-scoped execution playbooks:

- SEO & Web Discoverability Engineering
- GEO / AI Discoverability Engineering
- Analytics & Conversion Instrumentation

### Routing and evidence improvements

- public website and lead-generation work can automatically receive SEO/analytics execution guidance;
- explicit GEO/AEO/ChatGPT Search work receives SEO + GEO guidance without being misclassified as an AI/LLM application;
- pure visual website edits remain lightweight and do not trigger unnecessary web-growth procedures;
- actual-diff reassessment can detect canonical, crawler-policy or analytics changes introduced during implementation and require another verification cycle;
- SEO readiness, indexation and ranking outcomes are distinct evidence states;
- AI crawl readiness, observed AI visibility and referrals are distinct evidence states;
- analytics implementation, transport, ingestion, conversion semantics and reporting are verified separately.

### Retained

- 212 Core + 326 specialist = **538 controls**;
- **17 specialist governance packs**;
- multi-agent Codex + Claude Code adapters;
- project discovery / baseline / dynamic DoD;
- verification/evidence states and release-readiness gate.

### Validation

- historical policy regression: **30/30 PASS**;
- web/GEO/analytics routing red-team: **18/18 PASS**;
- project-first + actual-diff integration: **9/9 PASS**;
- v1.3 → v1.4 preservation: **11/11 PASS**;
- specialist-pack validator: **17 packs / 326 controls PASS**.

## v1.3 — Multi-agent bootstrap

### Added

- generic `agent-start` entry point;
- Codex project adapter via `AGENTS.md`;
- Claude Code project adapter via `CLAUDE.md`;
- preservation of existing instructions in both files;
- pre-Python bootstrap protocol readable directly from `sef.py`;
- explicit rule against silent host-level Python installation or permission bypass;
- generic multi-agent handoff while keeping `codex-start` as a compatibility alias.

### Retained

- 538 atomic controls represented;
- 17 specialist governance packs;
- 5 full-stack execution playbooks;
- project discovery / baseline / dynamic DoD;
- actual-diff risk reassessment;
- verification/evidence states;
- release-readiness gate.

### Validation

- targeted v1.3 multi-agent/bootstrap suite: **12/12 PASS**;
- historical policy regression: **30/30 PASS**.

## v1.2 — Full-stack execution

### Added

Five implementation playbooks:

- Frontend Application Engineering
- Backend / API Service Engineering
- Database Design & Query Engineering
- Full-Stack Architecture & Integration
- Reliability & Observability Engineering

`task-guidance` was added to load the actual selected HOW procedures after planning, rather than relying only on procedure names.

### Validation

- targeted full-stack suite: **13/13 PASS**;
- historical policy regression: **30/30 PASS**.

## v1.1 — Agent-operated UX

Added `codex-start`, automatic INIT vs ADOPT detection, session handoff, durable discovery/authoritative-context confirmation, implementation blocking while material facts remain unresolved, and preservation of existing project work/instructions during adoption and upgrade.

## v1.0 — Project Engineering OS

SEF moved from a task/diff-centric policy checker to a project-lifecycle engineering system covering intake, baseline, requirements, architecture, dynamic task planning/DoD, verification, release readiness and maintenance.

## Earlier prototypes

Earlier 0.x versions developed and normalized the Core control matrix, specialist packs, risk/action model, evidence model, red-team scenarios and compact distribution approach. They are development history, not recommended public releases.
