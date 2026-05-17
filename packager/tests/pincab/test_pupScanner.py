import logging
import unittest

from packager.model.baseModel import BaseModel


class PupScannerTestCase(unittest.TestCase):
    def setUp(self):
        self.base_model = BaseModel(logging.getLogger(), 'dev', '1.2')
        self.scanner = self.base_model.pupScanner

    def test_base_table_name_extraction(self):
        self.assertEqual(self.scanner._base_table_name('Aliens - Pup Pack Edition (Original 2020)'), 'Aliens')
        self.assertEqual(self.scanner._base_table_name('Flash Gordon - PuP Pack Patch (Bally 1981)'), 'Flash Gordon')
        self.assertEqual(self.scanner._base_table_name('Bourne Identity - PuP-Pack Edition (Original 2024)'), 'Bourne Identity')

    def test_find_for_table_matches_pup_pack(self):
        results = self.scanner.find_for_table('Aliens')
        self.assertIn('Aliens - Pup Pack Edition (Original 2020)', results)
        self.assertTrue(any('Pup Pack' in name or 'PuP-Pack' in name for name in results))


if __name__ == '__main__':
    unittest.main()
