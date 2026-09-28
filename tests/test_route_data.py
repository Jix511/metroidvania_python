import unittest

from systems.route_data import ROUTES
from world.world_data import ZONE_DEFS


class RouteDataTests(unittest.TestCase):
    def test_each_zone_has_one_ability_route(self):
        self.assertEqual(len(ROUTES), 5)
        self.assertEqual({route['zone_id'] for route in ROUTES.values()},
                         {zone['id'] for zone in ZONE_DEFS})

    def test_all_movement_abilities_are_used(self):
        self.assertEqual({route['required'] for route in ROUTES.values()},
                         {'double_jump', 'wall_jump', 'dash', 'teleport'})

    def test_special_obstacles_match_their_ability(self):
        dash = ROUTES['ruins_dash_tunnel']
        teleport = ROUTES['sanctum_rune_fold']
        self.assertEqual(dash['obstacle']['type'], 'dash_barrier')
        self.assertEqual(dash['required'], 'dash')
        self.assertEqual(teleport['obstacle']['type'], 'teleport_anchors')
        self.assertEqual(teleport['required'], 'teleport')


if __name__ == '__main__':
    unittest.main()
