import unittest

from systems.spatial import near_view


class Rect:
    def __init__(self, x, y, width, height):
        self.left, self.top = x, y
        self.right, self.bottom = x + width, y + height


class SpatialTests(unittest.TestCase):
    def test_rect_inside_and_margin_are_visible(self):
        self.assertTrue(near_view(Rect(90, 90, 20, 20), (100, 100), 100, 100))
        self.assertTrue(near_view(Rect(151, 95, 5, 5), (100, 100), 100, 100, 10))

    def test_distant_rect_is_culled(self):
        self.assertFalse(near_view(Rect(500, 500, 20, 20), (100, 100), 100, 100, 25))


if __name__ == '__main__':
    unittest.main()
