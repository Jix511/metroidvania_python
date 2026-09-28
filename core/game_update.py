import random

import pygame

from systems import audio, controls
from entities.boss import Boss
from constants import CAMERA_SMOOTH, SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE
from world.tilemap import ABILITY_NAMES, tutorial_signs
from core.screen_state import GameScreen
from presentation.death_effects import update_death_echo
from systems.npc_data import refuge_members
from systems.achievements import pending
from systems.rewards import grant_reward, reward_summary
from systems.spatial import near_view


class GameUpdateMixin:
    def update(self, dt):
        if self.screen_state is GameScreen.CLASS_MENU or self.player is None:
            return
        if self.screen_state is GameScreen.INTRO:
            self.charging = 0.0
            self.charge_notified = False
            self.charge_variant = 'neutral'
            return
        if self.screen_state is not GameScreen.GAMEPLAY:
            self.charging = 0.0
            self.charge_notified = False
            self.charge_variant = 'neutral'
            return
        self.player.stat_add('play_time', dt)
        unlocked = pending(self.player)
        if unlocked:
            achievement_id, definition = unlocked[0]
            self.player.unlocked_achievements.add(achievement_id)
            reward = grant_reward(self.player, definition['reward'])
            self.inv_message = f"LOGRO: {definition['name']} · {reward_summary(reward)}"
            self.inv_message_t = 4.0
            audio.play('levelup', 0.8)
        for platform in self.moving_platforms:
            platform.advance(dt, self.player)
        previous_bottom = self.player.rect.bottom
        # Todas las clases comparten toque, carga y variante direccional.
        if controls.held('attack') and self.player.attack_cooldown <= 0:
            from systems.attack_variants import CHARGE_PROFILES
            self.charging = min(1.0, self.charging + dt / 0.85)
            variant = self.attack_variant()
            if variant != 'neutral':
                self.charge_variant = variant
            self.player.slow_factor = 0.62 if self.charging >= 0.22 else 0.82
            color = CHARGE_PROFILES[self.player.character_class]['color']
            self.fx.trail(self.player.rect.centerx, self.player.rect.centery,
                          color=color, n=1, life=0.25, size=3)
            if self.charging >= 1.0 and not self.charge_notified:
                self.charge_notified = True
                audio.play('skill', 0.6)
                self.texts.add(self.player.rect.centerx, self.player.rect.top - 6,
                               "¡CARGADO!", color)
        else:
            self.player.slow_factor = 1.0
        if self.player.update(dt, self.game_map, self.enemies) is True:
            # Muerte por DoT (veneno/quemadura): sin daño extra, solo feedback
            if not self._go_sound:
                self._go_sound = True
                audio.play('gameover')
            self.set_screen(GameScreen.GAME_OVER)
            self.player.stat_add('deaths')
            self.texts.add(self.player.rect.centerx, self.player.rect.top - 4,
                        "Envenenado...", (120, 220, 120))
        for platform in self.moving_platforms:
            if platform.catch_falling(self.player, previous_bottom):
                break
        self._drain_fx_texts(self.player, (120, 220, 120))
        # Estela del dash/rodadura
        if self.player.dash_time > 0:
            self.fx.trail(self.player.rect.centerx, self.player.rect.centery,
                        color=getattr(self.player, 'dash_trail', (120, 220, 255)),
                        n=2, life=0.3, size=5)
        active_enemies = [e for e in self.enemies if isinstance(e, Boss) or near_view(
            e.rect, self.player.rect.center, SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2, 96)]
        for e in active_enemies:
            if isinstance(e, Boss):
                continue  # el jefe se actualiza en _update_boss
            res = e.update(self.player, self.game_map, dt)
            if e.alive() and self._handle_enemy_impact(e):
                res = 'died'
            self._drain_fx_texts(e, (255, 140, 40))
            if res == 'died':
                self.fx.burst(e.rect.centerx, e.rect.centery, n=16,
                            color=(255, 140, 40), speed=200.0, life=0.5)
                audio.play('kill', 0.7)
                self._on_enemy_killed(e)
        alerted = [enemy for enemy in active_enemies
                   if not isinstance(enemy, Boss) and getattr(enemy, 'alert_t', 0) > 0]
        for source in alerted:
            for ally in active_enemies:
                if (ally is not source and not isinstance(ally, Boss)
                        and abs(ally.rect.centerx - source.rect.centerx) < 150
                        and abs(ally.rect.centery - source.rect.centery) < 90):
                    ally.alert(1.2)
        self._update_boss(dt)
        self._update_spells(dt)
        self.update_drops(dt)
        self.update_secrets(dt)
        self.update_ability_routes()
        self.death_visuals[:] = [echo for echo in self.death_visuals
                                 if update_death_echo(echo, dt)]
        # Tutorial: cartel cercano del Claro Inicial
        self.sign_text = ""
        if self.current_zone == 'meadow':
            for sign in tutorial_signs():
                sx = sign['tx'] * TILE_SIZE + TILE_SIZE // 2
                if abs(self.player.rect.centerx - sx) < 70:
                    self.sign_text = f"{sign['title']}: {sign['text']}"
                    break
        nearby_npc = self.nearest_npc()
        self.shop_prompt = self.npc_prompt_text(nearby_npc) if nearby_npc else ""
        # Checkpoints: activación automática al tocar (desbloqueo + respawn + cura)
        cp = self.game_map.checkpoint_near(self.player.rect)
        if cp is not None and cp['id'] not in self.player.unlocked_checkpoints:
            self.player.unlocked_checkpoints.add(cp['id'])
            pos = self.game_map.spawn_pos_for(cp['id'])
            self.player.respawn_point = pos
            self.player.health = self.player.max_health
            self.inv_message = f"Santuario activado: {cp['name']} (M: viajar)"
            self.inv_message_t = 3.0
            audio.play('checkpoint')
            self.fx.emit('checkpoint', cp['rect'].centerx, cp['rect'].centery)
        # Puertas: auto-abrir si tiene habilidad, si no mostrar requisito
        gate, opened = self.game_map.try_open_nearby(self.player)
        if gate is not None and opened:
            need = ABILITY_NAMES.get(gate['required'], gate['required'])
            self.inv_message = f"{gate['name']} abierta ({need})"
            self.inv_message_t = 3.0
            self.gate_prompt = ""
            audio.play('gate')
            self.camera.add_trauma(0.25)
            self.fx.emit('gate', self.player.rect.centerx, self.player.rect.centery)
        elif gate is not None:
            need = ABILITY_NAMES.get(gate['required'], gate['required'])
            self.gate_prompt = f"Bloqueado: {gate['name']} requiere {need} (K: skills)"
        else:
            self.gate_prompt = ""
        # Zona actual + banner
        z = self.game_map.get_zone_at(self.player.rect.centerx)
        if z['id'] != self.current_zone:
            self.current_zone = z['id']
            self.player.explored_zones.add(z['id'])
            self.map_selected_zone = z['id']
            self.zone_banner, self.zone_banner_t = z['name'], 3.0
            # El salto entre biomas es una transición de sala, no un barrido
            # que deje visibles simultáneamente dos fondos incompatibles.
            self.camera.camera.x = -z['x0'] * TILE_SIZE
            self.camera_focus_x = float(self.camera.camera.x)
            self.camera_focus_y = float(self.camera.camera.y)
        room = self.game_map.get_room_at(self.player.rect.centerx)
        if room['id'] != self.current_room:
            self.current_room = room['id']
            self.player.explored_rooms.add(room['id'])
            self.zone_banner = f"{z['name']} · {room['name']}"
            self.zone_banner_t = 2.4
            self.room_transition_t = 0.32
        self.update_room_encounter(dt)
        self.room_transition_t = max(0.0, self.room_transition_t - dt)
        if self.zone_banner_t > 0:
            self.zone_banner_t -= dt
        if self.boss_banner_t > 0:
            self.boss_banner_t -= dt
        if self.boss_phase_t > 0:
            self.boss_phase_t -= dt
        if self.victory_t > 0:
            self.victory_t -= dt
        for hit in pygame.sprite.spritecollide(self.player, self.enemies, False):
            if hasattr(hit, 'can_damage_player') and not hit.can_damage_player():
                continue
            if self.try_parry(hit):
                if hasattr(hit, 'attack_window'):
                    hit.attack_window = 0.0
                continue
            was_invincible = self.player.invincible
            self.damage_player(hit.damage)
            # Élite: estado al golpear + robo de vida (solo si el golpe entró)
            elite = getattr(hit, 'elite', None)
            if (elite is not None and self.screen_state is not GameScreen.GAME_OVER
                    and hit.alive() and not was_invincible):
                st = elite.get('status')
                if st is not None:
                    sid, dur = st
                    if sid == 'poison':
                        if self.player.try_poison(dur) == 'applied':
                            self.texts.add(self.player.rect.centerx, self.player.rect.top - 16,
                                        "¡Envenenado!", (120, 220, 120))
                        else:
                            self.texts.add(self.player.rect.centerx, self.player.rect.top - 16,
                                           "INMUNE", (185, 185, 195))
                            audio.play('immune', 0.65)
                    else:
                        self.player.status.apply(sid, dur)
                if elite.get('lifesteal'):
                    hit.health = min(hit.max_health, hit.health + max(1, int(hit.damage * 0.3)))
            # Slimes contagian veneno al contacto (solo si el golpe entró)
            if (self.screen_state is not GameScreen.GAME_OVER and not was_invincible
                    and getattr(hit, 'enemy_type', '') == 'slime'):
                if self.player.try_poison(4.0) == 'applied':
                    self.texts.add(self.player.rect.centerx, self.player.rect.top - 16,
                                "¡Envenenado!", (120, 220, 120))
                else:
                    self.texts.add(self.player.rect.centerx, self.player.rect.top - 16,
                                   "INMUNE", (185, 185, 195))
                    audio.play('immune', 0.65)
            if self.screen_state is GameScreen.GAME_OVER:
                break
        self.ambient_fx_t -= dt
        if self.ambient_fx_t <= 0:
            self.ambient_fx_t = 0.5 if self.settings.get('reduced_motion') else 0.16
            if not self.settings.get('reduced_motion'):
                effect_id = f'ambient_{self.current_zone}'
                self.fx.emit(
                    effect_id,
                    self.player.rect.centerx + random.uniform(-SCREEN_WIDTH * 0.45,
                                                              SCREEN_WIDTH * 0.45),
                    self.player.rect.centery + random.uniform(-SCREEN_HEIGHT * 0.4,
                                                              SCREEN_HEIGHT * 0.35),
                )
        self.ambient_audio_t -= dt
        if self.ambient_audio_t <= 0:
            at_refuge = self.current_zone == 'meadow' and bool(refuge_members(self.player))
            audio.play_ambient(self.current_zone, refuge=at_refuge)
            self.ambient_audio_t = random.uniform(7.0, 12.0)
        self.execution_cue_t = max(0.0, self.execution_cue_t - dt)
        execute_target = self.execution_target()
        if execute_target is not None and self.execution_cue_t <= 0:
            audio.play('skill', 0.22)
            self.execution_cue_t = 0.8
        elif execute_target is None:
            self.execution_cue_t = 0.0
        self.fx.update(dt)
        self.combat_visuals.update(dt)
        self.environment.update(dt)
        self.texts.update(dt)
        if self.mark_cd > 0:
            self.mark_cd -= dt
        if self.combat_timer > 0:
            self.combat_timer -= dt
        self.update_camera(dt)

    def update_camera(self, dt):
        zone = self.game_map.get_zone_at(self.player.rect.centerx)
        zone_left = zone['x0'] * TILE_SIZE
        zone_right = (zone['x1'] + 1) * TILE_SIZE
        facing = 1 if self.player.facing_right else -1
        speed_ratio = min(1.0, abs(self.player.velocity.x) / max(1.0, self.player.speed))
        look_x = facing * (24 + 54 * speed_ratio)
        look_y = max(-45.0, min(55.0, self.player.velocity.y * 0.09))
        t = -self.player.rect.centerx + SCREEN_WIDTH // 2 - look_x
        u = -self.player.rect.centery + SCREEN_HEIGHT // 2 - look_y
        min_x = min(-zone_left, SCREEN_WIDTH - zone_right)
        max_x = -zone_left
        t = max(min_x, min(max_x, t))
        u = max(-(self.camera.height - SCREEN_HEIGHT), min(0, u))
        kx = min(1.0, CAMERA_SMOOTH * dt)
        ky = min(1.0, CAMERA_SMOOTH * 0.75 * dt)
        self.camera_focus_x += (t - self.camera_focus_x) * kx
        self.camera_focus_y += (u - self.camera_focus_y) * ky
        self.camera.camera.x = round(self.camera_focus_x)
        self.camera.camera.y = round(self.camera_focus_y)
        self.camera.trauma = max(0.0, self.camera.trauma - dt * 1.6)

    def snap_camera_to_player(self):
        """Reposiciona la cámara tras teletransporte, carga o respawn."""
        zone = self.game_map.get_zone_at(self.player.rect.centerx)
        zone_left = zone['x0'] * TILE_SIZE
        zone_right = (zone['x1'] + 1) * TILE_SIZE
        x = -self.player.rect.centerx + SCREEN_WIDTH // 2
        x = max(min(-zone_left, SCREEN_WIDTH - zone_right), min(-zone_left, x))
        y = -self.player.rect.centery + SCREEN_HEIGHT // 2
        y = max(-(self.camera.height - SCREEN_HEIGHT), min(0, y))
        self.camera_focus_x, self.camera_focus_y = float(x), float(y)
        self.camera.camera.x, self.camera.camera.y = round(x), round(y)
