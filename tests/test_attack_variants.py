import unittest

from constants import CHARACTER_CLASSES
from systems.attack_variants import (CHARGE_PROFILES, CHARGE_THRESHOLD,
    charge_values, directional_move)


BASE_MOVE = {
    'damage': 1.0, 'reach': 1.0, 'cooldown': 0.3,
    'pattern': 'sweep_high', 'arc': 110,
}


class AttackVariantTests(unittest.TestCase):
    def test_every_class_has_a_charge_identity(self):
        self.assertEqual(set(CHARACTER_CLASSES), set(CHARGE_PROFILES))
        for profile in CHARGE_PROFILES.values():
            self.assertGreater(profile['damage'], 1.0)
            self.assertEqual(len(profile['color']), 3)

    def test_charge_scales_from_normal_to_full_profile(self):
        empty = charge_values('warrior', 0.0)
        full = charge_values('warrior', 1.0)
        self.assertEqual(empty['damage'], 1.0)
        self.assertEqual(empty['reach'], 1.0)
        self.assertEqual(full['damage'], CHARGE_PROFILES['warrior']['damage'])
        self.assertGreater(CHARGE_THRESHOLD, 0)

    def test_up_variant_launches_and_down_variant_descends_in_air(self):
        upward = directional_move(BASE_MOVE, 'up')
        downward = directional_move(BASE_MOVE, 'down', airborne=True)
        self.assertEqual(upward['pattern'], 'sweep_high')
        self.assertGreaterEqual(upward['launch'], 300)
        self.assertEqual(downward['pattern'], 'downstrike')
        self.assertTrue(downward['downstrike'])

    def test_dash_variant_is_a_longer_stronger_thrust(self):
        move = directional_move(BASE_MOVE, 'dash')
        self.assertEqual(move['pattern'], 'thrust')
        self.assertGreater(move['reach'], BASE_MOVE['reach'])
        self.assertGreater(move['damage'], BASE_MOVE['damage'])


if __name__ == '__main__':
    unittest.main()
