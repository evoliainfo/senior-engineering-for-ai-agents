#!/usr/bin/env python3
"""Final calibrated build of the single post-v2 remediation cycle.

The only added change versus v2 is a materiality guard: content-only page copy
must not be treated as an interactive UI behavior change merely because the word
"page" appears. Real form/button/modal/navigation/component changes remain routed.
"""
from __future__ import annotations
import argparse, hashlib, subprocess, sys, tempfile
from pathlib import Path

V2_SHA="3df4d96ce430018421af00033c916227d39d5b3e182540a7d3aae2c485a99bd5"
ROOT=Path(__file__).resolve().parent

def digest(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--source',default='sef.py'); p.add_argument('--output',required=True); a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='sef-final-calibrated-') as tmp:
        v2=Path(tmp)/'v2.py'
        cp=subprocess.run([sys.executable,str(ROOT/'apply_final_generalization_v2.py'),'--source',a.source,'--output',str(v2)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        if cp.returncode!=0: raise SystemExit(cp.stderr or cp.stdout)
        got=digest(v2)
        if got!=V2_SHA: raise SystemExit(f'unexpected v2 candidate {got}')
        text=v2.read_text(encoding='utf-8')
    old='''    if hit(r"\\b(form|formulaire|button|bouton|modal|dialog|dialogue|navigation|interactive ui|interface interactive|frontend feature|fonctionnalité frontend|frontend|front-end|page|component|composant|dashboard|tableau de bord)\\b"): add("UI_BEHAVIOR_CHANGED","interactive/frontend behavior requested",["WEB_UI"])\n'''
    new='''    if hit(r"\\b(form|formulaire|button|bouton|modal|dialog|dialogue|navigation|interactive ui|interface interactive|frontend feature|fonctionnalité frontend|frontend|front-end|page|component|composant|dashboard|tableau de bord)\\b") and not b1_observation.get("content_only"): add("UI_BEHAVIOR_CHANGED","interactive/frontend behavior requested",["WEB_UI"])\n'''
    count=text.count(old)
    if count!=1: raise SystemExit(f'UI behavior anchor count={count}')
    text=text.replace(old,new,1)
    out=Path(a.output); out.write_text(text,encoding='utf-8'); print(digest(out)); return 0
if __name__=='__main__': raise SystemExit(main())
