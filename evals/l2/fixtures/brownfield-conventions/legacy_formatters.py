def _legacy_text(value):
    if value is None:
        return "<unknown>"
    text = str(value).strip()
    return text.upper() if text else "<unknown>"


def legacy_fmt_role(value):
    return f"ROLE::{_legacy_text(value)}"
