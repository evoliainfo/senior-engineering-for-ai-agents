# Changelog

All notable beta changes to SEF are recorded here.

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

### Routing improvements

- task-scoped frontend/backend/database execution routing;
- cross-layer integration guidance for full-stack work;
- lightweight R0 behavior retained for pure visual changes;
- database-design language no longer incorrectly routes to AI-system guidance;
- migration tasks combine data-design and migration/recovery procedures.

### Validation

- targeted full-stack suite: **13/13 PASS**;
- historical policy regression: **30/30 PASS**.

## v1.1 — Agent-operated UX

### Added

- `codex-start` one-command bootstrap;
- automatic `INIT` vs `ADOPT` detection;
- `session` project-state handoff;
- durable discovery/authoritative-context confirmation;
- explicit implementation blocking while material project facts remain unresolved;
- preservation of existing project work/instructions during adoption and upgrade.

The key UX change was moving SEF operation from the end user to the coding agent.

## v1.0 — Project Engineering OS

SEF moved from a task/diff-centric policy checker to a project-lifecycle engineering system:

- project intake;
- Project Engineering Baseline;
- requirements and inferred professional requirements;
- architecture and engineering strategy;
- dynamic task planning / DoD;
- implementation verification;
- release readiness;
- maintenance lifecycle.

## Earlier prototypes

Earlier 0.x versions developed and normalized the Core control matrix, specialist packs, risk/action model, evidence model, red-team scenarios and compact distribution approach. They are development history, not recommended public releases.
