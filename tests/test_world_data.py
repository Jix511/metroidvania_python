import unittest

from world.world_data import (
    BOSS_ARENAS,
    ABILITY_ROUTES,
    CHECKPOINT_DEFS,
    DIVIDERS,
    ENEMY_SPAWNS,
    GATE_DEFS,
    LOAD_SPAWNS,
    LOOT_SPAWNS,
    MAP_HEIGHT,
    MAP_WIDTH,
    MINIBOSS_SPAWNS,
    MOVING_PLATFORMS,
    ROOM_DEFS,
    SHOPKEEPER,
    TUTORIAL_SIGN_DEFS,
    ZONE_DEFS,
)


class WorldDataTests(unittest.TestCase):
    def test_world_dimensions_and_content_counts(self):
        self.assertEqual((MAP_WIDTH, MAP_HEIGHT), (300, 50))
        self.assertEqual(len(GATE_DEFS), 4)
        self.assertEqual(len(DIVIDERS), 4)
        self.assertEqual(len(ZONE_DEFS), 5)
        self.assertEqual(len(ROOM_DEFS), 15)
        self.assertEqual(len(ABILITY_ROUTES), 5)
        self.assertEqual(len(CHECKPOINT_DEFS), 5)
        self.assertEqual(len(TUTORIAL_SIGN_DEFS), 5)
        self.assertEqual(len(ENEMY_SPAWNS), 17)
        self.assertEqual(len(LOAD_SPAWNS), 10)
        self.assertEqual(len(MINIBOSS_SPAWNS), 2)
        self.assertEqual(len(BOSS_ARENAS), 3)
        self.assertEqual(len(MOVING_PLATFORMS), 5)
        self.assertEqual(len(LOOT_SPAWNS), 2)

    def test_zones_cover_the_map_without_gaps(self):
        cursor = 0
        for zone in ZONE_DEFS:
            self.assertEqual(zone['x0'], cursor)
            self.assertEqual(zone['x1'] - zone['x0'] + 1, 60)
            cursor = zone['x1'] + 1
        self.assertGreaterEqual(cursor, MAP_WIDTH)

    def test_each_zone_is_divided_into_three_contiguous_rooms(self):
        cursor = 0
        for zone in ZONE_DEFS:
            rooms = [room for room in ROOM_DEFS if room['zone_id'] == zone['id']]
            self.assertEqual(len(rooms), 3)
            self.assertEqual(rooms[0]['x0'], zone['x0'])
            self.assertEqual(rooms[-1]['x1'], zone['x1'])
            for room in rooms:
                self.assertEqual(room['x0'], cursor)
                cursor = room['x1'] + 1
        self.assertEqual(cursor, MAP_WIDTH)

    def test_landmarks_belong_to_their_declared_rooms(self):
        zones = {zone['id']: zone for zone in ZONE_DEFS}
        for checkpoint in CHECKPOINT_DEFS:
            zone = zones[checkpoint['zone_id']]
            self.assertLessEqual(zone['x0'], checkpoint['tx'])
            self.assertLessEqual(checkpoint['tx'], zone['x1'])
        expected_boss_zones = {
            'cavern_mother': 'caves',
            'sanctum_guardian': 'sanctum',
            'void_heart': 'peak',
        }
        for arena in BOSS_ARENAS:
            zone = zones[expected_boss_zones[arena['id']]]
            self.assertLessEqual(zone['x0'], arena['trigger_tx'])
            self.assertLessEqual(arena['spawn_tx'], zone['x1'])

    def test_world_landmarks_keep_their_original_positions(self):
        self.assertEqual((SHOPKEEPER['tx'], SHOPKEEPER['ty']), (41, 47))
        self.assertEqual(ENEMY_SPAWNS[0], ('slime', 15))
        self.assertEqual(MINIBOSS_SPAWNS[-1], ('broken_knight', 157))
        self.assertEqual(
            {(loot['tx'], loot['ty']) for loot in LOOT_SPAWNS},
            {(90, 31), (272, 30)},
        )

    def test_every_divider_uses_a_declared_gate(self):
        self.assertEqual(
            {divider['gate_id'] for divider in DIVIDERS},
            set(GATE_DEFS),
        )

    def test_dividers_are_local_doorways_not_full_height_walls(self):
        for divider in DIVIDERS:
            self.assertGreater(divider['wall_y0'], MAP_HEIGHT // 2)
            self.assertLessEqual(divider['wall_y1'] - divider['wall_y0'], 14)

    def test_each_zone_has_a_moving_traversal_route(self):
        self.assertEqual({platform['zone_id'] for platform in MOVING_PLATFORMS},
                         {zone['id'] for zone in ZONE_DEFS})

    def test_each_zone_has_its_signature_enemy(self):
        signature = {
            'meadow': 'moss_boar', 'caves': 'crystal_beetle',
            'ruins': 'ruin_drowned', 'sanctum': 'rune_acolyte',
            'peak': 'storm_harpy',
        }
        for zone in ZONE_DEFS:
            enemies = {enemy for enemy, tx in ENEMY_SPAWNS
                       if zone['x0'] <= tx <= zone['x1']}
            self.assertIn(signature[zone['id']], enemies)


if __name__ == '__main__':
    unittest.main()
