import unittest

from systems.bestiary import CATALOG


class PostureAITests(unittest.TestCase):
    def test_bestiary_explains_posture_for_every_entry(self):
        for entry in CATALOG.values():
            text = f"{entry['trait']} {entry['tip']}".lower()
            self.assertIn('postura', text)


if __name__ == '__main__':
    unittest.main()
