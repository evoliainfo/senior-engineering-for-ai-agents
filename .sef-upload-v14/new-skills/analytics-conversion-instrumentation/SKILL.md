---
name: analytics-conversion-instrumentation
description: Product/web analytics and conversion measurement execution playbook. Use for GA4, GTM/tag managers, analytics SDKs, event tracking, funnels, attribution, campaign UTMs, lead/conversion instrumentation, pixels and measurement reliability.
---

# Analytics & Conversion Instrumentation

Treat analytics as a data product. “The tag fires” is not sufficient evidence that business measurement is correct, privacy-safe, deduplicated or useful.

## 1. Start with a measurement plan, not a vendor tag
Define before implementation:
- business objective;
- user journey/funnel;
- decision the metric will support;
- primary conversions/key outcomes;
- supporting diagnostic events;
- required dimensions/properties;
- ownership and data destination;
- retention/consent/privacy constraints;
- success criteria and known attribution limits.

Avoid collecting events simply because the SDK makes them easy.

## 2. Event/data contract
Create a small stable taxonomy with explicit semantics. For each material event define:
- canonical event name;
- exact trigger condition;
- required/optional parameters and types;
- actor/session/tenant semantics if applicable;
- client timestamp vs server receipt semantics where relevant;
- source layer (browser, server, webhook, CRM);
- deduplication/idempotency key if the same business action can arrive from multiple paths;
- conversion/key-event classification;
- owner/version/change policy.

Use business events (`lead_submitted`, `checkout_completed`) rather than brittle UI implementation details (`green_button_clicked`) when business meaning is the goal.

## 3. Conversion semantics
For each conversion, define what must be true for it to count.
Examples:
- form validation passed is not necessarily a lead if backend persistence failed;
- payment button click is not purchase success;
- calendar CTA click is not completed booking;
- duplicate retries must not multiply revenue/conversion counts.

Prefer authoritative server/business-state confirmation for high-value conversions when feasible, with client events used for funnel diagnostics.

## 4. Privacy, consent and sensitive data
Route the SEF privacy specialist procedure when personal data, cookies/identifiers, consent, advertising profiles or cross-context tracking are in scope.
- Do not send secrets, passwords, free-form user content or unnecessary PII in analytics payloads.
- Check URLs/page titles/search fields/event parameters for accidental email/phone/name/token leakage.
- Keep consent state and collection behavior coherent across first load, navigation and consent changes.
- Distinguish analytics, personalization and advertising purposes rather than bundling them silently.
- Jurisdiction-specific legal conclusions require the appropriate qualified/legal review; the analytics playbook does not invent a universal consent rule.

For Google Analytics specifically, current Google policies prohibit sending information Google can recognize as PII. Re-check current vendor policy before implementation.

## 5. Client-side instrumentation
- Ensure SPA/client routing emits page/navigation semantics intentionally; do not assume traditional page-load behavior.
- Avoid duplicate initialization and duplicate event listeners across hydration/navigation.
- Keep tag-manager triggers narrowly defined and version-controlled/documented where possible.
- Treat third-party tags as performance, privacy, security and supply-chain dependencies.
- Prevent analytics failures from breaking the critical user journey.

## 6. Server-side / Measurement Protocol instrumentation
Use server-side events when they are more authoritative or resilient, but do not assume server-side means “privacy-free”.
- authenticate vendor requests/secrets correctly;
- avoid exposing server credentials to browsers;
- define deduplication between browser/server copies;
- preserve transaction/event IDs across retries;
- validate payload schema and vendor responses;
- monitor delivery failures and quotas;
- document timestamp/backfill semantics.

For GA4 Measurement Protocol or equivalent vendor APIs, consult current official schema/validation guidance at execution time.

## 7. Campaign and attribution hygiene
- Define a controlled UTM/source-medium naming convention when campaign tagging is used.
- Never put PII/secrets in UTM parameters.
- Preserve landing parameters only as long as required for the measurement design.
- Define cross-domain/referral exclusions/payment-provider behavior where applicable.
- Treat attribution as a model with limitations, not ground truth. Record which attribution model/window/source powers a reported KPI.

## 8. Verification ladder
Use multiple levels of evidence instead of a single “tag installed” check.

### Level A — implementation
- expected SDK/tag/container is present in the intended environment;
- no duplicate container/config IDs;
- consent/default configuration is intentional;
- events are emitted only on the defined trigger.

### Level B — transport
- browser/network or server logs show the expected request/payload;
- vendor endpoint accepts the event or returns a documented success/validation response;
- blocked requests/ad blockers/consent states are understood.

### Level C — vendor ingestion
- event appears in vendor real-time/debug tooling where available;
- event name and parameters match the measurement contract.

For GA4, use current official tools such as Tag Assistant and DebugView where applicable. A GTM “tag fired” indication alone does not prove GA4 ingestion.

### Level D — conversion semantics
- the authoritative business action occurred;
- exactly one intended conversion is recorded;
- failure/cancel/retry paths do not create false conversions;
- key-event/conversion configuration is verified in the destination system.

### Level E — reporting
- production reports expose the expected metric/dimensions after normal processing delay;
- test/internal traffic handling is understood;
- source/medium/campaign behavior matches the stated attribution design.

## 9. Regression protection
For critical funnels:
- add automated tests for event emission/data-layer contracts where practical;
- add E2E assertions against a test/stub collector when vendor calls would make tests flaky;
- monitor sudden event-volume drops/spikes and conversion-rate discontinuities;
- include analytics checks in release plans for route/form/checkout/consent/tag changes.

Do not make production CI dependent on a live third-party analytics endpoint unless there is a deliberate, resilient test design.

## 10. Evidence states
Use explicit states:
- `IMPLEMENTED_NOT_INGESTION_VERIFIED`;
- `INGESTION_VERIFIED`;
- `CONVERSION_SEMANTICS_VERIFIED`;
- `REPORTING_OBSERVED`;
- `ATTRIBUTION_MODEL_LIMITED`;
- `NOT_VERIFIED` when the required provider/production evidence is unavailable.

## 11. Anti-patterns / hard warnings
- Tag present != measurement correct.
- Tag Manager fired != analytics platform ingested.
- Event received != valid conversion semantics.
- Dashboard number != causal attribution.
- Do not collect PII “just in case”.
- Do not mark every event as a conversion.
- Do not silently change event names/parameters used by production dashboards or ads integrations.

## Authoritative anchors
Re-check current vendor docs at execution time.
- Google Analytics PII guidance: https://support.google.com/analytics/answer/6366371
- Google Analytics DebugView: https://support.google.com/analytics/answer/7201382
- GA4 Measurement Protocol: https://developers.google.com/analytics/devguides/collection/protocol/ga4
- GA4 Measurement Protocol validation: https://developers.google.com/analytics/devguides/collection/protocol/ga4/validating-events
- The selected analytics provider's official instrumentation/privacy documentation.
- SEF Privacy/Data Protection specialist pack for personal-data/consent governance.
