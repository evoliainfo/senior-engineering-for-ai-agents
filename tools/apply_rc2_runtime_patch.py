#!/usr/bin/env python3
"""One-shot canonical RC-2 integration patcher.

Applies the already validated RC-2 candidate behavior to root sef.py and updates
SHA256SUMS. The script is intentionally strict and aborts if expected source
anchors are not unique. Remove this helper before merging the runtime PR.
"""
from __future__ import annotations
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
SEF=ROOT/'sef.py'
SUMS=ROOT/'SHA256SUMS'
text=SEF.read_text(encoding='utf-8')

helper='''\n# ---------- RC-2 request polarity / bounded non-goals ----------\n_RC2_BOUNDARY_RE=re.compile(r"\\s*(?:[;.!?]+|\\bbut\\b|\\bmais\\b)\\s*",re.I)\n_RC2_NON_GOAL_PATTERNS=(\n  ("do_not_change",re.compile(r"\\b(?:do not|don't)\\s+(?:change|modify|touch)\\b",re.I)),\n  ("without_change",re.compile(r"\\bwithout\\s+(?:changing|modifying|touching)\\b",re.I)),\n  ("leave_unchanged",re.compile(r"\\b(?:leave|keep)\\b.+?\\bunchanged\\b",re.I)),\n  ("no_changes_to",re.compile(r"\\bno\\s+changes?\\s+to\\b",re.I)),\n  ("no_modifications_to",re.compile(r"\\bno\\s+modifications?\\s+to\\b",re.I)),\n  ("out_of_scope",re.compile(r"\\b(?:out of scope|not in scope)\\b",re.I)),\n  ("fr_sans_changer",re.compile(r"\\bsans\\s+(?:changer|modifier|toucher)\\b",re.I)),\n  ("fr_unchanged",re.compile(r"\\b(?:laisser|garder)\\b.+?\\binchang[ée]s?\\b",re.I)),\n  ("fr_no_change",re.compile(r"\\baucun\\s+changement\\b",re.I)),\n  ("fr_out_of_scope",re.compile(r"\\bhors\\s+p[ée]rim[èe]tre\\b",re.I)),\n)\n_RC2_POSITIVE_GUARDS=(\n  ("do_not_forget",re.compile(r"\\b(?:do not|don't)\\s+forget\\b",re.I)),\n  ("cannot_leave_unchanged",re.compile(r"\\bcannot\\s+(?:leave|keep)\\b.+?\\bunchanged\\b",re.I)),\n  ("prohibitive_requirement",re.compile(r"\\b(?:must not|cannot|may not)\\b",re.I)),\n  ("no_actor_may",re.compile(r"\\bno\\s+.+?\\bmay\\b",re.I)),\n  ("without_is_unsafe",re.compile(r"\\bwithout\\b.+?\\b(?:unsafe|insecure|vulnerable)\\b",re.I)),\n)\n\ndef _rc2_clauses(text):\n    out=[]; start=0\n    for m in _RC2_BOUNDARY_RE.finditer(str(text or "")):\n        chunk=str(text or "")[start:m.start()].strip(" ,")\n        if chunk: out.append((start,m.start(),chunk))\n        start=m.end()\n    raw=str(text or ""); chunk=raw[start:].strip(" ,")\n    if chunk: out.append((start,len(raw),chunk))\n    return out\n\ndef _rc2_annotate(request):\n    observations=[]\n    for start,end,clause in _rc2_clauses(request):\n        guards=[name for name,rx in _RC2_POSITIVE_GUARDS if rx.search(clause)]\n        matches=[]\n        if not guards:\n            for name,rx in _RC2_NON_GOAL_PATTERNS:\n                m=rx.search(clause)\n                if m: matches.append({"cue":name,"span":[start+m.start(),start+m.end()],"text":m.group(0)})\n        polarity="NON_GOAL" if matches else ("POSITIVE_GUARD" if guards else "UNMARKED")\n        observations.append({"span":[start,end],"clause":clause,"polarity":polarity,"cues":matches,"guards":guards})\n    return {"request":request,"clauses":observations,"shadow_only":False}\n\ndef _rc2_positive_request_text(request):\n    observation=_rc2_annotate(request); kept=[]; suppressed=[]\n    for clause in observation.get("clauses",[]):\n        value=str(clause.get("clause") or "").strip()\n        if not value: continue\n        if clause.get("polarity")=="NON_GOAL": suppressed.append(value)\n        else: kept.append(value)\n    return "; ".join(kept),suppressed,observation\n'''

anchor='# ---------- request → engineering task plan ----------\n'
if text.count(anchor)!=1: raise SystemExit(f'expected one request-plan anchor, got {text.count(anchor)}')
if '_RC2_BOUNDARY_RE=' not in text:
    text=text.replace(anchor,helper+'\n'+anchor,1)
else:
    raise SystemExit('RC-2 helper already present; refusing to reapply')

old='''def _request_change(profile,request):\n    t=request.lower(); triggers=set(); contexts=set(profile.get("contexts",[])); task_contexts=set(); profiles=set(profile.get("profiles",[])); evidence=[]\n'''
new='''def _request_change(profile,request):\n    original_request=request\n    request,rc2_suppressed,rc2_observation=_rc2_positive_request_text(request)\n    t=request.lower(); triggers=set(); contexts=set(profile.get("contexts",[])); task_contexts=set(); profiles=set(profile.get("profiles",[])); evidence=[]\n'''
if text.count(old)!=1: raise SystemExit(f'expected one request_change start, got {text.count(old)}')
text=text.replace(old,new,1)

risk_anchor='''    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"\n'''
risk_insert='''    if rc2_suppressed:\n        evidence.append({"trigger":"RC2_POLARITY_FILTER","reason":"bounded request non-goal excluded from request-derived routing","source":"rc2_canonical","suppressed_clauses":rc2_suppressed,"polarity_observation":rc2_observation})\n    risk="R0" if triggers=={"UI_STYLE_CHANGED"} else "R1"\n'''
if text.count(risk_anchor)!=1: raise SystemExit(f'expected one risk anchor, got {text.count(risk_anchor)}')
text=text.replace(risk_anchor,risk_insert,1)

return_old='''    return {"summary":request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence}\n'''
return_new='''    return {"summary":original_request,"risk":risk,"action_class":"A1","contexts":sorted(contexts),"execution_contexts":sorted(task_contexts),"triggers":sorted(triggers),"profiles":sorted(profiles),"environment":"LOCAL","request_detection":evidence}\n'''
if text.count(return_old)!=1: raise SystemExit(f'expected one request return, got {text.count(return_old)}')
text=text.replace(return_old,return_new,1)

supplier_old='''        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(request):\n'''
supplier_new='''        rc2_positive_request,_,_=_rc2_positive_request_text(request)\n        if "EXTERNAL_SUPPLIER" in _rc1_detected_ids(rc2_positive_request):\n'''
if text.count(supplier_old)!=1: raise SystemExit(f'expected one external supplier compatibility anchor, got {text.count(supplier_old)}')
text=text.replace(supplier_old,supplier_new,1)

SEF.write_text(text,encoding='utf-8')
digest=hashlib.sha256(SEF.read_bytes()).hexdigest()
SUMS.write_text(f'{digest}  sef.py\n',encoding='utf-8')
print('patched sef.py')
print('sha256',digest)
