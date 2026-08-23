import unittest

from legacy_formatter import legacy_fmt_user


class LegacyFormatterTests(unittest.TestCase):
    def test_user_formatter_preserves_existing_behavior(self):
        self.assertEqual(legacy_fmt_user(" alice "), "USER::ALICE")

    def test_user_formatter_handles_none(self):
        self.assertEqual(legacy_fmt_user(None), "USER::<unknown>")


if __name__ == "__main__":
    unittest.main()
