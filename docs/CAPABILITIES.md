# Capabilities

SEF v1.4 combines a general engineering control layer with specialist governance packs and task-scoped execution playbooks selected according to project context, task scope and risk.

## Engineering coverage

| Domain | Coverage | Mechanism |
|---|---|---|
| Product discovery / requirements | Strong | Project Engineering Baseline + requirements/risk planning |
| Architecture / boundaries | Strong | Core architecture controls + architecture/integration playbook |
| Frontend application engineering | Strong | Frontend playbook + accessibility/compatibility governance |
| Backend / HTTP API | Strong | Backend/API playbook + auth/security/webhook governance |
| Database design / SQL / ORM | Strong | Database design/query playbook + Core data controls |
| Database migration / backfill / recovery | Strong | Database Migration & Recovery specialist pack |
| Authentication / authorization | Strong | Dedicated specialist controls + backend integration |
| Multi-tenancy | Strong | Multi-Tenant Isolation pack |
| Testing / integration / E2E / negative cases | Strong | Test verification strategy + dynamic DoD |
| Performance / capacity / cost | Strong | Specialist pack + execution playbooks |
| Accessibility / compatibility | Strong | Accessibility/Compatibility pack + frontend playbook |
| Docker / containers | Strong | Docker/Container Engineering pack |
| CI / software supply chain | Strong | CI/Software Supply Chain pack |
| Infrastructure as code / network | Strong | IaC/Network pack |
| Observability / runtime reliability | Strong | Reliability/Observability playbook + Core operational controls |
| Release / rollback / progressive delivery | Strong | Release/Progressive Delivery pack |
| Maintenance / vulnerabilities / EOL | Strong | Maintenance/Vulnerability Lifecycle pack |
| Privacy / PII | Strong with applicability gate | Privacy/Data Protection pack |
| AI / agentic systems | Strong | AI/Agentic Systems pack |
| Technical SEO / web discoverability | Task-scoped playbook | SEO & Web Discoverability Engineering |
| GEO / AI-search discoverability | Task-scoped, provider evidence required | GEO / AI Discoverability Engineering |
| Analytics / conversion measurement | Task-scoped, ingestion evidence required | Analytics & Conversion Instrumentation |
| Regulated domains | Escalation, not simulated compliance | Qualified domain-specific review required |

## Eight execution playbooks

1. **Frontend Application Engineering**
2. **Backend / API Service Engineering**
3. **Database Design & Query Engineering**
4. **Application Architecture & Integration**
5. **Reliability & Observability Engineering**
6. **SEO & Web Discoverability Engineering**
7. **GEO / AI Discoverability Engineering**
8. **Analytics & Conversion Instrumentation**

### SEO & Web Discoverability Engineering

Covers search outcome framing, indexability contracts, crawl/URL architecture, canonicalization, metadata, structured data, rendering/JavaScript, performance evidence, content/search architecture, migrations and post-deploy verification.

It explicitly distinguishes `TECHNICALLY_DISCOVERABLE`, `INDEXATION_NOT_YET_PROVEN`, observed indexation/search performance and outcomes that cannot be guaranteed.

### GEO / AI Discoverability Engineering

Builds on ordinary web/search fundamentals and covers AI-search crawler policy, infrastructure access, citation-ready content, entity/factual consistency, provider-specific controls and observable AI-search/referral evidence.

It separates search-discovery crawlers from model-training crawlers where providers expose that distinction and treats emerging conventions such as `llms.txt` as experimental unless current provider documentation says otherwise.

### Analytics & Conversion Instrumentation

Covers measurement plans, event/data contracts, conversion semantics, client/server instrumentation, deduplication, campaign/attribution hygiene, privacy escalation and a verification ladder from implementation through transport, provider ingestion, conversion correctness and reporting.

## Specialist governance packs

SEF v1.4 retains 17 specialist routes:

1. Authentication / Authorization
2. Database Migration & Recovery
3. CI / Software Supply Chain
4. Docker / Containers
5. Infrastructure as Code / Network
6. Multi-Tenant Isolation
7. Webhook / External Input Trust
8. AI / Agentic Systems
9. Privacy / Data Protection
10. Performance / Capacity / Cost
11. Accessibility / Compatibility
12. External Supplier / SaaS Governance
13. Maintenance / Vulnerability Lifecycle
14. Release / Progressive Delivery
15. File Upload Security
16. Time / Clock Semantics
17. Regulated-Domain Escalation

## Proportionality

```text
CSS color change
→ R0
→ lightweight verification

public marketing site
→ frontend + SEO discoverability

lead-generation site
→ frontend + SEO + analytics/conversion

OAuth + admin authorization
→ R3
→ authentication + authorization + privacy controls

production destructive database operation
→ R4/A4
→ recovery evidence + qualified/human approval
```

The actual Git diff is reassessed after implementation. A task can be rerouted when implementation introduces authentication, destructive migration, production infrastructure, sensitive data, tenant boundaries, crawler/indexation behavior, analytics instrumentation or other specialist/task-scoped triggers.
