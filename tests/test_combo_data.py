import unittest

from constants import CHARACTER_CLASSES
from systems.combo_data import COMBOS


class ComboDataTests(unittest.TestCase):
    def test_every_class_has_ground_and_air_chains(self):
        self.assertEqual(set(COMBOS), set(CHARACTER_CLASSES))
        for chains in COMBOS.values():
            self.assertGreaterEqual(len(chains['ground']), 3)
            self.assertGreaterEqual(len(chains['air']), 2)

    def test_melee_finishers_define_launch_and_downstrike(self):
        for class_id in ('warrior', 'rogue', 'reaper'):
            self.assertGreater(COMBOS[class_id]['ground'][-1]['launch'], 0)
            self.assertTrue(COMBOS[class_id]['air'][-1]['downstrike'])

    def test_ranged_finishers_add_projectiles(self):
        for class_id in ('mage', 'ranger', 'kitsune'):
            self.assertGreaterEqual(COMBOS[class_id]['ground'][-1]['projectiles'], 2)
            self.assertGreaterEqual(COMBOS[class_id]['air'][-1]['projectiles'], 2)

    def test_all_moves_have_positive_timing_and_damage(self):
        for chains in COMBOS.values():
            for moves in chains.values():
                for move in moves:
                    self.assertGreater(move['damage'], 0)
                    self.assertGreater(move['cooldown'], 0)
                    self.assertGreater(move['reach'], 0)
                    self.assertIn('pattern', move)

    def test_melee_moves_define_curved_hit_geometry(self):
        for class_id in ('warrior', 'rogue', 'reaper'):
            for moves in COMBOS[class_id].values():
                for move in moves:
                    self.assertIn(move['pattern'],
                                  {'sweep_high', 'sweep_low', 'spin',
                                   'thrust', 'downstrike'})
                    self.assertGreater(move['arc'], 0)


if __name__ == '__main__':
    unittest.main()
