import unittest

from systems.run_stats import STAT_DEFAULTS, format_play_time, normalize_stats


class RunStatsTests(unittest.TestCase):
    def test_legacy_save_receives_all_counters(self):
        self.assertEqual(set(STAT_DEFAULTS), set(normalize_stats()))

    def test_invalid_and_negative_values_are_sanitized(self):
        stats = normalize_stats({'damage_dealt': -10, 'hits': 'many', 'play_time': 12.5})
        self.assertEqual(0, stats['damage_dealt'])
        self.assertEqual(0, stats['hits'])
        self.assertEqual(12.5, stats['play_time'])

    def test_play_time_format(self):
        self.assertEqual('01:01:01', format_play_time(3661.9))


if __name__ == '__main__':
    unittest.main()
