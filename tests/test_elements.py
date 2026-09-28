import unittest

from systems.elements import apply_element, damage_multiplier
from systems.status import StatusList


class Target:
    def __init__(self, enemy_type=None, boss_id=None, phase=1):
        self.enemy_type = enemy_type
        self.boss_id = boss_id
        self.phase = phase


class ElementTests(unittest.TestCase):
    def test_fire_detonates_poison(self):
        status = StatusList()
        status.apply('poison')
        reaction = apply_element(status, 'fire')
        self.assertEqual(reaction['id'], 'toxic_blast')
        self.assertFalse(status.has('poison'))
        self.assertTrue(status.has('burn'))

    def test_ice_and_fire_trigger_thermal_shock(self):
        status = StatusList()
        status.apply('burn')
        reaction = apply_element(status, 'ice')
        self.assertEqual(reaction['id'], 'thermal_shock')
        self.assertTrue(status.has('chill'))

    def test_electricity_chains_through_chilled_target(self):
        status = StatusList()
        status.apply('chill')
        self.assertEqual(apply_element(status, 'electric')['id'], 'chain_lightning')

    def test_enemy_weaknesses_change_damage(self):
        self.assertGreater(damage_multiplier(Target('slime'), 'electric'), 1.0)
        self.assertLess(damage_multiplier(Target('skeleton'), 'poison'), 1.0)

    def test_boss_phase_can_modify_resistance(self):
        boss = Target(boss_id='sanctum_guardian', phase=3)
        self.assertLess(damage_multiplier(boss, 'physical'), 0.8)


if __name__ == '__main__':
    unittest.main()
