---
name: geo-ai-discoverability-engineering
description: Generative/AI search discoverability execution playbook. Use for GEO/AEO, ChatGPT Search, Google AI Overviews/AI Mode, answer engines, AI crawler access, citation readiness, entity clarity and measuring AI-originated discovery. Always pair with technical SEO/web discoverability.
---

# GEO / AI Discoverability Engineering

Treat AI discoverability as an extension of high-quality web/search engineering plus provider-specific crawl and presentation controls. Do not present GEO/AEO as a guaranteed ranking formula or as a secret markup trick.

## 1. Define the surface and outcome
Identify which outcomes matter:
- inclusion/citation in ChatGPT Search or another answer engine;
- visibility in Google AI Overviews / AI Mode or equivalent generative search features;
- qualified referral traffic from AI/search experiences;
- accurate representation of the organization/product/entity;
- discoverability of documentation, products, local/business information or research.

Record the target providers when known, but keep the implementation provider-agnostic where possible.

## 2. Build on ordinary search fundamentals first
Before any provider-specific GEO work, apply the SEO & Web Discoverability playbook:
- public pages must be reachable and return correct responses;
- crawl/indexation policy must be intentional;
- canonical URLs and internal links must be coherent;
- content must be useful, original, accurate and understandable;
- structured data must match visible content.

For Google generative search experiences, do not invent a special AI-only technical requirement when current Google guidance says normal Search fundamentals apply.

## 3. Separate search crawlers from training crawlers
Crawler policy is a product/legal decision, not a single “allow AI” switch.

For providers that distinguish purposes, keep them separate. Example for OpenAI current guidance:
- `OAI-SearchBot` relates to discovery/surfacing in ChatGPT search experiences;
- `GPTBot` relates to potential model training and can be controlled independently.

Do not tell a client that blocking training necessarily blocks search visibility, or the reverse. Re-check the provider's current official crawler documentation, published IP ranges/verification mechanism and robots semantics before changing production policy.

Also verify infrastructure layers beyond robots.txt when a crawler should have access: CDN/WAF/bot mitigation, authentication, geo restrictions, rate limits, JavaScript challenges and HTTP status.

## 4. Make content citation-ready, not “LLM stuffed”
Prioritize content that can be correctly understood and cited:
- clear page purpose and descriptive headings;
- concise direct answers near the relevant question/problem;
- explicit entity names, products, services, locations and relationships;
- stable canonical URLs and fragment/section structure where useful;
- first-party evidence, methodology, examples, case studies and source attribution;
- publication/update dates when freshness materially matters;
- author/organization information when it supports trust and accountability;
- tables/lists only when they improve comprehension, not to game extraction.

Avoid vague marketing copy that never states what the company/product actually does. Avoid machine-generated content at scale with no original value.

## 5. Entity and factual consistency
- Keep organization/product naming, descriptions, contact/location data and public claims consistent across authoritative pages.
- Use appropriate structured data for real entities when supported and truthful.
- Link to primary evidence for claims that require verification.
- Distinguish facts, opinions, estimates and forward-looking claims.
- Correct stale/conflicting information rather than adding more duplicate pages.

The goal is to reduce ambiguity for humans and machines, not to manufacture an unsupported “knowledge graph score.”

## 6. Provider-specific controls
When a named provider matters, consult its current primary documentation and record what is actually supported.

Examples of current classes of controls:
- crawler/user-agent access in robots.txt;
- noindex/nosnippet/max-snippet/data-nosnippet or equivalent preview controls;
- structured data/search feature eligibility;
- search-console/webmaster reporting;
- referral parameters/source information;
- URL change notification protocols such as IndexNow where supported.

Do not assume one provider's crawler, preview directive or reporting semantics applies to another.

## 7. `llms.txt`, AI-specific files and emerging conventions
Treat `llms.txt`, `ai.txt` and similar proposals as **RADAR/EXPERIMENTAL** unless the target provider's current official documentation explicitly requires or supports them for the desired outcome.
- They are not a substitute for crawlable high-quality HTML, canonical URLs, robots directives or structured data.
- Their presence is not evidence of citation or ranking.
- Do not make them a release gate by default.
- If used experimentally, document the hypothesis and measure outcomes separately.

## 8. Measurement
Measure what can actually be observed:
- AI/search referral sessions and qualified actions where referrer/UTM data exists;
- provider search-console/webmaster impressions/clicks where exposed;
- citation/mention sampling using a defined query set and timestamped observations;
- crawl/log evidence where legally/operationally appropriate;
- branded/non-branded discovery and assisted conversions where attribution permits.

For ChatGPT Search, current OpenAI publisher guidance indicates referral URLs can include `utm_source=chatgpt.com`; verify the current behavior before building reports around it.

Do not claim “GEO success” from a one-off manual prompt. Generative answers are non-deterministic and can vary by time, model, locale and context.

## 9. Verification states
Use precise status language:
- `AI_CRAWL_READY`: desired provider crawler access verified as far as available evidence allows;
- `CITATION_READY_CONTENT`: content/entity/source structure reviewed and technically available;
- `AI_VISIBILITY_OBSERVED`: timestamped provider/query evidence exists;
- `AI_REFERRAL_OBSERVED`: measurable referral traffic exists;
- `AI_CONVERSION_OBSERVED`: downstream conversion evidence exists;
- `AI_VISIBILITY_NOT_GUARANTEED`: no provider placement/citation guarantee exists.

## 10. Anti-patterns / hard warnings
- Never guarantee citation, placement or inclusion in an AI answer.
- Do not confuse model training permission with search inclusion permission.
- Do not fabricate “AI authority scores” or provider ranking factors without evidence.
- Do not mass-produce FAQ/definition pages merely to target answer engines.
- Do not change robots/WAF policy without checking business, security, privacy and training implications.
- Do not present experimental GEO folklore as an established standard.

## Authoritative anchors
Re-check primary documentation at execution time because this area changes quickly.
- Google guidance for AI experiences in Search: https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search
- Google Search Essentials: https://developers.google.com/search/docs/essentials
- OpenAI Publishers & Developers FAQ (OAI-SearchBot / GPTBot / referrals): https://help.openai.com/en/articles/12627856-publishers-and-developers-faq
- IndexNow protocol when applicable: https://www.indexnow.org/documentation
- Current official documentation of any additional target answer/search provider.

Provider-specific crawler tokens, referral parameters and AI-search behavior are time-sensitive. Treat these links as starting points, not immutable facts; re-verify them during execution.
