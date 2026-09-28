"""Sealed room encounters, wave progression, and unique rewards."""

import pygame

from constants import TILE_SIZE
from entities.enemy import Enemy
from systems import audio
from systems.encounter_data import ENCOUNTERS
from systems.rewards import grant_reward, reward_summary


class GameEncountersMixin:
    def update_room_encounter(self, dt):
        room_id = self.current_room
        if self.active_room_encounter is None:
            if room_id in ENCOUNTERS and room_id not in self.player.completed_encounters:
                self._start_room_encounter(room_id)
            return

        state = self.active_room_encounter
        if room_id != state['room_id']:
            self._cancel_room_encounter()
            return
        self._contain_player_in_encounter(state)
        living = [enemy for enemy in state['members'] if enemy.alive()]
        state['members'] = living
        if living:
            return
        state['delay'] -= dt
        if state['delay'] > 0:
            return
        definition = ENCOUNTERS[state['room_id']]
        if state['wave'] + 1 < len(definition['waves']):
            state['wave'] += 1
            self._spawn_encounter_wave(state)
        else:
            self._complete_room_encounter(state)

    def _start_room_encounter(self, room_id):
        self.active_room_encounter = {
            'room_id': room_id, 'wave': 0, 'members': [], 'delay': 0.0,
        }
        definition = ENCOUNTERS[room_id]
        self.inv_message = f"Encuentro: {definition['name']}"
        self.inv_message_t = 2.5
        self.camera.add_trauma(0.2)
        audio.play('gate', 0.6)
        self._spawn_encounter_wave(self.active_room_encounter)

    def _spawn_encounter_wave(self, state):
        definition = ENCOUNTERS[state['room_id']]
        room = definition['room']
        enemies = definition['waves'][state['wave']]
        span = max(1, room['x1'] - room['x0'] - 6)
        members = []
        for index, enemy_type in enumerate(enemies):
            fraction = (index + 1) / (len(enemies) + 1)
            tx = room['x0'] + 3 + round(span * fraction)
            enemy = Enemy(enemy_type, tx * TILE_SIZE, TILE_SIZE * 8,
                          scale=self._difficulty())
            enemy.encounter_id = state['room_id']
            enemy.alert(4.0)
            self._resolve_spawn(enemy.rect)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)
            members.append(enemy)
            self.fx.emit('gate', enemy.rect.centerx, enemy.rect.centery)
        state['members'] = members
        state['delay'] = 0.7
        self.zone_banner = (f"OLEADA {state['wave'] + 1}/"
                            f"{len(definition['waves'])}")
        self.zone_banner_t = 1.4

    def _contain_player_in_encounter(self, state):
        room = ENCOUNTERS[state['room_id']]['room']
        left = room['x0'] * TILE_SIZE + 5
        right = (room['x1'] + 1) * TILE_SIZE - 5
        if self.player.rect.left < left:
            self.player.rect.left = left
            self.player.velocity.x = max(0, self.player.velocity.x)
        if self.player.rect.right > right:
            self.player.rect.right = right
            self.player.velocity.x = min(0, self.player.velocity.x)
        for enemy in state['members']:
            if enemy.rect.left < left:
                enemy.rect.left = left
                enemy.direction = 1
            elif enemy.rect.right > right:
                enemy.rect.right = right
                enemy.direction = -1

    def _complete_room_encounter(self, state):
        definition = ENCOUNTERS[state['room_id']]
        level_before = self.player.level
        reward = grant_reward(self.player, definition['reward'], item_level=self.player.level)
        self._check_levelup(level_before)
        for index, item in enumerate(reward['items']):
            self.drops.append({
                'item': item,
                'rect': pygame.Rect(self.player.rect.centerx + index * 16,
                                    self.player.rect.centery, 14, 14),
                'vy': -250.0, 'gold': reward['drop_gold'], 't': 0.0,
            })
        self.player.completed_encounters.add(state['room_id'])
        self.inv_message = f"¡Sala superada! {reward_summary(reward)}"
        self.inv_message_t = 4.0
        self.fx.emit('checkpoint', self.player.rect.centerx, self.player.rect.centery)
        self.camera.add_trauma(0.35)
        audio.play('victory', 0.7)
        self.active_room_encounter = None

    def _cancel_room_encounter(self):
        if self.active_room_encounter is not None:
            for enemy in self.active_room_encounter['members']:
                enemy.kill()
        self.active_room_encounter = None
