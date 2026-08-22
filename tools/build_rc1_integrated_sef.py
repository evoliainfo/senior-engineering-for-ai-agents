#!/usr/bin/env python3
"""Generate the RC-1 integrated single-file SEF runtime deterministically.

The source ``sef.py`` is treated as immutable input. This builder applies three
anchored transformations and refuses to continue unless every anchor occurs
exactly once. It is used to verify final single-file integration before the
canonical runtime is changed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "RC1_CONCEPT_NORMALIZATION_ADDITIVE_V1"

HELPERS = r'''
# ---------- RC-1 deterministic concept normalization ----------
# RC1_CONCEPT_NORMALIZATION_ADDITIVE_V1
# This layer normalizes bounded request-language variants into six canonical
# concepts. It is additive: it may add request routing signals, never remove or
# downgrade legacy routing, and actual-diff reassessment remains independent.
def _rc1_normalize_text(text):
    import unicodedata
    text=unicodedata.normalize("NFKC",str(text or ""))
    text=text.replace("’","'").replace("‘","'").replace("‐","-").replace("‑","-").replace("–","-")
    return re.sub(r"\s+"," ",text).strip().lower()

_RC1_CONCEPT_RULES=(
  ("AUTHORIZATION","pack","AUTHORIZATION",(
    r"\b(?:permission|permissions|rbac|access control|authorization|authorisation)\b",
    r"\b(?:authorized|authorised)\s+(?:administrator|admin|user|operator|person|role)\b",
    r"\bonly\s+(?:an?\s+)?(?:authorized|authorised)\s+(?:administrator|admin|user|operator|person|role)\b",
  )),
  ("DATABASE_MIGRATION","pack","DATABASE_MIGRATION",(
    r"\bdatabase\s+migration\b",
    r"\bmigrat(?:e|es|ed|ing)\b.{0,80}\b(?:existing|stored|records?|rows?|timestamps?|data|database)\b",
    r"\b(?:existing|stored|records?|rows?|timestamps?|data|database)\b.{0,80}\bmigrat(?:e|es|ed|ing)\b",
  )),
  ("WEBHOOK_TRUST","pack","WEBHOOK_TRUST",(
    r"\bwebhook(?:s)?\b.{0,100}\b(?:receive|receives|received|accept|accepts|inbound|event|events|provider|callback)\b",
    r"\b(?:receive|receives|accept|accepts|inbound)\b.{0,100}\bwebhook(?:s)?\b",
    r"\bprovider\s+webhook(?:s)?\b",
  )),
  ("EXTERNAL_SUPPLIER","pack","EXTERNAL_SUPPLIER",(
    r"\bexternal\s+api\b.{0,100}\b(?:supplied|provided|provider|vendor|third-party|third party)\b",
    r"\b(?:third-party|third party|external)\s+(?:saas\s+)?(?:vendor|provider|supplier|service|api)\b",
    r"\bdepend(?:s|ed|ing)?\s+on\b.{0,80}\b(?:third-party|third party|external)\b",
  )),
  ("BACKGROUND_JOB","execution_context","BACKGROUND_JOB",(
    r"\bqueue\s+consumer\b.{0,100}\b(?:job|jobs|async|asynchronously|retry|retries|retryable)\b",
    r"\bqueue\s+worker\b.{0,100}\b(?:job|jobs|async|asynchronously|retry|retries|retryable|failed)\b",
    r"\b(?:retryable\s+)?background\s+worker\b",
    r"\bworker\b.{0,100}\b(?:process|processes|processing|run|runs|running)\b.{0,80}\b(?:job|jobs|task|tasks)\b",
    r"\bworker\b.{0,100}\b(?:job|jobs)\b.{0,80}\b(?:background|async|asynchronously|retry|retries|retryable)\b",
  )),
  ("SEO_WEB_DISCOVERABILITY","execution_context","SEO_WEB_DISCOVERABILITY",(
    r"\bseo\b.{0,120}\b(?:public|page|search engine|index|indexing|indexation|crawl|discover)\b",
    r"\b(?:public\s+)?(?:product\s+)?page\b.{0,120}\b(?:search engines?|search engine)\b.{0,80}\b(?:find|index|discover|crawl)\w*\b",
    r"\b(?:find|discover)\w*\b.{0,80}\bthrough\s+search\s+engines?\b",
    r"\b(?:find|discover)\w*\b.{0,100}\bpublic\b.{0,80}\bpage\b.{0,120}\bsearch\s+engines?\b",
    r"\bdiscoverable\s+(?:in|through|via)\s+search\b",
  )),
)

def _rc1_detect_concepts(request):
    normalized=_rc1_normalize_text(request); observations=[]
    for concept,output_kind,output_id,patterns in _RC1_CONCEPT_RULES:
        matches=[]
        for pattern in patterns:
            m=re.search(pattern,normalized,re.I)
            if m: matches.append({"pattern":pattern,"match":m.group(0),"span":[m.start(),m.end()]})
        if matches:
            observations.append({"concept":concept,"candidate_output":{"kind":output_kind,"id":output_id},"evidence":matches})
    return observations

def _rc1_detected_ids(request):
    return {str(x.get("concept")) for x in _rc1_detect_concepts(request)}

def _rc1_stateful_database_companion(request):
    text=_rc1_normalize_text(request)
    return re.search(r"\bdatabase\b|\bledger\s+state\b|\bwrite(?:s|ing)?\b.{0,50}\b(?:ledger|state|record|records|row|rows|database)\b",text,re.I) is not None

'''

REQUEST_ENRICHMENT = r'''
    # RC-1 additive compatibility adapter. Legacy request signals above remain
    # untouched; canonical concepts may only add missing triggers/contexts.
    rc1_observations=_rc1_detect_concepts(request)
    for observation in rc1_observations:
        concept=str(observation.get("concept") or "")
        if concept=="AUTHORIZATION": triggers.add("AUTHZ_CHANGED")
        elif concept=="DATABASE_MIGRATION":
            triggers.add("DATABASE_SCHEMA_CHANGED"); contexts.add("DATABASE"); task_contexts.add("DATABASE")
        elif concept=="WEBHOOK_TRUST":
            triggers.add("INBOUND_WEBHOOK_ADDED"); contexts.update(["INBOUND_WEBHOOK","PUBLIC_API"]); task_contexts.update(["INBOUND_WEBHOOK","PUBLIC_API"])
        elif concept=="EXTERNAL_SUPPLIER":
            contexts.add("EXTERNAL_SAAS"); task_contexts.add("EXTERNAL_SAAS")
        elif concept=="BACKGROUND_JOB":
            contexts.add("BACKGROUND_JOB"); task_contexts.add("BACKGROUND_JOB")
            if _rc1_stateful_database_companion(request): contexts.add("DATABASE"); task_contexts.add("DATABASE")
        elif concept=="SEO_WEB_DISCOVERABILITY": task_contexts.add("SEO_WEB_DISCOVERABILITY")
        else: continue
        evidence.append({"trigger":"RC1_CONCEPT:"+concept,"reason":"deterministic canonical concept detected","source":"rc1_additive","concept_evidence":observation.get("evidence",[])})
'''

SUPPLIER_ADAPTER = r'''
        # RC-1 compatibility: v1.4 has an EXTERNAL_SUPPLIER pack but no request
        # trigger selecting it from EXTERNAL_SAAS alone.
        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(request):
            selected=set(result.get("required_context_packs",[])); selected.add("EXTERNAL_SUPPLIER")
            result["required_context_packs"]=sorted(selected)
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count=text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected anchor exactly once, found {count}")
    return text.replace(old,new,1)


def build(source: str) -> str:
    if MARKER in source:
        raise SystemExit("source already contains RC-1 integration marker")

    marker="# ---------- request → engineering task plan ----------\n"
    source=replace_once(source,marker,HELPERS+marker,"helper insertion")

    request_anchor='    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"\n'
    source=replace_once(source,request_anchor,REQUEST_ENRICHMENT+request_anchor,"request adapter")

    assess_anchor='        result=module.assess_workflow(matrix,normalized,packs)\n'
    source=replace_once(source,assess_anchor,assess_anchor+SUPPLIER_ADAPTER,"supplier adapter")
    return source


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="sef.py")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    source=Path(args.input).read_text(encoding="utf-8")
    result=build(source)
    Path(args.output).write_text(result,encoding="utf-8")
    print(f"generated {args.output}: {len(result)} bytes; marker={MARKER}")
    return 0

if __name__=="__main__": raise SystemExit(main())
