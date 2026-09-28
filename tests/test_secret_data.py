import unittest

from systems.secret_data import SECRETS
from world.world_data import ZONE_DEFS


class SecretDataTests(unittest.TestCase):
    def test_each_zone_has_one_secret(self):
        self.assertEqual(len(SECRETS), 5)
        self.assertEqual({secret['zone_id'] for secret in SECRETS.values()},
                         {zone['id'] for zone in ZONE_DEFS})

    def test_challenges_have_valid_enemies_and_time_limits(self):
        challenges = [secret for secret in SECRETS.values()
                      if secret['kind'] == 'combat']
        self.assertEqual(len(challenges), 3)
        self.assertTrue(all(secret['enemies'] and secret['time_limit'] > 0
                            for secret in challenges))

    def test_every_secret_has_a_meaningful_reward(self):
        for secret in SECRETS.values():
            reward = secret['reward']
            self.assertTrue(reward['xp'] or reward['gold']
                            or reward['skill_points'] or reward['items'])


if __name__ == '__main__':
    unittest.main()
