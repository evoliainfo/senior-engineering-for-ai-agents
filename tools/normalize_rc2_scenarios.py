#!/usr/bin/env python3
"""One-shot migration helper for the initial RC-2 diagnostic contracts.

Converts the research-only scenario fields to the existing eval harness schema.
This file is intentionally temporary and may be removed after the migration commit.
"""
from pathlib import Path
import json

root = Path('evals/diagnostic/rc2_polarity')
for path in sorted(root.rglob('*.json')):
    data = json.loads(path.read_text(encoding='utf-8'))
    data['set'] = 'DEV'
    if 'expect' not in data and 'plan_expect' in data:
        data['expect'] = data.pop('plan_expect')
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(path)
