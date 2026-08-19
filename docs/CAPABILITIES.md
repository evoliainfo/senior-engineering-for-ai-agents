# Capabilities

SEF v1.3 combines a general engineering control layer with specialist governance packs and execution playbooks selected according to project context and task risk.

## Engineering coverage

| Domain | Coverage | Mechanism |
|---|---|---|
| Product discovery / requirements | Strong | Project Engineering Baseline + requirements/risk planning |
| Architecture / boundaries | Strong | Core architecture controls + full-stack integration playbook |
| Frontend application engineering | Strong | Frontend execution playbook + accessibility/compatibility governance |
| Backend / HTTP API | Strong | Backend/API execution playbook + auth/security/webhook governance |
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
| Regulated domains | Escalation, not simulated compliance | Qualified domain-specific review required |

## Full-stack execution playbooks

### Frontend Application Engineering

Covers:

- user journeys and material UI states
- component boundaries and reuse
- server/client/local/URL state ownership
- forms and validation
- data fetching, mutation, stale/duplicate handling
- accessibility and responsive behavior
- browser compatibility
- frontend performance
- component/integration/browser/E2E verification

### Backend / API Service Engineering

Covers:

- API/service boundaries
- HTTP semantics and contracts
- input validation and trust boundaries
- server-side authorization
- domain invariants and state machines
- transactions and concurrency
- idempotency
- external dependency timeouts/retries/failure semantics
- error handling
- API/contract/authz/integration verification

### Database Design & Query Engineering

Covers:

- entities, relationships and domain invariants
- identifiers, types, nullability and defaults
- primary/foreign/unique/check constraints
- normalization and deliberate denormalization
- indexes and query plans
- N+1 and unbounded query patterns
- transaction/isolation/locking semantics
- ORM discipline and parameterized raw SQL
- data lifecycle
- representative database integration and concurrency evidence

### Full-Stack Architecture & Integration

Covers:

- browser/client → frontend → API → domain → database → async/external flow
- boundary ownership and contracts
- dependency direction
- cross-layer invariants
- compatibility of API/data changes
- failure propagation and user recovery
- end-to-end evidence
- thresholds for recording architecture decisions

### Reliability & Observability Engineering

Covers:

- health and critical user/business symptoms
- logs, metrics and traces
- correlation and diagnostic context
- background-worker and queue health
- timeouts/retries/backpressure/degraded behavior
- capacity and bottlenecks
- actionable alerts
- release/incident linkage

## Specialist governance packs

SEF v1.3 contains 17 specialist routes:

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

SEF is designed to avoid a universal heavyweight checklist.

Examples:

```text
CSS color change
→ R0
→ lightweight verification

standard business feature
→ R1/R2
→ relevant frontend/backend/database guidance

OAuth + admin authorization
→ R3
→ authentication + authorization + privacy controls

production destructive database operation
→ R4/A4
→ recovery evidence + qualified/human approval
```

The actual Git diff is reassessed after implementation. A task initially planned as low risk can be escalated if the implementation introduces authentication, destructive migration, production infrastructure, sensitive data, tenant boundaries, external side effects, or other specialist triggers.
