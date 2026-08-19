# Architecture

SEF is an agent-operated Project Engineering OS. The coding agent remains responsible for understanding and editing the actual application code; SEF provides the engineering governance, execution playbooks, evidence model and release gates around that work.

## High-level model

```text
USER / PRODUCT INTENT
        ↓
CODING AGENT
(Codex or Claude Code)
        ↓
SEF PROJECT ENGINEERING OS
        ↓
┌─────────────────────────────────────────┐
│ Project Engineering Baseline            │
│ Risk & action classification            │
│ Core + specialist policy routing        │
│ Full-stack execution playbooks          │
│ Dynamic Definition of Done              │
│ Verification & evidence                 │
│ Release readiness gate                  │
└─────────────────────────────────────────┘
        ↓
ACTUAL REPOSITORY / CI / RUNTIME
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

SEF separates several concepts that are often incorrectly collapsed into a single "done" signal.

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

SEF distinguishes:

`PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N_A`, `WAIVED`, and `BLOCKED`.

A missing test is not equivalent to a passing test.

## Evidence chain

```text
Requirement
→ Risk
→ Control
→ Verification
→ Evidence
→ Gate
→ DONE
```

This is intended to prevent an agent from treating compilation, a green unit test, or its own assertion as sufficient proof for every class of change.

## Project instruction adapters

SEF v1.3 supports:

- `AGENTS.md` for Codex
- `CLAUDE.md` for Claude Code

Existing user instructions are preserved. Both adapters point to the same underlying SEF lifecycle and policy.

## Embedded distribution

The beta is distributed as a compact `sef.py`. Internal policies, specialist packs and execution playbooks are embedded in the runtime so the end user does not receive dozens of framework files.

The public repository documents the internal architecture so the compact distribution is not intended to be a trust-by-obscurity mechanism.

## Stack-specific engineering

SEF is deliberately stack-agnostic. It detects project context and routes general engineering procedures, but framework-specific behavior must come from the actual repository and current authoritative documentation for the selected framework, database, runtime or cloud platform.

The framework should never pretend that React, Django, PostgreSQL, DynamoDB, .NET, Terraform and Kubernetes share identical implementation mechanics.
