import unittest

from systems.encounter_data import ENCOUNTERS
from systems.balance_data import ENEMY_STATS
from world.world_data import ROOM_DEFS, ZONE_DEFS


class EncounterDataTests(unittest.TestCase):
    def test_each_zone_has_one_room_encounter(self):
        rooms = {room['id']: room for room in ROOM_DEFS}
        zones = [rooms[room_id]['zone_id'] for room_id in ENCOUNTERS]
        self.assertEqual(set(zones), {zone['id'] for zone in ZONE_DEFS})
        self.assertEqual(len(zones), len(set(zones)))

    def test_waves_use_known_enemies(self):
        for encounter in ENCOUNTERS.values():
            self.assertGreaterEqual(len(encounter['waves']), 2)
            for wave in encounter['waves']:
                self.assertTrue(wave)
                self.assertTrue(set(wave).issubset(ENEMY_STATS))

    def test_rewards_grow_toward_the_peak(self):
        rewards = [ENCOUNTERS[room_id]['reward']['xp'] for room_id in (
            'meadow_gate', 'caves_depths', 'ruins_bastion',
            'sanctum_steps', 'peak_eye')]
        self.assertEqual(rewards, sorted(rewards))
        self.assertEqual(ENCOUNTERS['peak_eye']['reward']['heal'], 'full')


if __name__ == '__main__':
    unittest.main()
