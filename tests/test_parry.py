import unittest

from systems.run_stats import normalize_stats


class ParryDataTests(unittest.TestCase):
    def test_old_saves_receive_parry_counter(self):
        self.assertEqual(0, normalize_stats({})['perfect_parries'])

    def test_parry_counter_is_sanitized(self):
        self.assertEqual(4, normalize_stats({'perfect_parries': 4})['perfect_parries'])
        self.assertEqual(0, normalize_stats({'perfect_parries': -2})['perfect_parries'])


if __name__ == '__main__':
    unittest.main()
