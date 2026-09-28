import sys
import types
import unittest

pygame = sys.modules.setdefault('pygame', types.ModuleType('pygame'))

from presentation.frame_enrichment import TARGET_COUNTS


class FrameEnrichmentTests(unittest.TestCase):
    def test_every_core_state_has_multiple_frames(self):
        self.assertGreaterEqual(TARGET_COUNTS['idle'], 4)
        self.assertGreaterEqual(TARGET_COUNTS['run'], 6)
        self.assertGreaterEqual(TARGET_COUNTS['attack'], 6)
        self.assertGreaterEqual(TARGET_COUNTS['death'], 5)

    def test_damage_and_jump_are_not_single_frame(self):
        self.assertGreater(TARGET_COUNTS['hurt'], 1)
        self.assertGreater(TARGET_COUNTS['jump'], 1)


if __name__ == '__main__':
    unittest.main()
