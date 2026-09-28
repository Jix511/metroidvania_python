import unittest

from systems.aiming import assisted_target, melee_facing


class Rect:
    def __init__(self, x, y):
        self.centerx = x
        self.centery = y


class Target:
    def __init__(self, x, y, alive=True):
        self.rect = Rect(x, y)
        self._alive = alive

    def alive(self):
        return self._alive


class AimingTests(unittest.TestCase):
    def test_cursor_near_enemy_snaps_to_its_center(self):
        enemy = Target(300, 180)
        self.assertEqual(
            assisted_target((100, 200), (285, 165), [enemy]),
            (300, 180))

    def test_free_aim_is_preserved_away_from_enemies(self):
        self.assertEqual(
            assisted_target((100, 200), (500, 80), [Target(300, 200)]),
            (500, 80))

    def test_close_cursor_uses_horizontal_fallback(self):
        self.assertEqual(
            assisted_target((100, 200), (105, 198), [], facing=-1),
            (-80.0, 200))

    def test_melee_faces_nearest_reachable_enemy(self):
        targets = [Target(180, 200), Target(70, 205)]
        self.assertEqual(melee_facing((100, 200), targets, 1), -1)

    def test_melee_keeps_facing_when_targets_are_out_of_range(self):
        self.assertEqual(melee_facing((100, 200), [Target(500, 200)], -1), -1)


if __name__ == '__main__':
    unittest.main()
