import unittest

from systems.npc_data import NPCS, dialogue_for, npc_at_refuge, npc_position
from systems.quest_data import QUESTS


class DummyPlayer:
    def __init__(self):
        self.boss_defeated_ids = set()
        self.miniboss_defeated_ids = set()
        self.quest_states = {}


class NPCDataTests(unittest.TestCase):
    def test_npcs_are_distributed_across_world_zones(self):
        self.assertEqual(set(NPCS), {'maela', 'ilyra', 'caldus', 'sira', 'eira'})
        self.assertEqual({npc['zone_id'] for npc in NPCS.values()},
                         {'meadow', 'caves', 'ruins', 'sanctum', 'peak'})

    def test_every_quest_has_a_known_giver(self):
        self.assertTrue(all(quest['giver'] in NPCS for quest in QUESTS.values()))
        self.assertGreater(len({quest['giver'] for quest in QUESTS.values()}), 1)

    def test_dialogue_reacts_to_world_progress(self):
        player = DummyPlayer()
        before = dialogue_for(player, NPCS['ilyra'])
        player.boss_defeated_ids.add('cavern_mother')
        after = dialogue_for(player, NPCS['ilyra'])
        self.assertNotEqual(before, after)

    def test_completed_world_uses_final_dialogue(self):
        player = DummyPlayer()
        player.boss_defeated_ids.update(('one', 'two', 'three'))
        self.assertEqual(dialogue_for(player, NPCS['sira']),
                         NPCS['sira']['dialogue']['all_bosses'])

    def test_rescued_npc_moves_to_refuge(self):
        player = DummyPlayer()
        self.assertFalse(npc_at_refuge(player, NPCS['ilyra']))
        self.assertEqual(npc_position(player, NPCS['ilyra']),
                         (NPCS['ilyra']['x'], NPCS['ilyra']['y']))
        player.quest_states['lost_forge'] = 'completed'
        self.assertTrue(npc_at_refuge(player, NPCS['ilyra']))
        self.assertEqual(npc_position(player, NPCS['ilyra']),
                         (NPCS['ilyra']['refuge_x'], NPCS['ilyra']['refuge_y']))


if __name__ == '__main__':
    unittest.main()
