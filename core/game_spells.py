"""Player spell and ranged-ability execution."""

import math
import random

from entities.boss import Boss
from systems import audio
from systems.spells import ABILITY_SPELL, AllyShot, SPELL_DEFS, direction_to
from systems.aiming import assisted_target
from systems.elements import damage_multiplier


class GameSpellsMixin:
    def _assisted_aim(self, tx, ty):
        p = self.player
        return assisted_target(
            p.rect.center, (tx, ty), self.enemies,
            1 if p.facing_right else -1)

    def _spell_ready(self, spell):
        p = self.player
        abil = {v: k for k, v in ABILITY_SPELL.items()}
        need = abil.get(spell)
        if need not in p.unlocked_abilities:
            return False
        return p.spell_cd.get(spell, 0) <= 0

    def _spell_fire_mult(self):
        return self.player._stat_multipliers.get('fire_damage', 1.0)

    def cast_fireball(self, tx, ty):
        p = self.player
        if not self._spell_ready('fireball'):
            return False
        tx, ty = self._assisted_aim(tx, ty)
        p.spell_cd['fireball'] = SPELL_DEFS['fireball']['cooldown']
        p.begin_action(0.38)
        sx, sy = p.weapon_origin(tx, ty)
        dx, dy = direction_to(sx, sy, tx, ty)
        dmg = int(p.damage * 1.2 * self._spell_fire_mult())
        self.ally_shots.add(AllyShot(sx, sy, dx * 420.0, dy * 420.0, dmg,
                                     burn=True, visual='fireball', element='fire'))
        self.combat_visuals.class_attack('mage', sx, sy, 1 if dx >= 0 else -1)
        audio.play_class_attack('mage', p.combo_step, 0.7)
        self.fx.burst(sx, sy, n=6, color=(255, 140, 40), speed=120.0, life=0.25, grav=0.0)
        return True

    def fire_arcane_bolt(self, tx, ty):
        """Basic mage attack, aimed from the visible staff head."""
        p = self.player
        if p is None or p.attack_cooldown > 0:
            return False
        tx, ty = self._assisted_aim(tx, ty)
        move = p.next_combo_move()
        p.stat_add('attacks')
        p.stat_max('highest_combo', p.combo_step + 1)
        p.attack_cooldown = move['cooldown']
        p.begin_action(move['cooldown'])
        sx, sy = p.weapon_origin(tx, ty)
        dx, dy = direction_to(sx, sy, tx, ty)
        angle = math.atan2(dy, dx) + float(move.get('angle_offset', 0.0))
        count = int(move.get('projectiles', 1))
        spread = float(move.get('spread', 0.12 if count > 1 else 0.0))
        speed = float(move.get('speed', 440.0))
        for index in range(count):
            shot_angle = angle + (index - (count - 1) / 2.0) * spread
            self.ally_shots.add(AllyShot(
                sx, sy, math.cos(shot_angle) * speed, math.sin(shot_angle) * speed,
                int(p.damage * move['damage']), radius=5, life=1.7,
                color=(115, 190, 255), visual='arcane', element='electric'))
        self.combat_visuals.class_attack('mage', sx, sy,
                                         1 if p.facing_right else -1,
                                         variant=move.get('pattern'))
        self.fx.burst(sx, sy, n=5, color=(120, 190, 255),
                      speed=90.0, life=0.22, grav=0.0)
        audio.play_class_attack('mage', p.combo_step, 0.55)
        return True

    def fire_charged_attack(self, profile, variant='neutral'):
        """Proyectil cargado propio de Maga, Arquera o Kitsune."""
        p = self.player
        if p is None or p.attack_cooldown > 0:
            return False
        tx, ty = self._variant_target(variant)
        tx, ty = self._assisted_aim(tx, ty)
        sx, sy = p.weapon_origin(tx, ty)
        angle = math.atan2(ty - sy, tx - sx)
        speed = profile['speed']
        damage = int(p.damage * profile['damage'])
        burn = p.character_class == 'kitsune'
        self.ally_shots.add(AllyShot(
            sx, sy, math.cos(angle) * speed, math.sin(angle) * speed,
            damage, radius=profile['radius'], life=2.0,
            color=profile['color'], burn=burn, pierce=profile['pierce'],
            visual=profile['visual'], element=profile['element']))
        p.attack_cooldown = 0.58
        p.begin_action(0.58)
        p.stat_add('attacks')
        self.combat_visuals.class_attack(
            p.character_class, sx, sy, 1 if p.facing_right else -1,
            power=1.35, variant='thrust')
        self.fx.burst(sx, sy, n=14, color=profile['color'],
                      speed=170.0, life=0.4, grav=0.0)
        audio.play_class_attack(p.character_class, 2, 0.85)
        return True

    def cast_nova(self):
        p = self.player
        if not self._spell_ready('frost_nova'):
            return False
        p.spell_cd['frost_nova'] = SPELL_DEFS['frost_nova']['cooldown']
        p.begin_action(0.5)
        cx, cy = p.rect.centerx, p.rect.centery
        dmg = int(p.damage * 0.8)
        for e in list(self.enemies):
            dx, dy = e.rect.centerx - cx, e.rect.centery - cy
            if dx * dx + dy * dy <= 115 * 115:
                self._spell_hit(e, dmg, 'ice', apply_status=True)
                if e.alive():
                    e.status.apply('slow', 2.5)
        self.fx.burst(cx, cy, n=30, color=(140, 200, 255), speed=300.0, life=0.6, grav=0.0)
        self.combat_visuals.add('sigil', cx, cy, 1, (150, 220, 255), life=0.5, scale=1.8)
        audio.play('nova')
        self.camera.add_trauma(0.35)
        self.hitstop_t = max(self.hitstop_t, 0.06)
        return True

    def cast_meteor(self, tx, ty):
        p = self.player
        if not self._spell_ready('meteor'):
            return False
        # Fijar objetivo cerca del jugador (máx 500px)
        dx, dy = tx - p.rect.centerx, ty - p.rect.centery
        d = max(1.0, (dx * dx + dy * dy) ** 0.5)
        if d > 500:
            tx = p.rect.centerx + dx / d * 500
            ty = p.rect.centery + dy / d * 500
        p.spell_cd['meteor'] = SPELL_DEFS['meteor']['cooldown']
        p.begin_action(0.48)
        self.combat_visuals.class_attack('mage', p.rect.centerx, p.rect.centery,
                                         1 if tx >= p.rect.centerx else -1, 1.3)
        self.pending_meteors.append({'x': tx, 'y': ty, 't': 0.9,
                                     'damage': int(p.damage * 3.0 * self._spell_fire_mult())})
        audio.play_class_attack('mage', p.combo_step, 0.5)
        return True

    def cast_blizzard(self, tx, ty):
        p = self.player
        if not self._spell_ready('blizzard'):
            return False
        dx, dy = tx - p.rect.centerx, ty - p.rect.centery
        d = max(1.0, (dx * dx + dy * dy) ** 0.5)
        if d > 450:
            tx = p.rect.centerx + dx / d * 450
            ty = p.rect.centery + dy / d * 450
        p.spell_cd['blizzard'] = SPELL_DEFS['blizzard']['cooldown']
        p.begin_action(0.45)
        self.combat_visuals.add('sigil', p.rect.centerx, p.rect.centery, 1,
                                (190, 230, 255), life=0.45, scale=1.4)
        self.blizzards.append({'x': tx, 'y': ty, 't': 0.0, 'duration': 6.0, 'tick': 0.0})
        audio.play('nova', 0.7)
        return True

    def _spell_hit(self, enemy, dmg, element='physical', apply_status=False):
        """Daño de hechizo con recompensa. Retorna True si murió."""
        ex, ey = enemy.rect.centerx, enemy.rect.centery
        dmg = max(1, round(dmg * damage_multiplier(enemy, element)))
        res = enemy.take_damage(dmg, self.player.rect.centerx)
        if res is not True and not isinstance(enemy, Boss) and hasattr(enemy, 'apply_knockback'):
            enemy.apply_impact(self.player.rect.centerx, 105.0, -75.0)
        actual = getattr(enemy, 'last_damage_taken', dmg)
        blocked = getattr(enemy, 'last_blocked', False)
        if actual > 0:
            self.player.stat_add('hits')
            self.player.stat_add('damage_dealt', actual)
            self.player.gain_souls(7)
            if blocked:
                self.player.stat_add('blocked_hits')
            self._damage_posture(enemy, 10 if not blocked else 6)
        immune = actual <= 0
        self.texts.add(ex, ey - 6,
                       "INMUNE" if immune else f"BLOQUEO {actual}" if blocked else f"{actual}",
                       (185, 185, 195) if immune else
                       (180, 210, 235) if blocked else (150, 220, 255))
        self.fx.burst(ex, ey, n=8, color=(150, 200, 255), speed=180.0, life=0.35)
        if immune:
            audio.play('immune', 0.65)
        else:
            audio.play_impact(self.player.character_class, blocked=blocked, volume=0.6)
        if res == 'phase':
            self.inv_message = f"¡{enemy.name} enfurece! Fase {enemy.phase}"
            self.inv_message_t = 2.5
        if res is not True and apply_status and enemy.alive():
            self._apply_element(enemy, element)
        if res is True:
            self.fx.burst(ex, ey, n=20, color=(200, 200, 200), speed=220.0, life=0.6)
            audio.play('kill')
            if isinstance(enemy, Boss):
                self._begin_boss_defeat(enemy)
            else:
                self._on_enemy_killed(enemy)
            if enemy in self.enemies:
                self.enemies.remove(enemy)
            if enemy in self.all_sprites:
                self.all_sprites.remove(enemy)
            return True
        return False

    def _update_spells(self, dt):
        p = self.player
        # Proyectiles aliados
        for shot in list(self.ally_shots):
            shot.update(self.game_map, dt)
            if not shot.alive():
                continue
            self.fx.trail(shot.rect.centerx, shot.rect.centery,
                          color=shot.color, n=1, life=0.2, size=3)
            hit = None
            for e in self.enemies:
                if id(e) in shot.hit_ids:
                    continue
                if shot.rect.colliderect(e.rect):
                    hit = e
                    break
            if hit is not None:
                shot.hit_ids.add(id(hit))
                self._spell_hit(hit, shot.damage, shot.element,
                                apply_status=shot.element != 'physical')
                # Flecha explosiva: AoE + quemadura alrededor
                if 'explosive' in self.player.unlocked_abilities:
                    for e in list(self.enemies):
                        if e is hit or not e.alive():
                            continue
                        dx, dy = e.rect.centerx - shot.rect.centerx, e.rect.centery - shot.rect.centery
                        if dx * dx + dy * dy <= 50 * 50:
                            self._spell_hit(e, int(shot.damage * 0.5), 'fire',
                                            apply_status=True)
                            if e.alive():
                                e.status.apply('burn', 2.0)
                    self.fx.burst(shot.rect.centerx, shot.rect.centery, n=16,
                                  color=(255, 120, 50), speed=260.0, life=0.45)
                    audio.play('slam', 0.4)
                else:
                    self.fx.burst(shot.rect.centerx, shot.rect.centery, n=10,
                                  color=(255, 140, 40), speed=200.0, life=0.35)
                if shot.pierce > 0:
                    shot.pierce -= 1
                else:
                    shot.kill()
        # Meteoritos pendientes
        for m in list(self.pending_meteors):
            m['t'] -= dt
            if m['t'] <= 0:
                self.pending_meteors.remove(m)
                for e in list(self.enemies):
                    dx, dy = e.rect.centerx - m['x'], e.rect.centery - m['y']
                    if dx * dx + dy * dy <= 120 * 120:
                        self._spell_hit(e, m['damage'], 'fire', apply_status=True)
                self.fx.burst(m['x'], m['y'], n=40, color=(255, 120, 50),
                              speed=340.0, life=0.8)
                audio.play('meteor')
                self.camera.add_trauma(0.7)
                self.hitstop_t = max(self.hitstop_t, 0.1)
        # Ventiscas activas
        for z in list(self.blizzards):
            z['t'] += dt
            z['tick'] -= dt
            if z['t'] >= z['duration']:
                self.blizzards.remove(z)
                continue
            self.fx.burst(z['x'] + random.uniform(-90, 90), z['y'] - 40,
                        n=1, color=(200, 230, 255), speed=40.0, life=0.8, grav=-60.0)
            if z['tick'] <= 0:
                z['tick'] = 0.5
                for e in list(self.enemies):
                    dx, dy = e.rect.centerx - z['x'], e.rect.centery - z['y']
                    if dx * dx + dy * dy <= 100 * 100:
                        self._spell_hit(e, int(p.damage * 0.4), 'ice', apply_status=True)
                        if e.alive():
                            e.status.apply('slow', 1.2)
        # Órbita arcana: 2 orbes que dañan al contacto (ICD por enemigo)
        if 'arcane_orbit' in p.unlocked_abilities:
            self.orb_angle += 3.6 * dt
            for k in range(2):
                ang = self.orb_angle + k * math.pi
                ox_ = p.rect.centerx + math.cos(ang) * 58
                oy_ = p.rect.centery + math.sin(ang) * 58
                for e in list(self.enemies):
                    if getattr(e, 'orb_cd', 0.0) > 0:
                        continue
                    dx, dy = e.rect.centerx - ox_, e.rect.centery - oy_
                    if dx * dx + dy * dy <= 26 * 26:
                        e.orb_cd = 0.5
                        self._spell_hit(e, int(p.damage * 0.5))
        # Decaer ICD de orbes
        for e in self.enemies:
            if getattr(e, 'orb_cd', 0) > 0:
                e.orb_cd -= dt

    # --- Update ---

    def cast_whirlwind(self):
        """Torbellino 360° del guerrero (tecla X)."""
        p = self.player
        if 'whirlwind' not in p.unlocked_abilities or p.spell_cd.get('whirlwind', 0) > 0:
            return False
        p.spell_cd['whirlwind'] = SPELL_DEFS['whirlwind']['cooldown']
        p.stat_add('attacks')
        p.spin_t = 0.3
        p.begin_action(0.3)
        cx, cy = p.rect.centerx, p.rect.centery
        for e in list(self.enemies):
            dx, dy = e.rect.centerx - cx, e.rect.centery - cy
            if dx * dx + dy * dy <= 78 * 78:
                ex, ey = e.rect.centerx, e.rect.centery
                dealt = int(p.damage * 1.5)
                res = e.take_damage(dealt, p.rect.centerx)
                actual = getattr(e, 'last_damage_taken', dealt)
                if actual > 0:
                    p.stat_add('hits')
                    p.stat_add('damage_dealt', actual)
                self.texts.add(ex, ey - 6, f"{actual}", (255, 200, 120))
                if res == 'phase':
                    self.inv_message = f"¡{e.name} enfurece! Fase {e.phase}"
                    self.inv_message_t = 2.5
                if res is True:
                    self.fx.burst(ex, ey, n=16, color=(255, 200, 120), speed=240.0, life=0.5)
                    if isinstance(e, Boss):
                        self._begin_boss_defeat(e)
                    else:
                        self._on_enemy_killed(e)
                    if e in self.enemies:
                        self.enemies.remove(e)
                    if e in self.all_sprites:
                        self.all_sprites.remove(e)
        self.fx.burst(cx, cy, n=26, color=(255, 220, 140), speed=300.0, life=0.5, grav=0.0)
        audio.play_class_attack('warrior', p.combo_step, 1.0)
        audio.play_impact('warrior', volume=0.8)
        self.camera.add_trauma(0.3)
        self.hitstop_t = max(self.hitstop_t, 0.05)
        return True

    def fire_arrow(self, tx, ty, count=1, spread=0.0):
        """Flechazo básico del arquero. Retorna True si disparó."""
        p = self.player
        if p is None or p.attack_cooldown > 0:
            return False
        tx, ty = self._assisted_aim(tx, ty)
        import math
        move = p.next_combo_move()
        p.stat_add('attacks')
        p.stat_max('highest_combo', p.combo_step + 1)
        p.attack_cooldown = move['cooldown']
        p.begin_action(move['cooldown'])
        sx, sy = p.weapon_origin(tx, ty)
        base_ang = math.atan2(ty - sy, tx - sx) + float(move.get('angle_offset', 0.0))
        pierce = p.skill_ranks.get('piercing', 0)
        count = max(count, int(move.get('projectiles', 1)))
        spread = max(spread, float(move.get('spread', 0.12 if count > 1 else 0.0)))
        speed = float(move.get('speed', 520.0))
        fired = False
        for i in range(max(1, count)):
            ang = base_ang + (i - (count - 1) / 2.0) * spread
            self.ally_shots.add(AllyShot(sx, sy, math.cos(ang) * speed, math.sin(ang) * speed,
                                         int(p.damage * move['damage']), radius=4, life=1.6,
                                         color=(200, 230, 150), pierce=pierce,
                                         visual='arrow', element='physical'))
            fired = True
        if fired:
            self.combat_visuals.class_attack('ranger', sx, sy,
                                             1 if p.facing_right else -1,
                                             variant=move.get('pattern'))
            audio.play_class_attack('ranger', p.combo_step, 0.5)
        return fired

    def fire_foxfire(self, tx, ty, empowered=False):
        """Ataque básico de la Kitsune: orbes hacia el puntero."""
        p = self.player
        if p is None or p.attack_cooldown > 0:
            return False
        tx, ty = self._assisted_aim(tx, ty)
        move = p.next_combo_move()
        p.stat_add('attacks')
        p.stat_max('highest_combo', p.combo_step + 1)
        p.attack_cooldown = move['cooldown'] * (1.15 if empowered else 1.0)
        p.begin_action(p.attack_cooldown)
        sx, sy = p.weapon_origin(tx, ty)
        base_ang = math.atan2(ty - sy, tx - sx) + float(move.get('angle_offset', 0.0))
        count = max(int(move.get('projectiles', 1)), 2 if empowered else 1)
        spread = float(move.get('spread', 0.16 if count > 1 else 0.0))
        speed = float(move.get('speed', 470.0))
        for i in range(count):
            ang = base_ang + (i - (count - 1) / 2.0) * spread
            self.ally_shots.add(AllyShot(
                sx, sy, math.cos(ang) * speed, math.sin(ang) * speed,
                int(p.damage * move['damage'] * (1.15 if empowered else 1.0)),
                radius=5, life=1.7, color=(255, 105, 185),
                burn='spirit_burn' in p.unlocked_abilities, visual='orb',
                element='fire'))
        p.facing_right = tx >= sx
        self.combat_visuals.class_attack('kitsune', sx, sy,
                                         1 if p.facing_right else -1,
                                         variant=move.get('pattern'))
        self.fx.burst(sx, sy, n=5, color=(255, 145, 100),
                      speed=90.0, life=0.25, grav=0.0)
        audio.play_class_attack('kitsune', p.combo_step, 0.45)
        return True

    def cast_nine_tail_burst(self, tx, ty):
        """Dispara nueve llamas en abanico con enfriamiento propio."""
        p = self.player
        if (p is None or 'nine_tail_burst' not in p.unlocked_abilities
                or p.spell_cd.get('nine_tail_burst', 0) > 0):
            return False
        tx, ty = self._assisted_aim(tx, ty)
        p.spell_cd['nine_tail_burst'] = 6.0
        sx, sy = p.weapon_origin(tx, ty)
        base_ang = math.atan2(ty - sy, tx - sx)
        for i in range(9):
            ang = base_ang + (i - 4) * 0.095
            self.ally_shots.add(AllyShot(
                sx, sy, math.cos(ang) * 500.0, math.sin(ang) * 500.0,
                int(p.damage * 0.72), radius=5, life=1.6,
                color=(255, 105, 185), burn=True, visual='orb', element='fire'))
        p.begin_action(0.5)
        p.facing_right = tx >= sx
        self.fx.burst(sx, sy, n=20, color=(255, 130, 170),
                      speed=180.0, life=0.45, grav=0.0)
        audio.play('skill', 0.8)
        return True

    def cast_soul_reap(self, tx, ty):
        """Consume almas y libera filos espectrales perforantes."""
        p = self.player
        cost = 30
        if (p is None or p.character_class != 'reaper'
                or p.spell_cd.get('soul_reap', 0) > 0):
            return False
        if p.souls < cost:
            self.inv_message = f"Cosecha Espectral requiere {cost} almas"
            self.inv_message_t = 1.4
            return False
        tx, ty = self._assisted_aim(tx, ty)
        p.souls -= cost
        p.spell_cd['soul_reap'] = SPELL_DEFS['soul_reap']['cooldown']
        sx, sy = p.weapon_origin(tx, ty)
        base_ang = math.atan2(ty - sy, tx - sx)
        empowered = 'requiem' in p.unlocked_abilities
        count = 5 if empowered else 3
        spread = 0.12
        for i in range(count):
            ang = base_ang + (i - (count - 1) / 2.0) * spread
            self.ally_shots.add(AllyShot(
                sx, sy, math.cos(ang) * 500.0, math.sin(ang) * 500.0,
                int(p.damage * (1.55 if empowered else 1.25)),
                radius=8, life=1.35, color=(80, 235, 220),
                pierce=3 if empowered else 2, visual='scythe', element='physical'))
        p.begin_action(0.55)
        p.facing_right = tx >= sx
        self.combat_visuals.class_attack('reaper', p.rect.centerx,
                                         p.rect.centery,
                                         1 if p.facing_right else -1, 1.35)
        self.fx.burst(sx, sy, n=22, color=(80, 235, 220),
                      speed=210.0, life=0.55, grav=0.0)
        audio.play('skill', 0.9)
        return True

    def cast_triple(self, tx, ty):
        p = self.player
        if 'triple_shot' not in p.unlocked_abilities or p.spell_cd.get('triple_shot', 0) > 0:
            return False
        if p.attack_cooldown > 0:
            return False
        p.spell_cd['triple_shot'] = SPELL_DEFS['triple_shot']['cooldown']
        return self.fire_arrow(tx, ty, count=3, spread=0.2)
