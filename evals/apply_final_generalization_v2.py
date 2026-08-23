#!/usr/bin/env python3
"""Calibrated second build of the single final-remediation architecture.

This does not add new root causes. It tightens materiality boundaries exposed by
negative controls after the first candidate build: content-only security copy,
positive prohibitive authorization requirements, and arithmetic-only finance.
"""
from __future__ import annotations
import argparse, hashlib, subprocess, sys, tempfile
from pathlib import Path

V1_SHA="4a610cbb40a8ff0e1b59a3244cbf1a430adf553323aebeae0a486e6b89ce3ff8"
ROOT=Path(__file__).resolve().parent

def digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def replace_once(text:str,old:str,new:str,label:str)->str:
    n=text.count(old)
    if n!=1: raise RuntimeError(f"{label}: expected one match, found {n}")
    return text.replace(old,new,1)
def insert_after(text:str,anchor:str,addition:str,label:str)->str:
    return replace_once(text,anchor,anchor+addition,label)

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--source',default='sef.py'); p.add_argument('--output',required=True); a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='sef-final-v2-') as tmp:
        v1=Path(tmp)/'v1.py'
        cp=subprocess.run([sys.executable,str(ROOT/'apply_final_generalization.py'),'--source',a.source,'--output',str(v1)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        if cp.returncode!=0: raise SystemExit(cp.stderr or cp.stdout)
        got=digest(v1)
        if got!=V1_SHA: raise SystemExit(f'unexpected v1 candidate {got}')
        text=v1.read_text(encoding='utf-8')

    content_anchor='''    documentation_only=doc_surface and explicit_nonchange\n'''
    content_add='''    content_surface=bool(re.search(r"\\b(?:marketing|pricing|public|documentation|docs?|guide|readme)\\b.{0,70}\\b(?:copy|wording|text|sentence|heading|content|page)\\b|\\b(?:copy|wording|text|sentence|heading)\\b",original,re.I))
    content_only_cue=bool(re.search(r"\\b(?:wording|copy|text|sentence|heading|content|documentation)\\s+only\\b|\\bonly\\s+(?:wording|copy|text|sentence|heading|content|documentation)\\b",original,re.I))
    content_only=content_surface and content_only_cue
'''
    text=insert_after(text,content_anchor,content_add,'content-only materiality')

    return_anchor='''      "documentation_only":documentation_only,\n'''
    text=insert_after(text,return_anchor,'      "content_only":content_only,\n','content-only observation')

    auth_old='''    if hit(r"\\b(oauth|oidc|openid|google login|connexion google|sign[ -]?in|log[ -]?in|login|connexion|authentification|authentication|session|jwt)\\b"):\n'''
    auth_new='''    if hit(r"\\b(oauth|oidc|openid|google login|connexion google|sign[ -]?in|log[ -]?in|login|connexion|authentification|authentication|session|jwt)\\b") and not b1_observation.get("content_only"):\n'''
    text=replace_once(text,auth_old,auth_new,'content-only auth protocol suppression')
    authz_old='''    if hit(r"\\b(permission|permissions|rôle|rôles|role|roles|rbac|authori[sz]|autorisation|admin|propriétaire|owner|contrôle d.access|access control)\\b"): add("AUTHZ_CHANGED","authorization/role semantics in request")\n'''
    authz_new='''    if hit(r"\\b(permission|permissions|rôle|rôles|role|roles|rbac|authori[sz]|autorisation|admin|propriétaire|owner|contrôle d.access|access control)\\b") and not b1_observation.get("content_only"): add("AUTHZ_CHANGED","authorization/role semantics in request")\n'''
    text=replace_once(text,authz_old,authz_new,'content-only authz suppression')

    rc1_old='''        if concept=="AUTHORIZATION": triggers.add("AUTHZ_CHANGED")\n'''
    rc1_new='''        if concept=="AUTHORIZATION":
            if b1_observation.get("content_only"): continue
            triggers.add("AUTHZ_CHANGED")
'''
    text=replace_once(text,rc1_old,rc1_new,'content-only RC1 suppression')

    boundary_anchor='''        add("BUSINESS_OBJECT_AUTHORIZATION","AUTHORIZATION","R3","resource access must be authorized against the caller's business partition rather than caller-supplied scope")\n'''
    boundary_add='''

    # A real prohibitive access invariant remains positive intent. This protects
    # polarity filtering from laundering "unauthorized users must not access" into
    # a non-goal while still allowing "do not implement permissions" to disappear.
    unauthorized_subject=has(r"\\bunauthori[sz]ed\\s+(?:users?|callers?|clients?|actors?|operators?)\\b")
    explicit_denial=has(r"\\b(?:must not|cannot|may not|shall not|are not allowed to|is not allowed to)\\b.{0,70}\\b(?:access|read|view|download|export|edit|delete|retrieve)\\w*\\b")
    if unauthorized_subject and explicit_denial:
        add("EXPLICIT_AUTHORIZATION_DENIAL","AUTHORIZATION","R3","explicit denial for unauthorized actors is a material authorization requirement")
'''
    text=insert_after(text,boundary_anchor,boundary_add,'positive prohibitive authorization')

    regulated_old='''    if high_impact_domain and high_impact_decision:\n        add("HIGH_IMPACT_REGULATED_DECISION","REGULATED_DOMAIN","R3","software is asked to make or recommend a consequential regulated/high-impact decision")\n        human_decisions.add("REGULATED_DOMAIN")\n'''
    regulated_new='''    arithmetic_surface=bool(re.search(r"\\b(?:calculator|calculate|calculation|arithmetic|repayment|monthly payment|payment estimate|amortization)\\b",original,re.I))
    decision_disclaimed=bool(re.search(r"\\b(?:do not|don't|does not|will not|no)\\b.{0,110}\\b(?:determine\\s+eligibility|approve|approval|decline|deny|denial|recommend|underwrite)\\b",original,re.I))
    if high_impact_domain and high_impact_decision and not (arithmetic_surface and decision_disclaimed):
        add("HIGH_IMPACT_REGULATED_DECISION","REGULATED_DOMAIN","R3","software is asked to make or recommend a consequential regulated/high-impact decision")
        human_decisions.add("REGULATED_DOMAIN")
'''
    text=replace_once(text,regulated_old,regulated_new,'arithmetic regulated materiality guard')

    out=Path(a.output); out.write_text(text,encoding='utf-8'); print(digest(out)); return 0
if __name__=='__main__': raise SystemExit(main())
