# boss.py - Jefes con fases, telegraphs, proyectiles, invocaciones, AoE y veneno.

import math
import pygame
from entities.base import CombatEntity
from constants import TILE_SIZE, GRAVITY, MAX_FALL_SPEED
from systems.balance_data import BOSS_DEFS, PHASE_THRESHOLDS
from systems.status import StatusList

class Projectile(pygame.sprite.Sprite):
    """Proyectil hostil simple con física recta y tiempo de vida."""
    def __init__(self, x, y, vx, vy, damage, radius=5, life=3.0, color=(220, 80, 255),
                 status=None):
        super().__init__()
        self.damage = int(damage)
        self.velocity = pygame.math.Vector2(vx, vy)
        self.life = float(life)
        self.radius = radius
        self.status = status  # (sid, duration) a aplicar al jugador o None
        size = radius * 2 + 2
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), radius)
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def update(self, tilemap, dt):
        dt = min(dt, 1.0 / 20.0)
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.rect.x += int(round(self.velocity.x * dt))
        self.rect.y += int(round(self.velocity.y * dt))
        if tilemap is not None and tilemap.check_collision(self.rect):
            self.kill()


class Boss(CombatEntity):
    def __init__(self, boss_id, x, y, scale=0):
        """scale = ciclo NG+ (0 = primera partida)."""
        super().__init__()
        d = BOSS_DEFS[boss_id]
        self.boss_id = boss_id
        self.scale = max(0, int(scale))
        self.dmg_scale = 1.0 + 0.4 * self.scale
        self.name = d['name'] + (f" +{self.scale}" if self.scale else "")
        self.max_health = int(d['health'] * (1 + 0.8 * self.scale))
        self.health = self.max_health
        self.base_damage = d['damage']
        self.base_speed = d['speed']
        self.xp_value = int(d['xp'] * (1 + 0.5 * self.scale))
        self.gold_value = int(d['gold'] * (1 + 0.5 * self.scale))
        self.damage = d['damage']
        self.speed = d['speed']
        self.attacks = d['attacks']
        self.tuning = d['tuning']
        self.phase_defs = d['phases']
        self.cinematic_lock = True

        self.image = pygame.Surface((d['width'], d['height']))
        self.image.fill(d['color'])
        pygame.draw.rect(self.image, (255, 220, 60), pygame.Rect(6, 8, 7, 7))
        pygame.draw.rect(self.image, (255, 220, 60), pygame.Rect(d['width'] - 13, 8, 7, 7))
        self.rect = self.image.get_rect(topleft=(int(x), int(y)))

        self.velocity = pygame.math.Vector2(0, 0)
        self.direction = -1
        self.on_ground = False

        self.phase = 1
        self.state = 'chase'  # chase | telegraph_charge | charging | stunned | telegraph_leap | leaping | telegraph_slam | recover | blink_out | meteor_fall
        self.state_t = 0.0
        self.shoot_cd = 1.5
        self.charge_cd = 4.0
        self.slam_cd = 3.0
        self.summon_cd = 6.0
        self.pool_cd = 4.0
        self.blink_cd = 3.0
        self.ring_cd = 3.0
        self.meteor_cd = 5.0
        self._blink_meteor = False
        self._blink_dest = (0, 0)
        self.charge_dir = pygame.math.Vector2(-1, 0)
        self.leap_from = pygame.math.Vector2(0, 0)
        self.leap_to = pygame.math.Vector2(0, 0)
        self.flash_t = 0.0
        self._phase_event_pending = None
        self.status = StatusList()
        self.init_posture(240 + self.max_health * 0.18)
        self.posture_response_cd = 0.0

    @property
    def enemy_type(self):
        return 'boss'

    def phase_of(self, hp_frac):
        for thresh, ph in PHASE_THRESHOLDS:
            if hp_frac > thresh:
                return ph
        return 3

    def take_damage(self, amount, source_x=None):
        if self.cinematic_lock or self.state == 'phase_transition':
            self.last_damage_taken = 0
            return False
        amount = int(amount * self.status.damage_taken_mult())
        self.last_damage_taken = amount
        self.health -= amount
        self.flash_t = max(self.flash_t, 0.08)  # flash de impacto (además del telegraph)
        if self.health <= 0:
            self.health = 0
            self.kill()
            return True
        new_phase = self.phase_of(self.health_ratio)
        if new_phase != self.phase:
            self.phase = new_phase
            t = self.tuning[self.phase]
            self.speed = self.base_speed * t['speed_mult']
            self.damage = int(round(self.base_damage * t['dmg_mult']))
            self.state = 'phase_transition'
            self.state_t = 1.1
            self.flash_t = 1.1
            self.velocity.update(0, 0)
            self.shoot_cd = 1.0
            self._phase_event_pending = self.phase
            return 'phase'
        return False

    def can_damage_player(self):
        return not self.cinematic_lock

    def _move_with_collision(self, tilemap, dt):
        dx = self.velocity.x * dt
        old_x = self.rect.x
        self.rect.x += int(round(dx))
        if tilemap is not None and tilemap.check_collision(self.rect):
            self.rect.x = old_x
            self.velocity.x = 0
            return True
        dy = self.velocity.y * dt
        self.rect.y += int(round(dy))
        if tilemap is not None and tilemap.check_collision(self.rect):
            if self.velocity.y > 0:
                self.on_ground = True
                self.rect.bottom = (self.rect.bottom // TILE_SIZE) * TILE_SIZE
            elif self.velocity.y < 0:
                self.rect.top = ((self.rect.top // TILE_SIZE) + 1) * TILE_SIZE
            self.velocity.y = 0
        else:
            self.on_ground = False
        return False

    def _blink_spot(self, player, tilemap, above=False):
        """Busca un punto libre: anillo alrededor del jugador o encima (meteoro)."""
        import random as _r
        if above:
            cand = pygame.Rect(player.rect.centerx - self.rect.width // 2,
                               player.rect.top - 150, self.rect.width, self.rect.height)
            if tilemap is None or not tilemap.check_collision(cand):
                return cand.topleft
            return None
        for _ in range(6):
            ang = _r.uniform(0, 2 * math.pi)
            dist = _r.uniform(150, 220)
            cx = player.rect.centerx + math.cos(ang) * dist
            cy = player.rect.centery + math.sin(ang) * dist * 0.5
            cand = pygame.Rect(int(cx - self.rect.width // 2), int(cy - self.rect.height // 2),
                               self.rect.width, self.rect.height)
            if tilemap is None or not tilemap.check_collision(cand):
                return cand.topleft
        return None

    def _ring_shot(self, tuning):
        projs = []
        n = max(4, int(self.attacks.get('ring_n', 10)))
        dmg = int(round(tuning['proj_dmg'] * self.dmg_scale))
        st = ('chill', 1.5) if self.boss_id == 'void_heart' else None
        sx, sy = self.rect.centerx, self.rect.centery
        for i in range(n):
            ang = 2 * math.pi * i / n
            vx, vy = math.cos(ang) * tuning['proj_speed'], math.sin(ang) * tuning['proj_speed']
            projs.append(Projectile(sx, sy, vx, vy, dmg, color=(180, 60, 220), status=st))
        return projs

    def _shoot_at(self, player, tuning):
        """Disparo simple o abanico según attacks['spread']."""
        projs = []
        dmg = int(round(tuning['proj_dmg'] * self.dmg_scale))
        sx, sy = self.rect.centerx, self.rect.centery - 6
        dx, dy = player.rect.centerx - sx, player.rect.centery - sy
        base_ang = math.atan2(dy, dx)
        n = max(1, int(self.attacks.get('spread', 1)))
        spread_step = 0.26  # ~15 grados
        for i in range(n):
            ang = base_ang + (i - (n - 1) / 2.0) * spread_step
            vx, vy = math.cos(ang) * tuning['proj_speed'], math.sin(ang) * tuning['proj_speed']
            if self.boss_id == 'cavern_mother':
                color, st = (140, 255, 120), ('poison', 3.0)
            elif self.boss_id == 'void_heart':
                color, st = (220, 80, 255), ('chill', 1.5)
            else:
                color, st = (220, 80, 255), None
            projs.append(Projectile(sx, sy, vx, vy, dmg, color=color, status=st))
        return projs

    def update(self, player, tilemap=None, dt=1.0 / 60.0, alive_minions=0):
        """Retorna eventos: projectiles[], summon_requests[], slam{}, hazard{}, phase_changed, telegraph."""
        dt = min(dt, 1.0 / 20.0)
        self.anim_t += dt
        self.update_posture(dt)
        t = self.tuning[self.phase]
        atk = self.attacks
        events = {'projectiles': [], 'summon_requests': [], 'slam': None, 'hazard': None,
                  'phase_changed': None, 'telegraph': None, 'blink': None}
        self.shoot_cd -= dt
        self.charge_cd -= dt
        self.slam_cd -= dt
        self.summon_cd -= dt
        self.pool_cd -= dt
        self.blink_cd -= dt
        self.ring_cd -= dt
        self.meteor_cd -= dt
        self.posture_response_cd = max(0.0, self.posture_response_cd - dt)
        posture_ratio = self.posture / max(1.0, self.posture_max)
        if (posture_ratio <= 0.28 and self.state == 'chase'
                and self.posture_response_cd <= 0
                and 'slam_radius' in atk):
            self.state = 'telegraph_slam'
            self.state_t = 0.48
            self.posture_response_cd = 6.0
        if self.flash_t > 0:
            self.flash_t -= dt

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist_x = abs(dx)
        self.direction = 1 if dx > 0 else -1

        # Estados: DoT completo, slow a la mitad, inmune a stun, marca completa
        dot = self.status.update(dt)
        if dot > 0:
            # Acumular fracciones: los ticks son <1 dmg y el int() los mataría
            self._dot_carry = getattr(self, '_dot_carry', 0.0) + dot
            whole = int(self._dot_carry)
            if whole > 0:
                self._dot_carry -= whole
                self.queue_fx_text(whole, (255, 140, 40))
                self.take_damage(whole)
                if self.health <= 0:
                    return events
        slow_m = 1.0 - (1.0 - self.status.speed_mult()) * 0.5

        if self.state == 'phase_transition':
            self.velocity.update(0, 0)
            if self._phase_event_pending is not None:
                events['phase_changed'] = self._phase_event_pending
                self._phase_event_pending = None
            self.state_t -= dt
            events['telegraph'] = 'phase'
            if self.state_t <= 0:
                self.state = 'chase'
                entry = self.phase_defs[self.phase]['entry']
                if entry == 'summon' and atk.get('summon_types'):
                    events['summon_requests'].extend(atk['summon_types'][:2])
                elif entry == 'ring':
                    events['projectiles'].extend(self._ring_shot(t))
                elif entry == 'hazard' and atk.get('pools'):
                    events['hazard'] = {
                        'x': player.rect.centerx, 'y': player.rect.centery,
                        'radius': atk['pool_radius'] + 15,
                        'damage': int(round(atk['pool_damage'] * self.dmg_scale)),
                        'duration': atk['pool_duration'],
                    }
                elif entry == 'meteor':
                    spot = self._blink_spot(player, tilemap, above=True)
                    if spot is not None:
                        self.state = 'blink_out'
                        self.state_t = 0.35
                        self._blink_dest = spot
                        self._blink_meteor = True
            return events

        if self.shoot_cd <= 0 and self.state == 'chase':
            events['projectiles'].extend(self._shoot_at(player, t))
            self.shoot_cd = t['shoot_cd']

        if self.state == 'chase':
            self.velocity.x = self.direction * t['speed_mult'] * self.base_speed * slow_m
            if atk.get('charge') and self.phase >= 2 and self.charge_cd <= 0 and 120 < dist_x < 420:
                self.state = 'telegraph_charge'
                self.state_t = 0.7
                self.flash_t = 0.7
                self.velocity.x = 0
            elif atk.get('leap') and self.phase >= 2 and self.slam_cd <= 0 and atk.get('leap_min_dist', 100) < dist_x < atk.get('leap_max_dist', 300):
                self.state = 'telegraph_leap'
                self.state_t = 0.6
                self.flash_t = 0.6
                self.velocity.x = 0
            elif atk.get('slam') and not atk.get('leap') and self.phase >= 3 and self.slam_cd <= 0 and dist_x < 95 and abs(dy) < 80:
                # Guardián: slam cuerpo a cuerpo en P3. La Madre llega al slam vía salto.
                self.state = 'telegraph_slam'
                self.state_t = 0.5
                self.flash_t = 0.5
                self.velocity.x = 0
            if atk.get('pools') and self.phase >= 3 and self.pool_cd <= 0:
                events['hazard'] = {'x': player.rect.centerx, 'y': player.rect.centery,
                                    'radius': atk['pool_radius'], 'damage': atk['pool_damage'],
                                    'duration': atk['pool_duration']}
                self.pool_cd = atk['pool_cd']
            if atk.get('ring') and self.phase >= 2 and self.ring_cd <= 0:
                events['projectiles'].extend(self._ring_shot(t))
                self.ring_cd = atk.get('ring_cd', 5.0)
            if atk.get('meteor') and self.phase >= 3 and self.meteor_cd <= 0:
                spot = self._blink_spot(player, tilemap, above=True)
                if spot is not None:
                    self.state = 'blink_out'
                    self.state_t = 0.35
                    self.flash_t = 0.35
                    self.velocity.x = 0
                    self._blink_dest = spot
                    self._blink_meteor = True
                    self.meteor_cd = atk.get('meteor_cd', 7.0)
            elif atk.get('blink') and self.blink_cd <= 0:
                spot = self._blink_spot(player, tilemap)
                if spot is not None:
                    self.state = 'blink_out'
                    self.state_t = 0.35
                    self.flash_t = 0.35
                    self.velocity.x = 0
                    self._blink_dest = spot
                    self._blink_meteor = False
                    cds = atk.get('blink_cd', [4.5, 3.5, 2.8])
                    self.blink_cd = cds[min(self.phase - 1, len(cds) - 1)]
            if atk.get('summon_types') and self.phase >= 2 and self.summon_cd <= 0 and alive_minions < atk.get('summon_max', 2):
                need = min(atk['summon_max'] - alive_minions, 2 if alive_minions == 0 else 1)
                events['summon_requests'].extend(atk['summon_types'][:need])
                self.summon_cd = atk.get('summon_cd', 12.0)

        elif self.state == 'telegraph_charge':
            self.velocity.x = 0
            self.state_t -= dt
            events['telegraph'] = 'charge'
            if self.state_t <= 0:
                self.state = 'charging'
                self.state_t = 0.6
                px, sx = player.rect.centerx, self.rect.centerx
                self.charge_dir = pygame.math.Vector2(1 if px > sx else -1, 0)

        elif self.state == 'charging':
            self.velocity.x = self.charge_dir.x * 430.0
            self.state_t -= dt
            events['telegraph'] = 'charging'
            if self.state_t <= 0:
                self.state = 'chase'
                self.charge_cd = 7.0
                self.velocity.x = 0

        elif self.state == 'stunned':
            self.velocity.x = 0
            self.state_t -= dt
            events['telegraph'] = 'stunned'
            if self.state_t <= 0:
                self.state = 'chase'
                self.charge_cd = 5.0

        elif self.state == 'telegraph_leap':
            self.velocity.x = 0
            self.state_t -= dt
            events['telegraph'] = 'leap'
            if self.state_t <= 0:
                self.state = 'leaping'
                self.state_t = 0.7
                self.leap_from = pygame.math.Vector2(self.rect.topleft)
                self.leap_to = pygame.math.Vector2(
                    max(0, player.rect.centerx - self.rect.width // 2),
                    max(0, player.rect.top - self.rect.height - 4))

        elif self.state == 'leaping':
            self.state_t -= dt
            k = 1.0 - max(0.0, self.state_t) / 0.7  # 0 -> 1
            nx = self.leap_from.x + (self.leap_to.x - self.leap_from.x) * k
            arc = -90.0 * math.sin(math.pi * min(1.0, k))  # parábola
            ny = self.leap_from.y + (self.leap_to.y - self.leap_from.y) * k + arc
            self.rect.topleft = (int(nx), int(ny))
            self.velocity.x, self.velocity.y = 0, 0
            events['telegraph'] = 'leaping'
            if self.state_t <= 0:
                self.state = 'recover'
                self.state_t = 0.8
                # Resolver si aterrizó dentro de un muro: subir hasta quedar libre
                if tilemap is not None:
                    for _ in range(TILE_SIZE * 3):
                        if not tilemap.check_collision(self.rect):
                            break
                        self.rect.y -= 1
                    if tilemap.check_collision(self.rect):
                        # Muro demasiado grueso: volver al punto de salto
                        self.rect.topleft = (int(self.leap_from.x), int(self.leap_from.y))
                events['slam'] = {'x': self.rect.centerx, 'y': self.rect.centery,
                                  'radius': atk['slam_radius'], 'damage': atk['slam_damage']}

        elif self.state == 'telegraph_slam':
            self.velocity.x = 0
            self.state_t -= dt
            events['telegraph'] = 'slam'
            if self.state_t <= 0:
                self.state = 'recover'
                self.state_t = 0.8
                events['slam'] = {'x': self.rect.centerx, 'y': self.rect.centery,
                                  'radius': atk['slam_radius'], 'damage': atk['slam_damage']}

        elif self.state == 'recover':
            self.velocity.x = 0
            self.state_t -= dt
            if self.state_t <= 0:
                self.state = 'chase'
                self.slam_cd = 5.0

        elif self.state == 'blink_out':
            self.velocity.x, self.velocity.y = 0, 0
            self.state_t -= dt
            events['telegraph'] = 'blink'
            if self.state_t <= 0:
                old = (self.rect.centerx, self.rect.centery)
                self.rect.topleft = (int(self._blink_dest[0]), int(self._blink_dest[1]))
                events['blink'] = {'from': old, 'to': (self.rect.centerx, self.rect.centery),
                                   'meteor': self._blink_meteor}
                if self._blink_meteor:
                    self.state = 'meteor_fall'
                    self.velocity.x, self.velocity.y = 0, 500.0
                else:
                    self.state = 'chase'
                    self.shoot_cd = min(self.shoot_cd, 0.4)

        elif self.state == 'meteor_fall':
            # Caída libre hasta tocar suelo -> AoE
            self.velocity.x = 0
            self.velocity.y = min(MAX_FALL_SPEED, self.velocity.y + GRAVITY * 1.5 * dt)
            events['telegraph'] = 'falling'
            old_bottom = self.rect.bottom
            self.rect.y += int(round(self.velocity.y * dt))
            if tilemap is not None and tilemap.check_collision(self.rect):
                self.rect.bottom = (self.rect.bottom // TILE_SIZE) * TILE_SIZE
                self.velocity.y = 0
                self.state = 'recover'
                self.state_t = 0.9
                events['slam'] = {'x': self.rect.centerx, 'y': self.rect.centery,
                                  'radius': atk['slam_radius'], 'damage': atk['slam_damage']}

        # Gravedad + movimiento (salto y meteoro usan trayectoria directa)
        if self.state not in ('leaping', 'blink_out', 'meteor_fall'):
            self.velocity.y += GRAVITY * dt
            if self.velocity.y > MAX_FALL_SPEED:
                self.velocity.y = MAX_FALL_SPEED
            hit_wall = self._move_with_collision(tilemap, dt)
            if hit_wall and self.state == 'charging':
                self.state = 'stunned'
                self.state_t = 0.8
                self.velocity.x = 0

        # Escala NG+: daño de slam y charcos
        if events['slam'] is not None:
            events['slam']['damage'] = int(round(events['slam']['damage'] * self.dmg_scale))
        if events['hazard'] is not None:
            events['hazard']['damage'] = int(round(events['hazard']['damage'] * self.dmg_scale))

        return events
