"""Boss spawning, combat updates, and victory rewards."""

import pygame

from constants import TILE_SIZE
from entities.boss import Boss
from entities.enemy import Enemy
from systems import audio
from systems.balance_data import BOSS_DEFS
from systems.rewards import boss_reward, grant_reward
from core.game_data import BOSS_ARENAS, TOTAL_BOSSES, VICTORY_TEXT
from core.screen_state import GameScreen


class GameBossesMixin:
    def _spawn_boss(self, boss_id, spawn_tx):
        self.boss = Boss(boss_id, spawn_tx * TILE_SIZE, TILE_SIZE * 10, scale=self._difficulty())
        self.enemies.add(self.boss)
        self.all_sprites.add(self.boss)
        self.boss_banner_t = 3.0
        self.boss_intro_t = 2.4
        self.inv_message = f"¡{self.boss.name} despierta!"
        self.inv_message_t = 3.0
        audio.play('roar')
        self.camera.add_trauma(0.5)
        self.fx.emit('boss_spawn', self.boss.rect.centerx, self.boss.rect.centery)

    def _begin_boss_defeat(self, boss):
        if self.pending_boss_defeat is not None:
            return
        self._queue_death_visual(boss, boss=True)
        bx, by = boss.rect.center
        self.pending_boss_defeat = boss
        self.boss_defeat_t = 1.8
        self.boss = None
        for projectile in list(self.projectiles):
            projectile.kill()
        self.hazards = []
        self.fx.burst(bx, by, n=36, color=(255, 175, 85), speed=270.0, life=1.0)
        self.camera.add_trauma(0.75)
        self.hitstop_t = max(self.hitstop_t, 0.18)

    def _update_boss_cinematics(self, dt):
        if self.boss_intro_t > 0:
            self.boss_intro_t = max(0.0, self.boss_intro_t - dt)
            if self.boss is not None:
                self.boss.velocity.update(0, 0)
                if self.boss_intro_t <= 0:
                    self.boss.cinematic_lock = False
                    self.boss.status.active.clear()
                    audio.play('roar', 0.9)
            return True
        if self.pending_boss_defeat is not None:
            self.boss_defeat_t = max(0.0, self.boss_defeat_t - dt)
            if self.boss_defeat_t <= 0:
                defeated = self.pending_boss_defeat
                self.pending_boss_defeat = None
                self._on_boss_killed(defeated)
            return True
        altar = self.boss_reward_altar
        if altar is not None:
            altar['t'] -= dt
            dx = self.player.rect.centerx - altar['x']
            dy = self.player.rect.centery - altar['y']
            if not altar['claimed'] and altar['delay'] <= 0 and dx * dx + dy * dy < 70 * 70:
                altar['claimed'] = True
                self.inv_message = f"Altar reclamado · {altar['summary']}"
                self.inv_message_t = 4.0
                self.fx.emit('checkpoint', altar['x'], altar['y'])
                audio.play('victory', 0.6)
            altar['delay'] -= dt
            if altar['t'] <= 0:
                self.boss_reward_altar = None
        return False

    def _on_boss_killed(self, boss):
        p = self.player
        p.stat_add('bosses_defeated')
        p.boss_defeated_ids.add(boss.boss_id)
        if p.record_kill(f"boss:{boss.boss_id}"):
            self._bestiary_found(boss.name)
        d = BOSS_DEFS[boss.boss_id]
        lvl0 = p.level
        reward = grant_reward(p, boss_reward(d, boss.xp_value, boss.gold_value),
                              item_level=p.level)
        self._check_levelup(lvl0)
        bx, by = boss.rect.centerx, boss.rect.centery
        for item in reward['items']:
            p.add_item(item)
        from systems.rewards import reward_summary
        self.boss_reward_altar = {
            'x': bx, 'y': by, 'boss_id': boss.boss_id,
            'summary': reward_summary(reward), 'claimed': False,
            'delay': 0.8, 't': 12.0,
        }
        self.boss = None
        for proj in list(self.projectiles):
            proj.kill()
        self.hazards = []
        self.victory_t = 5.0
        self.victory_text = VICTORY_TEXT.get(boss.boss_id, '¡Jefe derrotado!')
        if len(p.boss_defeated_ids) >= TOTAL_BOSSES:
            self.victory_text = '¡JUEGO COMPLETADO! Los 3 jefes han caído'
        self.inv_message = self.victory_text
        self.inv_message_t = 5.0
        self.fx.emit('victory', bx, by)
        audio.play('victory')
        self.camera.add_trauma(0.7)
        self.hitstop_t = max(self.hitstop_t, 0.15)

    def _update_boss(self, dt):
        p = self.player
        if self._update_boss_cinematics(dt):
            return
        # Trigger por arena: el jefe de la zona que pisa el jugador
        if (self.boss is None and self.pending_boss_defeat is None
                and self.screen_state is not GameScreen.GAME_OVER):
            ptx = int(p.rect.centerx // TILE_SIZE)
            for arena in BOSS_ARENAS:
                if (arena['id'] not in p.boss_defeated_ids
                        and arena['x0'] <= ptx <= arena['x1']
                        and p.rect.centerx > arena['trigger_tx'] * TILE_SIZE):
                    self._spawn_boss(arena['id'], arena['spawn_tx'])
                    break
        if self.boss is None:
            return
        alive_minions = sum(1 for e in self.enemies
                            if e is not self.boss
                            and abs(e.rect.centerx - self.boss.rect.centerx) < 500
                            and abs(e.rect.centery - self.boss.rect.centery) < 400)
        ev = self.boss.update(p, self.game_map, dt, alive_minions)
        self._drain_fx_texts(self.boss, (255, 140, 40))
        if not self.boss.alive():
            # Muerte por DoT: misma recompensa que por golpe
            bx, by = self.boss.rect.centerx, self.boss.rect.centery
            self.fx.burst(bx, by, n=24, color=(255, 140, 40), speed=240.0, life=0.7)
            self._begin_boss_defeat(self.boss)
            return
        if ev['phase_changed'] is not None:
            phase = ev['phase_changed']
            phase_data = self.boss.phase_defs[phase]
            for proj in list(self.projectiles):
                proj.kill()
            self.hazards = []
            self.boss_phase_text = phase_data['message']
            self.boss_phase_color = phase_data['color']
            self.boss_phase_t = 2.6
            self.inv_message = f'Fase {phase}: {phase_data["message"]}'
            self.inv_message_t = 2.6
            self.fx.burst(self.boss.rect.centerx, self.boss.rect.centery,
                          n=30, color=phase_data['color'], speed=300.0,
                          life=0.8, grav=0.0)
            audio.play('roar', 0.9)
            self.camera.add_trauma(0.65)
            self.hitstop_t = max(self.hitstop_t, 0.12)
        for proj in ev['projectiles']:
            self.projectiles.add(proj)
        if ev['projectiles'] and len(self.projectiles) < 6:
            audio.play('shoot', 0.5)
        if ev['blink'] is not None:
            b = ev['blink']
            for pos in (b['from'], b['to']):
                self.fx.burst(pos[0], pos[1], n=14, color=(150, 60, 220),
                              speed=190.0, life=0.4, grav=0.0)
            audio.play('teleport', 0.7)
            if b.get('meteor'):
                self.inv_message = "¡El Vacío cae sobre ti! ¡Corre!"
                self.inv_message_t = 1.5
        for mtype in ev['summon_requests']:
            m = Enemy(mtype, self.boss.rect.centerx, self.boss.rect.top - 20, scale=self._difficulty())
            self._resolve_spawn(m.rect)
            self.enemies.add(m)
            self.all_sprites.add(m)
            self.fx.burst(m.rect.centerx, m.rect.centery, n=12, color=(180, 100, 255),
                          speed=150.0, life=0.5)
            audio.play('teleport', 0.6)
            self.inv_message = f"¡{self.boss.name} invoca esbirros!"
            self.inv_message_t = 2.0
        if ev['hazard'] is not None:
            h = ev['hazard']
            self.hazards.append({'x': h['x'], 'y': h['y'], 'radius': h['radius'],
                                 'damage': h['damage'], 't': 0.0, 'duration': h['duration']})
            audio.play('shoot', 0.4)
        slam = ev['slam']
        if slam is not None:
            self.fx.burst(slam['x'], slam['y'], n=22, color=(160, 120, 80),
                          speed=280.0, life=0.6)
            audio.play('slam')
            self.camera.add_trauma(0.5)
            self.hitstop_t = max(self.hitstop_t, 0.08)
            dx = p.rect.centerx - slam['x']
            dy = p.rect.centery - slam['y']
            if dx * dx + dy * dy <= slam['radius'] ** 2:
                self.damage_player(slam['damage'], p.rect.centerx, p.rect.centery)
        # Charcos de veneno: daño por contacto (los iframes del jugador limitan los ticks)
        for h in list(self.hazards):
            h['t'] += dt
            if h['t'] >= h['duration']:
                self.hazards.remove(h)
                continue
            dx = p.rect.centerx - h['x']
            dy = p.rect.centery - h['y']
            if dx * dx + dy * dy <= h['radius'] ** 2:
                self.damage_player(h['damage'], p.rect.centerx, p.rect.centery)
                if self.screen_state is GameScreen.GAME_OVER:
                    break
        # Proyectiles hostiles
        for proj in list(self.projectiles):
            proj.update(self.game_map, dt)
        hits = pygame.sprite.spritecollide(p, self.projectiles, False)
        for proj in hits:
            if self.try_parry(proj, projectile=True):
                proj.kill()
                continue
            was_invincible = p.invincible
            self.damage_player(proj.damage, proj.rect.centerx, proj.rect.centery)
            st = getattr(proj, 'status', None)
            if (st is not None and self.screen_state is not GameScreen.GAME_OVER
                    and not was_invincible):
                sid, dur = st
                if sid == 'poison':
                    res = p.try_poison(dur)
                    self.texts.add(p.rect.centerx, p.rect.top - 16,
                                "¡Envenenado!" if res == 'applied' else "Inmune al veneno",
                                (120, 220, 120) if res == 'applied' else (180, 180, 180))
                else:
                    p.status.apply(sid, dur)
                    self.texts.add(p.rect.centerx, p.rect.top - 16, "¡Helado!",
                                (180, 230, 255))
            proj.kill()
            if self.screen_state is GameScreen.GAME_OVER:
                break
