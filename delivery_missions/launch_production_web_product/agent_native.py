"""Agent-native run workspace for the first Modern SEF Delivery Mission.

The active coding-agent session remains the executor.  This module does not
spawn Codex, call a model, or invoke provider tools.  It freezes the exact M5
decision/plan into a repository-local run directory, snapshots evidence bytes
produced by the active harness, and assembles the execution-result envelope
that the existing M5 evidence layer can verify.

The trust boundary is intentionally narrow:

* the M5 decision remains the authority for selected M4 surfaces and packs;
* the execution plan remains a recomputable hand-off, not an authorization;
* registered evidence is copied into the run workspace and SHA-256 hashed;
* a TOOL artifact must name an exact surface selected by the plan;
* finalization only seals a result after required plan slots and active pack
  observation documents are present;
* this module never advances Project State by itself.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from project_state import validate_state

from .core import MissionError, validate_decision, validate_spec
from .evidence import seal_execution_result, validate_execution_result
from .execution_plan import build_execution_plan, validate_execution_plan

RUN_SCHEMA_ID = "sef.agent-native-mission-run.launch-production-web-product.v1"
RUN_STATUSES = {"PREPARED", "COLLECTING", "FINALIZED", "ACCEPTED"}
PRODUCERS = {"AGENT", "SYSTEM", "TOOL"}
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
KIND_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

RUN_KEYS = {
    "schema",
    "run_id",
    "mission_id",
    "project_id",
    "decision_sha256",
    "project_state_sha256",
    "plan_sha256",
    "created_at",
    "status",
    "evidence_namespace",
    "artifacts",
    "pack_observations",
    "execution_result_ref",
    "evidence_receipt_ref",
    "state_after_sha256",
    "content_sha256",
}
RUN_ARTIFACT_KEYS = {
    "id",
    "slot_id",
    "ref",
    "kind",
    "path",
    "sha256",
    "producer",
    "capability",
    "surface_id",
}
PACK_LINK_KEYS = {"pack_id", "artifact_ref"}


class AgentNativeRunError(MissionError):
    """Raised when the agent-native run workspace is unsafe or inconsistent."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _seal_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result.pop("content_sha256", None)
    result["content_sha256"] = _digest(result)
    validate_run_manifest(result)
    return result


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise AgentNativeRunError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise AgentNativeRunError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise AgentNativeRunError(f"{label} must be a compact stable identifier")
    return value


