from unittest import TestCase

from packager.tools.toolbox import build_target_filename


class TestPackage(TestCase):
    def test_build_target_filename_preserves_only_final_extension(self):
        target_name = build_target_filename(
            "Diablo 2 (ChuckRibbits Original 2026) 1.0.vpx",
            "Diablo 2 (Original 2026)",
        )

        self.assertEqual(target_name, "Diablo 2 (Original 2026).vpx")

    def test_build_target_filename_preserves_ini_extension(self):
        target_name = build_target_filename(
            "Diablo 2 (ChuckRibbits Original 2026) 1.0.ini",
            "Diablo 2 (Original 2026)",
        )

        self.assertEqual(target_name, "Diablo 2 (Original 2026).ini")
