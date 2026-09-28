import unittest

from systems.achievements import ACHIEVEMENTS, completed, progress


class PlayerStub:
    character_class = 'warrior'
    statistics = {'enemies_defeated': 5, 'damage_dealt': 3000, 'critical_hits': 0,
                  'highest_combo': 3, 'bosses_defeated': 0, 'hits': 0}
    explored_rooms = {'a', 'b'}
    discovered_secrets = {'x'}
    unlocked_achievements = set()


class AchievementTests(unittest.TestCase):
    def test_catalog_has_general_and_class_challenges(self):
        self.assertTrue(any('class' not in item for item in ACHIEVEMENTS.values()))
        classes = {item.get('class') for item in ACHIEVEMENTS.values() if item.get('class')}
        self.assertEqual({'warrior', 'ranger', 'mage', 'rogue', 'kitsune',
                          'reaper'}, classes)

    def test_progress_reads_stats_and_collections(self):
        player = PlayerStub()
        self.assertEqual(5, progress(player, ACHIEVEMENTS['hunter']))
        self.assertEqual(2, progress(player, ACHIEVEMENTS['explorer']))

    def test_class_requirement_is_enforced(self):
        player = PlayerStub()
        self.assertTrue(completed(player, ACHIEVEMENTS['warrior_trial']))
        self.assertFalse(completed(player, ACHIEVEMENTS['mage_trial']))


if __name__ == '__main__':
    unittest.main()
