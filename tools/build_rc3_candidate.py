#!/usr/bin/env python3
"""Build an isolated RC-3 candidate from canonical sef.py for evaluation only.

The generated candidate changes only plan-time promotion of unresolved
MULTI_TENANT context. It does not mutate project facts or actual-diff routing.
"""
from pathlib import Path
import sys

src=Path(sys.argv[1] if len(sys.argv)>1 else 'sef.py')
out=Path(sys.argv[2] if len(sys.argv)>2 else 'artifacts/rc3-candidate/sef_candidate.py')
text=src.read_text(encoding='utf-8')
marker='# ---------- request → engineering task plan ----------'
helper=r'''
# ---------- RC-3 candidate task-materiality projection ----------
_RC3_ACTOR=r"(?:tenant|organization|organisation|workspace|customer|company|account)"
_RC3_ACTORS=r"(?:tenants|organizations|organisations|workspaces|customers|companies|accounts)"
_RC3_RESOURCE=r"(?:data|records?|objects?|files?|documents?|storage|prefix(?:es)?|cache(?:\s+(?:entries|keys))?|queries|reads?|jobs?|queues?|processing|metrics?)"
_RC3_MATERIAL_PATTERNS=(
  re.compile(rf"\b(?:separate|separately|isolat(?:e|ed|ion)|partition(?:ed|ing)?)\b.{{0,90}}\b(?:{_RC3_ACTOR}|{_RC3_ACTORS})\b",re.I),
  re.compile(rf"\b{_RC3_ACTOR}[- ](?:scoped|aware|specific|isolated|partitioned)\b",re.I),
  re.compile(rf"\bper[- ]{_RC3_ACTOR}\b",re.I),
  re.compile(rf"\b(?:for\s+)?(?:each|every)\s+{_RC3_ACTOR}\b",re.I),
  re.compile(rf"\b(?:own|owning|active)\s+{_RC3_ACTOR}\b",re.I),
  re.compile(rf"\b{_RC3_RESOURCE}\b.{{0,55}}\b(?:by|to|according to|for)\b.{{0,25}}\b(?:the\s+)?(?:owning|active|selected|target)?\s*{_RC3_ACTOR}\b",re.I),
  re.compile(rf"\b{_RC3_ACTOR}\b.{{0,55}}\b(?:only|own)\b.{{0,35}}\b{_RC3_RESOURCE}\b",re.I),
  re.compile(rf"\b(?:switch|change)\b.{{0,40}}\b(?:between|across|from|to)\b.{{0,45}}\b(?:{_RC3_ACTOR}|{_RC3_ACTORS})\b",re.I),
  re.compile(rf"\b(?:selected|target|active)\s+{_RC3_ACTOR}\b",re.I),
  re.compile(rf"\bcross[- ]{_RC3_ACTOR}\b|\bacross\s+(?:tenant|organization|organisation|workspace|company)\s+boundar(?:y|ies)\b",re.I),
  re.compile(rf"\b(?:prevent|without|cannot|can't|must not)\b.{{0,80}}\b(?:leak|mix|access|address)\w*\b.{{0,80}}\b(?:{_RC3_ACTOR}|{_RC3_ACTORS})\b",re.I),
  re.compile(rf"\b(?:multiple|different)\s+{_RC3_ACTORS}\b",re.I),
)
_RC3_PROJECT_ONLY_PATTERNS=(
  re.compile(r"\bpublic\b.{0,55}\b(?:marketing|company|brochure|landing|pricing|contact|website|site|page|homepage|blog|footer|documentation|docs?)\b",re.I),
  re.compile(r"\b(?:seo|sitemap|robots\.txt|canonical metadata|title tags?|metadata|search engine|discoverable in search)\b",re.I),
  re.compile(r"\b(?:typography|copy|footer|legal links?|hero illustration|spacing|font sizes?|copyright notice|marketing image|public image|blog article|documentation copy|docs? copy)\b",re.I),
  re.compile(r"\b(?:local|pure|deterministic)\b.{0,45}\b(?:utilit(?:y|ies)|helper)\b",re.I),
)
_RC3_AMBIGUOUS_PATTERNS=(
  re.compile(rf"\b{_RC3_ACTOR}\b",re.I),
  re.compile(r"\b(?:dashboard|settings|preferences|administration|management)\b",re.I),
)
def _rc3_multitenant_materiality(request):
    text=str(request or '')
    if any(rx.search(text) for rx in _RC3_MATERIAL_PATTERNS): return 'TASK_MATERIAL'
    if any(rx.search(text) for rx in _RC3_PROJECT_ONLY_PATTERNS): return 'PROJECT_ONLY'
    if any(rx.search(text) for rx in _RC3_AMBIGUOUS_PATTERNS): return 'UNCERTAIN'
    return 'PROJECT_ONLY'
'''
if marker not in text: raise SystemExit('RC-3 insertion marker not found')
text=text.replace(marker,helper+'\n'+marker,1)
old='''    human_decisions=sorted(set(\n        [c.get("context") for c in project_profile.get("context_candidates",[]) if c.get("context") in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))'''
new='''    human_decisions=sorted(set(\n        [c.get("context") for c in project_profile.get("context_candidates",[]) if c.get("context") in MATERIAL_CONFIRMATIONS]\n        + [ctx for ctx in baseline.get("discovery",{}).get("context_confirmations_needed",[]) if ctx in MATERIAL_CONFIRMATIONS]\n    ))\n    rc3_materiality=_rc3_multitenant_materiality(request) if "MULTI_TENANT" in human_decisions else None\n    if rc3_materiality=="PROJECT_ONLY":\n        human_decisions=[ctx for ctx in human_decisions if ctx!="MULTI_TENANT"]'''
if old not in text: raise SystemExit('RC-3 human decision block not found')
text=text.replace(old,new,1)
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(text,encoding='utf-8')
print(out)
