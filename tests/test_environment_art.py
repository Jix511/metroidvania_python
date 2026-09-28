import sys
import types
import unittest

pygame = sys.modules.setdefault('pygame', types.ModuleType('pygame'))

from presentation.environment import PALETTES


class EnvironmentArtTests(unittest.TestCase):
    def test_all_five_biomes_have_distinct_palettes(self):
        self.assertEqual(len(PALETTES), 5)
        self.assertEqual(len(set(PALETTES.values())), 5)

    def test_each_biome_has_three_depth_colors(self):
        for palette in PALETTES.values():
            self.assertEqual(len(palette), 3)


if __name__ == '__main__':
    unittest.main()
