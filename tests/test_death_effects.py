import sys
import types
import unittest

pygame = sys.modules.setdefault('pygame', types.ModuleType('pygame'))

from presentation.death_effects import create_death_echo, update_death_echo


class Image:
    def copy(self):
        return self


class DeathEffectTests(unittest.TestCase):
    def test_echo_moves_and_expires(self):
        echo = create_death_echo(Image(), (100, 100), direction=1)
        x0, y0 = echo['x'], echo['y']
        self.assertTrue(update_death_echo(echo, 0.1))
        self.assertNotEqual(echo['x'], x0)
        self.assertNotEqual(echo['y'], y0)
        self.assertFalse(update_death_echo(echo, 1.0))

    def test_boss_echo_lasts_longer(self):
        normal = create_death_echo(Image(), (0, 0))
        boss = create_death_echo(Image(), (0, 0), boss=True)
        self.assertGreater(boss['duration'], normal['duration'])


if __name__ == '__main__':
    unittest.main()
