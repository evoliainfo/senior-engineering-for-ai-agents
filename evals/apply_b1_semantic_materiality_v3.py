#!/usr/bin/env python3
"""B1 candidate patcher v3: preserve explicit documentation non-goals from the original request."""
from __future__ import annotations

import argparse
from pathlib import Path

import apply_b1_semantic_materiality as v1
import apply_b1_semantic_materiality_v2 as v2


def corrected_helpers() -> str:
    helpers=v1.HELPERS
    old='''    doc_surface=bool(re.search(r"\\b(readme|documentation|docs?|documentation note|sentence|example)\\b",text,re.I))\n    explicit_nonchange=bool(re.search(\n        r"\\b(?:do not|don\'t|without|no)\\b.{0,90}\\b(?:change|modify|touch|edit|alter)\\b.{0,120}\\b(?:images?|dependencies|ci|pipeline|release|deployment|build|configuration|config)\\b",\n        text,re.I))'''
    new='''    doc_surface=bool(re.search(r"\\b(readme|documentation|docs?|documentation note|sentence|example)\\b",original,re.I))\n    explicit_nonchange=bool(re.search(\n        r"\\b(?:do not|don\'t|without|no)\\b.{0,90}\\b(?:change|modify|touch|edit|alter)\\b.{0,120}\\b(?:images?|dependencies|ci|pipeline|release|deployment|build|configuration|config)\\b",\n        original,re.I))'''
    if helpers.count(old)!=1:
        raise SystemExit(f"documentation helper anchor mismatch: {helpers.count(old)}")
    return helpers.replace(old,new,1)


def build(source: str) -> str:
    original=v1.HELPERS
    try:
        v1.HELPERS=corrected_helpers()
        return v2.build(source)
    finally:
        v1.HELPERS=original


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output",required=True); p.add_argument("--allow-input-sha",default=v1.EXPECTED_INPUT_SHA256); a=p.parse_args()
    inp=Path(a.input); raw=inp.read_bytes(); actual=v1.sha256(raw)
    if actual!=a.allow_input_sha: raise SystemExit(f"unexpected input SHA-256: {actual}; expected {a.allow_input_sha}")
    candidate=build(raw.decode("utf-8")); Path(a.output).write_text(candidate,encoding="utf-8")
    print(f"input_sha256={actual}"); print(f"candidate_sha256={v1.sha256(candidate.encode('utf-8'))}")
    return 0

if __name__=="__main__": raise SystemExit(main())
