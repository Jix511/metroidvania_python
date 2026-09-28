import struct
import unittest

from constants import CHARACTER_CLASSES
from presentation.sprite_data import SPRITE_SHEETS, SpriteDataError


class SpriteDataTests(unittest.TestCase):
    def test_every_player_class_has_an_external_sheet(self):
        expected = {f'player:{class_id}' for class_id in CHARACTER_CLASSES}
        self.assertTrue(expected.issubset(SPRITE_SHEETS))
        for sprite_id in expected:
            definition = SPRITE_SHEETS[sprite_id]
            self.assertEqual(definition['canvas'], (80, 56))
            self.assertEqual(definition['scaling'], 'nearest')
            self.assertTrue(definition['source_path'].is_file())

    def test_ranger_pilot_has_required_animations(self):
        ranger = SPRITE_SHEETS['player:ranger']
        self.assertEqual(ranger['canvas'], (80, 56))
        self.assertEqual(ranger['scaling'], 'nearest')
        self.assertEqual(ranger['source_path'].name, 'ranger-female-pilot-v2.png')
        self.assertEqual(set(ranger['animations']),
                         {'idle', 'run', 'jump', 'hurt', 'attack'})
        self.assertEqual(len(ranger['animations']['idle']), 4)
        self.assertEqual(len(ranger['animations']['attack']), 4)

    def test_ranger_source_exists_and_is_rgba_png(self):
        path = SPRITE_SHEETS['player:ranger']['source_path']
        self.assertTrue(path.is_file())
        with path.open('rb') as handle:
            signature = handle.read(8)
            length = struct.unpack('>I', handle.read(4))[0]
            chunk = handle.read(4)
            width, height, bit_depth, color_type = struct.unpack('>IIBB', handle.read(10))
        self.assertEqual(signature, b'\x89PNG\r\n\x1a\n')
        self.assertEqual((length, chunk), (13, b'IHDR'))
        self.assertEqual((width, height), (1312, 1199))
        self.assertEqual(bit_depth, 8)
        self.assertIn(color_type, (4, 6))

    def test_every_combatant_family_has_external_art(self):
        expected = {
            'enemy:slime', 'enemy:skeleton', 'enemy:bat', 'enemy:goblin',
            'enemy:moss_boar', 'enemy:crystal_beetle', 'enemy:ruin_drowned',
            'enemy:rune_acolyte', 'enemy:storm_harpy',
            'miniboss:colossal_slime', 'miniboss:broken_knight',
            'boss:cavern_mother', 'boss:sanctum_guardian', 'boss:void_heart',
        }
        self.assertTrue(expected.issubset(SPRITE_SHEETS))
        for sprite_id in expected:
            definition = SPRITE_SHEETS[sprite_id]
            self.assertTrue(definition['source_path'].is_file())
            self.assertTrue({'idle', 'run', 'attack', 'hurt'}.issubset(
                definition['animations']))

    def test_signature_enemies_share_the_five_row_atlas(self):
        ids = ('moss_boar', 'crystal_beetle', 'ruin_drowned',
               'rune_acolyte', 'storm_harpy')
        definitions = [SPRITE_SHEETS[f'enemy:{enemy_id}'] for enemy_id in ids]
        self.assertEqual({item['source_path'].name for item in definitions},
                         {'zone-enemies-atlas-v1.png'})
        self.assertTrue(all(item['columns'] == 4 and item['rows'] == 5
                            for item in definitions))

    def test_animation_cells_stay_inside_the_grid(self):
        for definition in SPRITE_SHEETS.values():
            for cells in definition['animations'].values():
                for column, row in cells:
                    self.assertLess(column, definition['columns'])
                    self.assertLess(row, definition['rows'])


if __name__ == '__main__':
    unittest.main()
