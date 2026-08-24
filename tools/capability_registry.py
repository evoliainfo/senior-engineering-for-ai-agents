#!/usr/bin/env python3
"""SEF capability contract validator and deterministic registry generator.

The user-facing capability remains a portable Agent Skill in ``SKILL.md``.
SEF-specific composition/evaluation metadata lives in ``capability.json``.
This module is standard-library only and performs no model/provider calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
ALLOWED_CATEGORIES = {"foundation", "specialist", "workflow", "project"}
ALLOWED_STATUSES = {"experimental", "candidate", "stable"}
REQUIRED_KEYS = {
    "schema_version",
    "id",
    "version",
    "category",
    "status",
    "purpose",
    "activate_when",
    "inputs",
    "outputs",
    "related_capabilities",
    "guardrail_hooks",
    "evals",
}
OPTIONAL_KEYS = {"tags"}
FORBIDDEN_PROVIDER_KEYS = {
    "api_key",
    "api_key_env",
    "api_base",
    "model",
    "provider",
    "openai_api_key",
    "anthropic_api_key",
}


class CapabilityError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require_string_list(meta: dict[str, Any], key: str) -> list[str]:
    value = meta.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise CapabilityError(f"{key} must be a list of non-empty strings")
    if len(set(value)) != len(value):
        raise CapabilityError(f"{key} must not contain duplicates")
    return value


def parse_skill_frontmatter(path: Path) -> dict[str, str]:
    """Parse the small portable frontmatter surface SEF requires.

    Agent Skills only need a standard ``SKILL.md``. We intentionally avoid a
    YAML dependency and only read scalar ``name`` and ``description`` fields.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise CapabilityError(f"{path}: SKILL.md must start with YAML frontmatter")
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        raise CapabilityError(f"{path}: unterminated SKILL.md frontmatter")
    values: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in {"name", "description"}:
            values[key] = value
    if not values.get("name") or not values.get("description"):
        raise CapabilityError(f"{path}: frontmatter requires non-empty name and description")
    return values


def _find_forbidden_provider_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
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


def load_capability(directory: Path) -> dict[str, Any]:
    skill_path = directory / "SKILL.md"
    meta_path = directory / "capability.json"
    if not skill_path.is_file():
        raise CapabilityError(f"{directory}: missing SKILL.md")
    if not meta_path.is_file():
        raise CapabilityError(f"{directory}: missing capability.json")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CapabilityError(f"{meta_path}: invalid JSON: {exc}") from exc
    if not isinstance(meta, dict):
        raise CapabilityError(f"{meta_path}: root must be an object")

    unknown = set(meta) - REQUIRED_KEYS - OPTIONAL_KEYS
    missing = REQUIRED_KEYS - set(meta)
    if missing:
        raise CapabilityError(f"{meta_path}: missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise CapabilityError(f"{meta_path}: unknown keys: {', '.join(sorted(unknown))}")
    forbidden = _find_forbidden_provider_keys(meta)
    if forbidden:
        raise CapabilityError(f"{meta_path}: provider/API configuration is forbidden: {', '.join(forbidden)}")

    if meta["schema_version"] != 1:
        raise CapabilityError(f"{meta_path}: schema_version must equal 1")
    cap_id = meta["id"]
    if not isinstance(cap_id, str) or not ID_RE.fullmatch(cap_id):
        raise CapabilityError(f"{meta_path}: id must be lowercase kebab-case")
    if directory.name != cap_id:
        raise CapabilityError(f"{meta_path}: id must match directory name")
    if not isinstance(meta["version"], str) or not SEMVER_RE.fullmatch(meta["version"]):
        raise CapabilityError(f"{meta_path}: version must be semantic version x.y.z")
    if meta["category"] not in ALLOWED_CATEGORIES:
        raise CapabilityError(f"{meta_path}: invalid category")
    if meta["status"] not in ALLOWED_STATUSES:
        raise CapabilityError(f"{meta_path}: invalid status")
    if not isinstance(meta["purpose"], str) or not meta["purpose"].strip():
        raise CapabilityError(f"{meta_path}: purpose must be a non-empty string")

    for key in ("activate_when", "inputs", "outputs", "related_capabilities", "guardrail_hooks", "evals"):
        _require_string_list(meta, key)
    if "tags" in meta:
        _require_string_list(meta, "tags")
    if cap_id in meta["related_capabilities"]:
        raise CapabilityError(f"{meta_path}: capability cannot reference itself")

    skill = parse_skill_frontmatter(skill_path)
    if skill["name"] != cap_id:
        raise CapabilityError(f"{skill_path}: skill name must equal capability id")

    resources: list[dict[str, str]] = []
    for subdir in ("references", "examples"):
        root = directory / subdir
        if root.is_dir():
            for resource in sorted(path for path in root.rglob("*") if path.is_file()):
                resources.append({
                    "path": resource.relative_to(directory).as_posix(),
                    "sha256": _sha256_file(resource),
                })

    return {
        "id": cap_id,
        "version": meta["version"],
        "category": meta["category"],
        "status": meta["status"],
        "purpose": meta["purpose"],
        "description": skill["description"],
        "activate_when": meta["activate_when"],
        "inputs": meta["inputs"],
        "outputs": meta["outputs"],
        "related_capabilities": meta["related_capabilities"],
        "guardrail_hooks": meta["guardrail_hooks"],
        "evals": meta["evals"],
        "tags": meta.get("tags", []),
        "skill_sha256": _sha256_file(skill_path),
        "metadata_sha256": _sha256_file(meta_path),
        # Resource files are indexed for integrity but never injected into the
        # core capability by this registry. Harness progressive disclosure owns loading.
        "resources": resources,
    }


def discover_capability_dirs(root: Path) -> list[Path]:
    if not root.exists():
        raise CapabilityError(f"capability root does not exist: {root}")
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and not path.name.startswith("_") and not path.name.startswith(".")
    )


