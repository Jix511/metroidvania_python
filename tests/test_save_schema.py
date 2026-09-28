import unittest

from systems.save_schema import (CURRENT_SAVE_VERSION,
    is_player_save_candidate, migrate_player_save)


class SaveSchemaTests(unittest.TestCase):
    def test_legacy_speed_and_boss_flag_are_migrated(self):
        legacy = {
            'character_class': 'warrior',
            'position': [10, 20],
            'level': 2,
            'speed': 5,
            'base_speed': 4,
            'boss_defeated': True,
        }

        migrated = migrate_player_save(legacy)

        self.assertEqual(migrated['speed'], 300)
        self.assertEqual(migrated['base_speed'], 240)
        self.assertEqual(migrated['boss_defeated_ids'], ['sanctum_guardian'])
        self.assertEqual(migrated['explored_zones'], ['meadow'])
        self.assertEqual(migrated['quest_states'], {})
        self.assertEqual(migrated['collected_items'], [])
        self.assertEqual(migrated['discovered_secrets'], [])
        self.assertEqual(migrated['opened_secret_chests'], [])
        self.assertEqual(migrated['save_version'], CURRENT_SAVE_VERSION)

    def test_legacy_save_discovers_its_current_zone(self):
        legacy = {
            'character_class': 'ranger',
            'position': [70 * 16, 20],
            'level': 4,
        }

        migrated = migrate_player_save(legacy)

        self.assertEqual(migrated['explored_zones'], ['meadow', 'sanctum'])
        self.assertGreater(migrated['position'][0], 180 * 16)

    def test_version_12_position_is_remapped_to_the_same_expanded_zone(self):
        old = {
            'character_class': 'warrior', 'position': [35 * 16, 20],
            'respawn_point': [35 * 16, 20], 'level': 2, 'save_version': 12,
        }
        migrated = migrate_player_save(old)
        self.assertEqual(migrated['explored_zones'], ['caves', 'meadow'])
        self.assertGreaterEqual(migrated['position'][0], 60 * 16)
        self.assertGreaterEqual(migrated['respawn_point'][0], 60 * 16)

    def test_unknown_explored_zones_are_removed(self):
        save = {
            'character_class': 'mage',
            'position': [10 * 16, 20],
            'level': 3,
            'explored_zones': ['meadow', 'developer_room', {}],
        }

        migrated = migrate_player_save(save)

        self.assertEqual(migrated['explored_zones'], ['meadow'])

    def test_legacy_save_discovers_its_current_room(self):
        save = {
            'character_class': 'warrior', 'position': [85 * 16, 200],
            'level': 2, 'explored_zones': ['meadow', 'caves'],
            'save_version': 15,
        }
        migrated = migrate_player_save(save)
        self.assertIn('caves_depths', migrated['explored_rooms'])

    def test_completed_encounters_are_validated(self):
        save = {
            'character_class': 'warrior', 'position': [45 * 16, 200],
            'level': 2, 'save_version': CURRENT_SAVE_VERSION,
            'completed_encounters': ['meadow_gate', 'deleted_room', 7],
        }
        migrated = migrate_player_save(save)
        self.assertEqual(migrated['completed_encounters'], ['meadow_gate'])

    def test_completed_routes_are_validated(self):
        save = {
            'character_class': 'warrior', 'position': [158 * 16, 700],
            'level': 2, 'save_version': 16,
            'completed_routes': ['ruins_dash_tunnel', 'removed_route', None],
        }
        migrated = migrate_player_save(save)
        self.assertEqual(migrated['completed_routes'], ['ruins_dash_tunnel'])

    def test_invalid_position_is_rejected(self):
        invalid = {'character_class': 'mage', 'position': ['x'], 'level': 1}

        self.assertFalse(is_player_save_candidate(invalid))


if __name__ == '__main__':
    unittest.main()
