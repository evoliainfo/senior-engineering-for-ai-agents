#!/usr/bin/env python3
"""RC-3 shadow-only task materiality classifier for MULTI_TENANT.

Diagnostic only. This module never changes SEF planning, routing, project facts,
or implementation gates.
"""
from __future__ import annotations
import json, re, sys

ACTOR = r"(?:tenant|organization|organisation|workspace|customer|company|account)"
ACTORS = r"(?:tenants|organizations|organisations|workspaces|customers|companies|accounts)"
RESOURCE = r"(?:data|records?|objects?|files?|documents?|storage|prefix(?:es)?|cache(?:\s+(?:entries|keys))?|queries|reads?|jobs?|queues?|processing|metrics?)"

# Strong task-local evidence that the requested change crosses, isolates, scopes,
# or partitions an organization/account boundary. These are semantic boundary
# constructions rather than bare project nouns.
MATERIAL_PATTERNS = [
    ("separate_boundary", re.compile(rf"\b(?:separate|separately|isolat(?:e|ed|ion)|partition(?:ed|ing)?)\b.{{0,90}}\b(?:{ACTOR}|{ACTORS})\b", re.I)),
    ("tenant_scoped", re.compile(rf"\b{ACTOR}[- ](?:scoped|aware|specific|isolated|partitioned)\b", re.I)),
    ("per_tenant", re.compile(rf"\bper[- ]{ACTOR}\b", re.I)),
    ("each_tenant", re.compile(rf"\b(?:for\s+)?(?:each|every)\s+{ACTOR}\b", re.I)),
    ("own_tenant", re.compile(rf"\b(?:own|owning|active)\s+{ACTOR}\b", re.I)),
    ("resource_to_boundary", re.compile(rf"\b{RESOURCE}\b.{{0,55}}\b(?:by|to|according to|for)\b.{{0,25}}\b(?:the\s+)?(?:owning|active|selected|target)?\s*{ACTOR}\b", re.I)),
    ("boundary_to_resource", re.compile(rf"\b{ACTOR}\b.{{0,55}}\b(?:only|own)\b.{{0,35}}\b{RESOURCE}\b", re.I)),
    ("switch_tenant", re.compile(rf"\b(?:switch|change)\b.{{0,40}}\b(?:between|across|from|to)\b.{{0,45}}\b(?:{ACTOR}|{ACTORS})\b", re.I)),
    ("selected_tenant", re.compile(rf"\b(?:selected|target|active)\s+{ACTOR}\b", re.I)),
    ("cross_tenant", re.compile(rf"\bcross[- ]{ACTOR}\b|\bacross\s+(?:tenant|organization|organisation|workspace|company)\s+boundar(?:y|ies)\b", re.I)),
    ("prevent_boundary_leak", re.compile(rf"\b(?:prevent|without|cannot|can't|must not)\b.{{0,80}}\b(?:leak|mix|access|address)\w*\b.{{0,80}}\b(?:{ACTOR}|{ACTORS})\b", re.I)),
    ("one_another", re.compile(rf"\b(?:one|another)\s+{ACTOR}\b.{{0,80}}\b(?:another|other)\b", re.I)),
    ("multi_org_boundary", re.compile(rf"\b(?:multiple|different)\s+{ACTORS}\b", re.I)),
]

PROJECT_ONLY_PATTERNS = [
    ("public_marketing", re.compile(r"\bpublic\b.{0,55}\b(?:marketing|company|brochure|landing|pricing|contact|website|site|page|homepage|blog|footer|documentation|docs?)\b", re.I)),
    ("seo_public", re.compile(r"\b(?:seo|sitemap|robots\.txt|canonical metadata|title tags?|metadata|search engine|discoverable in search)\b", re.I)),
    ("presentation_only", re.compile(r"\b(?:typography|copy|footer|legal links?|hero illustration|spacing|font sizes?|copyright notice|marketing image|public image|blog article|documentation copy|docs? copy)\b", re.I)),
    ("local_pure_utility", re.compile(r"\b(?:local|pure|deterministic)\b.{0,45}\b(?:utilit(?:y|ies)|helper)\b", re.I)),
]

AMBIGUOUS_PATTERNS = [
    ("broad_org_noun", re.compile(rf"\b{ACTOR}\b", re.I)),
    ("management_surface", re.compile(r"\b(?:dashboard|settings|preferences|administration|management)\b", re.I)),
]

def classify(request: str, project_brief: str = ""):
    text=request.strip()
    material=[name for name,rx in MATERIAL_PATTERNS if rx.search(text)]
    project_only=[name for name,rx in PROJECT_ONLY_PATTERNS if rx.search(text)]
    ambiguous=[name for name,rx in AMBIGUOUS_PATTERNS if rx.search(text)]
    # Material evidence wins over presentation/public evidence so mixed requests
    # remain conservative: a public edit plus a tenant-boundary change is material.
    if material:
        label="TASK_MATERIAL"; signals=material
    elif project_only:
        label="PROJECT_ONLY"; signals=project_only
    elif ambiguous:
        label="UNCERTAIN"; signals=ambiguous
    else:
        label="PROJECT_ONLY"; signals=["no_task_local_tenant_boundary_signal"]
    return {
        "context":"MULTI_TENANT",
        "project_candidate": bool(re.search(r"\b(?:company|organization|organisation|workspace|team|b2b|tenant|customer|account)\b", project_brief, re.I)),
        "task_materiality":label,
        "signals":signals,
        "blocking_shadow":label in {"TASK_MATERIAL","UNCERTAIN"},
        "shadow_only":True,
        "routing_effect":"NONE",
        "request":request,
    }

def main():
    if len(sys.argv)>1:
        request=" ".join(sys.argv[1:]); project=""
    else:
        payload=json.load(sys.stdin); request=payload.get("request",""); project=payload.get("project_brief","")
    print(json.dumps(classify(request,project),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
