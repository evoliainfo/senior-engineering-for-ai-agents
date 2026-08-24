#!/usr/bin/env python3
"""C1 deterministic qualification for the SEF capability contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.capability_registry import (  # noqa: E402
    CapabilityError,
    _validate_graph,
    build_manifest,
    load_capability,
)


def _metadata(cap_id: str, *, related: list[str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "id": cap_id,
        "version": "0.1.0",
        "category": "foundation",
        "status": "experimental",
        "purpose": f"Exercise {cap_id} safely.",
        "activate_when": ["the capability is relevant"],
        "inputs": ["user intent", "repository evidence"],
        "outputs": ["verified result"],
        "related_capabilities": related or [],
        "guardrail_hooks": [],
        "evals": [f"CAP-{cap_id.upper()}-001"],
        "tags": ["c1-test"],
    }


def _write_capability(
    root: Path,
    cap_id: str,
    *,
    related: list[str] | None = None,
    metadata_patch: dict | None = None,
    reference_text: str | None = None,
) -> Path:
    directory = root / cap_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        "---\n"
        f"name: {cap_id}\n"
        f"description: Use {cap_id} when its engineering method is relevant.\n"
        "---\n\n"
        f"# {cap_id}\n\n"
        "Apply the method using repository evidence.\n",
        encoding="utf-8",
    )
    meta = _metadata(cap_id, related=related)
    if metadata_patch:
        meta.update(metadata_patch)
    (directory / "capability.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if reference_text is not None:
        references = directory / "references"
        references.mkdir()
        (references / "detail.md").write_text(reference_text, encoding="utf-8")
    return directory


def _expect_error(fn, *, contains: str | None = None) -> str:
    try:
        fn()
    except CapabilityError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected error containing {contains!r}, got {message!r}") from exc
        return message
    raise AssertionError("expected CapabilityError")


def control_valid_capability_loads() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        directory = _write_capability(Path(tmp), "repository-discovery")
        entry = load_capability(directory)
        assert entry["id"] == "repository-discovery"
        assert entry["description"]
        assert entry["resources"] == []
        assert len(entry["skill_sha256"]) == 64
        assert len(entry["metadata_sha256"]) == 64
        return {"id": entry["id"], "version": entry["version"]}


def control_malformed_metadata_fails() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = _write_capability(root, "bad-metadata")
        (directory / "capability.json").write_text('{"schema_version": 1,', encoding="utf-8")
        message = _expect_error(lambda: load_capability(directory), contains="invalid JSON")
        return {"rejected": message}


def control_duplicate_ids_fail() -> dict:
    entry = {
        "id": "same-id",
        "related_capabilities": [],
    }
    message = _expect_error(lambda: _validate_graph([entry, dict(entry)]), contains="duplicate capability id")
    return {"rejected": message}


def control_graph_integrity_fails_closed() -> dict:
    findings: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_capability(root, "alpha", related=["missing-capability"])
        findings["missing_reference"] = _expect_error(
            lambda: build_manifest(root), contains="does not exist"
        )
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_capability(root, "alpha", related=["beta"])
        _write_capability(root, "beta", related=["alpha"])
        findings["cycle"] = _expect_error(lambda: build_manifest(root), contains="cycle")
    return findings


def control_optional_resources_are_progressive() -> dict:
    marker = "SECRET_REFERENCE_MARKER_NOT_CORE_CONTEXT"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = _write_capability(root, "with-reference", reference_text=marker)
        entry = load_capability(directory)
        assert entry["resources"] == [
            {
                "path": "references/detail.md",
                "sha256": hashlib.sha256(marker.encode("utf-8")).hexdigest(),
            }
        ]
        serialized = json.dumps(entry, sort_keys=True)
        assert marker not in serialized, "registry must index resource integrity without loading content"
        return {"resource_indexed": True, "resource_content_loaded": False}


def control_manifest_is_deterministic() -> dict:
    def make(order: list[str]) -> dict:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for cap_id in order:
            _write_capability(root, cap_id)
        result = build_manifest(root)
        tmp.cleanup()
        return result

    first = make(["zeta", "alpha"])
    second = make(["alpha", "zeta"])
    assert first == second
    assert [item["id"] for item in first["capabilities"]] == ["alpha", "zeta"]
    return {"content_sha256": first["content_sha256"], "order": ["alpha", "zeta"]}


def control_provider_configuration_is_forbidden() -> dict:
    findings: list[str] = []
    for key, value in (
        ("provider", "openai"),
        ("model", "frontier-model"),
        ("api_key_env", "SOME_KEY"),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = _write_capability(root, "provider-neutral")
            meta = _metadata("provider-neutral")
            meta[key] = value
            (directory / "capability.json").write_text(
                json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            findings.append(_expect_error(lambda d=directory: load_capability(d)))
    return {"rejected_provider_fields": 3, "errors": findings}


def control_frozen_runtime_is_unchanged() -> dict:
    sums_path = REPO_ROOT / "SHA256SUMS"
    runtime_path = REPO_ROOT / "sef.py"
    expected = None
    for raw in sums_path.read_text(encoding="utf-8").splitlines():
        parts = raw.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
            expected = parts[0]
            break
    assert expected, "SHA256SUMS must contain sef.py"
    observed = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    assert observed == expected, f"sef.py integrity mismatch: expected {expected}, observed {observed}"
    return {"sef_sha256": observed}


CONTROLS = [
    ("C1-01-valid-capability", control_valid_capability_loads),
    ("C1-02-malformed-metadata", control_malformed_metadata_fails),
    ("C1-03-duplicate-ids", control_duplicate_ids_fail),
    ("C1-04-graph-integrity", control_graph_integrity_fails_closed),
    ("C1-05-progressive-resources", control_optional_resources_are_progressive),
    ("C1-06-deterministic-manifest", control_manifest_is_deterministic),
    ("C1-07-provider-neutral", control_provider_configuration_is_forbidden),
    ("C1-08-runtime-integrity", control_frozen_runtime_is_unchanged),
]


def run() -> dict:
    results = []
    for control_id, fn in CONTROLS:
        try:
            detail = fn()
            results.append({"id": control_id, "status": "PASS", "detail": detail})
        except Exception as exc:  # report all controls rather than aborting at first failure
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.capability-c1.v1",
        "stage": "C1_CAPABILITY_CONTRACT_AND_REGISTRY",
        "control_count": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "status": "PASS" if passed == len(results) else "FAIL",
        "provider_calls": 0,
        "runtime_mutation_expected": False,
        "results": results,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="")
    args = parser.parse_args()
    report = run()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
