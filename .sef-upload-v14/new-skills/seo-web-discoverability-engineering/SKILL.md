---
name: seo-web-discoverability-engineering
description: Senior technical SEO and web discoverability execution playbook. Use for public websites, marketing sites, landing pages, organic acquisition, crawl/indexation, canonicalization, metadata, structured data, sitemaps, migrations, search performance and search-engine readiness.
---

# SEO & Web Discoverability Engineering

Treat organic discoverability as a product/engineering concern, not as a collection of meta tags. The goal is to make valuable public content technically discoverable, interpretable, measurable and maintainable without claiming rankings that cannot be guaranteed.

## 1. Start from the business/search outcome
- Identify the business outcome: qualified leads, product discovery, local visibility, documentation discovery, ecommerce, recruitment, support deflection or another explicit goal.
- Identify the intended audience, geography/language, search intents and the pages that should satisfy them.
- Separate user value from keyword targeting. Do not create thin or duplicative pages solely to manufacture query coverage.
- Distinguish technical readiness, indexation, impressions, clicks, conversions and ranking. They are different evidence states.

## 2. Define the indexability contract
For each material route/template, decide whether it should be:
- public and indexable;
- public but intentionally non-indexable;
- authenticated/private;
- canonicalized to another URL;
- redirected or retired.

Verify that the implementation is coherent across HTTP status, robots.txt, meta robots/X-Robots-Tag, canonical, authentication/WAF/CDN behavior and sitemap membership. A production `noindex`, accidental crawler block, incorrect canonical or protected public page is a release blocker when organic discovery is a stated requirement.

## 3. Crawl and URL architecture
- Use stable, descriptive, human-readable URLs appropriate to the product and locale.
- Preserve a coherent information architecture and internal-link graph; important public pages should not be orphaned.
- Ensure links required for discovery are crawlable HTML links where applicable.
- Generate sitemap entries from canonical indexable URLs only; use absolute URLs and truthful last-modified semantics when emitted.
- For large/dynamic sites, define crawl-budget and faceted/filter URL policy proportionately.
- On migrations, map old -> new URLs explicitly and verify redirect chains, 404/410 behavior and canonical consistency.

## 4. Canonicalization and duplicate control
- Choose one preferred URL for materially duplicate content and make signals consistent: redirects, internal links, sitemap and `rel=canonical`.
- Do not use canonical as a substitute for access control or for content that should be removed.
- For multilingual/multiregional sites, define locale URL strategy and apply `hreflang` only when variants genuinely exist and reciprocal semantics are correct.
- Test generated canonicals in production-like routing, including query parameters, trailing slashes, host/protocol variants and pagination where applicable.

## 5. Page semantics and metadata
For indexable pages, define deterministic metadata from authoritative page data:
- unique, accurate document title;
- descriptive main heading and visible content hierarchy;
- useful meta description where appropriate;
- canonical URL;
- social metadata where sharing matters;
- language/locale metadata;
- image alt text for meaningful images.

Do not stuff keywords, hide text, or generate large volumes of near-identical metadata. Metadata must describe the visible page, not a fictional search-target version of it.

## 6. Structured data
- Use Schema.org/engine-supported structured data only where the page content and entity type justify it.
- Markup must match visible, truthful content and current provider eligibility rules.
- Prefer JSON-LD when consistent with the chosen stack/provider guidance.
- Validate syntax and eligibility with current official tooling/documentation.
- Do not invent ratings, reviews, prices, authorship, organization attributes or other facts to obtain rich results.
- Structured data eligibility is not evidence that a rich result will be shown.

## 7. Rendering and JavaScript
- Ensure the search engine can receive meaningful indexable content with the real production rendering architecture.
- Verify status codes, redirects and metadata at the response/rendering layer actually used by the framework.
- Do not assume client-side rendering is understood merely because it works in a developer browser.
- Keep critical navigation/content discoverable under realistic crawler execution and WAF/CDN settings.

## 8. Performance and page experience
Route relevant performance/accessibility procedures. For important templates and journeys:
- measure field data when available and lab data for diagnosis;
- review LCP, INP and CLS using current official thresholds/guidance;
- prevent regressions in image delivery, fonts, JavaScript, third-party tags and caching;
- do not trade correctness/accessibility/content quality for a synthetic score.

Lab scores are diagnostic evidence, not proof of real-user Core Web Vitals.

## 9. Content/search architecture
When organic acquisition is part of the product:
- map meaningful search/user intents to canonical destination pages;
- avoid multiple pages competing for the same purpose without deliberate differentiation;
- make expertise, offering, scope, evidence and next action clear on the page;
- create internal links based on user journeys and topical relationships, not arbitrary keyword loops;
- use current search data (Search Console or another defensible source) when making demand/performance claims.

Never fabricate search volume, ranking difficulty, traffic forecasts or competitor performance. External demand claims require external evidence.

## 10. Release verification
For material SEO changes, verify in a production-like or production environment as applicable:
- expected HTTP status;
- indexability directives;
- robots.txt behavior;
- canonical target;
- sitemap membership;
- rendered title/main content;
- structured-data validity where used;
- internal discoverability;
- redirect behavior for migrations;
- mobile/responsive rendering and critical performance regressions.

After deployment, separate these states explicitly:
- `TECHNICALLY_DISCOVERABLE`: technical prerequisites verified;
- `INDEXATION_NOT_YET_PROVEN`: no external index evidence yet;
- `INDEXED`: external search-console/engine evidence exists;
- `SEARCH_PERFORMANCE_OBSERVED`: impressions/clicks/query data exists;
- `SEO_OUTCOME_NOT_GUARANTEED`: rankings/traffic are not guaranteed by technical compliance.

## 11. Anti-patterns / hard warnings
- Do not promise first-page or top-ranking outcomes.
- Do not use doorway pages, scaled low-value pages, hidden text, fake structured data or other spam tactics.
- Do not treat sitemap submission as proof of indexation.
- Do not treat a green Lighthouse run as proof of field performance.
- Do not ship a marketing site without an intentional crawl/indexation policy.

## Authoritative anchors
Re-check current official documentation at execution time because search behavior evolves.
- Google Search Essentials: https://developers.google.com/search/docs/essentials
- Google sitemap guidance: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- Google structured-data guidance: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- Google guidance for AI experiences in Search: https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search
- Schema.org vocabulary: https://schema.org/
- W3C web standards and accessibility guidance as applicable.
