# Legacy formatter conventions

This repository intentionally uses a small legacy formatter module. For narrow formatter work:

- keep formatter helpers in `legacy_formatters.py`;
- public formatter names use `legacy_fmt_<noun>`;
- wire values use `<NOUN>::<UPPERCASE_VALUE>`;
- `None` or blank input becomes `<unknown>`;
- tests use the standard-library `unittest` style in `test_legacy_formatters.py`;
- do not add dependencies or split this small module into a new architecture layer.

These conventions are deliberate for this repository even if another project might choose a different structure.
