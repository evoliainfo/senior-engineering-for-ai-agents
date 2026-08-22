#!/usr/bin/env python3
"""RC-1 shadow concept detector.

This module is intentionally non-authoritative: it emits concept observations and
matched evidence only. It does not mutate SEF triggers, contexts, packs, risk, or
routing decisions. Promotion into routing requires a separate reviewed change.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

SHADOW_VERSION = "rc1-shadow-v1"


def normalize_text(text: str) -> str:
    """Normalize request morphology without changing semantic polarity."""
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("’", "'").replace("‘", "'").replace("‐", "-").replace("‑", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


@dataclass(frozen=True)
class ConceptRule:
    concept: str
    output_kind: str
    output_id: str
    patterns: tuple[str, ...]


# Rules deliberately model concepts, not isolated keywords. Each positive rule
# requires either a specialist term or a compositional phrase carrying the same
# governed intent. This keeps lexical near-misses outside the shadow signal.
CONCEPT_RULES: tuple[ConceptRule, ...] = (
    ConceptRule(
        "AUTHORIZATION", "pack", "AUTHORIZATION",
        (
            r"\b(?:permission|permissions|rbac|access control|authorization|authorisation)\b",
            r"\b(?:authorized|authorised)\s+(?:administrator|admin|user|operator|person|role)\b",
            r"\bonly\s+(?:an?\s+)?(?:authorized|authorised)\s+(?:administrator|admin|user|operator|person|role)\b",
        ),
    ),
    ConceptRule(
        "DATABASE_MIGRATION", "pack", "DATABASE_MIGRATION",
        (
            r"\bdatabase\s+migration\b",
            r"\bmigrat(?:e|es|ed|ing)\b.{0,80}\b(?:existing|stored|records?|rows?|timestamps?|data|database)\b",
            r"\b(?:existing|stored|records?|rows?|timestamps?|data|database)\b.{0,80}\bmigrat(?:e|es|ed|ing)\b",
        ),
    ),
    ConceptRule(
        "WEBHOOK_TRUST", "pack", "WEBHOOK_TRUST",
        (
            r"\bwebhook(?:s)?\b.{0,100}\b(?:receive|receives|received|accept|accepts|inbound|event|events|provider|callback)\b",
            r"\b(?:receive|receives|accept|accepts|inbound)\b.{0,100}\bwebhook(?:s)?\b",
        ),
    ),
    ConceptRule(
        "EXTERNAL_SUPPLIER", "pack", "EXTERNAL_SUPPLIER",
        (
            r"\bexternal\s+api\b.{0,100}\b(?:supplied|provided|provider|vendor|third-party|third party)\b",
            r"\b(?:third-party|third party|external)\s+(?:saas\s+)?(?:vendor|provider|supplier|service|api)\b",
            r"\bdepend(?:s|ed|ing)?\s+on\b.{0,80}\b(?:third-party|third party|external)\b",
        ),
    ),
    ConceptRule(
        "BACKGROUND_JOB", "execution_context", "BACKGROUND_JOB",
        (
            r"\bqueue\s+consumer\b.{0,100}\b(?:job|jobs|async|asynchronously|retry|retries|retryable)\b",
            r"\bworker\b.{0,100}\b(?:job|jobs|background|async|asynchronously|retry|retries)\b",
            r"\b(?:job|jobs)\b.{0,100}\b(?:background|asynchronously|queue\s+consumer|worker|retry|retries)\b",
        ),
    ),
    ConceptRule(
        "SEO_WEB_DISCOVERABILITY", "execution_context", "SEO_WEB_DISCOVERABILITY",
        (
            r"\bseo\b.{0,120}\b(?:public|page|search engine|index|indexing|indexation|crawl|discover)\b",
            r"\b(?:public\s+)?(?:product\s+)?page\b.{0,120}\b(?:search engines?|search engine)\b.{0,80}\b(?:find|index|discover|crawl)\w*\b",
            r"\b(?:find|discover)\w*\b.{0,80}\bthrough\s+search\s+engines?\b",
        ),
    ),
)


def detect_concepts(request: str) -> dict:
    normalized = normalize_text(request)
    observations = []
    for rule in CONCEPT_RULES:
        matches = []
        for pattern in rule.patterns:
            m = re.search(pattern, normalized, re.I)
            if m:
                matches.append({
                    "pattern": pattern,
                    "match": m.group(0),
                    "span": [m.start(), m.end()],
                })
        if matches:
            observations.append({
                "concept": rule.concept,
                "candidate_output": {"kind": rule.output_kind, "id": rule.output_id},
                "evidence": matches,
            })
    return {
        "mode": "SHADOW_ONLY",
        "version": SHADOW_VERSION,
        "request": request,
        "normalized_request": normalized,
        "observations": observations,
        "candidate_outputs": [o["candidate_output"] for o in observations],
        "routing_effect": "NONE",
    }


def detected_ids(result: dict) -> set[str]:
    return {str(x.get("id")) for x in result.get("candidate_outputs", [])}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="RC-1 shadow-only concept detector")
    parser.add_argument("request", nargs="+")
    args = parser.parse_args()
    print(json.dumps(detect_concepts(" ".join(args.request)), ensure_ascii=False, indent=2))
