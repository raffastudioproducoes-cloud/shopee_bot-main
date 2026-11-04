"""Regressões do bloqueio SemVer em PR de release."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_release_semver import is_material_change, is_valid_step, validate_release


class SemverReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.changelog = "## [Não lançado]\n\n## [3.2.0] - 2026-11-04\n"

    def test_minor_compatible_is_valid(self):
        validate_release("3.1.2", "3.2.0", ["api/routers/dashboard.py"], self.changelog)

    def test_missing_bump_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "sem bump"):
            validate_release("3.1.2", "3.1.2", ["api/account_erasure.py"], self.changelog)

    def test_changelog_missing_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "CHANGELOG"):
            validate_release("3.1.2", "3.2.0", ["api/main.py"], "## [Não lançado]\n")

    def test_arbitrary_jump_is_blocked(self):
        self.assertFalse(is_valid_step("3.1.2", "3.4.0"))
        self.assertFalse(is_valid_step("3.1.2", "3.2.1"))
        self.assertTrue(is_valid_step("3.1.2", "3.1.3"))
        self.assertTrue(is_valid_step("3.1.2", "4.0.0"))

    def test_docs_only_does_not_force_bump(self):
        self.assertFalse(is_material_change("docs/RULES.md"))
        validate_release("3.1.2", "3.1.2", ["docs/RULES.md"], "## [Não lançado]\n")


if __name__ == "__main__":
    unittest.main()
