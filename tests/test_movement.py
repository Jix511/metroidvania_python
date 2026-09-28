import unittest

from systems.movement import approach


class MovementTests(unittest.TestCase):
    def test_approach_never_overshoots(self):
        self.assertEqual(10, approach(0, 10, 20))
        self.assertEqual(-10, approach(0, -10, 20))

    def test_approach_moves_in_both_directions(self):
        self.assertEqual(3, approach(0, 10, 3))
        self.assertEqual(7, approach(10, 0, 3))

    def test_negative_amount_does_not_move(self):
        self.assertEqual(5, approach(5, 10, -1))


if __name__ == '__main__':
    unittest.main()
