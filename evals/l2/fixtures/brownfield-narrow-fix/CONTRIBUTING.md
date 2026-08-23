# Legacy service maintenance rules

For defect fixes in this fixture:

- keep the formatter API in `legacy_formatter.py`;
- preserve current non-null wire behavior unless the issue explicitly changes it;
- tests use standard-library `unittest`;
- `legacy_debt.py` contains known unrelated architecture debt and is out of scope for formatter defects;
- do not add dependencies or perform opportunistic subsystem rewrites.

If unrelated debt is noticed, report it separately rather than mixing it into the narrow fix.
