import unittest

from systems.run_stats import normalize_stats


class PostureStatsTests(unittest.TestCase):
    def test_legacy_stats_gain_posture_counters(self):
        stats = normalize_stats({})
        self.assertEqual(0, stats['posture_breaks'])
        self.assertEqual(0, stats['executions'])


if __name__ == '__main__':
    unittest.main()
