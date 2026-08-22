#!/usr/bin/env python3
"""RC-2 shadow-only request polarity annotator.

This module NEVER changes SEF routing. It produces diagnostic observations used to
validate clause-local non-goal detection before any behavioral integration.
"""
from __future__ import annotations
import json, re, sys

BOUNDARY_RE = re.compile(r"\s*(?:[;.!?]+|\bbut\b|\bmais\b)\s*", re.I)

# Explicit bounded non-goal constructions. We deliberately do not treat generic
# prohibitions such as "users cannot access" or "must not expose" as non-goals.
NON_GOAL_PATTERNS = [
    ("do_not_change", re.compile(r"\b(?:do not|don't)\s+(?:change|modify|touch)\b", re.I)),
    ("without_change", re.compile(r"\bwithout\s+(?:changing|modifying|touching)\b", re.I)),
    ("leave_unchanged", re.compile(r"\b(?:leave|keep)\b.+?\bunchanged\b", re.I)),
    ("no_changes_to", re.compile(r"\bno\s+changes?\s+to\b", re.I)),
    ("out_of_scope", re.compile(r"\b(?:out of scope|not in scope)\b", re.I)),
    ("fr_sans_changer", re.compile(r"\bsans\s+(?:changer|modifier|toucher)\b", re.I)),
    ("fr_unchanged", re.compile(r"\b(?:laisser|garder)\b.+?\binchang[ée]s?\b", re.I)),
    ("fr_no_change", re.compile(r"\baucun\s+changement\b", re.I)),
    ("fr_out_of_scope", re.compile(r"\bhors\s+p[ée]rim[èe]tre\b", re.I)),
]

# Guard constructions that look negative lexically but express a positive
# engineering obligation. They are observed, never suppressed.
POSITIVE_GUARDS = [
    ("do_not_forget", re.compile(r"\b(?:do not|don't)\s+forget\b", re.I)),
    ("cannot_leave_unchanged", re.compile(r"\bcannot\s+(?:leave|keep)\b.+?\bunchanged\b", re.I)),
    ("prohibitive_requirement", re.compile(r"\b(?:must not|cannot|may not)\b", re.I)),
    ("no_actor_may", re.compile(r"\bno\s+.+?\bmay\b", re.I)),
    ("without_is_unsafe", re.compile(r"\bwithout\b.+?\b(?:unsafe|insecure|vulnerable)\b", re.I)),
]

def clauses(text: str):
    out=[]; start=0
    for m in BOUNDARY_RE.finditer(text):
        chunk=text[start:m.start()].strip(" ,")
        if chunk: out.append((start,m.start(),chunk))
        start=m.end()
    chunk=text[start:].strip(" ,")
    if chunk: out.append((start,len(text),chunk))
    return out

def annotate(text: str):
    observations=[]
    for start,end,clause in clauses(text):
        guards=[name for name,rx in POSITIVE_GUARDS if rx.search(clause)]
        matches=[]
        if not guards:
            for name,rx in NON_GOAL_PATTERNS:
                m=rx.search(clause)
                if m:
                    matches.append({"cue":name,"span":[start+m.start(),start+m.end()],"text":m.group(0)})
        polarity="NON_GOAL" if matches else ("POSITIVE_GUARD" if guards else "UNMARKED")
        observations.append({"span":[start,end],"clause":clause,"polarity":polarity,"cues":matches,"guards":guards})
    return {"request":text,"clauses":observations,"shadow_only":True}

def main():
    text=" ".join(sys.argv[1:]).strip() if len(sys.argv)>1 else sys.stdin.read().strip()
    print(json.dumps(annotate(text),ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
