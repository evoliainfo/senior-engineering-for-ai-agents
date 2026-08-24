"""Deterministic Stable Expert Pack contract for modern SEF.

Stable Expert Packs carry durable executable expertise. They may expose a
portable Agent Skill entry point, but unlike ordinary prompt-only skills they
must also declare tool needs, executable entry points, evidence semantics and
failure/recovery behavior. This module validates and fingerprints pack bundles;
it performs no model, provider or network calls.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

SCHEMA_ID = "sef.expert-pack.v1"
MANIFEST_SCHEMA_ID = "sef.expert-pack-manifest.v1"

PACK_STATUSES = {"experimental", "candidate", "stable"}
TOOL_ACCESS = {"READ", "WRITE"}
TOOL_SENSITIVITY = {"LOCAL", "SANDBOX", "PRODUCTION_SENSITIVE"}
ENTRY_KINDS = {"SCRIPT", "EVALUATOR", "COLLECTOR", "ADAPTER"}
ENTRY_ROOT = {
    "SCRIPT": "scripts",
    "EVALUATOR": "evaluators",
    "COLLECTOR": "collectors",
    "ADAPTER": "adapters",
}
ALLOWED_CONTENT_ROOTS = {
    "scripts",
    "references",
    "fixtures",
    "evaluators",
    "collectors",
    "adapters",
}

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PACK_KEYS = {
    "schema",
    "id",
    "version",
    "status",
    "purpose",
    "activate_when",
    "tool_requirements",
    "entry_points",
    "evidence_contract",
    "failure_recovery",
    "tags",
}
TOOL_KEYS = {"capability", "access", "sensitivity", "required", "evidence"}
ENTRY_KEYS = {"id", "kind", "path", "purpose"}
EVIDENCE_KEYS = {"requires", "produces"}
RECOVERY_KEYS = {"failure_modes", "recovery_actions", "stop_conditions"}

FORBIDDEN_PROVIDER_KEYS = {
    "api_key",
    "api_key_env",
    "api_base",
    "model",
    "provider",
    "openai_api_key",
    "anthropic_api_key",
    "client_secret",
    "access_token",
}

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"),
)

MAX_PACK_FILES = 128
MAX_FILE_BYTES = 2_000_000


class ExpertPackError(ValueError):
    """Raised when an Expert Pack violates the stable bundle contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ExpertPackError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ExpertPackError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _nonempty_text(value: Any, label: str, *, limit: int = 1200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExpertPackError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise ExpertPackError(f"{label} exceeds {limit} characters")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ExpertPackError(f"{label} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise ExpertPackError(f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise ExpertPackError(f"{label} must not contain duplicates")
    return list(value)


def _scan_secret_values(value: Any, path: str = "pack") -> None:
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise ExpertPackError(f"credential-shaped secret value detected at {path}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _scan_secret_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secret_values(child, f"{path}[{index}]")


def _find_forbidden_provider_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in FORBIDDEN_PROVIDER_KEYS:
                found.append(child_path)
            found.extend(_find_forbidden_provider_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_provider_keys(child, f"{prefix}[{index}]"))
    return found


def parse_skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    _scan_secret_values(text, str(path))
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ExpertPackError(f"{path}: SKILL.md must start with YAML frontmatter")
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        raise ExpertPackError(f"{path}: unterminated SKILL.md frontmatter")
    values: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw = stripped.split(":", 1)
        key = key.strip()
        raw = raw.strip().strip('"').strip("'")
        if key in {"name", "description"}:
            values[key] = raw
    if not values.get("name") or not values.get("description"):
        raise ExpertPackError(f"{path}: frontmatter requires non-empty name and description")
    return values


def _safe_relative_path(raw: Any, label: str, *, expected_root: str | None = None) -> str:
    value = _nonempty_text(raw, label, limit=500)
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ExpertPackError(f"{label} must be a confined relative path")
    if expected_root is not None and pure.parts[0] != expected_root:
        raise ExpertPackError(f"{label} for this entry kind must live under {expected_root}/")
    return pure.as_posix()


def _validate_tools(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ExpertPackError("tool_requirements must be a list")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        label = f"tool_requirements[{index}]"
        if not isinstance(raw, dict):
            raise ExpertPackError(f"{label} must be an object")
        _require_exact(raw, TOOL_KEYS, label)
        capability = raw["capability"]
        if not isinstance(capability, str) or not CAPABILITY_RE.fullmatch(capability):
            raise ExpertPackError(f"{label}.capability must be lowercase snake_case")
        if capability in seen:
            raise ExpertPackError(f"duplicate tool capability: {capability}")
        seen.add(capability)
        if raw["access"] not in TOOL_ACCESS:
            raise ExpertPackError(f"{label}.access is invalid")
        if raw["sensitivity"] not in TOOL_SENSITIVITY:
            raise ExpertPackError(f"{label}.sensitivity is invalid")
        if not isinstance(raw["required"], bool):
            raise ExpertPackError(f"{label}.required must be boolean")
        evidence = _string_list(raw["evidence"], f"{label}.evidence")
        out.append({**raw, "evidence": evidence})
    return out


def _validate_entry_points(directory: Path, value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ExpertPackError("entry_points must be a non-empty list")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    out: list[dict[str, str]] = []
    for index, raw in enumerate(value):
        label = f"entry_points[{index}]"
        if not isinstance(raw, dict):
            raise ExpertPackError(f"{label} must be an object")
        _require_exact(raw, ENTRY_KEYS, label)
        entry_id = raw["id"]
        if not isinstance(entry_id, str) or not ITEM_ID_RE.fullmatch(entry_id):
            raise ExpertPackError(f"{label}.id must be a compact stable identifier")
        if entry_id in seen_ids:
            raise ExpertPackError(f"duplicate entry point id: {entry_id}")
        seen_ids.add(entry_id)
        kind = raw["kind"]
        if kind not in ENTRY_KINDS:
            raise ExpertPackError(f"{label}.kind is invalid")
        rel = _safe_relative_path(raw["path"], f"{label}.path", expected_root=ENTRY_ROOT[kind])
        if rel in seen_paths:
            raise ExpertPackError(f"duplicate entry point path: {rel}")
        seen_paths.add(rel)
        path = directory / rel
        if not path.is_file():
            raise ExpertPackError(f"{label}.path does not exist: {rel}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ExpertPackError(f"{label}.path exceeds file-size limit")
        _nonempty_text(raw["purpose"], f"{label}.purpose")
        _scan_secret_values(path.read_text(encoding="utf-8", errors="ignore"), rel)
        out.append(dict(raw))
    return out


def _validate_evidence(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ExpertPackError("evidence_contract must be an object")
    _require_exact(value, EVIDENCE_KEYS, "evidence_contract")
    requires = _string_list(value["requires"], "evidence_contract.requires")
    produces = _string_list(value["produces"], "evidence_contract.produces", allow_empty=False)
    return {"requires": requires, "produces": produces}


def _validate_recovery(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise ExpertPackError("failure_recovery must be an object")
    _require_exact(value, RECOVERY_KEYS, "failure_recovery")
    return {
        "failure_modes": _string_list(value["failure_modes"], "failure_recovery.failure_modes", allow_empty=False),
        "recovery_actions": _string_list(value["recovery_actions"], "failure_recovery.recovery_actions", allow_empty=False),
        "stop_conditions": _string_list(value["stop_conditions"], "failure_recovery.stop_conditions", allow_empty=False),
    }


def _bundle_files(directory: Path) -> list[dict[str, Any]]:
    allowed_top_files = {"SKILL.md", "pack.json"}
    for child in directory.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_file() and child.name not in allowed_top_files:
            raise ExpertPackError(f"{directory}: unsupported top-level file {child.name}")
        if child.is_dir() and child.name not in ALLOWED_CONTENT_ROOTS:
            raise ExpertPackError(f"{directory}: unsupported content directory {child.name}")

    files = sorted(path for path in directory.rglob("*") if path.is_file() and not any(part.startswith(".") for part in path.relative_to(directory).parts))
    if len(files) > MAX_PACK_FILES:
        raise ExpertPackError(f"{directory}: pack exceeds {MAX_PACK_FILES} files")
    out: list[dict[str, Any]] = []
    for path in files:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ExpertPackError(f"{path}: file exceeds {MAX_FILE_BYTES} bytes")
        rel = path.relative_to(directory).as_posix()
        if rel not in allowed_top_files and PurePosixPath(rel).parts[0] not in ALLOWED_CONTENT_ROOTS:
            raise ExpertPackError(f"{path}: file is outside allowed pack content roots")
        data = path.read_bytes()
        _scan_secret_values(data.decode("utf-8", errors="ignore"), rel)
        out.append({"path": rel, "size": size, "sha256": hashlib.sha256(data).hexdigest()})
    return out


def load_pack(directory: Path) -> dict[str, Any]:
    directory = Path(directory)
    skill_path = directory / "SKILL.md"
    meta_path = directory / "pack.json"
    if not skill_path.is_file():
        raise ExpertPackError(f"{directory}: missing SKILL.md")
    if not meta_path.is_file():
        raise ExpertPackError(f"{directory}: missing pack.json")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExpertPackError(f"{meta_path}: invalid JSON: {exc}") from exc
    if not isinstance(meta, dict):
        raise ExpertPackError(f"{meta_path}: root must be an object")
    _require_exact(meta, PACK_KEYS, str(meta_path))
    _scan_secret_values(meta, str(meta_path))
    forbidden = _find_forbidden_provider_keys(meta)
    if forbidden:
        raise ExpertPackError(f"{meta_path}: provider/API configuration is forbidden: {', '.join(forbidden)}")

    if meta["schema"] != SCHEMA_ID:
        raise ExpertPackError(f"{meta_path}: schema must equal {SCHEMA_ID}")
    pack_id = meta["id"]
    if not isinstance(pack_id, str) or not ID_RE.fullmatch(pack_id):
        raise ExpertPackError(f"{meta_path}: id must be lowercase kebab-case")
    if directory.name != pack_id:
        raise ExpertPackError(f"{meta_path}: id must match directory name")
    if not isinstance(meta["version"], str) or not SEMVER_RE.fullmatch(meta["version"]):
        raise ExpertPackError(f"{meta_path}: version must be semantic version x.y.z")
    if meta["status"] not in PACK_STATUSES:
        raise ExpertPackError(f"{meta_path}: status is invalid")
    purpose = _nonempty_text(meta["purpose"], f"{meta_path}.purpose")
    activate_when = _string_list(meta["activate_when"], f"{meta_path}.activate_when", allow_empty=False)
    tags = _string_list(meta["tags"], f"{meta_path}.tags")

    skill = parse_skill_frontmatter(skill_path)
    if skill["name"] != pack_id:
        raise ExpertPackError(f"{skill_path}: skill name must equal pack id")

    tools = _validate_tools(meta["tool_requirements"])
    entries = _validate_entry_points(directory, meta["entry_points"])
    evidence = _validate_evidence(meta["evidence_contract"])
    recovery = _validate_recovery(meta["failure_recovery"])
    files = _bundle_files(directory)

    bundle = {
        "schema": SCHEMA_ID,
        "id": pack_id,
        "version": meta["version"],
        "status": meta["status"],
        "purpose": purpose,
        "description": skill["description"],
        "activate_when": activate_when,
        "tool_requirements": tools,
        "entry_points": entries,
        "evidence_contract": evidence,
        "failure_recovery": recovery,
        "tags": tags,
        "files": files,
    }
    bundle["content_sha256"] = _digest(bundle)
    return bundle


def discover_pack_dirs(root: Path) -> list[Path]:
    root = Path(root)
    if not root.exists():
        raise ExpertPackError(f"expert pack root does not exist: {root}")
    return sorted(path for path in root.iterdir() if path.is_dir() and not path.name.startswith("_") and not path.name.startswith("."))


def build_manifest(root: Path) -> dict[str, Any]:
    packs = [load_pack(path) for path in discover_pack_dirs(root)]
    ids = [pack["id"] for pack in packs]
    if len(ids) != len(set(ids)):
        raise ExpertPackError("duplicate Expert Pack id")
    packs.sort(key=lambda item: item["id"])
    manifest = {
        "schema": MANIFEST_SCHEMA_ID,
        "pack_count": len(packs),
        "packs": packs,
    }
    manifest["content_sha256"] = _digest(manifest)
    return manifest


def validate_manifest(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise ExpertPackError("manifest must be an object")
    expected = build_manifest(root)
    observed = copy.deepcopy(dict(manifest))
    if observed != expected:
        raise ExpertPackError("expert pack manifest does not match current bundle contents")
    digest = observed.get("content_sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise ExpertPackError("manifest content_sha256 is invalid")
    return observed


def write_manifest(root: Path, path: Path) -> dict[str, Any]:
    manifest = build_manifest(root)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
