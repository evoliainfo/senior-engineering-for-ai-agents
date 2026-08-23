# Final generalization remediation

Status: **LAST ALLOWED DETERMINISTIC REMEDIATION CYCLE**

## Trigger

Fresh CHALLENGE v2 was a valid independent run against frozen candidate `4132711f9d0ad74ff41b26deff7b9966d6e54e94` / runtime SHA-256 `bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd`.

Official result: **4/10 PASS, 6/10 FAIL**. Harness integrity passed and the holdout is now consumed.

## Root-cause model

The six failures collapse into four structural causes:

1. **Boundary relation vocabulary remains too narrow.** Shared-customer authorization is recognized for tenant/workspace/organization vocabulary but not for equivalent business partitions such as franchise/dealer groups.
2. **External trust/dependency relations remain too lexical.** Caller-controlled server destinations miss variable-like locators such as `source_uri`, while ordinary outbound SaaS dependencies can miss supplier governance unless the request uses explicit third-party/provider vocabulary.
3. **Regulated outcome classification is sector-specific.** Clinical decisions are handled, but materially equivalent consumer-finance/insurance decisions can remain ordinary R1 work.
4. **Polarity and actual-diff composition are asymmetric.** Explicit non-goals such as `do not implement ... deployment` or `no deployment change is planned` can still trigger specialist packs, while a real deploy/publish workflow discovered in the diff can fail to compose `RELEASE_ENGINEERING`.

## Remediation design

This cycle must change relations, not memorize CHALLENGE v2 strings:

- extend bounded non-goal recognition to implementation/deployment clauses while preserving prohibitive requirements such as `must not allow unauthorized access`;
- detect shared-customer authorization from membership + peer-boundary + access relations, including generic group/account/unit/team/department partitions;
- detect server-side destination trust from actor control + locator + privileged backend network action, including variable-like locator names;
- detect material outbound supplier dependencies from integration action + external API/service semantics + quota/vendor failure signals;
- classify materially outcome-affecting decisions across regulated/high-impact domains, not health only;
- compose release governance from actual delivery workflow paths plus CI/container supply-chain evidence, without treating ordinary lint/test CI as a release.

## Acceptance gates

A candidate is promotable only if all are true on one exact runtime SHA:

- historical DEV: `38/38 PASS`;
- B1: `10/10 PASS`;
- B2: `10/10 PASS`;
- RC-8 calibrated: `14/14 PASS`;
- CHALLENGE #1 replay: `10/10 PASS` as consumed regression only;
- CHALLENGE v2 replay: `10/10 PASS` as consumed regression only;
- new final-generalization positive/negative controls: all PASS;
- zero harness/accounting errors.

No CHALLENGE v3 scenario may be materialized before the remediated candidate is merged and re-frozen.

## Stop rule

After this cycle there is exactly one fresh CHALLENGE v3. If v3 still contains critical structural failures, deterministic tuning stops. The next decision must be architecture redesign or an explicitly limited experimental/beta release, not a fourth hidden tuning loop.
