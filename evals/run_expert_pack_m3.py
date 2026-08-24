#!/usr/bin/env python3
"""Deterministic M3 qualification for SEF Stable Expert Pack contract."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from expert_packs import (  # noqa: E402
    ENTRY_KINDS,
    PACK_STATUSES,
    SCHEMA_ID,
    TOOL_ACCESS,
    TOOL_SENSITIVITY,
    ExpertPackError,
    build_manifest,
    load_pack,
    validate_manifest,
)

SCHEMA_PATH = ROOT / "expert_packs" / "expert-pack.schema.json"
REPORT_PATH = ROOT / "eval-results" / "expert-pack-m3-report.json"


def _metadata(pack_id: str) -> dict:
    return {
        "schema": SCHEMA_ID,
        "id": pack_id,
        "version": "0.1.0",
        "status": "experimental",
        "purpose": "Provide durable executable evidence for a focused engineering specialty.",
        "activate_when": ["A mission needs this durable executable specialty."],
        "tool_requirements": [
            {
                "capability": "browser",
                "access": "READ",
                "sensitivity": "SANDBOX",
                "required": True,
                "evidence": ["Observed browser behavior"],
            }
        ],
        "entry_points": [
            {
                "id": "run-check",
                "kind": "SCRIPT",
                "path": "scripts/run.py",
                "purpose": "Emit deterministic fixture evidence.",
            }
        ],
        "evidence_contract": {"requires": [], "produces": ["pack-check-report"]},
        "failure_recovery": {
            "failure_modes": ["Required tool or observable evidence is unavailable."],
            "recovery_actions": ["Report an explicit capability gap and preserve prior evidence."],
            "stop_conditions": ["Required evidence cannot be obtained truthfully."],
        },
        "tags": ["m3"],
    }


def _create_pack(root: Path, pack_id: str = "demo-pack", *, meta: dict | None = None, skill_name: str | None = None) -> Path:
    directory = root / pack_id
    (directory / "scripts").mkdir(parents=True, exist_ok=True)
    (directory / "fixtures").mkdir(parents=True, exist_ok=True)
    skill = skill_name or pack_id
    (directory / "SKILL.md").write_text(
        "---\n"
        f"name: {skill}\n"
        "description: Durable executable demo pack used only for deterministic M3 qualification.\n"
        "---\n\n# Demo pack\n\nRun the declared executable and preserve observable evidence.\n",
        encoding="utf-8",
    )
    (directory / "pack.json").write_text(
        json.dumps(meta if meta is not None else _metadata(pack_id), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (directory / "scripts" / "run.py").write_text(
        "#!/usr/bin/env python3\nimport json\nprint(json.dumps({'status': 'PASS'}))\n",
        encoding="utf-8",
    )
    (directory / "fixtures" / "case.json").write_text('{"expected":"PASS"}\n', encoding="utf-8")
    return directory


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except ExpertPackError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected ExpertPackError")


def control_schema_contract_alignment() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == SCHEMA_ID
    assert set(schema["properties"]["status"]["enum"]) == PACK_STATUSES
    assert set(schema["$defs"]["toolRequirement"]["properties"]["access"]["enum"]) == TOOL_ACCESS
    assert set(schema["$defs"]["toolRequirement"]["properties"]["sensitivity"]["enum"]) == TOOL_SENSITIVITY
    assert set(schema["$defs"]["entryPoint"]["properties"]["kind"]["enum"]) == ENTRY_KINDS
    return {"statuses": len(PACK_STATUSES), "entry_kinds": len(ENTRY_KINDS)}


def control_valid_executable_pack() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        pack = load_pack(_create_pack(Path(tmp)))
        assert pack["id"] == "demo-pack"
        assert pack["entry_points"][0]["path"] == "scripts/run.py"
        assert pack["evidence_contract"]["produces"] == ["pack-check-report"]
        assert any(item["path"] == "fixtures/case.json" for item in pack["files"])
        assert len(pack["content_sha256"]) == 64
        return {"files": len(pack["files"]), "digest": pack["content_sha256"]}


def control_manifest_is_deterministic() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _create_pack(root, "zeta-pack")
        _create_pack(root, "alpha-pack")
        first = build_manifest(root)
        second = build_manifest(root)
        assert first == second
        assert [item["id"] for item in first["packs"]] == ["alpha-pack", "zeta-pack"]
        return {"pack_count": first["pack_count"], "digest": first["content_sha256"]}


def control_skill_name_must_bind_pack() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        directory = _create_pack(Path(tmp), skill_name="other-pack")
        return {"rejected": _expect_error(lambda: load_pack(directory), "skill name must equal pack id")}


def control_directory_id_must_bind_pack() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("different-pack")
        directory = _create_pack(Path(tmp), "demo-pack", meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "id must match directory name")}


def control_semver_required() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["version"] = "latest"
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "semantic version")}


def control_duplicate_tool_requirement_rejected() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["tool_requirements"].append(copy.deepcopy(meta["tool_requirements"][0]))
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "duplicate tool capability")}


def control_tool_contract_is_closed() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["tool_requirements"][0]["sensitivity"] = "MAGIC"
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "sensitivity is invalid")}


def control_executable_entry_point_required() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["entry_points"] = []
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "entry_points must be a non-empty list")}


def control_missing_entry_point_rejected() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        directory = _create_pack(Path(tmp))
        (directory / "scripts" / "run.py").unlink()
        return {"rejected": _expect_error(lambda: load_pack(directory), "path does not exist")}


def control_entry_point_path_is_confined() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["entry_points"][0]["path"] = "scripts/../outside.py"
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "confined relative path")}


def control_entry_kind_matches_content_root() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["entry_points"][0]["kind"] = "EVALUATOR"
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "must live under evaluators/")}


def control_duplicate_entry_id_rejected() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        duplicate = copy.deepcopy(meta["entry_points"][0])
        duplicate["path"] = "scripts/second.py"
        meta["entry_points"].append(duplicate)
        directory = _create_pack(Path(tmp), meta=meta)
        (directory / "scripts" / "second.py").write_text("print('ok')\n", encoding="utf-8")
        return {"rejected": _expect_error(lambda: load_pack(directory), "duplicate entry point id")}


def control_evidence_output_required() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["evidence_contract"]["produces"] = []
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "evidence_contract.produces must not be empty")}


def control_failure_recovery_is_not_optional() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["failure_recovery"]["stop_conditions"] = []
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "stop_conditions must not be empty")}


def control_provider_configuration_forbidden() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        meta = _metadata("demo-pack")
        meta["tool_requirements"][0]["provider"] = "example"
        directory = _create_pack(Path(tmp), meta=meta)
        return {"rejected": _expect_error(lambda: load_pack(directory), "provider/API configuration is forbidden")}


def control_secret_shaped_value_rejected() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        directory = _create_pack(Path(tmp))
        generated_secret = "sk" + "-" + ("x" * 24)
        (directory / "scripts" / "run.py").write_text(
            "token = " + repr(generated_secret) + "\nprint(token)\n",
            encoding="utf-8",
        )
        return {"rejected": _expect_error(lambda: load_pack(directory), "credential-shaped secret value")}


def control_manifest_detects_tampering() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = _create_pack(root)
        manifest = build_manifest(root)
        (directory / "fixtures" / "case.json").write_text('{"expected":"FAIL"}\n', encoding="utf-8")
        return {"rejected": _expect_error(lambda: validate_manifest(root, manifest), "does not match current bundle contents")}


def control_legacy_runtime_integrity() -> dict:
    expected = None
    for raw in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = raw.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
            expected = parts[0]
            break
    assert expected
    observed = hashlib.sha256((ROOT / "sef.py").read_bytes()).hexdigest()
    assert observed == expected
    return {"sef_sha256": observed}


CONTROLS = [
    ("M3-01-schema-contract", control_schema_contract_alignment),
    ("M3-02-valid-executable-pack", control_valid_executable_pack),
    ("M3-03-deterministic-manifest", control_manifest_is_deterministic),
    ("M3-04-skill-name-binding", control_skill_name_must_bind_pack),
    ("M3-05-directory-id-binding", control_directory_id_must_bind_pack),
    ("M3-06-semver", control_semver_required),
    ("M3-07-duplicate-tool", control_duplicate_tool_requirement_rejected),
    ("M3-08-tool-contract", control_tool_contract_is_closed),
    ("M3-09-entry-required", control_executable_entry_point_required),
    ("M3-10-entry-exists", control_missing_entry_point_rejected),
    ("M3-11-entry-path-confinement", control_entry_point_path_is_confined),
    ("M3-12-entry-kind-root", control_entry_kind_matches_content_root),
    ("M3-13-duplicate-entry", control_duplicate_entry_id_rejected),
    ("M3-14-evidence-output", control_evidence_output_required),
    ("M3-15-failure-recovery", control_failure_recovery_is_not_optional),
    ("M3-16-no-provider-config", control_provider_configuration_forbidden),
    ("M3-17-secret-guard", control_secret_shaped_value_rejected),
    ("M3-18-manifest-tamper", control_manifest_detects_tampering),
    ("M3-19-runtime-integrity", control_legacy_runtime_integrity),
]


def main() -> int:
    results = []
    for control_id, fn in CONTROLS:
        try:
            results.append({"id": control_id, "status": "PASS", "detail": fn()})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.expert-pack-m3.v1",
        "stage": "M3_STABLE_EXPERT_PACK_CONTRACT",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "provider_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "agent_outcome_claim": False,
        "initial_pack_outcome_claim": False,
        "runtime_mutation_expected": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
