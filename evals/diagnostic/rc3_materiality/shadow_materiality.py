#!/usr/bin/env python3
"""RC-3 shadow-only task materiality classifier for MULTI_TENANT.

Diagnostic only. This module never changes SEF planning, routing, project facts,
or implementation gates.
"""
from __future__ import annotations
import json, re, sys

# Strong task-local evidence that the requested change crosses or creates a
# tenant/organization boundary. Broad project nouns alone are intentionally not
# enough.
MATERIAL_PATTERNS = [
    ("separate_tenant_data", re.compile(r"\b(?:separate|isolat(?:e|ed|ion)|partition(?:ed|ing)?)\b.{0,55}\b(?:customer|tenant|organization|organisation|workspace|company)\b.{0,35}\b(?:data|records?|storage|files?|keys?|queries?)\b", re.I)),
    ("tenant_scoped", re.compile(r"\b(?:tenant|organization|organisation|workspace|customer|company)[- ](?:scoped|aware|specific|isolated|partitioned)\b", re.I)),
    ("per_tenant", re.compile(r"\bper[- ](?:tenant|organization|organisation|workspace|customer|company)\b", re.I)),
    ("switch_tenant", re.compile(r"\bswitch\b.{0,35}\b(?:between|across)\b.{0,35}\b(?:companies|organizations|organisations|workspaces|tenants)\b", re.I)),
    ("selected_tenant", re.compile(r"\b(?:selected|target)\s+(?:tenant|organization|organisation|workspace|company)\b", re.I)),
    ("cross_tenant", re.compile(r"\bcross[- ](?:tenant|organization|organisation|workspace|company)\b", re.I)),
    ("workspace_keys", re.compile(r"\b(?:cache|storage|database|file|query|queries)\b.{0,45}\b(?:workspace|tenant|organization|organisation|customer)[- ](?:scoped|partitioned|aware)\b", re.I)),
    ("multi_org_boundary", re.compile(r"\b(?:multiple|different)\s+(?:organizations|organisations|companies|tenants|customers|workspaces)\b", re.I)),
]

# Clearly public/presentation/local work where a project-level MULTI_TENANT
# candidate is not material to the requested implementation.
PROJECT_ONLY_PATTERNS = [
    ("public_marketing", re.compile(r"\bpublic\b.{0,45}\b(?:marketing|company|brochure|landing|website|site|page|blog|footer|documentation|docs?)\b", re.I)),
    ("seo_public", re.compile(r"\b(?:seo|sitemap|metadata|search engine|discoverable in search)\b", re.I)),
    ("presentation_only", re.compile(r"\b(?:typography|copy|footer|legal links?|marketing image|public image|blog article|documentation copy|docs? copy)\b", re.I)),
    ("local_pure_utility", re.compile(r"\b(?:local|pure)\b.{0,30}\butilit(?:y|ies)\b", re.I)),
]

# Broad tenant-ish nouns with no boundary semantics are deliberately uncertain.
AMBIGUOUS_PATTERNS = [
    ("broad_org_noun", re.compile(r"\b(?:company|organization|organisation|workspace|tenant)\b", re.I)),
    ("management_surface", re.compile(r"\b(?:dashboard|settings|management)\b", re.I)),
]

def classify(request: str, project_brief: str = ""):
    text=request.strip()
    material=[name for name,rx in MATERIAL_PATTERNS if rx.search(text)]
    project_only=[name for name,rx in PROJECT_ONLY_PATTERNS if rx.search(text)]
    ambiguous=[name for name,rx in AMBIGUOUS_PATTERNS if rx.search(text)]
    if material:
        label="TASK_MATERIAL"
        signals=material
    elif project_only:
        label="PROJECT_ONLY"
        signals=project_only
    elif ambiguous:
        label="UNCERTAIN"
        signals=ambiguous
    else:
        # No task-local tenant signal: the project candidate remains visible but
        # there is no evidence that the current task materially depends on it.
        label="PROJECT_ONLY"
        signals=["no_task_local_tenant_boundary_signal"]
    return {
        "context":"MULTI_TENANT",
        "project_candidate": bool(re.search(r"\b(?:company|organization|organisation|workspace|team|b2b|tenant)\b", project_brief, re.I)),
        "task_materiality": label,
        "signals": signals,
        "blocking_shadow": label in {"TASK_MATERIAL","UNCERTAIN"},
        "shadow_only": True,
        "routing_effect":"NONE",
        "request": request,
    }

def main():
    if len(sys.argv)>1:
        request=" ".join(sys.argv[1:])
        project=""
    else:
        payload=json.load(sys.stdin)
        request=payload.get("request","")
        project=payload.get("project_brief","")
    print(json.dumps(classify(request,project),ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
