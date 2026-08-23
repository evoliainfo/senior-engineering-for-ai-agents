#!/usr/bin/env python3
"""Build the final generalization-remediation candidate from the exact canonical sef.py.

This patcher is intentionally deterministic and anchor-checked. It changes only
request semantic relations, bounded non-goal polarity and actual-diff release
composition. It must never silently patch an unexpected runtime revision.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_SOURCE_SHA256 = "bfeda790cd70c78ceb9fae862441df35c9bfe819001c0d429c09c0dde2a0c2bd"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def insert_after(text: str, anchor: str, addition: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(anchor, anchor + addition, 1)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="sef.py")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    source = Path(args.source)
    raw = source.read_bytes()
    actual = sha256(raw)
    if actual != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"unexpected source runtime: {actual}")
    text = raw.decode("utf-8")

    rc2_anchor = '''  ("no_modifications_to",re.compile(r"\\bno\\s+modifications?\\s+to\\b",re.I)),\n'''
    rc2_add = '''  ("do_not_implement",re.compile(r"\\b(?:do not|don't)\\s+(?:implement|add|introduce|create|configure|deploy|alter|enable)\\b",re.I)),
  ("no_change_planned",re.compile(r"\\bno\\b.{0,120}\\b(?:change|changes|modification|implementation)\\b.{0,50}\\b(?:is|are|was|were)?\\s*(?:planned|intended|requested|required)\\b",re.I)),
'''
    text = insert_after(text, rc2_anchor, rc2_add, "RC2 non-goal expansion")

    tenant_anchor = '''    if tenant_scope and access_action and cross_scope:\n        add("TENANT_ACCESS_BOUNDARY","MULTI_TENANT","R3","task explicitly constrains object/data access across organization or tenant boundaries")\n        add("OBJECT_AUTHORIZATION","AUTHORIZATION","R3","cross-scope denial is an authorization invariant, not only a tenancy label")\n'''
    tenant_add = '''

    # Final-cycle relation generalization: business partitions need not be named
    # tenant/workspace. Membership in one bounded group/account/unit plus an
    # explicit peer-boundary denial and a resource access action is equivalent.
    business_partition=has(r"\\b(?:franchise|dealer|partner|merchant|business|customer)\\s+(?:group|account|unit|team)s?\\b") or has(r"\\b(?:group|account|unit|team|department)\\b")
    membership_relation=has(r"\\b(?:belong(?:s|ing)?\\s+to|assigned\\s+to|scoped\\s+to)\\b.{0,70}\\b(?:one|a|an|the|that)\\b.{0,45}\\b(?:group|account|unit|team|department)\\b")
    peer_boundary=has(r"\\b(?:another|other|different)\\b.{0,45}\\b(?:group|account|unit|team|department)\\b")
    boundary_effect=has(r"\\b(?:expose|leak|access|read|view|return|retrieve|show)\\w*\\b.{0,90}\\b(?:data|records?|reports?|stores?|resources?|objects?)\\b") or has(r"\\b(?:data|records?|reports?|stores?|resources?|objects?)\\b.{0,90}\\b(?:another|other|different)\\b")
    if business_partition and membership_relation and peer_boundary and access_action and boundary_effect:
        add("BUSINESS_PARTITION_ACCESS_BOUNDARY","MULTI_TENANT","R3","membership and peer-boundary relations define shared-customer isolation even without tenant vocabulary")
        add("BUSINESS_OBJECT_AUTHORIZATION","AUTHORIZATION","R3","resource access must be authorized against the caller's business partition rather than caller-supplied scope")
'''
    text = insert_after(text, tenant_anchor, tenant_add, "business-partition authorization")

    trust_anchor = '''    if backend_actor and caller_control and remote_destination and server_fetch:\n        add("SERVER_SIDE_DESTINATION_TRUST","WEBHOOK_TRUST","R3","caller controls a destination reached by a privileged server-side network client")\n'''
    trust_add = '''

    # Variable-like locators and business actors are equivalent to URL/user forms.
    boundary_actor=has(r"\\b(?:callers?|users?|clients?|merchants?|customers?|partners?|requesters?|operators?|tenants?)\\b")
    locator_variable=has(r"\\b[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?:_url|_uri|_endpoint|_host|_address)\\b")
    locator_phrase=has(r"\\b(?:source|remote|target|asset|resource|network)\\s+(?:uri|url|endpoint|host|address|location)\\b") or has(r"\\b(?:that|the|this)\\s+address\\b")
    actor_control_v2=has(r"\\b(?:caller|user|client|merchant|customer|partner|requester|operator|tenant)s?\\b.{0,90}\\b(?:submit|submits|supply|supplies|provide|provides|choose|chooses|select|selects|control|controls)\\b") or has(r"\\b(?:submitted|supplied|provided|selected|controlled)\\b.{0,70}\\bby\\s+(?:the\\s+)?(?:caller|user|client|merchant|customer|partner|requester|operator|tenant)\\b")
    if backend_actor and boundary_actor and actor_control_v2 and (remote_destination or locator_variable or locator_phrase) and server_fetch:
        add("GENERAL_SERVER_DESTINATION_TRUST","WEBHOOK_TRUST","R3","a lower-privilege business actor controls a locator consumed by a privileged backend network operation")

    # Material outbound SaaS/API dependency: integration action plus API/service
    # semantics plus quota/vendor-failure evidence is supplier governance even
    # when the request never says 'third-party'.
    integration_action=has(r"\\b(?:sync|synchroni[sz]e|push|send|export|import|call|connect|integrate|forward)\\w*\\b")
    api_service=has(r"\\b(?:api|saas|crm|erp|hosted service|support platform|payment processor|external service)\\b")
    supplier_failure=has(r"\\b(?:rate limits?|quotas?|vendor outages?|provider outages?|service outages?|vendor failures?|provider failures?|deprecation|through its api|via its api)\\b")
    if integration_action and api_service and supplier_failure:
        add("MATERIAL_EXTERNAL_SERVICE_DEPENDENCY","EXTERNAL_SUPPLIER","R2","outbound integration depends materially on an independently operated API/service contract and failure modes")
'''
    text = insert_after(text, trust_anchor, trust_add, "trust and supplier relation generalization")

    regulated_anchor = '''    if clinical_domain and decision_semantics:\n        add("REGULATED_OUTCOME_DECISION","REGULATED_DOMAIN","R3","software is asked to make or recommend a patient/clinical outcome decision")\n        human_decisions.add("REGULATED_DOMAIN")\n'''
    regulated_add = '''

    # High-impact regulated decisions are cross-sector. Require a consequential
    # domain plus a decision/eligibility verb so calculators/content remain light.
    high_impact_domain=has(r"\\b(?:mortgage|lending|loan|credit[- ]bureau|credit decision|underwriting|underwriter|insurance|claim|benefits?|employment|hiring|housing|legal eligibility)\\b")
    high_impact_decision=has(r"\\b(?:approve|approval|decline|deny|denial|underwrite|determine|decide|recommend|eligib(?:le|ility)|accept|reject)\\w*\\b")
    if high_impact_domain and high_impact_decision:
        add("HIGH_IMPACT_REGULATED_DECISION","REGULATED_DOMAIN","R3","software is asked to make or recommend a consequential regulated/high-impact decision")
        human_decisions.add("REGULATED_DOMAIN")
'''
    text = insert_after(text, regulated_anchor, regulated_add, "cross-sector regulated decision")

    diff_anchor = '''            evidence.append({"pack":"RELEASE_ENGINEERING","reason":"destructive migration discovered in actual diff requires release/recovery governance","source":"b2_actual_diff"})\n'''
    diff_add = '''
    changed_paths=[str(x) for x in assessment.get("changed_paths",[]) if x]
    delivery_path=any(re.search(r"(?:^|/)(?:deploy|deployment|release|publish|promote|ship|delivery|prod(?:uction)?)[^/]*\\.(?:ya?ml|json|toml|sh)$",p,re.I) or re.search(r"(?:^|/)\\.github/workflows/[^/]*(?:deploy|release|publish|promote|prod|ship)[^/]*\\.ya?ml$",p,re.I) for p in changed_paths)
    if "CI_WORKFLOW_CHANGED" in triggers and delivery_path and ({"CI_SUPPLY_CHAIN","CONTAINER_ENGINEERING"} & packs):
        if "RELEASE_ENGINEERING" not in packs:
            packs.add("RELEASE_ENGINEERING")
            evidence.append({"pack":"RELEASE_ENGINEERING","reason":"actual diff introduces a delivery/publish workflow with CI or container supply-chain materiality","source":"final_actual_diff"})
'''
    text = insert_after(text, diff_anchor, diff_add, "actual-diff delivery composition")

    out = Path(args.output)
    out.write_text(text, encoding="utf-8")
    print(sha256(out.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
