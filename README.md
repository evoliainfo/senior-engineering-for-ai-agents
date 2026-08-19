# Senior Engineering for AI Coding Agents

**Governed full-stack engineering workflows for Codex and Claude Code, from project discovery to production.**

> You describe the software. Your coding agent writes the code. SEF governs the engineering.

**Current beta:** `v1.3.0-beta`  
**Runtime:** [`sef.py`](sef.py)  
**Integrity:** [`SHA256SUMS`](SHA256SUMS)

SEF (Senior Engineering Framework) is a project engineering layer for AI coding agents. It is designed for people who want to build serious software with Codex or Claude Code without having to know every senior-engineering requirement in advance.

SEF does **not** claim to make an AI model infallible or to turn it literally into a human senior engineer. It gives the agent a structured engineering operating system: project framing, inferred professional requirements, risk classification, specialist playbooks, dynamic Definition of Done, verification evidence, and release gates.

## Quick start

1. Download [`sef.py`](sef.py) and put it at the root of your project.
2. Open the project in **Codex** or **Claude Code**.
3. Describe the software you want to build.

Example:

> Use `sef.py` to initialize or adopt this project with SEF. Here is what I want to build: **[describe the product]**. Operate SEF yourself. Do not start material implementation until the project is sufficiently framed. Ask me only for product, business, data, criticality, regulatory, or approval decisions that you cannot responsibly infer.

That's the normal user workflow. You do **not** need to learn the SEF CLI.

## What happens first

For a new project, SEF starts with project discovery rather than immediately generating code:

```text
PRODUCT DESCRIPTION
        ↓
PROJECT DISCOVERY
        ↓
EXPLICIT REQUIREMENTS
+ INFERRED PROFESSIONAL REQUIREMENTS
        ↓
AUTHORITATIVE USER DECISIONS
        ↓
PROJECT ENGINEERING BASELINE
        ↓
ARCHITECTURE / DATA / SECURITY / QUALITY STRATEGY
        ↓
PROJECT DEFINITION OF DONE
        ↓
IMPLEMENTATION
```

For an existing repository, SEF uses **ADOPT** mode: it inspects the current architecture and codebase, preserves existing work, compares the implementation with the intended product, and builds the engineering baseline around reality instead of replacing the project with a theoretical architecture.

## The operating loop

Once the initial project framing is sufficient, the user can talk to the coding agent normally:

> Add the customer portal.

> Fix the booking concurrency bug.

> Add Google OAuth.

> Prepare this version for production.

The agent then operates the SEF lifecycle itself:

```text
USER INTENT
    ↓
SESSION / PROJECT BASELINE
    ↓
PLAN + RISK + DYNAMIC DOD
    ↓
TASK-GUIDANCE
    ↓
IMPLEMENTATION
    ↓
ACTUAL-DIFF REASSESSMENT
    ↓
VERIFY / EVIDENCE
    ↓
VERIFIED | NOT_VERIFIED | BLOCKED
    ↓
RELEASE GATE
```

## Full-stack engineering coverage

SEF v1.3 includes five execution playbooks for the implementation HOW:

- **Frontend Application Engineering**
- **Backend / API Service Engineering**
- **Database Design & Query Engineering**
- **Full-Stack Architecture & Integration**
- **Reliability & Observability Engineering**

These complement **17 specialist governance packs** covering authentication/authorization, database migration/recovery, CI and software supply chain, containers, IaC/network, multi-tenancy, webhooks, AI/agentic systems, privacy, performance/cost, accessibility/compatibility, external suppliers, maintenance/vulnerability lifecycle, release/progressive delivery, file uploads, time semantics, and regulated-domain escalation.

## Governance baseline

Current v1.3 baseline:

- **212** Core engineering controls
- **326** specialist controls
- **17** specialist packs
- **538** atomic controls represented
- **5** full-stack execution playbooks
- historical policy regression suite: **30/30 PASS**

The framework applies controls proportionately. A CSS color change should stay lightweight; authentication, tenant isolation, destructive database changes, production infrastructure, or irreversible operations receive deeper controls and evidence requirements.

## Codex and Claude Code

SEF installs and preserves the native project instruction surfaces used by both agents:

```text
AGENTS.md   → Codex adapter
CLAUDE.md   → Claude Code adapter
```

Both adapters enforce the same SEF lifecycle. Existing user instructions in those files are preserved.

## Python bootstrap

The current beta runtime is Python-based.

The agent first checks for an existing compatible Python 3 interpreter (`python3`, `python`, or Windows `py -3`). If Python is missing, the agent must **not silently modify the host machine**. It should explain the required installation and use a trusted OS/package-manager or official Python distribution only through the normal sandbox, network and approval model of the coding agent.

The bootstrap rule is written directly at the top of `sef.py`, so an agent can read it before Python is available.

## What SEF does not do

SEF is not:

- a guarantee that an AI model never makes mistakes;
- a replacement for CI, protected branches, sandbox permissions or qualified human approval;
- a claim of legal/regulatory compliance by itself;
- a reason to ignore official framework, database or cloud documentation;
- a giant universal checklist applied to every code change.

The evidence model distinguishes `PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N/A`, `WAIVED`, and `BLOCKED` so that "the agent says it is done" is not treated as objective verification.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Capabilities](docs/CAPABILITIES.md)
- [Validation](docs/VALIDATION.md)
- [Security model](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Status

**Public beta.** The current release is intended for controlled real-project testing with Codex and Claude Code.

Feedback and reproducible failure cases are especially valuable: wrong risk classification, missing requirements, unnecessary friction, missing playbooks, false-positive routing, false-negative routing, or ways an agent can incorrectly claim completion.

## License

No open-source license has been granted yet. A licensing decision will be made separately from the technical beta. Please do not assume MIT/Apache-style reuse rights merely because the repository is public.
