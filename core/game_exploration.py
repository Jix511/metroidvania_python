"""Hidden-room discovery, chests, and timed combat challenges."""

import pygame

from constants import TILE_SIZE
from entities.enemy import Enemy
from systems import audio
from systems.rewards import grant_reward, reward_summary
from systems.secret_data import SECRETS


class GameExplorationMixin:
    def _secret_point(self, secret, key):
        point = secret[key]
        return (point['tx'] * TILE_SIZE + TILE_SIZE // 2,
                point.get('ty', point.get('y1')) * TILE_SIZE + TILE_SIZE // 2)

    def _near_secret_point(self, secret, key, radius):
        x, y = self._secret_point(secret, key)
        dx = self.player.rect.centerx - x
        dy = self.player.rect.centery - y
        return dx * dx + dy * dy <= radius * radius

    def _discover_secret(self, secret_id, secret):
        self.player.discovered_secrets.add(secret_id)
        self.game_map.reveal_secret(secret_id)
        self.inv_message = f'Secreto descubierto: {secret["name"]}'
        self.inv_message_t = 3.5
        x, y = self._secret_point(secret, 'wall')
        self.fx.burst(x, y, n=24, color=(125, 210, 240),
                      speed=190.0, life=0.7, grav=80.0)
        self.camera.add_trauma(0.3)
        audio.play('gate', 0.8)

    def _open_secret_chest(self, secret_id, secret):
        if secret_id in self.player.opened_secret_chests:
            return
        result = grant_reward(self.player, secret['reward'], item_level=self.player.level)
        for item in result['items']:
            self.player.add_item(item)
        self.player.opened_secret_chests.add(secret_id)
        self.inv_message = f'{secret["name"]}: {reward_summary(result)}'
        self.inv_message_t = 4.0
        x, y = self._secret_point(secret, 'chest')
        self.fx.burst(x, y, n=30, color=(255, 215, 90),
                      speed=230.0, life=0.8, grav=120.0)
        audio.play('victory', 0.65)

    def _start_secret_challenge(self, secret_id, secret):
        enemies = []
        cx, cy = self._secret_point(secret, 'chest')
        for index, enemy_type in enumerate(secret['enemies']):
            offset = (index - (len(secret['enemies']) - 1) / 2.0) * 42
            enemy = Enemy(enemy_type, cx + offset, cy - 40, scale=self._difficulty())
            enemy.secret_challenge_id = secret_id
            self._resolve_spawn(enemy.rect)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)
            enemies.append(enemy)
        self.active_secret_challenge = {
            'id': secret_id, 'timer': float(secret['time_limit']), 'enemies': enemies,
        }
        self.inv_message = f'Prueba secreta: derrota a todos en {secret["time_limit"]:.0f}s'
        self.inv_message_t = 3.0
        audio.play('roar', 0.55)

    def _fail_secret_challenge(self):
        challenge = self.active_secret_challenge
        if challenge is None:
            return
        for enemy in challenge['enemies']:
            enemy.kill()
            self.enemies.remove(enemy)
            self.all_sprites.remove(enemy)
        self.active_secret_challenge = None
        self.secret_retry_t = 2.5
        self.inv_message = 'Prueba fallida. El sello volverá a responder.'
        self.inv_message_t = 3.0

    def reset_secret_challenge(self):
        if self.active_secret_challenge is not None:
            for enemy in self.active_secret_challenge['enemies']:
                enemy.kill()
        self.active_secret_challenge = None
        self.secret_retry_t = 0.0

    def update_secrets(self, dt):
        if self.player is None:
            return
        self.secret_retry_t = max(0.0, self.secret_retry_t - dt)
        for secret_id, secret in SECRETS.items():
            if (secret_id not in self.player.discovered_secrets
                    and self._near_secret_point(secret, 'wall', 54)):
                self._discover_secret(secret_id, secret)
            if (secret_id not in self.player.discovered_secrets
                    or secret_id in self.player.opened_secret_chests
                    or not self._near_secret_point(secret, 'chest', 42)):
                continue
            if secret['kind'] == 'chest':
                self._open_secret_chest(secret_id, secret)
            elif self.active_secret_challenge is None and self.secret_retry_t <= 0:
                self._start_secret_challenge(secret_id, secret)

        challenge = self.active_secret_challenge
        if challenge is None:
            return
        challenge['timer'] -= dt
        living = [enemy for enemy in challenge['enemies'] if enemy.alive()]
        if not living:
            secret_id = challenge['id']
            self.active_secret_challenge = None
            self._open_secret_chest(secret_id, SECRETS[secret_id])
        elif challenge['timer'] <= 0:
            self._fail_secret_challenge()
