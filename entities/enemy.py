# enemy.py - Clase base para enemigos con física y persecución simple

import pygame
from entities.base import CombatEntity
from constants import TILE_SIZE, GRAVITY, MAX_FALL_SPEED, JUMP_STRENGTH
from systems.balance_data import ENEMY_STATS, MINIBOSS_DEFS
from systems.status import StatusList
from systems.impact_physics import ground_impact, launch_response, wall_bounce

class Enemy(CombatEntity):
    def __init__(self, enemy_type, x, y, scale=0, elite=None, miniboss=None):
        """scale = ciclo NG+ (0 = primera partida). elite = dict de ELITE_AFFIXES."""
        super().__init__()

        self.enemy_type = enemy_type
        self.scale = max(0, int(scale))
        self.elite = elite
        self.miniboss = miniboss
        self.display_name = enemy_type
        self.health = 0
        self.max_health = 0
        self.damage = 0
        self.speed = 0
        self.xp_value = 0
        
        enemy_stats = ENEMY_STATS

        if enemy_type in enemy_stats:
            stats = enemy_stats[enemy_type]
            self.health = int(stats['health'] * (1 + 0.6 * self.scale))
            self.max_health = self.health
            self.damage = int(round(stats['damage'] * (1 + 0.35 * self.scale)))
            self.speed = stats['speed']
            self.xp_value = int(stats['xp'] * (1 + 0.5 * self.scale))
            self.color = stats['color']
            self.display_name = stats.get('name', enemy_type)
            self.ai = dict(stats['ai'])
            self.behavior = stats.get('behavior', enemy_type)
            self.flying = stats.get('flying', enemy_type == 'bat')
            self.impact_weight = float(stats.get('weight', 1.0))
        else:
            self.health = int(20 * (1 + 0.6 * self.scale))
            self.max_health = self.health
            self.damage = int(round(5 * (1 + 0.35 * self.scale)))
            self.speed = 1
            self.xp_value = int(15 * (1 + 0.5 * self.scale))
            self.color = (255, 0, 0)
            self.ai = {'detection': 220, 'leash': 320, 'memory': 2.0,
                       'attack_cooldown': 1.5}
            self.behavior = enemy_type
            self.flying = enemy_type == 'bat'
            self.impact_weight = 1.0

        # Afijo de élite
        if self.elite is not None:
            self.display_name = f"{self.elite['name']} {enemy_type}"
            self.health = int(self.health * self.elite.get('hp', 1.0))
            self.max_health = self.health
            self.damage = int(round(self.damage * self.elite.get('dmg', 1.0)))
            self.speed = self.speed * self.elite.get('speed', 1.0)
            self.xp_value = int(self.xp_value * self.elite.get('xp', 1.0))

        # Minijefe: stats fijas (ya incluyen dureza) + tamaño
        _w, _h = TILE_SIZE, TILE_SIZE
        if self.miniboss is not None:
            md = MINIBOSS_DEFS[self.miniboss]
            self.display_name = md['name']
            self.health = int(md['health'] * (1 + 0.6 * self.scale))
            self.max_health = self.health
            self.damage = int(round(md['damage'] * (1 + 0.35 * self.scale)))
            self.speed = md['speed']
            self.xp_value = int(md.get('xp', 50) * (1 + 0.5 * self.scale))
            self.color = md['color']
            _w, _h = md['w'], md['h']
            self.split_into = md.get('split')
            self.charge_cd = 3.0
            self._charging = 0.0
            self._telegraph = 0.0
            self._charge_dir = 1
            self.impact_weight *= 2.1
        else:
            self.split_into = None
            self.charge_cd = 0.0
            self._charging = 0.0
            self._telegraph = 0.0
            self._charge_dir = 1

        self.width = _w
        self.height = _h
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.color)
        
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        self.velocity = pygame.math.Vector2(0, 0)
        self.direction = 1
        
        self.patrol_range = 100
        self.patrol_start_x = x
        self.chase_range = 220
        self.chase_range = self.ai['detection']
        self.on_ground = False
        self.hit_flash = 0.0  # parpadeo blanco al recibir daño (pulido)
        self.status = StatusList()
        # Anti-atasco
        self._blocked_x = False
        self._hop_cd = 0.0
        self._stuck_t = 0.0
        self._last_px = float(x)
        self._dot_carry = 0.0  # acumula fracciones de DoT para mostrar enteros
        self._mx_carry = 0.0  # resto fraccional de movimiento (lentos)
        self._my_carry = 0.0
        self.ai_state = 'patrol'
        self.alert_t = 0.0
        self.attack_cd = 0.0
        self.attack_windup = 0.0
        self.attack_window = 0.0
        self.retreat_t = 0.0
        self.dive_t = 0.0
        self.dive_target = pygame.math.Vector2(0, 0)
        self.blocking = False
        self.last_damage_taken = 0
        self.last_blocked = False
        self.knockback_t = 0.0
        self.impact_t = 0.0
        self.knocked_down_t = 0.0
        self.juggle_resistance = 0.0
        self.juggle_decay_delay = 0.0
        self.impact_events = []
        # Migrar speeds viejos (px/frame) a px/s
        if self.speed < 20:
            self.speed *= 60.0
        posture = 36 + self.max_health * 0.15
        if self.elite is not None:
            posture *= 1.35
        if self.miniboss is not None:
            posture *= 1.7
        self.init_posture(posture)
        self._posture_was_broken = False
        self.posture_counter_cd = 0.0

    def _step(self, delta, carry_name):
        """Mueve píxeles enteros acumulando la fracción (evita congelar lentos)."""
        total = getattr(self, carry_name) + delta
        px = int(total)  # trunca hacia cero; el resto se conserva
        setattr(self, carry_name, total - px)
        return px

    def _unembed(self, tilemap):
        """Garantía: si quedamos dentro de un sólido, salir hacia arriba."""
        if tilemap is not None and tilemap.check_collision(self.rect):
            for _ in range(48):
                self.rect.y -= 1
                if not tilemap.check_collision(self.rect):
                    break
            self.velocity.y = min(self.velocity.y, 0)

    def alert(self, seconds=None):
        self.alert_t = max(self.alert_t, seconds or self.ai['memory'])

    def can_damage_player(self):
        return self.miniboss is not None or self.attack_window > 0

    def _line_of_sight(self, player, tilemap):
        if tilemap is None:
            return True
        x0, y0 = self.rect.center
        x1, y1 = player.rect.center
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) // TILE_SIZE))
        for index in range(1, steps):
            t = index / steps
            if tilemap.is_solid(int(x0 + (x1 - x0) * t),
                                int(y0 + (y1 - y0) * t)):
                return False
        return True

    def _begin_attack(self, windup):
        self.attack_windup = windup
        self.velocity.x = 0
        self.ai_state = 'telegraph'

    def _finish_windup(self, player):
        self.attack_window = 0.28
        self.attack_cd = self.ai['attack_cooldown']
        self.ai_state = 'attack'
        self.direction = 1 if player.rect.centerx > self.rect.centerx else -1
        if self.behavior in ('goblin', 'charger', 'skirmisher'):
            self.velocity.x = self.direction * self.speed * 2.4
            if self.behavior == 'charger':
                self.attack_window = 0.48
            elif self.behavior == 'skirmisher':
                self.attack_window = 0.22
        elif self.behavior == 'leaper':
            self.velocity.x = self.direction * self.speed * 1.75
            self.velocity.y = JUMP_STRENGTH * 0.78
            self.on_ground = False
            self.attack_window = 0.62
        elif self.behavior in ('bat', 'diver'):
            target = pygame.math.Vector2(player.rect.center)
            origin = pygame.math.Vector2(self.rect.center)
            delta = target - origin
            if delta.length_squared() > 0:
                delta.scale_to_length(self.speed * (2.25 if self.flying else 1.8))
            self.velocity.update(delta)
            if self.flying:
                self.dive_t = 0.55
            self.attack_window = 0.55

    def apply_impact(self, source_x, horizontal=145.0, vertical=None, heavy=False):
        """Launch this enemy while weight and repeated aerial hits resist loops."""
        direction = 1 if self.rect.centerx >= source_x else -1
        vertical = -horizontal * 0.28 if vertical is None else vertical
        vx, vy = launch_response(
            self.impact_weight, direction * horizontal, vertical,
            self.juggle_resistance)
        self.velocity.x = vx
        self.velocity.y = vy if vertical >= 0 else min(self.velocity.y, vy)
        self.on_ground = False
        self.knockback_t = max(self.knockback_t, 0.18 if heavy else 0.13)
        self.impact_t = max(self.impact_t, 1.35)
        self.juggle_resistance = min(
            0.72, self.juggle_resistance + (0.18 if not self.on_ground else 0.1))
        self.juggle_decay_delay = 0.8
        return vx, vy

    def apply_knockback(self, source_x, power=145.0):
        return self.apply_impact(source_x, power)

    def drain_impact_events(self):
        pending = list(self.impact_events)
        self.impact_events.clear()
        return pending

    def _move_with_collision(self, tilemap, dt):
        old_x = self.rect.x
        incoming_x = self.velocity.x
        self.rect.x += self._step(self.velocity.x * dt, '_mx_carry')
        self._blocked_x = False
        if tilemap is not None and tilemap.check_collision(self.rect):
            self.rect.x = old_x
            self.direction *= -1
            rebound, damage = wall_bounce(incoming_x, self.impact_weight)
            if self.impact_t > 0 and damage > 0:
                self.velocity.x = rebound
                self.velocity.y = min(self.velocity.y, -95.0 / self.impact_weight)
                self.impact_events.append({'kind': 'wall', 'damage': damage,
                                           'speed': abs(incoming_x)})
                self.knockback_t = max(self.knockback_t, 0.12)
                self.juggle_resistance = min(0.72, self.juggle_resistance + 0.2)
            else:
                self.velocity.x = 0
            self._blocked_x = True
            self._mx_carry = 0.0
        incoming_y = self.velocity.y
        self.rect.y += self._step(self.velocity.y * dt, '_my_carry')
        if tilemap is not None and tilemap.check_collision(self.rect):
            if self.velocity.y > 0:
                self.on_ground = True
                self.rect.bottom = (self.rect.bottom // TILE_SIZE) * TILE_SIZE
                duration, damage = ground_impact(incoming_y, self.impact_weight)
                if self.impact_t > 0 and damage > 0:
                    self.knocked_down_t = max(self.knocked_down_t, duration)
                    self.impact_events.append({'kind': 'ground', 'damage': damage,
                                               'speed': incoming_y})
                    self.velocity.x *= 0.35
                    self.juggle_resistance = min(0.72, self.juggle_resistance + 0.24)
            elif self.velocity.y < 0:
                self.rect.top = ((self.rect.top // TILE_SIZE) + 1) * TILE_SIZE
            self.velocity.y = 0
        else:
            if not self.flying:
                self.on_ground = False
        
    def update(self, player, tilemap=None, dt=1.0/60.0):
        """Patrulla/persigue con dt. Retorna 'died' si el DoT lo mató."""
        dt = min(dt, 1.0 / 20.0)
        self.anim_t += dt
        was_broken = self.posture_broken_t > 0
        self.update_posture(dt)
        if was_broken and self.posture_broken_t <= 0 and self.elite is not None:
            self.posture_resist_t = 3.0
        self.posture_counter_cd = max(0.0, self.posture_counter_cd - dt)
        if self.hit_flash > 0:
            self.hit_flash -= dt
        self.alert_t = max(0.0, self.alert_t - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.attack_window = max(0.0, self.attack_window - dt)
        self.knockback_t = max(0.0, self.knockback_t - dt)
        self.impact_t = max(0.0, self.impact_t - dt)
        self.knocked_down_t = max(0.0, self.knocked_down_t - dt)
        self.juggle_decay_delay = max(0.0, self.juggle_decay_delay - dt)
        if self.juggle_decay_delay <= 0:
            self.juggle_resistance = max(0.0, self.juggle_resistance - 0.32 * dt)
        # Auto-reparación: si amanecimos dentro de un sólido, salir hacia arriba
        self._unembed(tilemap)
        # DoT de estados (solo enteros al mostrar, sin columnas de "0")
        dot = self.status.update(dt)
        if dot > 0:
            self.health -= dot
            self._dot_carry += dot
            whole = int(self._dot_carry)
            if whole >= 1:
                self._dot_carry -= whole
                self.queue_fx_text(whole, (255, 140, 40))
            if self.health <= 0:
                self.health = 0
                self.kill()
                return 'died'
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance_sq = dx * dx + dy * dy
        within_leash = abs(self.rect.centerx - self.patrol_start_x) <= self.ai['leash']
        sees_player = (distance_sq <= self.chase_range ** 2 and within_leash
                       and self._line_of_sight(player, tilemap))
        if sees_player:
            self.alert()
        chasing = within_leash and (sees_player or self.alert_t > 0)
        self.ai_state = 'chase' if chasing else 'return' if not within_leash else 'patrol'
        self.blocking = False
        posture_ratio = self.posture / max(1.0, self.posture_max)

        if self.knockback_t > 0 or self.knocked_down_t > 0 or (self.impact_t > 0 and not self.on_ground):
            self.ai_state = 'knocked_down' if self.knocked_down_t > 0 else 'hurt'
            self.attack_windup = 0.0
            self.attack_window = 0.0
        elif self.status.stunned():
            self.velocity.x = 0
            self.attack_windup = 0.0
            self.attack_window = 0.0
        elif (self.miniboss is None and self.behavior in ('skeleton', 'guardian')
              and posture_ratio <= 0.42 and abs(dx) < 150):
            self.velocity.x = 0
            self.blocking = True
            self.ai_state = 'guard_posture'
            self.posture = min(self.posture_max,
                               self.posture + self.posture_max * 0.24 * dt)
        elif (self.miniboss is None and self.behavior in ('goblin', 'skirmisher', 'bat')
              and posture_ratio <= 0.32 and abs(dx) < 180):
            self.direction = 1 if dx > 0 else -1
            self.velocity.x = -self.direction * self.speed * 1.15
            self.ai_state = 'retreat_posture'
        elif (self.miniboss is not None and posture_ratio <= 0.35
              and self.posture_counter_cd <= 0 and not self.status.stunned()):
            self.direction = 1 if dx > 0 else -1
            self.velocity.x = self.direction * max(280.0, self.speed * 2.2)
            self.attack_window = 0.38
            self.posture_counter_cd = 5.0
            self.ai_state = 'counter'
        elif self.miniboss == 'broken_knight' and (self._charging > 0 or self._telegraph > 0):
            # Carga del Caballero: telegraph quieto -> embestida
            self.charge_cd -= dt
            if self._telegraph > 0:
                self.velocity.x = 0
                self.hit_flash = max(self.hit_flash, 0.05)
                self._telegraph -= dt
                if self._telegraph <= 0:
                    self._charging = 0.5
                    self._charge_dir = 1 if dx > 0 else -1
            else:
                self.velocity.x = self._charge_dir * 360.0
                self._charging -= dt
                if self._charging <= 0:
                    self.charge_cd = 6.0
        elif self.miniboss is None and self.attack_windup > 0:
            self.velocity.x = 0
            self.attack_windup -= dt
            self.ai_state = 'telegraph'
            if self.attack_windup <= 0:
                self._finish_windup(player)
        elif self.miniboss is None and self.attack_window > 0:
            self.ai_state = 'attack'
            if self.behavior in ('skeleton', 'guardian'):
                self.velocity.x = 0
        elif chasing:
            self.direction = 1 if dx > 0 else -1
            # Zona muerta: al llegar, quieto mirando (sin vibrar ±1px)
            if self.miniboss is None and self.behavior == 'slime' and self.on_ground and self.attack_cd <= 0:
                self.velocity.y = JUMP_STRENGTH * 0.72
                self.velocity.x = self.direction * self.speed * 1.35
                self.on_ground = False
                self.attack_window = 0.65
                self.attack_cd = self.ai['attack_cooldown']
                self.ai_state = 'attack'
            elif self.miniboss is None and self.behavior in ('skeleton', 'guardian') and abs(dx) < 52 and self.attack_cd <= 0:
                self._begin_attack(0.42)
            elif self.miniboss is None and self.behavior in ('skeleton', 'guardian') and abs(dx) < 120:
                self.blocking = self.attack_cd > 0.35
                self.velocity.x = self.direction * self.speed * 0.28
                self.ai_state = 'block' if self.blocking else self.ai_state
            elif self.miniboss is None and self.behavior in ('goblin', 'charger', 'skirmisher') and abs(dx) < (125 if self.behavior == 'charger' else 62) and self.attack_cd <= 0:
                self._begin_attack(0.48 if self.behavior == 'charger' else 0.28)
            elif self.miniboss is None and self.behavior in ('goblin', 'skirmisher') and abs(dx) < 120 and self.attack_cd > 0:
                self.velocity.x = -self.direction * self.speed * 0.85
                self.ai_state = 'retreat'
            elif self.miniboss is None and self.behavior in ('bat', 'diver') and abs(dx) < 190 and self.attack_cd <= 0:
                self._begin_attack(0.36)
            elif self.miniboss is None and self.behavior == 'leaper' and self.on_ground and abs(dx) < 150 and self.attack_cd <= 0:
                self._begin_attack(0.5)
            elif abs(dx) < 6:
                self.velocity.x = 0
            else:
                self.velocity.x = self.direction * self.speed * self.status.speed_mult()
            if self.miniboss == 'broken_knight':
                self.charge_cd -= dt
                if (self.charge_cd <= 0 and abs(dx) < 300
                        and abs(player.rect.centery - self.rect.centery) < 40):
                    self._telegraph = 0.5
                    self.velocity.x = 0
        else:
            distance_from_start = self.rect.x - self.patrol_start_x
            if abs(distance_from_start) >= self.patrol_range:
                self.direction = -1 if distance_from_start > 0 else 1
            speed_mult = 0.7 if not within_leash else 0.5
            self.velocity.x = self.direction * self.speed * speed_mult * self.status.speed_mult()

        if self.flying and self.impact_t > 0:
            old_x, old_y = self.rect.x, self.rect.y
            incoming_x = self.velocity.x
            self.rect.x += self._step(self.velocity.x * dt, '_mx_carry')
            self.rect.y += self._step(self.velocity.y * dt, '_my_carry')
            if tilemap is not None and tilemap.check_collision(self.rect):
                self.rect.update(old_x, old_y, self.rect.width, self.rect.height)
                rebound, damage = wall_bounce(incoming_x, self.impact_weight)
                self.velocity.x = rebound
                self.velocity.y *= -0.3
                if damage > 0:
                    self.impact_events.append({'kind': 'wall', 'damage': damage,
                                               'speed': abs(incoming_x)})
            self.velocity *= max(0.0, 1.0 - 0.65 * dt)
        elif self.flying:
            if self.dive_t > 0:
                self.dive_t -= dt
                if self.dive_t <= 0:
                    self.attack_window = 0.0
                    self.velocity.update(0, -self.speed * 0.45)
            else:
                self.velocity.y = 0
                if chasing:
                    self.rect.y += int(round((60.0 if dy > 0 else -60.0) * dt)) if dy != 0 else 0
            old_bx = self.rect.x
            old_by = self.rect.y
            self.rect.x += self._step(self.velocity.x * dt, '_mx_carry')
            self.rect.y += self._step(self.velocity.y * dt, '_my_carry')
            if tilemap is not None and tilemap.check_collision(self.rect):
                self.rect.x = old_bx
                self.rect.y = old_by
                self._mx_carry = 0.0
                self.direction *= -1
                # Trepar el muro en vez de molerlo: subir si hay hueco, si no bajar
                up = self.rect.move(0, -2)
                down = self.rect.move(0, 2)
                if tilemap is not None and not tilemap.check_collision(up):
                    self.rect.y -= 2
                elif tilemap is not None and not tilemap.check_collision(down):
                    self.rect.y += 2
        else:
            self.velocity.y += GRAVITY * dt
            if self.velocity.y > MAX_FALL_SPEED:
                self.velocity.y = MAX_FALL_SPEED
            # Salto ante obstáculo persiguiendo (con cooldown para no rebotar)
            if self._hop_cd > 0:
                self._hop_cd -= dt
            if chasing and self._blocked_x and self.on_ground and self._hop_cd <= 0:
                self.velocity.y = JUMP_STRENGTH * 0.62
                self.on_ground = False
                self._hop_cd = 0.9
                self._stuck_t = 0.0
            # Seguro: si persigue sin progresar (muro o borde), saltar
            if chasing and self.on_ground and abs(self.velocity.x) > 1:
                if abs(self.rect.x - self._last_px) < 1.0:
                    self._stuck_t += dt
                else:
                    self._stuck_t = 0.0
                if self._stuck_t > 1.2:
                    self.velocity.y = JUMP_STRENGTH * 0.8
                    self.on_ground = False
                    self._stuck_t = 0.0
                    self._hop_cd = 0.9
            else:
                self._stuck_t = 0.0
            self._last_px = float(self.rect.x)
            self._move_with_collision(tilemap, dt)
            self._unembed(tilemap)
    
    def take_damage(self, amount, source_x=None):
        """Recibir daño (con bonus de marca). Retorna True si murió."""
        amount = int(amount * self.status.damage_taken_mult())
        self.last_blocked = False
        if (self.behavior in ('skeleton', 'guardian') and self.miniboss is None and self.blocking
                and source_x is not None
                and (source_x - self.rect.centerx) * self.direction > 0):
            amount = max(1, int(amount * 0.35))
            self.last_blocked = True
        self.last_damage_taken = amount
        self.health -= amount
        self.hit_flash = 0.12
        if self.health <= 0:
            self.health = 0
            self.kill()
            return True
        return False
    
    def draw(self, surface):
        surface.blit(self.image, self.rect)
