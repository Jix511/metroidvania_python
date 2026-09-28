import ast
import unittest
from pathlib import Path

from systems import controls


def _spell_data():
    tree = ast.parse(Path('systems/spells.py').read_text(encoding='utf-8'))
    data = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('ABILITY_SPELL', 'SPELL_DEFS'):
                data[node.targets[0].id] = ast.literal_eval(node.value)
    return data['ABILITY_SPELL'], data['SPELL_DEFS']


class SpellControlTests(unittest.TestCase):
    def test_every_ability_points_to_a_defined_spell(self):
        ability_spell, spell_defs = _spell_data()
        self.assertTrue(set(ability_spell.values()).issubset(spell_defs))

    def test_every_spell_has_one_valid_control_source(self):
        _, spell_defs = _spell_data()
        for spell_id, definition in spell_defs.items():
            sources = [name for name in ('action', 'key', 'passive')
                       if definition.get(name)]
            self.assertEqual(len(sources), 1, spell_id)
            if 'action' in definition:
                self.assertIn(definition['action'], controls.DEFAULTS, spell_id)


if __name__ == '__main__':
    unittest.main()
