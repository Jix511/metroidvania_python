import unittest

from systems.impact_physics import ground_impact, launch_response, wall_bounce


class ImpactPhysicsTests(unittest.TestCase):
    def test_light_enemy_launches_farther_than_heavy_enemy(self):
        light = launch_response(0.6, 240, -320)
        heavy = launch_response(1.6, 240, -320)
        self.assertGreater(abs(light[0]), abs(heavy[0]))
        self.assertGreater(abs(light[1]), abs(heavy[1]))

    def test_juggle_resistance_reduces_repeated_launch(self):
        first = launch_response(1.0, 200, -300, 0.0)
        repeated = launch_response(1.0, 200, -300, 0.6)
        self.assertGreater(abs(first[1]), abs(repeated[1]))

    def test_fast_wall_hit_rebounds_and_causes_damage(self):
        rebound, damage = wall_bounce(320, 1.0)
        self.assertLess(rebound, 0)
        self.assertGreater(damage, 0)

    def test_slow_wall_hit_does_not_trigger_impact(self):
        self.assertEqual(wall_bounce(100, 1.0), (0.0, 0))

    def test_hard_landing_knocks_down(self):
        duration, damage = ground_impact(480, 1.0)
        self.assertGreater(duration, 0)
        self.assertGreater(damage, 0)


if __name__ == '__main__':
    unittest.main()
