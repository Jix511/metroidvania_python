import sys
import types
import unittest

pygame = types.ModuleType('pygame')
pygame.transform = types.SimpleNamespace()
sys.modules.setdefault('pygame', pygame)

from presentation.animation import frame_index, pick_frame, state_elapsed


class AnimationTests(unittest.TestCase):
    def test_looping_animation_wraps(self):
        self.assertEqual(frame_index(4, 0.5, 'run'), 1)

    def test_progress_animation_reaches_last_frame(self):
        self.assertEqual(frame_index(4, 1.0, 'attack', progress=1.0), 3)

    def test_single_frame_atlas_is_stable(self):
        self.assertEqual(frame_index(1, 999, 'idle'), 0)

    def test_missing_animation_falls_back_to_idle(self):
        self.assertEqual(pick_frame({'idle': ['a', 'b']}, 'fall', 0), 'a')

    def test_state_clock_resets_on_transition(self):
        entity = types.SimpleNamespace(anim_phase=0.0)
        self.assertEqual(state_elapsed(entity, 'idle', 5.0), 0.0)
        self.assertEqual(state_elapsed(entity, 'idle', 5.5), 0.5)
        self.assertEqual(state_elapsed(entity, 'attack', 5.5), 0.0)


if __name__ == '__main__':
    unittest.main()
