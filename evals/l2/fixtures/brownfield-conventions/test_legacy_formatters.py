import unittest

from legacy_formatters import legacy_fmt_role


class LegacyFormatterTests(unittest.TestCase):
    def test_role_formatter_preserves_wire_style(self):
        self.assertEqual(legacy_fmt_role(" admin "), "ROLE::ADMIN")

    def test_role_formatter_handles_missing_values(self):
        self.assertEqual(legacy_fmt_role(None), "ROLE::<unknown>")


if __name__ == "__main__":
    unittest.main()
