import unittest

from systems.balance_data import (BOSS_DEFS, ELITE_AFFIXES, ENEMY_STATS,
    MINIBOSS_DEFS, PHASE_THRESHOLDS)


class BalanceDataTests(unittest.TestCase):
    def test_all_expected_definitions_are_loaded(self):
        self.assertEqual(set(ENEMY_STATS), {
            'slime', 'skeleton', 'bat', 'goblin', 'moss_boar',
            'crystal_beetle', 'ruin_drowned', 'rune_acolyte', 'storm_harpy',
        })
        self.assertEqual(set(MINIBOSS_DEFS), {'colossal_slime', 'broken_knight'})
        self.assertEqual(set(BOSS_DEFS), {
            'sanctum_guardian', 'cavern_mother', 'void_heart',
        })
        self.assertEqual(len(ELITE_AFFIXES), 5)

    def test_runtime_types_are_restored_from_json(self):
        self.assertIsInstance(ENEMY_STATS['slime']['color'], tuple)
        self.assertEqual(ELITE_AFFIXES[0]['status'], ('burn', 2.0))
        self.assertEqual(PHASE_THRESHOLDS, [(0.7, 1), (0.4, 2), (0.0, 3)])
        self.assertEqual(set(BOSS_DEFS['void_heart']['tuning']), {1, 2, 3})
        self.assertEqual(set(BOSS_DEFS['void_heart']['phases']), {1, 2, 3})
        self.assertEqual(BOSS_DEFS['void_heart']['phases'][3]['entry'], 'meteor')
        self.assertIsInstance(BOSS_DEFS['cavern_mother']['phases'][2]['color'], tuple)
        for boss in BOSS_DEFS.values():
            self.assertTrue(boss['epithet'])
            self.assertTrue(boss['intro'])
            self.assertTrue(boss['restoration'])
        self.assertEqual(BOSS_DEFS['sanctum_guardian']['loot'][0],
                         ('weapon', 'legendary'))
        for enemy in ENEMY_STATS.values():
            self.assertGreater(enemy['weight'], 0)
            self.assertEqual(set(enemy['ai']),
                             {'detection', 'leash', 'memory', 'attack_cooldown'})
            self.assertIsInstance(enemy['behavior'], str)
            self.assertIsInstance(enemy['flying'], bool)

    def test_representative_balance_values_are_preserved(self):
        self.assertEqual(ENEMY_STATS['goblin']['damage'], 10)
        self.assertEqual(MINIBOSS_DEFS['broken_knight']['health'], 220)
        self.assertEqual(BOSS_DEFS['cavern_mother']['attacks']['spread'], 3)
        self.assertEqual(BOSS_DEFS['void_heart']['health'], 800)
        self.assertEqual(BOSS_DEFS['sanctum_guardian']['phases'][3]['entry'], 'ring')
        self.assertGreater(ENEMY_STATS['bat']['ai']['detection'],
                           ENEMY_STATS['slime']['ai']['detection'])


if __name__ == '__main__':
    unittest.main()
