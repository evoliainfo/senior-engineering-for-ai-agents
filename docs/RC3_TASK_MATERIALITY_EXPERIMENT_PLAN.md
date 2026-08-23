# RC-3 Task Materiality — Experiment Gate

Status: PRE-IMPLEMENTATION RESEARCH

Baseline runtime: `main` after RC-2 promotion (`19d1b1ae6713ada7c0edbf04afbd776cd507753c`).

No runtime behavior is changed by this document.

## 1. Confirmed residual symptom

Official scenario `WEB-001` uses:

- project brief: `A public company website.`
- task: `Create a public company website with SEO so it is discoverable in search.`

Expected plan:

- frontend + SEO discoverability;
- no analytics/conversion by default;
- implementation allowed;
- no multi-tenant blocking question inferred from `company` alone.

The remaining failure is caused by a project-level candidate context becoming a task-level blocker even though the current task does not materially depend on that context.

## 2. Current mechanism

Project discovery can infer `MULTI_TENANT` from broad organization language such as `company`, `organization`, `workspace`, `team` or `B2B`.

`MULTI_TENANT` is a material confirmation. Planning currently gathers unresolved material project candidates globally and converts all of them into `human_decisions_needed`. Any such decision makes:

```text
implementation_gate = BLOCKED_PENDING_AUTHORITATIVE_CONTEXT
implementation_allowed = false
```

This means the system currently conflates three distinct states:

1. a context is plausible somewhere in the project;
2. the current task touches that context materially;
3. the task cannot safely proceed without an authoritative answer.

RC-3 addresses only that promotion rule.

## 3. Safety objective

Project-level uncertainty must remain visible, but it should block a task only when the task materially depends on the unresolved fact.

Required invariant:

```text
candidate project context
        ≠
automatic task blocker

candidate project context
  + task-material evidence
  + unresolved authoritative fact
        -> blocking decision
```

The change must never invent an authoritative product fact. It changes whether an unresolved fact is blocking for the current task, not whether the fact is true.

## 4. Candidate architecture boundary

Preferred first candidate: deterministic task-materiality projection over unresolved material candidates.

```text
project profile / baseline candidates
             ↓
unresolved material contexts
             ↓
current task request + request routing + execution contexts
             ↓
deterministic materiality rules
             ↓
TASK_MATERIAL | PROJECT_ONLY | UNCERTAIN
             ↓
blocking decisions only for TASK_MATERIAL or deliberately fail-safe UNCERTAIN cases
```

Actual-diff assessment remains independent. If implementation later changes a tenant/auth/data/infrastructure boundary, actual diff can still escalate regardless of the plan-time projection.

## 5. Initial RC-3 scope

The first candidate should focus narrowly on `MULTI_TENANT`, because that is the confirmed DEV failure.

Do not generalize the first patch to all `MATERIAL_CONFIRMATIONS` until the materiality semantics are demonstrated. Other contexts such as PII, regulated domain, production, high availability or customer criticality may require different blocking thresholds.

## 6. Treatment probes to freeze before tuning

Project-level `MULTI_TENANT` candidate should NOT block tasks that are clearly unrelated to tenant isolation:

1. Public company marketing website + SEO.
2. Fix typography on public landing page.
3. Update public documentation copy.
4. Add sitemap/metadata to public brochure site.
5. Change public footer/legal links.
6. Update a public marketing image/component.
7. Add a public blog article/page.
8. Refactor a local pure utility with no identity/data boundary.

Expected: candidate remains visible as project context, but task implementation is allowed unless another blocker exists.

## 7. Positive controls — genuine task materiality

An unresolved multi-tenant candidate MUST remain blocking or explicitly escalated when the task touches tenant boundaries, for example:

1. `Add organization workspaces with separate customer data.`
2. `Allow users to switch between companies.`
3. `Add an admin endpoint that reads records for a selected tenant.`
4. `Move shared cache keys to workspace-scoped keys.`
5. `Add background jobs that process records per organization.`
6. `Add file storage paths partitioned by customer.`
7. `Create tenant-aware database queries.`
8. `Implement cross-organization reporting.`

These controls are more important than making `WEB-001` green: RC-3 must not weaken real tenant-boundary governance.

## 8. Ambiguity controls

Some tasks should remain conservative because task materiality cannot be established safely from wording alone, for example:

- `Add the company dashboard.`
- `Implement organization settings.`
- `Add workspace management.`

The experiment should record these separately rather than forcing them into the treatment set. A later design decision can choose whether `UNCERTAIN` blocks, asks a question, or requires inspection before implementation.

## 9. Evidence contract

A future shadow materiality annotator should emit evidence equivalent to:

```json
{
  "context": "MULTI_TENANT",
  "project_candidate": true,
  "task_materiality": "PROJECT_ONLY",
  "signals": ["public marketing site", "SEO task"],
  "blocking": false,
  "shadow_only": true
}
```

For a genuine tenant-boundary task:

```json
{
  "context": "MULTI_TENANT",
  "project_candidate": true,
  "task_materiality": "TASK_MATERIAL",
  "signals": ["workspace", "separate customer data"],
  "blocking": true,
  "shadow_only": true
}
```

## 10. Hard gates before behavioral integration

1. Freeze treatment, positive-control and ambiguity probes before runtime tuning.
2. Persist the post-RC-2 baseline on unchanged runtime.
3. Build shadow materiality classification first with `routing_effect = NONE`.
4. `WEB-001` must become implementation-allowed in the candidate while retaining frontend + SEO and no default analytics.
5. All tenant-boundary positive controls must remain blocked/escalated while unresolved.
6. Zero regression on RC-1 and RC-2 permanent gates.
7. Zero regression on actual-diff escalation.
8. Evidence/Release behavior unchanged in RC-3.
9. CHALLENGE remains held out from tuning.

## 11. Rejected shortcuts

Do not solve RC-3 by:

- deleting `company` from project discovery;
- automatically confirming `MULTI_TENANT = false` for marketing sites;
- disabling all material confirmations during planning;
- keying a special case directly to `WEB-001` wording;
- allowing task wording to overwrite authoritative project facts;
- weakening actual-diff tenant/security routing.

## 12. Recommended sequence

1. Freeze RC-3 probes.
2. Measure unchanged post-RC-2 runtime and persist artifacts.
3. Implement shadow task-materiality annotator for `MULTI_TENANT` only.
4. Test neighboring/metamorphic formulations.
5. Build an executable candidate outside canonical runtime if needed.
6. Compare official DEV + RC-1 + RC-2 + RC-3 controls + Evidence/Release.
7. Promote to canonical `sef.py` only after zero-regression evidence.

## 13. Current decision

Proceed with RC-3 diagnostic probes and shadow materiality observation. Do not modify canonical planning behavior yet.
