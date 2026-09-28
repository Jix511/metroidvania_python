import unittest

from systems.rewards import (REWARD_PRESETS, RewardDataError, boss_reward,
                             grant_reward, reward_summary, validate_reward)


class FakePlayer:
    def __init__(self):
        self.level = 2
        self.experience = 0
        self.gold = 10
        self.skill_points = 1
        self.health = 20
        self.max_health = 100

    def gain_experience(self, amount):
        self.experience += amount
        if self.experience >= 100:
            self.level += 1

    def add_gold(self, amount):
        gained = int(amount * 1.2)
        self.gold += gained
        return gained


def fake_item(level, slot=None, rarity=None, luck=0.0):
    return {
        'level': level,
        'slot': slot or 'weapon',
        'rarity': rarity or 'common',
        'luck': luck,
        'name': 'Objeto de prueba',
    }


class RewardTests(unittest.TestCase):
    def test_miniboss_preset_is_externalized(self):
        reward = REWARD_PRESETS['miniboss_unique']
        self.assertEqual(reward['skill_points'], 1)
        self.assertEqual(reward['items'][0]['minimum_rarity'], 'epic')

    def test_reward_grants_every_resource_and_heals(self):
        player = FakePlayer()
        result = grant_reward(player, {
            'xp': 120,
            'gold': 50,
            'skill_points': 2,
            'heal': 'half',
            'items': [{'slot': 'armor', 'rarity': 'rare', 'level_offset': 1}],
        }, item_level=3, item_factory=fake_item)

        self.assertEqual(player.level, 3)
        self.assertEqual(player.gold, 70)
        self.assertEqual(player.skill_points, 3)
        self.assertEqual(player.health, 70)
        self.assertEqual(result['items'][0]['level'], 4)
        self.assertEqual(result['items'][0]['rarity'], 'rare')
        self.assertEqual(result['levels_gained'], 1)

    def test_minimum_rarity_replaces_a_lower_roll(self):
        player = FakePlayer()
        calls = []

        def item_factory(level, slot=None, rarity=None, luck=0.0):
            calls.append(rarity)
            return fake_item(level, slot, rarity, luck)

        result = grant_reward(player, {
            'items': [{'minimum_rarity': 'epic'}],
        }, item_factory=item_factory)

        self.assertEqual(calls, [None, 'epic'])
        self.assertEqual(result['items'][0]['rarity'], 'epic')

    def test_invalid_reward_is_rejected(self):
        with self.assertRaises(RewardDataError):
            validate_reward('bad reward', {'gold': -1})
        with self.assertRaises(RewardDataError):
            validate_reward('bad reward', {'items': [{'slot': 'spaceship'}]})

    def test_boss_adapter_and_summary(self):
        definition = {
            'skill_points': 3,
            'heal_on_kill': 'full',
            'loot': [('weapon', 'legendary')],
        }
        reward = boss_reward(definition, 250, 150)
        player = FakePlayer()
        result = grant_reward(player, reward, item_factory=fake_item)

        self.assertEqual(player.health, player.max_health)
        self.assertIn('+250 XP', reward_summary(result))
        self.assertIn('+3 pt habilidad', reward_summary(result))


if __name__ == '__main__':
    unittest.main()
