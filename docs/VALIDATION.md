# Validation

SEF is developed with a regression-oriented validation model. The goal is not to prove that an AI coding agent can never fail; the goal is to verify that SEF routes representative engineering situations to the intended risk, controls, procedures and gates, and that its own lifecycle cannot silently convert missing evidence into success.

## Current beta baseline

SEF v1.3 retains the validated policy baseline:

- **212 Core controls**
- **326 specialist controls**
- **17 specialist packs**
- **538 atomic controls represented**
- **30/30 historical policy regression scenarios PASS**
- **5 full-stack execution playbooks**

## v1.2 full-stack execution validation

Targeted scenarios verified that task routing distinguishes the implementation domain rather than loading every playbook merely because a repository contains multiple technologies.

Representative cases:

- frontend-only task → frontend playbook
- backend/API-only task → backend/API playbook
- database-design task → database playbook
- explicit cross-layer feature → frontend + backend + database + integration guidance
- CSS-only visual change → remains lightweight / R0
- OAuth change → backend execution + authentication/privacy governance
- database migration → database design + migration/recovery guidance
- production API work → backend + reliability + release engineering
- `task-guidance` loads actual embedded HOW content rather than only procedure names

Targeted v1.2 full-stack validation: **13/13 PASS**.

## v1.3 multi-agent validation

v1.3 adds the generic agent bootstrap and Claude Code adapter while preserving Codex support.

Validated scenarios include:

- pre-Python bootstrap protocol readable from the source file
- generic `agent-start`
- Codex adapter declared and preserved
- Claude Code adapter declared and preserved
- existing `AGENTS.md` instructions preserved
- existing `CLAUDE.md` instructions preserved
- installation manifest records both adapters
- `doctor` validates installed project artifacts
- full-stack guidance remains available after multi-agent changes
- `codex-start` remains backward-compatible
- v1.2 → v1.3 upgrade preserves baseline and user instructions
- adapter instructions prohibit silent system-runtime installation and permission bypass

Targeted v1.3 validation: **12/12 PASS**.

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

For this reason, SEF does not collapse these outcomes into a single boolean:

- `PASS`
- `FAIL`
- `NOT_RUN`
- `UNAVAILABLE`
- `INCONCLUSIVE`
- `FLAKY`
- `N_A`
- `WAIVED`
- `BLOCKED`

## Hard-stop examples

Representative conditions that must not be reported as production-ready include:

- required critical test/build/security failure
- authentication/authorization bypass
- exposed secret
- uncontrolled destructive migration
- unresolved material data-loss risk
- critical requirement not verified
- known regression
- unexplained out-of-scope changes
- absent required recovery/rollback evidence
- tenant-isolation violation or unverified high-risk path
- release artifact/revision not tied to verified source
- missing independent/human approval where required
- hard gate skipped, unavailable or silently treated as N/A

## What these results mean

The current results mean that **SEF's own routing and lifecycle passed the documented regression scenarios**. They do not mean that every future application built with an AI agent is automatically secure, correct, scalable, compliant or production-ready.

Real-project pilots, CI evidence, deployment evidence and adversarial testing remain necessary.