def _validate_graph(entries: Iterable[dict[str, Any]]) -> None:
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        cap_id = entry["id"]
        if cap_id in by_id:
            raise CapabilityError(f"duplicate capability id: {cap_id}")
        by_id[cap_id] = entry
    for cap_id, entry in by_id.items():
        for related in entry["related_capabilities"]:
            if related not in by_id:
                raise CapabilityError(f"{cap_id}: related capability does not exist: {related}")

    state: dict[str, int] = {cap_id: 0 for cap_id in by_id}
    stack: list[str] = []

    def visit(cap_id: str) -> None:
        if state[cap_id] == 2:
            return
        if state[cap_id] == 1:
            start = stack.index(cap_id) if cap_id in stack else 0
            cycle = stack[start:] + [cap_id]
            raise CapabilityError(f"capability relation cycle: {' -> '.join(cycle)}")
        state[cap_id] = 1
        stack.append(cap_id)
        for related in sorted(by_id[cap_id]["related_capabilities"]):
            visit(related)
        stack.pop()
        state[cap_id] = 2

    for cap_id in sorted(by_id):
        visit(cap_id)


def build_manifest(root: Path) -> dict[str, Any]:
    entries = [load_capability(path) for path in discover_capability_dirs(root)]
    _validate_graph(entries)
    entries.sort(key=lambda item: item["id"])
    payload = {
        "schema": "sef.capability-manifest.v1",
        "capability_count": len(entries),
        "capabilities": entries,
    }
    payload["content_sha256"] = _sha256_bytes(_canonical_json(payload).encode("utf-8"))
    return payload


def write_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = build_manifest(root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def check_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    expected = build_manifest(root)
    try:
        actual = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise CapabilityError(f"manifest unreadable: {manifest_path}: {exc}") from exc
    if actual != expected:
        raise CapabilityError("capability manifest is stale; regenerate it")
    return expected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "manifest", "check-manifest"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--root", default="capabilities")
        if name != "validate":
            cmd.add_argument("--manifest", default="capabilities/manifest.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = Path(args.root)
        if args.command == "validate":
            manifest = build_manifest(root)
        elif args.command == "manifest":
            manifest = write_manifest(root, Path(args.manifest))
        else:
            manifest = check_manifest(root, Path(args.manifest))
        print(json.dumps({"status": "PASS", "capability_count": manifest["capability_count"], "content_sha256": manifest["content_sha256"]}, sort_keys=True))
        return 0
    except CapabilityError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
