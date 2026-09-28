import sys
import types
import unittest

pygame = sys.modules.setdefault('pygame', types.ModuleType('pygame'))

from presentation.environment import AMBIENT_DARKNESS, ambient_alpha


class EnvironmentLightingTests(unittest.TestCase):
    def test_caves_are_darker_than_meadow(self):
        self.assertGreater(ambient_alpha('caves'), ambient_alpha('meadow'))

    def test_every_palette_has_a_light_profile(self):
        self.assertEqual(set(AMBIENT_DARKNESS),
                         {'meadow', 'caves', 'ruins', 'sanctum', 'peak'})

    def test_high_contrast_caps_darkness(self):
        self.assertLessEqual(ambient_alpha('caves', high_contrast=True), 72)

    def test_light_strengths_remain_translucent(self):
        for strength in (80, 100, 125, 135):
            self.assertLess(int(strength * 0.32), 64)


if __name__ == '__main__':
    unittest.main()
