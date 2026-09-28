"""Optional traversal routes unlocked by movement abilities."""

from constants import TILE_SIZE
from systems import audio
from systems.rewards import grant_reward, reward_summary
from systems.route_data import ROUTES
from world.world_data import ABILITY_NAMES


class GameRoutesMixin:
    def update_ability_routes(self):
        self.route_prompt = ''
        if self.player is None:
            return
        for route_id, route in ROUTES.items():
            if route_id in self.player.completed_routes:
                continue
            sx = route['start'][0] * TILE_SIZE + TILE_SIZE // 2
            sy = (route['start'][1] + 1) * TILE_SIZE
            near_start = ((self.player.rect.centerx - sx) ** 2
                          + (self.player.rect.bottom - sy) ** 2 <= 72 * 72)
            if near_start:
                ability = ABILITY_NAMES[route['required']]
                self.route_prompt = (f"Ruta: {route['name']} · {ability}"
                                     if route['required'] in self.player.unlocked_abilities
                                     else f"Ruta bloqueada: requiere {ability}")
            gx = route['goal'][0] * TILE_SIZE + TILE_SIZE // 2
            gy = (route['goal'][1] + 1) * TILE_SIZE
            reached = ((self.player.rect.centerx - gx) ** 2
                       + (self.player.rect.bottom - gy) ** 2 <= 46 * 46)
            if reached and route['required'] in self.player.unlocked_abilities:
                self._complete_ability_route(route_id, route)

    def _complete_ability_route(self, route_id, route):
        level_before = self.player.level
        result = grant_reward(self.player, route['reward'], item_level=self.player.level)
        self._check_levelup(level_before)
        for item in result['items']:
            self.player.add_item(item)
        self.player.completed_routes.add(route_id)
        self.inv_message = f"Ruta dominada: {route['name']} · {reward_summary(result)}"
        self.inv_message_t = 4.0
        self.fx.emit('checkpoint', self.player.rect.centerx, self.player.rect.centery)
        self.camera.add_trauma(0.22)
        audio.play('victory', 0.65)
