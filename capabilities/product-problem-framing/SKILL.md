---
name: product-problem-framing
description: Turn a rough product idea or outcome request into a clear problem, user, success, constraint, and non-goal frame before architecture or implementation begins, while avoiding unnecessary product ceremony for small changes.
---

# Product Problem Framing

Use this capability when the user has an idea, desired outcome, or loosely defined product but has not supplied a professional product/engineering brief.

The objective is to establish **what problem is worth solving and what outcome would count as success** before technical decisions harden around an assumption.

## Core Principle

> Do not make the user write a PRD to receive senior engineering behavior.

The agent should infer ordinary framing structure from the user's intent and available evidence. Ask only for choices that materially change the product, business model, target user, risk, or success definition.

## 1. Capture the Product Intent

Start from the user's own words. Identify, when relevant:

- intended user, operator, customer, or system actor;
- problem, friction, opportunity, or job to be done;
- desired observable outcome;
- why the outcome matters;
- any named market, workflow, platform, audience, or operating constraint.

Do not convert an exploratory idea into a falsely precise specification.

For a tiny feature request in an existing product, keep this to one or two sentences and hand off quickly.

## 2. Separate Problem from Proposed Solution

Users often express a solution as though it were the requirement.

Example:

> "I need an AI chatbot on the dashboard."

Possible underlying needs might include reducing support workload, helping users locate internal information, or automating a specific transaction.

Do not reject the proposed solution. Instead determine whether the solution itself is fixed or whether it is one candidate for the outcome.

Record:

- **fixed user intent** — what must remain true;
- **proposed mechanism** — what can still be challenged if a better path exists;
- **open product decision** — what genuinely requires user authority.

## 3. Identify the Primary Actor and Journey

For material products, establish the smallest useful journey:

```text
Actor -> trigger/context -> action -> expected result -> value
```

If multiple actors exist, identify the primary one and only the secondary actors that materially affect design.

Avoid inventing personas, demographics, or market assumptions without evidence.

## 4. Define Success at the Right Level

Success should be observable, but not over-engineered.

Possible layers:

- user can complete a critical journey;
- operator can manage a required workflow;
- system produces a defined business result;
- a measurable operational constraint is respected;
- a known failure or cost is reduced.

Distinguish:

- **delivery success** — the product capability works;
- **business outcome hypothesis** — adoption, conversion, revenue, retention, time saved, etc.;
- **longer-term outcome** — something that cannot be proven by shipping the first implementation.

Do not promise business outcomes merely because the software is technically correct.

## 5. Surface Material Constraints

Capture constraints only when they can change architecture, scope, or acceptance.

Examples:

- existing platform/repository;
- target devices or browsers;
- offline/real-time requirement;
- expected scale or latency where genuinely material;
- budget or vendor restriction;
- sensitive data;
- authentication/access policy;
- regulatory/high-impact domain;
- required integration;
- deployment environment;
- deadline that changes trade-offs.

Do not ask the user to estimate technical quantities that can be derived later or are not yet decision-relevant.

## 6. Define Non-Goals and First Delivery Boundary

For a new product, prevent "build the whole vision" scope collapse.

Define the smallest coherent first delivery that proves the important capability without deliberately creating a throwaway architecture.

A non-goal is useful when it prevents a plausible scope misunderstanding. Do not add a long exclusion list for obvious omissions.

Separate:

- required first-delivery behavior;
- later opportunities;
- explicit non-goals;
- unresolved product choices.

## 7. Decide What Can Be Inferred

The agent should normally infer:

- need for testable acceptance criteria;
- ordinary error and empty-state handling;
- repository/platform conventions;
- common security/configuration hygiene;
- appropriate technical investigation before stack choice.

The user should normally decide:

- who the product is for when genuinely ambiguous;
- paid/free or business policy;
- destructive data semantics;
- access policy with materially different user rights;
- material cost/latency/privacy trade-off;
- legal/regulatory posture;
- what outcome matters when multiple product directions are valid.

Do not ask "Which database/framework should I use?" unless the user has a real constraint or preference that materially matters.

## 8. Produce a Compact Product Frame

For a material greenfield project, a useful output is:

```text
PRODUCT FRAME
Primary actor:
Problem/opportunity:
Desired outcome:
Critical first journey:
Success for first delivery:
Material constraints:
Non-goals:
Assumptions:
User decisions still required:
Business outcome hypotheses, not yet proven:
```

For a small brownfield change, this may be a short internal summary rather than a visible artifact.

## Decision Points

### Explore vs commit

If the user is brainstorming, preserve alternatives and identify what evidence would choose among them. Do not force an architecture decision prematurely.

If the product outcome is clear enough for engineering, move forward rather than asking for a perfect strategy document.

### MVP vs durable foundation

Prefer the smallest coherent product slice, not the smallest amount of code. An MVP can still need durable identity, data, security, or deployment foundations when those are intrinsic to the product.

### User question vs professional inference

Ask only when different answers would materially change user-visible behavior, business policy, irreversible state, risk, or cost. Otherwise proceed with a documented engineering assumption that can be revised.

## Context Budget

Use only the context needed to frame the product:

1. user intent and conversation;
2. existing product/repository context when present;
3. authoritative business constraints supplied by the user;
4. external research only when the decision genuinely depends on current market/platform facts.

Do not read the full repository before knowing the product problem. Use `repository-discovery` after the task/product boundary is clear enough to target exploration.

## Anti-Patterns

Avoid:

- demanding a complete PRD from a non-expert user;
- treating the user's first technical idea as unquestionable product truth;
- inventing personas, market size, metrics, or business policy;
- asking framework/database/cloud questions before requirements justify them;
- turning every small feature into product strategy work;
- defining success only as "feature implemented" when the requested outcome is user-visible;
- confusing a shipped feature with proven commercial impact;
- expanding an MVP into every plausible future feature;
- making architecture decisions inside product framing without evidence.

## Evidence Contract

Before handoff on a material product, be able to answer:

1. Who or what is the primary actor?
2. What problem/outcome is being addressed?
3. What is the smallest coherent first delivery?
4. What success is observable at delivery time?
5. Which business outcomes remain hypotheses?
6. Which constraints materially affect engineering?
7. Which assumptions were inferred?
8. Which decisions genuinely require the user?

## Handoff

Use `requirements-to-acceptance` to convert the product frame into observable behavior and evidence criteria.

Use `repository-discovery` when an existing codebase/product must constrain the solution.

Use `solution-architecture-stack-selection` only after the outcome and material constraints are sufficiently clear.
