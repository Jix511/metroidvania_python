import random

import pygame

from systems import audio
from entities.boss import Boss
from entities.enemy import Enemy
from systems.rewards import REWARD_PRESETS, grant_reward, reward_summary
from core.screen_state import GameScreen
from systems.aiming import melee_facing
from presentation.death_effects import create_death_echo
from systems.elements import ELEMENT_COLORS, apply_element, damage_multiplier
from systems.spells import AllyShot

class GameCombatMixin:

    def execution_target(self):
        p = self.player
        if p is None:
            return None
        candidates = [enemy for enemy in self.enemies if enemy.alive()
                      and getattr(enemy, 'posture_broken_t', 0) > 0
                      and abs(enemy.rect.centerx - p.rect.centerx) <= 86
                      and abs(enemy.rect.centery - p.rect.centery) <= 70]
        return min(candidates, key=lambda enemy:
                   abs(enemy.rect.centerx - p.rect.centerx)) if candidates else None

    def _damage_posture(self, target, amount):
        if not target.alive() or not target.damage_posture(amount):
            return False
        self.player.stat_add('posture_breaks')
        target.status.apply('stun', target.posture_broken_t)
        if isinstance(target, Boss):
            target.state = 'stunned'
            target.state_t = target.posture_broken_t
        self.texts.add(target.rect.centerx, target.rect.top - 24, '¡POSTURA ROTA!',
                       (255, 205, 85))
        self.fx.burst(target.rect.centerx, target.rect.centery, n=20,
                      color=(255, 205, 85), speed=240.0, life=0.45, grav=80.0)
        audio.play('critical', 0.9)
        return True

    def try_execute(self):
        p = self.player
        target = self.execution_target()
        if target is None:
            return False
        colors = {'warrior': (255, 190, 80), 'rogue': (210, 120, 255),
                  'ranger': (150, 230, 120), 'mage': (120, 200, 255),
                  'kitsune': (255, 115, 175), 'reaper': (80, 235, 220)}
        color = colors.get(p.character_class, (255, 220, 100))
        p.stat_add('executions')
        p.begin_action(0.45)
        p.invincible = True
        p.invincibility_timer = max(p.invincibility_timer, 0.5)
        self.texts.add(target.rect.centerx, target.rect.top - 28,
                       '¡REMATE!', color)
        self.fx.burst(target.rect.centerx, target.rect.centery, n=28,
                      color=color, speed=300.0, life=0.55, grav=90.0)
        self.hitstop_t = max(self.hitstop_t, 0.12)
        self.camera.add_trauma(0.35)
        audio.play('critical', 1.0)
        if isinstance(target, Boss):
            damage = min(max(1, int(target.max_health * 0.12)), max(0, target.health - 1))
            result = target.take_damage(damage, p.rect.centerx)
            target.posture_broken_t = 0.0
            target.posture = target.posture_max
            target.state = 'stunned'
            target.state_t = 1.2
            if result == 'phase':
                self.inv_message = f'¡{target.name} cambia de fase!'
                self.inv_message_t = 2.0
        else:
            target.take_damage(target.health + 1, p.rect.centerx)
            self._on_enemy_killed(target)
        return True

    def try_parry(self, source, projectile=False):
        p = self.player
        if p is None or p.parry_window <= 0:
            return False
        p.parry_window = 0.0
        p.invincible = True
        p.invincibility_timer = max(p.invincibility_timer, 0.32)
        p.counter_bonus_t = 1.2
        p.stat_add('perfect_parries')
        if hasattr(source, 'damage_posture'):
            self._damage_posture(source, 42 if p.character_class == 'warrior' else 32)
        self.texts.add(p.rect.centerx, p.rect.top - 18, '¡PARADA PERFECTA!',
                       (150, 230, 255))
        self.fx.burst(p.rect.centerx, p.rect.centery, n=18,
                      color=(150, 230, 255), speed=230.0, life=0.4, grav=0.0)
        self.camera.add_trauma(0.2)
        self.hitstop_t = max(self.hitstop_t, 0.08)
        audio.play('block', 1.0)
        if projectile and p.character_class == 'mage':
            velocity = getattr(source, 'velocity', pygame.Vector2(1, 0))
            direction = -velocity.normalize() if velocity.length() else pygame.Vector2(
                1 if p.facing_right else -1, 0)
            self.ally_shots.add(AllyShot(
                p.rect.centerx, p.rect.centery, direction.x * 520, direction.y * 520,
                max(p.damage * 2, getattr(source, 'damage', 1)), visual='arcane',
                element='electric', color=(145, 220, 255)))
        elif hasattr(source, 'status'):
            if not isinstance(source, Boss):
                source.status.apply('stun', 0.8 if p.character_class != 'warrior' else 1.25)
            if p.character_class == 'warrior':
                p.counter_bonus_t = 1.6
            elif p.character_class == 'kitsune':
                source.status.apply('burn', 2.5)
        if p.character_class == 'ranger' and hasattr(source, 'rect'):
            p.attack_cooldown = 0.0
            self.fire_arrow(source.rect.centerx, source.rect.centery)
        elif p.character_class in ('rogue', 'kitsune'):
            p.velocity.x = (-1 if source.rect.centerx > p.rect.centerx else 1) * 280
            p.movement_lock_t = 0.12
        return True

    def is_ranger(self):
        return self.player is not None and self.player.character_class == 'ranger'

    def charge_available(self):
        return self.player is not None

    def attack_variant(self):
        """Variante elegida mientras se mantiene la dirección al atacar."""
        from systems import controls
        p = self.player
        if p is not None and p.dash_time > 0:
            return 'dash'
        if controls.held('down'):
            return 'down'
        if controls.held('jump'):
            return 'up'
        return 'neutral'

    def _variant_target(self, variant):
        p = self.player
        tx, ty = self._mouse_world()
        if variant == 'up':
            return p.rect.centerx, p.rect.centery - 220
        if variant == 'down':
            return p.rect.centerx, p.rect.centery + 220
        if variant == 'dash':
            direction = 1 if p.facing_right else -1
            return p.rect.centerx + direction * 300, p.rect.centery
        return tx, ty

    def try_basic_attack(self, variant='neutral'):
        p = self.player
        if p is None:
            return False
        if p.character_class == 'ranger':
            return self.fire_arrow(*self._variant_target(variant))
        if p.character_class == 'mage':
            return self.fire_arcane_bolt(*self._variant_target(variant))
        if p.character_class == 'kitsune':
            return self.fire_foxfire(*self._variant_target(variant))
        self.try_attack(attack_variant=variant)
        return True
    
    def damage_player(self, amount, x=None, y=None):
        """Daño al jugador con feedback: número rojo, shake, sonido, hitstop."""
        p = self.player
        hp0 = p.health
        died, msg = p.take_damage(amount)
        lost = hp0 - p.health

        if lost > 0:
            p.stat_add('damage_taken', int(round(lost)))
            self.combat_timer = 4.0
            px = p.rect.centerx if x is None else x
            py = p.rect.top if y is None else y
            self.texts.add(
                px,
                py,
                f"-{max(1, int(round(lost)))}",
                (255, 90, 90),
            )
            self.fx.emit('hurt', px, py + 8)
            self.camera.add_trauma(0.3)
            audio.play("hurt")
            self.hitstop_t = max(self.hitstop_t, 0.06)

        if died and not self._go_sound:
            p.stat_add('deaths')
            self._go_sound = True
            audio.play("gameover")
            self.set_screen(GameScreen.GAME_OVER)
        elif died:
            self.set_screen(GameScreen.GAME_OVER)

        return died
    
    def try_attack(self, mult=1.0, range_mult=1.0,
                   attack_variant='neutral'):
        p = self.player
        if p is None or p.attack_cooldown > 0:
            return
        facing = melee_facing(p.rect.center, self.enemies,
                              1 if p.facing_right else -1)
        p.facing_right = facing > 0
        move = p.next_combo_move()
        from systems.attack_variants import directional_move
        move = directional_move(move, attack_variant, airborne=not p.on_ground)
        p.stat_add('attacks')
        p.stat_max('highest_combo', p.combo_step + 1)
        mult *= move['damage']
        range_mult *= move['reach']
        audio.play_class_attack(p.character_class, p.combo_step, 0.7)
        hits = p.attack(self.enemies, range_mult=range_mult,
                        cooldown=move['cooldown'],
                        downstrike=move.get('downstrike', False), move=move)
        self.combat_visuals.class_attack(
            p.character_class, p.rect.centerx, p.rect.centery,
            1 if p.facing_right else -1, power=max(1.0, mult),
            variant=move.get('pattern'))
        if hits:
            self.combat_timer = 4.0
            self.texts.add(p.rect.centerx, p.rect.top - 22,
                           f'COMBO {p.combo_step + 1}', (255, 220, 100))
            if move.get('downstrike'):
                p.velocity.y = -260.0
                self.fx.burst(p.rect.centerx, p.rect.bottom, n=14,
                              color=(255, 210, 120), speed=190.0,
                              life=0.4, grav=100.0)
        for enemy in hits:
            behind = (p.rect.centerx - enemy.rect.centerx) * getattr(enemy, 'direction', 1) < 0
            crit = (p.counter_bonus_t > 0
                    or random.random() < p._stat_multipliers.get('crit_chance', 0))
            # Puñalada trapera: por la espalda, crítico garantizado y doble daño
            if 'backstab' in p.unlocked_abilities and behind:
                crit = True
            dmg = int(p.damage * p._stat_multipliers.get('crit_damage', 1.5)) if crit else p.damage
            if crit and 'backstab' in p.unlocked_abilities and behind:
                dmg *= 2
            if p.counter_bonus_t > 0:
                dmg = int(dmg * 1.35)
                p.counter_bonus_t = 0.0
            if mult != 1.0:
                dmg = int(dmg * mult)
            # Verdugo: +50% contra enemigos bajo el 30% de vida
            if 'execute_bonus' in p.unlocked_abilities and enemy.health_ratio < 0.3:
                dmg = int(dmg * 1.5)
                self.texts.add(enemy.rect.centerx, enemy.rect.top - 18, "¡Ejecutado!", (255, 80, 80))
            ex, ey = enemy.rect.centerx, enemy.rect.centery
            lvl0 = p.level
            element = ('fire' if 'fire_burn' in p.unlocked_abilities else
                       'ice' if 'ice_slow' in p.unlocked_abilities else 'physical')
            dmg = max(1, round(dmg * damage_multiplier(enemy, element)))
            res = enemy.take_damage(dmg, p.rect.centerx)
            if res is not True and not isinstance(enemy, Boss):
                force = 220.0 if crit else 145.0
                force *= min(1.6, max(0.8, mult))
                vertical = None
                if move.get('downstrike'):
                    vertical = 460.0
                    force *= 0.72
                elif move.get('launch'):
                    vertical = -float(move['launch'])
                enemy.apply_impact(
                    p.rect.centerx, force, vertical,
                    heavy=crit or mult >= 1.35 or bool(move.get('launch')))
            actual = getattr(enemy, 'last_damage_taken', dmg)
            blocked = getattr(enemy, 'last_blocked', False)
            immune = actual <= 0
            if actual > 0:
                p.stat_add('hits')
                p.stat_add('damage_dealt', actual)
                p.gain_souls(8)
                if crit:
                    p.stat_add('critical_hits')
                if blocked:
                    p.stat_add('blocked_hits')
                posture_damage = 12 + 9 * p.combo_step
                if crit or mult >= 1.35:
                    posture_damage *= 1.55
                self._damage_posture(enemy, posture_damage)
            label = ("INMUNE" if immune else
                     f"BLOQUEO {actual}" if blocked else
                     f"{actual}" + (" CRIT" if crit else ""))
            color = ((185, 185, 195) if immune else
                     (180, 210, 235) if blocked else
                     (255, 220, 60) if crit else (255, 255, 255))
            self.texts.add(ex, ey - 6, label, color)
            self.fx.emit('critical' if crit else 'hit', ex, ey)
            # Estados al golpear según habilidades
            if enemy.alive() and element != 'physical':
                self._apply_element(enemy, element, heavy=crit or mult >= 1.35)
            elif enemy.alive() and (crit or mult >= 1.35):
                self._apply_element(enemy, 'physical', heavy=True)
            if 'stun_chance' in p.unlocked_abilities and enemy.alive():
                if not isinstance(enemy, Boss) and random.random() < 0.2:
                    enemy.status.apply('stun', 1.0)
                    self.texts.add(ex, ey - 20, "¡Aturdido!", (255, 230, 80))
            if immune:
                audio.play('immune', 0.7)
            else:
                audio.play_impact(p.character_class, crit, blocked, 0.8)
            self.hitstop_t = max(self.hitstop_t, 0.025 if blocked or immune else
                                 0.075 if crit else 0.045)
            self.camera.add_trauma(0.06 if blocked or immune else 0.18 if crit else 0.12)
            if res == 'phase':
                self.inv_message = f"¡{enemy.name} enfurece! Fase {enemy.phase}"
                self.inv_message_t = 2.5
            died = (res is True)
            if died:
                self.fx.emit('death', ex, ey)
                audio.play('kill')
                self.hitstop_t = max(self.hitstop_t, 0.09)
                self.camera.add_trauma(0.2)
                if isinstance(enemy, Boss):
                    self._begin_boss_defeat(enemy)
                else:
                    self._on_enemy_killed(enemy)
                if enemy in self.enemies:
                    self.enemies.remove(enemy)
                if enemy in self.all_sprites:
                    self.all_sprites.remove(enemy)

    def _handle_enemy_impact(self, enemy):
        """Resolve queued wall and ground impacts after enemy movement."""
        died = False
        for event in enemy.drain_impact_events():
            if died or not enemy.alive():
                break
            kind = event['kind']
            damage = event['damage']
            ex, ey = enemy.rect.center
            died = enemy.take_damage(damage, self.player.rect.centerx) is True
            actual = getattr(enemy, 'last_damage_taken', damage)
            if actual > 0:
                self.player.stat_add('damage_dealt', actual)
            if kind == 'wall':
                label, color = '¡REBOTE!', (255, 185, 95)
                self.fx.burst(ex, ey, n=12, color=color, speed=210.0,
                              life=0.36, grav=80.0)
            else:
                label, color = '¡DERRIBO!', (235, 205, 145)
                self.fx.burst(ex, enemy.rect.bottom, n=16, color=color,
                              speed=190.0, life=0.45, grav=150.0)
            self.texts.add(ex, enemy.rect.top - 18, f'{label} {actual}', color)
            self.camera.add_trauma(0.18 if kind == 'wall' else 0.24)
            self.hitstop_t = max(self.hitstop_t, 0.045)
            audio.play('slam', 0.65)
        return died

    def _apply_element(self, enemy, element, duration=3.0, heavy=False):
        if not enemy.alive():
            return None
        reaction = apply_element(enemy.status, element, duration, heavy)
        if reaction is None:
            return None
        ex, ey = enemy.rect.center
        self.texts.add(ex, enemy.rect.top - 22, reaction['name'], reaction['color'])
        self.fx.burst(ex, ey, n=22, color=reaction['color'], speed=270.0,
                      life=0.55, grav=30.0)
        audio.play_reaction(reaction['id'], 0.8)
        self.camera.add_trauma(0.22)
        victims = [enemy]
        if reaction['radius'] > 40:
            victims.extend(e for e in self.enemies if e is not enemy and e.alive()
                           and (e.rect.centerx - ex) ** 2 + (e.rect.centery - ey) ** 2
                           <= reaction['radius'] ** 2)
        for victim in victims:
            damage = max(1, round(reaction['damage'] * damage_multiplier(victim, element)))
            result = victim.take_damage(damage, self.player.rect.centerx)
            actual = getattr(victim, 'last_damage_taken', damage)
            if actual > 0:
                self.player.stat_add('hits')
                self.player.stat_add('damage_dealt', actual)
            if result is True:
                if isinstance(victim, Boss):
                    self._begin_boss_defeat(victim)
                else:
                    self._on_enemy_killed(victim)
        self.player.gain_experience(2)
        return reaction

    def release_charge(self):
        """Resuelve toque o carga usando la dirección mantenida al soltar."""
        p = self.player
        c = self.charging
        self.charging = 0.0
        self.charge_notified = False
        if p is None or c <= 0:
            self.charge_variant = 'neutral'
            return False
        variant = self.charge_variant
        if variant == 'neutral':
            variant = self.attack_variant()
        self.charge_variant = 'neutral'
        from systems.attack_variants import CHARGE_THRESHOLD, charge_values
        if c < CHARGE_THRESHOLD:
            return self.try_basic_attack(variant)
        profile = charge_values(p.character_class, c)
        if p.character_class == 'warrior' and 'charge_attack' in p.unlocked_abilities:
            profile['damage'] += 0.35 * min(c, 1.0)
            profile['reach'] += 0.15 * min(c, 1.0)
        label = {'up': 'ASCENSO', 'down': 'DESCENSO',
                 'dash': 'EMBESTIDA', 'neutral': 'CARGA'}[variant]
        self.texts.add(p.rect.centerx, p.rect.top - 8,
                       f"{label} x{profile['damage']:.1f}", profile['color'])
        self.fx.burst(p.rect.centerx, p.rect.centery, n=int(8 + 16 * c),
                      color=profile['color'], speed=230.0, life=0.45)
        if p.character_class in ('mage', 'ranger', 'kitsune'):
            return self.fire_charged_attack(profile, variant)
        self.try_attack(mult=profile['damage'], range_mult=profile['reach'],
                        attack_variant=variant)
        return True

    def _resolve_spawn(self, rect):
        """Sube el rect hasta quedar fuera de tiles sólidos (máx 48px)."""
        for _ in range(48):
            if not self.game_map.check_collision(rect):
                return True
            rect.y -= 1
        return False

    def _on_enemy_killed(self, enemy):
        """Recompensa por enemigo normal muerto (golpe o DoT)."""
        self._queue_death_visual(enemy)
        p = self.player
        if p.character_class == 'reaper':
            gained = p.gain_souls(18)
            if gained:
                self.texts.add(enemy.rect.centerx, enemy.rect.top - 24,
                               f'+{gained} ALMAS', (80, 235, 220))
        lvl0 = p.level
        grant_reward(p, {'xp': enemy.xp_value})
        self._check_levelup(lvl0)
        # Bestiario: base + élite + minijefe
        if p.record_kill(f"enemy:{enemy.enemy_type}"):
            self._bestiary_found(enemy.display_name)
        elite = getattr(enemy, 'elite', None)
        if elite is not None:
            if p.record_kill(f"elite:{elite['id']}:{enemy.enemy_type}"):
                self._bestiary_found(f"{elite['name']} {enemy.display_name}")
        mid = getattr(enemy, 'miniboss', None)
        if mid is not None and p.record_kill(f'mini:{mid}'):
            self._bestiary_found(enemy.display_name)
        if elite is not None:
            self.spawn_drop(enemy.rect.centerx, enemy.rect.centery, p.level,
                            force_item=True, luck_bonus=3.0)
            self.texts.add(enemy.rect.centerx, enemy.rect.top - 6,
                           f"¡Élite {elite['name']}!", (255, 220, 100))
        else:
            self.spawn_drop(enemy.rect.centerx, enemy.rect.centery, p.level)
        mid = getattr(enemy, 'miniboss', None)
        if mid is not None:
            # División del Moco Colosal (crías fuera de muros)
            for stype in (getattr(enemy, 'split_into', None) or []):
                m = Enemy(stype, enemy.rect.centerx, enemy.rect.top - 10,
                          scale=self._difficulty())
                self._resolve_spawn(m.rect)
                self.enemies.add(m)
                self.all_sprites.add(m)
            # Recompensa única por ciclo: +1 pt + épico
            if mid not in p.miniboss_defeated_ids:
                p.miniboss_defeated_ids.add(mid)
                reward = grant_reward(p, REWARD_PRESETS['miniboss_unique'],
                                      item_level=p.level)
                self.drops.append({'item': reward['items'][0],
                                   'rect': pygame.Rect(enemy.rect.centerx, enemy.rect.centery, 14, 14),
                                   'vy': -260.0, 'gold': reward['drop_gold'], 't': 0.0})
                self.inv_message = (f"¡Minijefe derrotado: {enemy.display_name}! "
                                    f"{reward_summary(reward)}")
                self.inv_message_t = 4.0
                audio.play('victory', 0.6)
                self.camera.add_trauma(0.4)
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        if enemy in self.all_sprites:
            self.all_sprites.remove(enemy)

    def _queue_death_visual(self, enemy, boss=False):
        if getattr(enemy, '_death_visual_queued', False):
            return
        enemy._death_visual_queued = True
        image, flip, scale = self._entity_frame(enemy)
        if flip:
            image = pygame.transform.flip(image, True, False)
        if scale != 1.0:
            image = pygame.transform.scale(
                image, (max(1, round(image.get_width() * scale)),
                        max(1, round(image.get_height() * scale))))
        color = (255, 160, 90)
        status = getattr(enemy, 'status', None)
        if status is not None:
            if status.has('burn'):
                color = (255, 105, 45)
            elif status.has('poison'):
                color = (105, 220, 120)
            elif status.has('slow') or status.has('chill'):
                color = (125, 205, 255)
        direction = 1 if enemy.rect.centerx >= self.player.rect.centerx else -1
        if isinstance(enemy, Boss):
            source_frames = self.sprite_frames[('boss', enemy.boss_id)].get('death', [])
        else:
            miniboss_id = getattr(enemy, 'miniboss', None)
            key = (('miniboss', miniboss_id) if miniboss_id else
                   ('enemy', getattr(enemy, 'enemy_type', 'skeleton')))
            source_frames = self.sprite_frames.get(key, {}).get('death', [])
        death_frames = []
        for frame in source_frames:
            current = pygame.transform.flip(frame, True, False) if flip else frame.copy()
            if scale != 1.0:
                current = pygame.transform.scale(
                    current, (max(1, round(current.get_width() * scale)),
                              max(1, round(current.get_height() * scale))))
            death_frames.append(current)
        self.death_visuals.append(create_death_echo(
            image, enemy.rect.center, direction, boss=boss, color=color,
            frames=death_frames))
        self.fx.burst(enemy.rect.centerx, enemy.rect.centery,
                      n=34 if boss else 14, color=color,
                      speed=300.0 if boss else 210.0,
                      life=0.8 if boss else 0.45, grav=120.0)

    def _bestiary_found(self, name):
        self.inv_message = f"¡Nuevo registro: {name}! (J: bestiario)"
        self.inv_message_t = 3.0
        audio.play('skill', 0.8)
        self.fx.burst(self.player.rect.centerx, self.player.rect.centery, n=12,
                    color=(150, 220, 255), speed=160.0, life=0.5, grav=100.0)

    def _drain_fx_texts(self, entity, default_color=(255, 255, 255)):
        pending = (entity.drain_fx_texts() if hasattr(entity, 'drain_fx_texts')
                   else list(getattr(entity, 'fx_texts', [])))
        for dmg, color in pending:
            self.texts.add(entity.rect.centerx, entity.rect.top - 4,
                        f"{int(dmg)}", color or default_color)
        if not hasattr(entity, 'drain_fx_texts') and hasattr(entity, 'fx_texts'):
            entity.fx_texts.clear()

    def _check_levelup(self, before):
        p = self.player
        if p.level > before:
            self.fx.emit('level_up', p.rect.centerx, p.rect.centery)
            self.texts.add(p.rect.centerx, p.rect.top - 6, f"¡NIVEL {p.level}!", (255, 220, 80))
            audio.play('levelup')
            self.camera.add_trauma(0.3)
