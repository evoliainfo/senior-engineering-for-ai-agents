#!/usr/bin/env python3
"""OpenAI Responses API adapter for Semantic Routing v2 development evaluation.

This provider has semantic authority only. It cannot emit governance packs, risk,
implementation approval, or release decisions. Model output is still validated by
``ModelAssistedExtractor`` before the deterministic policy composer sees it.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping


SEMANTIC_DEFINITIONS: dict[str, str] = {
    "ACCESS_CONTROL_BOUNDARY": "A material rule restricts which actor may read, create, update, delete, or otherwise act on a resource or object.",
    "PARTITION_ISOLATION": "Resources are separated into business or organizational scopes and access across those scopes is denied or isolated.",
    "AUTHENTICATION_PROTOCOL": "The change implements or materially changes an authentication protocol, identity exchange, or login/session establishment flow.",
    "SERVER_DESTINATION_TRUST": "The server or backend connects to a network destination whose location is controlled by a caller, user, tenant, customer, merchant, partner, or other external actor.",
    "EXTERNAL_OPERATIONAL_DEPENDENCY": "Correct operation materially depends on an independently operated external service whose outage, quota, API change, or deprecation can affect the system.",
    "CONSEQUENTIAL_DECISION": "A system or model decides, recommends, ranks, approves, rejects, or determines eligibility for a consequential outcome affecting a person, rights, access, employment, lending, insurance, housing, benefits, or similar high-impact opportunity. Pure arithmetic or informational calculators do not qualify by themselves.",
    "LIVE_DATA_TRANSFORMATION": "The change transforms, rewrites, migrates, backfills, or normalizes live persistent data used by an operating system or production-like service.",
    "CAPACITY_MATERIALITY": "Scale, throughput, volume, latency, storage, or cost is material enough to change engineering risk or execution strategy.",
    "PRODUCTION_RELEASE_CHANGE": "The change materially alters how software is deployed, published, progressively delivered, rolled out, or released to production.",
    "DEPLOYMENT_ARTIFACT": "The change materially alters a deployable container, image, package, artifact, or its runtime construction.",
    "BUILD_SUPPLY_CHAIN": "The change materially alters CI build provenance, dependencies, artifact integrity, signing, or software supply-chain behavior.",
    "UNTRUSTED_FILE_INPUT": "The system accepts or processes a file supplied by an untrusted or external actor and that file is material to security behavior.",
}

PROVIDER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["facts", "uncertainties", "complete"],
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "kind", "material", "subject", "object", "attributes", "provenance"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "kind": {"type": "string", "enum": sorted(SEMANTIC_DEFINITIONS)},
                    "material": {"type": "boolean"},
                    "subject": {"type": ["string", "null"]},
                    "object": {"type": ["string", "null"]},
                    "attributes": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["labels", "notes"],
                        "properties": {
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "provenance": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["source_kind", "locator", "confidence", "ambiguity"],
                            "properties": {
                                "source_kind": {"type": "string", "enum": ["request", "project_context"]},
                                "locator": {"type": "string", "minLength": 1},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "ambiguity": {"type": "string", "enum": ["none", "low", "medium", "high"]},
                            },
                        },
                    },
                },
            },
        },
        "uncertainties": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "relation_hint", "material", "state", "reason", "provenance"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "relation_hint": {"type": "string", "minLength": 1},
                    "material": {"type": "boolean"},
                    "state": {"type": "string", "enum": ["AMBIGUOUS", "UNAVAILABLE", "CONFLICT", "INVALID"]},
                    "reason": {"type": "string", "minLength": 1},
                    "provenance": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["source_kind", "locator", "confidence", "ambiguity"],
                            "properties": {
                                "source_kind": {"type": "string", "enum": ["request", "project_context"]},
                                "locator": {"type": "string", "minLength": 1},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "ambiguity": {"type": "string", "enum": ["none", "low", "medium", "high"]},
                            },
                        },
                    },
                },
            },
        },
        "complete": {"type": "boolean"},
    },
}


def _instructions(contract: Mapping[str, Any]) -> str:
    definitions = "\n".join(f"- {kind}: {description}" for kind, description in SEMANTIC_DEFINITIONS.items())
    return (
        "You are a semantic relation extractor for an engineering governance system. "
        "Return semantic facts and material uncertainty only. Never choose governance packs, risk, procedures, implementation approval, or release status. "
        "Infer relations from meaning, not from a noun whitelist. A business label by itself is not an access boundary; require an actual permission or isolation relation. "
        "A URL by itself is not server-destination trust; require a server/backend network action and external control of the destination. "
        "A regulated-sector noun by itself is not a consequential decision; distinguish arithmetic/informational tools from accept/reject/eligibility/recommendation outcomes. "
        "If a material relation is genuinely unresolved from the request and project context, set complete=false and emit an AMBIGUOUS uncertainty instead of guessing. "
        "Preserve important literal labels in attributes.labels and concise semantic evidence in attributes.notes.\n\n"
        "Allowed semantic fact definitions:\n"
        f"{definitions}\n\n"
        "Provider contract rules:\n"
        + "\n".join(f"- {rule}" for rule in contract.get("rules", []))
    )


def _extract_output_text(response: Mapping[str, Any]) -> str:
    for item in response.get("output", []) or []:
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, Mapping):
                continue
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return str(content["text"])
            if content.get("type") == "refusal":
                raise RuntimeError("OpenAI semantic provider refused the extraction request")
    raise RuntimeError("OpenAI response did not contain output_text")


class OpenAIResponsesSemanticProvider:
    """Provider adapter using the OpenAI Responses API with structured output."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "medium",
        api_base: str = "https://api.openai.com/v1",
        timeout_seconds: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for live OpenAI semantic evaluation")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.last_response_id: str | None = None
        self.last_model: str | None = None
        self.last_usage: Mapping[str, Any] | None = None

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = {
            "model": self.model,
            "instructions": _instructions(contract),
            "input": json.dumps(
                {"request": request, "project_context": dict(project_context)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            "reasoning": {"effort": self.reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "semantic_provider_output",
                    "strict": True,
                    "schema": PROVIDER_OUTPUT_SCHEMA,
                }
            },
            "store": False,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.api_base}/responses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")[:1200]
            raise RuntimeError(f"OpenAI Responses API HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI Responses API unavailable: {exc.reason}") from exc

        if not isinstance(response_payload, Mapping):
            raise RuntimeError("OpenAI Responses API returned a non-object payload")
        self.last_response_id = str(response_payload.get("id")) if response_payload.get("id") else None
        self.last_model = str(response_payload.get("model")) if response_payload.get("model") else None
        self.last_usage = response_payload.get("usage") if isinstance(response_payload.get("usage"), Mapping) else None
        text = _extract_output_text(response_payload)
        parsed = json.loads(text)
        if not isinstance(parsed, Mapping):
            raise RuntimeError("OpenAI structured output is not an object")
        return parsed
