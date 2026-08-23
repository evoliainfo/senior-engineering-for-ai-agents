#!/usr/bin/env python3
"""Deterministic reference adapter for L2 harness solvability tests only."""
from __future__ import annotations

import json
import os
from pathlib import Path

repo = Path(os.environ["SEF_L2_REPO"])
scenario = os.environ["SEF_L2_SCENARIO_ID"]
result_path = Path(os.environ["SEF_L2_RESULT_PATH"])

if scenario == "BROWN-001":
    module = repo / "legacy_formatters.py"
    text = module.read_text(encoding="utf-8")
    if "def legacy_fmt_status" not in text:
        text += "\n\ndef legacy_fmt_status(value):\n    return f\"STATUS::{_legacy_text(value)}\"\n"
        module.write_text(text, encoding="utf-8")
    tests = repo / "test_legacy_formatters.py"
    test_text = tests.read_text(encoding="utf-8")
    if "StatusFormatterRegressionTests" not in test_text:
        test_text += '''\n\nclass StatusFormatterRegressionTests(unittest.TestCase):\n    def test_status_formatter_preserves_wire_style(self):\n        from legacy_formatters import legacy_fmt_status\n        self.assertEqual(legacy_fmt_status(" ready "), "STATUS::READY")\n\n    def test_status_formatter_handles_missing_values(self):\n        from legacy_formatters import legacy_fmt_status\n        self.assertEqual(legacy_fmt_status(None), "STATUS::<unknown>")\n'''
        tests.write_text(test_text, encoding="utf-8")
    summary = "Added the status formatter and regression tests using the repository's existing legacy formatter and unittest conventions."
elif scenario == "BROWN-003":
    module = repo / "legacy_formatter.py"
    text = module.read_text(encoding="utf-8")
    text = text.replace(
        'def legacy_fmt_user(value):\n    return "USER::" + value.strip().upper()\n',
        'def legacy_fmt_user(value):\n    if value is None:\n        return "USER::<unknown>"\n    return "USER::" + value.strip().upper()\n',
    )
    module.write_text(text, encoding="utf-8")
    summary = "Fixed only the null-handling defect. Unrelated debt in legacy_debt.py remains visible and intentionally untouched."
else:
    raise SystemExit(f"unsupported reference scenario: {scenario}")

result_path.write_text(json.dumps({"scenario_id": scenario, "summary": summary}, indent=2) + "\n", encoding="utf-8")
print(summary)
