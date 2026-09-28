import unittest

from systems.combat_geometry import arc_intersects_rect


class CombatGeometryTests(unittest.TestCase):
    def test_forward_sweep_hits_front_but_not_back(self):
        origin = (100, 100)
        self.assertTrue(arc_intersects_rect(origin, (135, 90, 20, 20),
                                            1, 70, 110))
        self.assertFalse(arc_intersects_rect(origin, (45, 90, 20, 20),
                                             1, 70, 110))

    def test_facing_left_mirrors_the_sector(self):
        origin = (100, 100)
        self.assertTrue(arc_intersects_rect(origin, (45, 90, 20, 20),
                                            -1, 70, 110))
        self.assertFalse(arc_intersects_rect(origin, (135, 90, 20, 20),
                                             -1, 70, 110))

    def test_high_and_low_sweeps_select_different_targets(self):
        origin = (100, 100)
        high = (135, 52, 16, 16)
        low = (135, 132, 16, 16)
        self.assertTrue(arc_intersects_rect(origin, high, 1, 80, 70, -35))
        self.assertFalse(arc_intersects_rect(origin, low, 1, 80, 70, -35))
        self.assertTrue(arc_intersects_rect(origin, low, 1, 80, 70, 35))

    def test_spin_hits_in_every_direction(self):
        for rect in ((135, 90, 20, 20), (45, 90, 20, 20),
                     (90, 45, 20, 20), (90, 135, 20, 20)):
            self.assertTrue(arc_intersects_rect((100, 100), rect, 1,
                                                70, 360))


if __name__ == '__main__':
    unittest.main()
