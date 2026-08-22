#!/usr/bin/env python3
"""Executable RC-1 additive-routing candidate.

This file is intentionally separate from the canonical ``sef.py`` while the
candidate is evaluated. It loads the frozen v1.4 runtime, adds only the six
accepted RC-1 concept signals to request routing, and preserves every legacy
route. Promotion into ``sef.py`` requires a separate reviewed integration step.
"""
from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "sef_base.py" if (HERE / "sef_base.py").exists() else HERE / "sef.py"
SHADOW_PATH = HERE / "rc1_shadow.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sef = _load_module("sef_rc1_base", BASE_PATH)
shadow = _load_module("sef_rc1_shadow", SHADOW_PATH)

_ORIGINAL_REQUEST_CHANGE = sef._request_change
_ORIGINAL_INSTALL = sef.install


def _rc1_request_change(profile, request):
    """Add RC-1 concept signals without removing or downgrading legacy signals."""
    change = copy.deepcopy(_ORIGINAL_REQUEST_CHANGE(profile, request))
    triggers = set(change.get("triggers", []))
    contexts = set(change.get("contexts", []))
    execution_contexts = set(change.get("execution_contexts", []))
    evidence = list(change.get("request_detection", []))

    detected = shadow.detect_concepts(request)
    for observation in detected.get("observations", []):
        concept = str(observation.get("concept") or "")
        if concept == "AUTHORIZATION":
            triggers.add("AUTHZ_CHANGED")
        elif concept == "DATABASE_MIGRATION":
            triggers.add("DATABASE_SCHEMA_CHANGED")
            contexts.add("DATABASE")
            execution_contexts.add("DATABASE")
        elif concept == "WEBHOOK_TRUST":
            triggers.add("INBOUND_WEBHOOK_ADDED")
            contexts.update({"INBOUND_WEBHOOK", "PUBLIC_API"})
            execution_contexts.update({"INBOUND_WEBHOOK", "PUBLIC_API"})
        elif concept == "EXTERNAL_SUPPLIER":
            # Existing v1.4 policy already models supplier governance from the
            # EXTERNAL_SAAS context; RC-1 only supplies the missing request signal.
            contexts.add("EXTERNAL_SAAS")
            execution_contexts.add("EXTERNAL_SAAS")
        elif concept == "BACKGROUND_JOB":
            contexts.add("BACKGROUND_JOB")
            execution_contexts.add("BACKGROUND_JOB")
        elif concept == "SEO_WEB_DISCOVERABILITY":
            execution_contexts.add("SEO_WEB_DISCOVERABILITY")
        else:
            continue

        evidence.append({
            "trigger": f"RC1_CONCEPT:{concept}",
            "reason": "deterministic canonical concept detected",
            "source": "rc1_additive_candidate",
            "concept_evidence": observation.get("evidence", []),
        })

    # Additive invariant: candidate sets are supersets of legacy request sets.
    change["triggers"] = sorted(triggers)
    change["contexts"] = sorted(contexts)
    change["execution_contexts"] = sorted(execution_contexts)
    change["request_detection"] = evidence
    change["rc1_candidate"] = {
        "mode": "ADDITIVE",
        "concepts": sorted(
            str(item.get("concept")) for item in detected.get("observations", []) if item.get("concept")
        ),
        "routing_effect": "ADD_ONLY",
    }
    return change


def _candidate_install(repo, github=False, brief="", mode="ADOPT"):
    """Install the candidate wrapper while retaining the canonical base runtime."""
    result = _ORIGINAL_INSTALL(repo, github=github, brief=brief, mode=mode)
    if result.get("status") != "PASS":
        return result
    repo = Path(repo).resolve()
    runtime_dir = repo / ".sef"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    # Original install copied the canonical base to .sef/sef.py. Preserve it,
    # then place this candidate wrapper at the public runtime path.
    shutil.copy2(runtime_dir / "sef.py", runtime_dir / "sef_base.py")
    shutil.copy2(Path(__file__).resolve(), runtime_dir / "sef.py")
    shutil.copy2(SHADOW_PATH, runtime_dir / "rc1_shadow.py")
    result = dict(result)
    result["candidate"] = "RC1_ADDITIVE"
    result["candidate_runtime_files"] = [".sef/sef.py", ".sef/sef_base.py", ".sef/rc1_shadow.py"]
    return result


sef._request_change = _rc1_request_change
sef.install = _candidate_install
# init_project/adopt_project resolve the module-global ``install`` at call time,
# so replacing sef.install is sufficient for fixture installation.


def main() -> int:
    return int(sef.main())


if __name__ == "__main__":
    raise SystemExit(main())
