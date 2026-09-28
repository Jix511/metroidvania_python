import unittest

from presentation.effect_data import (EFFECT_PRESETS, EffectDataError,
                                      validate_effect)
from presentation.fx import Particle, Particles
from world.world_data import ZONE_DEFS


class EffectTests(unittest.TestCase):
    def test_core_and_ambient_presets_exist(self):
        for effect_id in ('hurt', 'hit', 'critical', 'death', 'level_up',
                          'checkpoint', 'gate', 'boss_spawn', 'victory'):
            self.assertIn(effect_id, EFFECT_PRESETS)
        for zone in ZONE_DEFS:
            self.assertIn(f"ambient_{zone['id']}", EFFECT_PRESETS)

    def test_invalid_shape_and_color_are_rejected(self):
        base = {
            'count': 1, 'colors': [[255, 255, 255]], 'speed': [1, 2],
            'life': [0.1, 0.2], 'size': [1, 2], 'gravity': 0,
            'drag': 0, 'shape': 'circle', 'layer': 1,
        }
        with self.assertRaises(EffectDataError):
            validate_effect('bad', dict(base, shape='triangle'))
        with self.assertRaises(EffectDataError):
            validate_effect('bad', dict(base, colors=[[300, 0, 0]]))

    def test_particle_lifecycle_and_drag(self):
        particle = Particle(vx=100, life=0.2, drag=1.0)
        self.assertTrue(particle.update(0.1))
        self.assertLess(particle.vx, 100)
        self.assertFalse(particle.update(0.11))

    def test_pool_respects_capacity_and_reuses_particles(self):
        particles = Particles(cap=5)
        particles.emit('hit', 10, 20, count=8)
        self.assertEqual(len(particles.parts), 5)
        identities = {id(particle) for particle in particles.parts}
        particles.update(10.0)
        self.assertEqual(len(particles.parts), 0)
        particles.emit('hurt', 10, 20, count=3)
        self.assertTrue(all(id(particle) in identities for particle in particles.parts))

    def test_legacy_burst_api_remains_available(self):
        particles = Particles(cap=10)
        particles.burst(0, 0, n=4, color=(1, 2, 3))
        self.assertEqual(len(particles.parts), 4)
        self.assertTrue(all(particle.color == (1, 2, 3) for particle in particles.parts))


if __name__ == '__main__':
    unittest.main()
