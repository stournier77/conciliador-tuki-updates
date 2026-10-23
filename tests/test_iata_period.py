import importlib.util
from pathlib import Path
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]

class PeriodTests(unittest.TestCase):
    def test_both_platforms(self):
        for folder in ('APP_MAC', 'APP_PC'):
            spec = importlib.util.spec_from_file_location('period_' + folder, ROOT / folder / 'iata_period.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            detect = module.period_from_text
            self.assertEqual(detect('Billing Period: 261002 (08-OCT-2026 to 15-OCT-2026)'), (date(2026, 10, 8), date(2026, 10, 15)))
            self.assertEqual(detect('billing period: 261201 (28-DEC-2026\n to 04-JAN-2027)'), (date(2026, 12, 28), date(2027, 1, 4)))
            for text in ('', 'Issue date: 08-OCT-2026', 'Billing Period: 261002 (31-FEB-2026 to 15-MAR-2026)', 'Billing Period: 261002 (15-OCT-2026 to 08-OCT-2026)'):
                self.assertIsNone(detect(text))

if __name__ == '__main__':
    unittest.main()
