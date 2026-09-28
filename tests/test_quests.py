import unittest

from systems.quest_data import QUESTS, condition_progress, quest_status


class DummyPlayer:
    def __init__(self):
        self.quest_states = {}
        self.boss_defeated_ids = set()
        self.miniboss_defeated_ids = set()
        self.inventory = []
        self.equipment = {'weapon': None}
        self.collected_items = set()
        self.completed_encounters = set()


class QuestTests(unittest.TestCase):
    def setUp(self):
        self.player = DummyPlayer()

    def test_quest_catalog_is_loaded(self):
        self.assertEqual(len(QUESTS), 5)
        self.assertIn('heart_of_kingdom', QUESTS)
        self.assertEqual(QUESTS['broken_knight']['giver'], 'caldus')

    def test_prerequisites_unlock_quests_in_order(self):
        self.assertEqual(quest_status(self.player, 'swamp_echoes'), 'available')
        self.assertEqual(quest_status(self.player, 'broken_knight'), 'locked')
        self.player.quest_states['swamp_echoes'] = 'completed'
        self.assertEqual(quest_status(self.player, 'broken_knight'), 'available')
        self.assertEqual(quest_status(self.player, 'lost_forge'), 'available')

    def test_active_boss_quest_becomes_ready(self):
        self.player.quest_states['swamp_echoes'] = 'active'
        self.assertEqual(quest_status(self.player, 'swamp_echoes'), 'active')
        self.player.boss_defeated_ids.add('cavern_mother')
        self.assertEqual(quest_status(self.player, 'swamp_echoes'), 'ready')

    def test_collected_item_counts_after_it_leaves_inventory(self):
        self.player.collected_items.add('Talismán del Vigía')
        progress = condition_progress(
            self.player, {'type': 'item_name', 'name': 'Talismán del Vigía'})
        self.assertEqual(progress, (1, 1))

    def test_final_quest_tracks_all_bosses(self):
        self.player.boss_defeated_ids.update(('one', 'two'))
        self.assertEqual(condition_progress(
            self.player, {'type': 'boss_count', 'count': 3}), (2, 3))

    def test_storm_quest_tracks_room_encounter(self):
        condition = {'type': 'encounter', 'id': 'peak_eye'}
        self.assertEqual(condition_progress(self.player, condition), (0, 1))
        self.player.completed_encounters.add('peak_eye')
        self.assertEqual(condition_progress(self.player, condition), (1, 1))


if __name__ == '__main__':
    unittest.main()
