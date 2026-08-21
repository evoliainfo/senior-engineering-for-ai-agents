# Senior Engineering for AI Coding Agents

**Governed engineering workflows for Codex and Claude Code, from project discovery to production.**

> You describe the product. Your coding agent writes the code. SEF governs the engineering.

**Current beta:** `v1.4.0-beta`  
**Runtime:** [`sef.py`](sef.py)  
**Integrity:** [`SHA256SUMS`](SHA256SUMS)

SEF (Senior Engineering Framework) is a Project Engineering OS for AI coding agents. It is designed for people who want to build serious software with Codex or Claude Code without having to know every senior-engineering requirement in advance.

SEF does **not** claim to make an AI model infallible or literally replace a senior engineer. It gives the agent a structured engineering operating system: project framing, inferred professional requirements, risk classification, specialist governance, task-scoped execution playbooks, dynamic Definition of Done, verification evidence and release gates.

## Quick start

1. Download [`sef.py`](sef.py) and put it at the root of your project.
2. Open the project in **Codex** or **Claude Code**.
3. Describe the software, website or change you want to build.

Example:

> Use `sef.py` to initialize or adopt this project with SEF. Here is what I want to build: **[describe the product]**. Operate SEF yourself. Do not start material implementation until the project is sufficiently framed. Ask me only for product, business, data, criticality, regulatory, or approval decisions that you cannot responsibly infer.

That's the normal user workflow. You do **not** need to learn the SEF CLI.

## How SEF works

```text
USER / PRODUCT INTENT
        ↓
PROJECT DISCOVERY + ENGINEERING BASELINE
        ↓
INFERRED PROFESSIONAL REQUIREMENTS
        ↓
PLAN + RISK + DYNAMIC DEFINITION OF DONE
        ↓
TASK-SCOPED EXECUTION PLAYBOOKS
        ↓
IMPLEMENTATION
        ↓
ACTUAL-DIFF REASSESSMENT
        ↓
VERIFICATION + EVIDENCE
        ↓
VERIFIED | VERIFIED_WITH_RESIDUAL_RISK | NOT_VERIFIED | BLOCKED
        ↓
RELEASE READINESS
```

For an existing repository, SEF uses an adoption workflow: it inspects the actual architecture and codebase, preserves existing work, and builds the engineering baseline around reality rather than replacing the project with a theoretical design.

## Eight execution playbooks

SEF v1.4 includes eight task-scoped execution playbooks for the implementation HOW:

1. **Frontend Application Engineering**
2. **Backend / API Service Engineering**
3. **Database Design & Query Engineering**
4. **Application Architecture & Integration**
5. **Reliability & Observability Engineering**
6. **SEO & Web Discoverability Engineering**
7. **GEO / AI Discoverability Engineering**
8. **Analytics & Conversion Instrumentation**

The three v1.4 web-growth playbooks make SEF better suited to public websites and acquisition-oriented web projects without turning every website edit into a heavyweight audit.

### SEO & Web Discoverability

Covers crawlability, indexation policy, robots directives, canonicals, sitemap integrity, metadata, structured data, rendering, URL architecture, internal linking, redirects/migrations, performance evidence and post-deploy verification.

SEF explicitly distinguishes **technical SEO readiness** from **indexation** and **observed ranking/traffic**. Technical correctness is not reported as proof of search success.

### GEO / AI Discoverability

Covers AI-search and answer-engine discoverability with an evidence-first approach: provider crawler access, CDN/WAF behavior, citation-ready and extractable content, entity consistency, source quality, provider-specific evidence, referrals and conversion measurement.

SEF does not promise placement or citations in generative answers. Provider-specific guidance must be re-checked against current primary documentation at execution time.

### Analytics & Conversion Instrumentation

Treats analytics as a measurement system rather than "a tag was installed": measurement plans, event contracts, conversion semantics, client/server instrumentation boundaries, deduplication, campaign/UTM hygiene, privacy/consent escalation, ingestion verification, reporting and critical-funnel regression protection.