def _safe_relative(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or len(value) > 512 or "\\" in value:
        raise AgentNativeRunError(f"{label} must be a portable relative path")
    rel = Path(value)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise AgentNativeRunError(f"unsafe {label}: {value}")
    return rel


def _safe_existing(root: Path, relative: str, label: str) -> Path:
    rel = _safe_relative(relative, label)
    resolved_root = Path(root).resolve()
    candidate = (resolved_root / rel).resolve()
    try:
        common = os.path.commonpath([str(resolved_root), str(candidate)])
    except ValueError as exc:
        raise AgentNativeRunError(f"unsafe {label}: {relative}") from exc
    if common != str(resolved_root) or not candidate.is_file():
        raise AgentNativeRunError(f"{label} does not resolve to a file under run root: {relative}")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentNativeRunError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise AgentNativeRunError(f"{label} root must be an object")
    return value


def validate_run_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentNativeRunError("run manifest root must be an object")
    _exact(value, RUN_KEYS, "run")
    if value["schema"] != RUN_SCHEMA_ID:
        raise AgentNativeRunError(f"run.schema must equal {RUN_SCHEMA_ID}")
    _item_id(value["run_id"], "run_id")
    _item_id(value["mission_id"], "mission_id")
    if not isinstance(value["project_id"], str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value["project_id"]):
        raise AgentNativeRunError("project_id must be lowercase kebab-case")
    for field in ("decision_sha256", "project_state_sha256", "plan_sha256", "content_sha256"):
        if not isinstance(value[field], str) or not SHA256_RE.fullmatch(value[field]):
            raise AgentNativeRunError(f"{field} must be a lowercase SHA-256")
    if not isinstance(value["created_at"], str) or not value["created_at"]:
        raise AgentNativeRunError("created_at must be a non-empty timestamp")
    if value["status"] not in RUN_STATUSES:
        raise AgentNativeRunError("run status is invalid")
    if not isinstance(value["evidence_namespace"], str) or not value["evidence_namespace"].startswith("artifact://") or not value["evidence_namespace"].endswith("/"):
        raise AgentNativeRunError("evidence_namespace must be an artifact:// namespace")

    ids: set[str] = set()
    refs: set[str] = set()
    paths: set[str] = set()
    for index, item in enumerate(value["artifacts"]):
        if not isinstance(item, dict):
            raise AgentNativeRunError(f"artifacts[{index}] must be an object")
        _exact(item, RUN_ARTIFACT_KEYS, f"artifacts[{index}]")
        artifact_id = _item_id(item["id"], f"artifacts[{index}].id")
        if artifact_id in ids:
            raise AgentNativeRunError("run artifacts contain duplicate ids")
        ids.add(artifact_id)
        if item["slot_id"] is not None:
            _item_id(item["slot_id"], f"artifacts[{index}].slot_id")
        if not isinstance(item["ref"], str) or not item["ref"].startswith(value["evidence_namespace"]):
            raise AgentNativeRunError("artifact ref must remain under run evidence namespace")
        if item["ref"] in refs:
            raise AgentNativeRunError("run artifacts contain duplicate refs")
        refs.add(item["ref"])
        _safe_relative(item["path"], f"artifacts[{index}].path")
        if item["path"] in paths:
            raise AgentNativeRunError("run artifacts contain duplicate paths")
        paths.add(item["path"])
        if not isinstance(item["kind"], str) or not KIND_RE.fullmatch(item["kind"]):
            raise AgentNativeRunError("artifact kind must be lowercase kebab-case")
        if not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise AgentNativeRunError("artifact sha256 must be lowercase SHA-256")
        if item["producer"] not in PRODUCERS:
            raise AgentNativeRunError("artifact producer is invalid")
        if item["producer"] == "TOOL":
            if not isinstance(item["capability"], str) or not item["capability"]:
                raise AgentNativeRunError("TOOL artifact requires capability")
            _item_id(item["surface_id"], "surface_id")
        elif item["capability"] is not None or item["surface_id"] is not None:
            raise AgentNativeRunError("non-TOOL artifact must have null capability and surface_id")

    packs: set[str] = set()
    for index, item in enumerate(value["pack_observations"]):
        if not isinstance(item, dict):
            raise AgentNativeRunError(f"pack_observations[{index}] must be an object")
        _exact(item, PACK_LINK_KEYS, f"pack_observations[{index}]")
        pack_id = _item_id(item["pack_id"], f"pack_observations[{index}].pack_id")
        if pack_id in packs:
            raise AgentNativeRunError("pack_observations contain duplicate pack ids")
        packs.add(pack_id)
        if item["artifact_ref"] not in refs:
            raise AgentNativeRunError(f"pack observation references unknown artifact: {item['artifact_ref']}")

    for field in ("execution_result_ref", "evidence_receipt_ref"):
        if value[field] is not None:
            _safe_relative(value[field], field)
    if value["state_after_sha256"] is not None and (
        not isinstance(value["state_after_sha256"], str) or not SHA256_RE.fullmatch(value["state_after_sha256"])
    ):
        raise AgentNativeRunError("state_after_sha256 must be null or lowercase SHA-256")

    unsigned = copy.deepcopy(value)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != value["content_sha256"]:
        raise AgentNativeRunError("run manifest content hash mismatch")
    return value


def load_run(run_dir: Path) -> dict[str, Any]:
    value = _load_json(Path(run_dir) / "run.json", "run manifest")
    return validate_run_manifest(value)


def _load_bound_inputs(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = Path(run_dir)
    spec = _load_json(root / "spec.json", "mission spec")
    state = _load_json(root / "state.before.json", "Project State snapshot")
    decision = _load_json(root / "decision.json", "mission decision")
    plan = _load_json(root / "plan.json", "execution plan")
    validate_spec(spec)
    validate_state(state)
    validate_decision(decision)
    validate_execution_plan(plan, spec=spec, state=state, decision=decision)
    manifest = load_run(root)
    if manifest["decision_sha256"] != decision["content_sha256"]:
        raise AgentNativeRunError("run decision snapshot diverges from manifest")
    if manifest["project_state_sha256"] != state["content_sha256"]:
        raise AgentNativeRunError("run Project State snapshot diverges from manifest")
    if manifest["plan_sha256"] != plan["content_sha256"]:
        raise AgentNativeRunError("run execution plan diverges from manifest")
    return spec, state, decision, plan


def prepare_run(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    *,
    run_dir: Path,
    generated_at: str,
) -> dict[str, Any]:
    """Freeze a READY decision and its execution plan into a new run workspace."""
    validate_spec(spec)
    validate_state(state)
    validate_decision(decision)
    if decision.get("status") != "READY_FOR_AGENT":
        raise AgentNativeRunError("only READY_FOR_AGENT decisions can prepare an agent-native run")

    root = Path(run_dir)
    if root.exists() and any(root.iterdir()):
        raise AgentNativeRunError(f"refusing to reuse non-empty run directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    run_id = f"{decision['mission_id']}-{decision['content_sha256'][:12]}"
    namespace = f"artifact://mission-runs/{run_id}/"
    plan = build_execution_plan(
        spec,
        state,
        decision,
        generated_at=generated_at,
        evidence_namespace=namespace,
    )
    validate_execution_plan(plan, spec=spec, state=state, decision=decision)

    manifest = _seal_manifest(
        {
            "schema": RUN_SCHEMA_ID,
            "run_id": run_id,
            "mission_id": decision["mission_id"],
            "project_id": decision["project_id"],
            "decision_sha256": decision["content_sha256"],
            "project_state_sha256": state["content_sha256"],
            "plan_sha256": plan["content_sha256"],
            "created_at": generated_at,
            "status": "PREPARED",
            "evidence_namespace": namespace,
            "artifacts": [],
            "pack_observations": [],
            "execution_result_ref": None,
            "evidence_receipt_ref": None,
            "state_after_sha256": None,
        }
    )
    _atomic_json(root / "spec.json", spec)
    _atomic_json(root / "state.before.json", state)
    _atomic_json(root / "decision.json", decision)
    _atomic_json(root / "plan.json", plan)
    _atomic_json(root / "run.json", manifest)
    return manifest


def register_artifact(
    run_dir: Path,
    source_path: Path,
    *,
    artifact_id: str,
    kind: str,
    producer: str,
    slot_id: str | None = None,
    capability: str | None = None,
    surface_id: str | None = None,
) -> dict[str, Any]:
    """Snapshot one evidence file into the run workspace and hash its bytes."""
    root = Path(run_dir)
    _, _, _, plan = _load_bound_inputs(root)
    manifest = load_run(root)
    if manifest["status"] not in {"PREPARED", "COLLECTING"}:
        raise AgentNativeRunError("artifacts can only be registered before finalization")
    _item_id(artifact_id, "artifact_id")
    if not isinstance(kind, str) or not KIND_RE.fullmatch(kind):
        raise AgentNativeRunError("kind must be lowercase kebab-case")
    if producer not in PRODUCERS:
        raise AgentNativeRunError("producer is invalid")
    source = Path(source_path)
    if not source.is_file() or source.stat().st_size <= 0:
        raise AgentNativeRunError("source_path must be a non-empty file")

    selected_tools = {item["capability"]: item for item in plan["selected_tools"]}
    slots = {item["id"]: item for item in plan["artifact_slots"]}
    slot = None
    if slot_id is not None:
        slot = slots.get(slot_id)
        if slot is None:
            raise AgentNativeRunError(f"unknown artifact slot: {slot_id}")
        if kind != slot["kind"]:
            raise AgentNativeRunError(f"artifact kind must equal slot kind {slot['kind']}")
        if producer not in slot["allowed_producers"]:
            raise AgentNativeRunError(f"producer {producer} is not allowed for slot {slot_id}")
        if slot["capability"] is not None and capability != slot["capability"]:
            raise AgentNativeRunError(f"artifact capability must equal slot capability {slot['capability']}")
        if slot["surface_id"] is not None and surface_id != slot["surface_id"]:
            raise AgentNativeRunError(f"artifact surface must equal slot surface {slot['surface_id']}")

    if producer == "TOOL":
        selected = selected_tools.get(capability or "")
        if selected is None:
            raise AgentNativeRunError(f"TOOL artifact capability is not selected by plan: {capability}")
        if surface_id != selected["surface_id"]:
            raise AgentNativeRunError(
                f"TOOL artifact surface does not match exact selected {capability} surface"
            )
    elif capability is not None or surface_id is not None:
        raise AgentNativeRunError("non-TOOL artifact must not declare capability or surface")

    if any(item["id"] == artifact_id for item in manifest["artifacts"]):
        raise AgentNativeRunError(f"artifact id already registered: {artifact_id}")
    if slot_id is not None and any(item["slot_id"] == slot_id for item in manifest["artifacts"]):
        raise AgentNativeRunError(f"artifact slot already satisfied: {slot_id}")

    suffix = source.suffix if source.suffix and len(source.suffix) <= 12 else ".bin"
    destination_rel = Path("artifacts") / f"{artifact_id}{suffix}"
    destination = root / destination_rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise AgentNativeRunError(f"refusing to overwrite run artifact: {destination_rel.as_posix()}")
    shutil.copyfile(source, destination)
    digest = _sha256_file(destination)
    artifact_ref = manifest["evidence_namespace"] + f"artifacts/{artifact_id}"
    record = {
        "id": artifact_id,
        "slot_id": slot_id,
        "ref": artifact_ref,
        "kind": kind,
        "path": destination_rel.as_posix(),
        "sha256": digest,
        "producer": producer,
        "capability": capability,
        "surface_id": surface_id,
    }
    manifest["artifacts"].append(record)
    manifest["artifacts"] = sorted(manifest["artifacts"], key=lambda item: item["id"])
    manifest["status"] = "COLLECTING"
    manifest = _seal_manifest(manifest)
    _atomic_json(root / "run.json", manifest)
    return copy.deepcopy(record)


def attach_pack_observation(run_dir: Path, *, pack_id: str, artifact_id: str) -> dict[str, Any]:
    """Bind one registered observation JSON artifact to an active M3 pack."""
    root = Path(run_dir)
    _, _, decision, plan = _load_bound_inputs(root)
    manifest = load_run(root)
    if manifest["status"] not in {"PREPARED", "COLLECTING"}:
        raise AgentNativeRunError("pack observations can only be attached before finalization")
    active = set(decision.get("active_packs", []))
    if pack_id not in active:
        raise AgentNativeRunError(f"pack is not active for exact decision: {pack_id}")
    task_ids = {item["pack_id"] for item in plan["pack_tasks"]}
    if pack_id not in task_ids:
        raise AgentNativeRunError(f"pack has no execution-plan task: {pack_id}")
    matches = [item for item in manifest["artifacts"] if item["id"] == artifact_id]
    if len(matches) != 1:
        raise AgentNativeRunError(f"pack observation artifact is not registered: {artifact_id}")
    if any(item["pack_id"] == pack_id for item in manifest["pack_observations"]):
        raise AgentNativeRunError(f"pack observation already attached: {pack_id}")
    link = {"pack_id": pack_id, "artifact_ref": matches[0]["ref"]}
    manifest["pack_observations"].append(link)
    manifest["pack_observations"] = sorted(manifest["pack_observations"], key=lambda item: item["pack_id"])
    manifest["status"] = "COLLECTING"
    manifest = _seal_manifest(manifest)
    _atomic_json(root / "run.json", manifest)
    return copy.deepcopy(link)


def finalize_run(run_dir: Path, *, observed_at: str, status: str = "SUCCEEDED") -> dict[str, Any]:
    """Build and seal the exact M5 execution-result from snapshotted evidence."""
    root = Path(run_dir)
    _, _, decision, plan = _load_bound_inputs(root)
    manifest = load_run(root)
    if manifest["status"] not in {"PREPARED", "COLLECTING"}:
        raise AgentNativeRunError("run can only be finalized once")

    required_slots = {item["id"] for item in plan["artifact_slots"] if item["required"]}
    satisfied_slots = {item["slot_id"] for item in manifest["artifacts"] if item["slot_id"] is not None}
    missing_slots = sorted(required_slots - satisfied_slots)
    if status == "SUCCEEDED" and missing_slots:
        raise AgentNativeRunError(f"required artifact slots are missing: {missing_slots}")

    expected_packs = set(decision.get("active_packs", []))
    attached_packs = {item["pack_id"] for item in manifest["pack_observations"]}
    if status == "SUCCEEDED" and attached_packs != expected_packs:
        raise AgentNativeRunError(
            f"pack observation set must equal active packs; missing={sorted(expected_packs - attached_packs)} extra={sorted(attached_packs - expected_packs)}"
        )

    artifacts = [
        {
            "id": item["id"],
            "ref": item["ref"],
            "kind": item["kind"],
            "path": item["path"],
            "sha256": item["sha256"],
            "producer": item["producer"],
            "capability": item["capability"],
            "surface_id": item["surface_id"],
        }
        for item in manifest["artifacts"]
    ]
    result = seal_execution_result(
        {
            "schema": plan["result_contract"]["schema"],
            "mission_id": plan["mission_id"],
            "project_id": plan["project_id"],
            "decision_sha256": plan["decision_sha256"],
            "project_state_sha256": plan["project_state_sha256"],
            "action": plan["action"],
            "observed_at": observed_at,
            "status": status,
            "artifacts": artifacts,
            "pack_observations": copy.deepcopy(manifest["pack_observations"]),
        }
    )
    validate_execution_result(result)
    result_path = root / "execution-result.json"
    _atomic_json(result_path, result)
    manifest["status"] = "FINALIZED"
    manifest["execution_result_ref"] = "execution-result.json"
    manifest = _seal_manifest(manifest)
    _atomic_json(root / "run.json", manifest)
    return result


def mark_accepted(
    run_dir: Path,
    *,
    evidence_receipt_ref: str,
    state_after_sha256: str,
) -> dict[str, Any]:
    """Record successful acceptance after the canonical evidence API advanced M1."""
    root = Path(run_dir)
    manifest = load_run(root)
    if manifest["status"] != "FINALIZED":
        raise AgentNativeRunError("only a finalized run can be marked accepted")
    _safe_existing(root, evidence_receipt_ref, "evidence_receipt_ref")
    if not isinstance(state_after_sha256, str) or not SHA256_RE.fullmatch(state_after_sha256):
        raise AgentNativeRunError("state_after_sha256 must be lowercase SHA-256")
    manifest["status"] = "ACCEPTED"
    manifest["evidence_receipt_ref"] = evidence_receipt_ref
    manifest["state_after_sha256"] = state_after_sha256
    manifest = _seal_manifest(manifest)
    _atomic_json(root / "run.json", manifest)
    return manifest


__all__ = [
    "AgentNativeRunError",
    "RUN_SCHEMA_ID",
    "attach_pack_observation",
    "finalize_run",
    "load_run",
    "mark_accepted",
    "prepare_run",
    "register_artifact",
    "validate_run_manifest",
]
