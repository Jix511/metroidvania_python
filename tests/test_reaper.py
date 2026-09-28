import ast
import unittest
from pathlib import Path

from constants import CHARACTER_CLASSES
from systems.combo_data import COMBOS
from systems.skill_data import CLASS_SKILL_TREES
from systems.souls import gain_souls, soul_limit


def _spell_data():
    tree = ast.parse(Path('systems/spells.py').read_text(encoding='utf-8'))
    data = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('ABILITY_SPELL', 'SPELL_DEFS'):
                data[node.targets[0].id] = ast.literal_eval(node.value)
    return data


class ReaperTests(unittest.TestCase):
    def test_reaper_content_contract_is_complete(self):
        spells = _spell_data()
        self.assertEqual(CHARACTER_CLASSES['reaper']['starting_ability'], 'soul_reap')
        self.assertIn('reaper', COMBOS)
        self.assertEqual(len(CLASS_SKILL_TREES['reaper']), 7)
        self.assertEqual(spells['ABILITY_SPELL']['soul_reap'], 'soul_reap')
        self.assertEqual(spells['SPELL_DEFS']['soul_reap']['key'], 'RMB')

    def test_soul_meter_is_capped(self):
        current, gained = gain_souls(0, 140)
        self.assertEqual((current, gained), (100, 100))
        self.assertEqual(gain_souls(current, 20), (100, 0))

    def test_reservoir_increases_soul_capacity(self):
        self.assertEqual(soul_limit(True), 125)
        self.assertEqual(gain_souls(100, 40, True), (125, 25))


if __name__ == '__main__':
    unittest.main()