A tag firing is not accepted as evidence that a correct business conversion was ingested.

## Proportional routing

The new capabilities are **execution playbooks, not new specialist governance packs**. The governance catalog remains stable.

Examples:

```text
"Create a public company website"
  → Frontend + SEO/Web Discoverability

"Create a website to generate leads"
  → Frontend + SEO/Web Discoverability + Analytics/Conversion

"Optimize for ChatGPT Search / GEO"
  → SEO/Web Discoverability + GEO/AI Discoverability

"Change only the button color on the website"
  → lightweight frontend path (R0)
  → no unnecessary SEO/GEO/analytics playbooks
```

SEF also reassesses the **actual Git diff**. If implementation introduces crawler policy, canonical behavior, analytics instrumentation or another material domain not present in the saved task plan, verification surfaces the newly required procedure and requires another review/verification cycle before a supported completion claim.

## Governance baseline

Current v1.4 baseline:

- **212** Core engineering controls
- **326** specialist controls
- **17** specialist governance packs
- **538** atomic controls represented
- **8** execution playbooks
- historical policy regression suite: **30/30 PASS**

The 17 specialist packs cover authentication/authorization, database migration/recovery, CI and software supply chain, containers, IaC/network, multi-tenancy, webhooks/external input, AI/agentic systems, privacy, performance/cost, accessibility/compatibility, external suppliers, maintenance/vulnerability lifecycle, release/progressive delivery, file uploads, time semantics and regulated-domain escalation.

## Codex and Claude Code

SEF installs and preserves the native project instruction surfaces used by both agents:

```text
AGENTS.md   → Codex adapter
CLAUDE.md   → Claude Code adapter
```

Both adapters use the same underlying SEF lifecycle and policy. Existing user instructions in those files are preserved during installation and upgrade.

## Python bootstrap

The beta runtime is Python-based. The agent first checks for an existing compatible Python 3 interpreter (`python3`, `python`, or Windows `py -3`). If Python is missing, the agent must **not silently modify the host machine**. It should explain the required installation and use a trusted OS/package manager or official Python distribution through the normal sandbox, network and approval model of the coding agent.

The bootstrap rule is written directly at the top of `sef.py`, so an agent can read it before Python is available.

## Evidence model

SEF separates states that are often incorrectly collapsed into "done":

`PASS`, `FAIL`, `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE`, `FLAKY`, `N_A`, `WAIVED`, and `BLOCKED`.

Examples:

```text
SEO implementation ≠ indexation ≠ ranking outcome
AI crawl readiness ≠ AI citation / placement
analytics tag present ≠ event ingestion ≠ valid conversion
lab performance ≠ real-user field performance
plan scope ≠ actual diff scope
```

## What SEF does not do

SEF is not:

- a guarantee that an AI model never makes mistakes;
- a replacement for CI, protected branches, sandbox permissions or qualified human approval;
- a claim of legal or regulatory compliance by itself;
- a guarantee of search rankings, AI citations, traffic or causal attribution;
- a reason to ignore official framework, database, cloud, search or analytics documentation;
- a giant universal checklist applied to every code change.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Capabilities](docs/CAPABILITIES.md)
- [Validation](docs/VALIDATION.md)
- [Security model](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [v1.4.0-beta release notes](RELEASES/v1.4.0-beta.md)
- [Contributing / beta feedback](CONTRIBUTING.md)

## Status

**Public beta.** v1.4.0-beta is intended for controlled real-project testing with Codex and Claude Code.

Feedback and reproducible failure cases are especially valuable: wrong risk classification, missing requirements, unnecessary friction, missing playbooks, false-positive routing, false-negative routing, or ways an agent can incorrectly claim completion.

## License

No open-source license has been granted yet. A licensing decision will be made separately from the technical beta. Please do not assume MIT/Apache-style reuse rights merely because the repository is public.
