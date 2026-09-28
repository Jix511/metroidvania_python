# tilemap.py - Mapa con zonas, puertas por habilidad (gating) y colisiones.

import math

import pygame
from constants import TILE_SIZE, COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from world.world_data import (ABILITY_NAMES, BOUNDARIES, CHECKPOINT_DEFS,
    ABILITY_ROUTES, DIVIDERS, GATE_DEFS, MAP_HEIGHT, MAP_WIDTH, PLATFORMS,
    ROOM_DEFS, TUTORIAL_SIGN_DEFS, ZONE_DEFS)
from presentation.art_loader import load_biome_tiles
from systems.secret_data import SECRETS


ZONE_SKIES = {
    'meadow': (22, 34, 38), 'caves': (12, 22, 34),
    'ruins': (16, 32, 35), 'sanctum': (29, 22, 43),
    'peak': (25, 35, 49),
}


def tutorial_signs():
    from systems import controls

    labels = {
        action: "+".join(controls.key_label(code) for code in controls.codes(action))
        for action in ('jump', 'travel', 'attack', 'skills', 'potion', 'inventory')
    }
    return [
        {**definition, 'text': definition['text'].format_map(labels)}
        for definition in TUTORIAL_SIGN_DEFS
    ]

class TileMap:
    def __init__(self, width=None, height=None):
        self.width = MAP_WIDTH if width is None else width
        self.height = MAP_HEIGHT if height is None else height
        self.tiles = {}
        self.tile_colors = {}
        self.gates = {}  # (tx,ty) -> {'id','required','name','open'}
        self.route_barriers = {}
        self.zones = []  # [{'id','name','x0','x1'}] en tiles X
        self.checkpoints = []  # [{'id','zone_id','name','rect'}] rect en px
        self.biome_tiles = load_biome_tiles()
        self.generate_gated_map()

    # --- Generación ---
    def generate_gated_map(self):
        W, H = self.width, self.height
        self.tiles = {}
        self.tile_colors = {}
        self.gates = {}
        self.route_barriers = {}
        floor_depth = BOUNDARIES['floor_depth']
        side_wall_width = BOUNDARIES['side_wall_width']
        for y in range(H):
            for x in range(W):
                if y >= H - floor_depth:
                    self.tiles[(x, y)] = 'floor'
                elif x < side_wall_width or x >= W - side_wall_width:
                    self.tiles[(x, y)] = 'wall'
                else:
                    self.tiles[(x, y)] = 'empty'

        for platform in PLATFORMS:
            for x in range(platform['x0'], platform['x1'] + 1):
                position = (x, platform['y'])
                self.tiles[position] = 'floor'
                if 'color' in platform:
                    self.tile_colors[position] = platform['color']

        for divider in DIVIDERS:
            gx = divider['tx']
            gid = divider['gate_id']
            for y in range(divider['wall_y0'], divider['wall_y1'] + 1):
                if divider['gate_y0'] <= y <= divider['gate_y1']:
                    self.gates[(gx, y)] = {
                        'id': gid,
                        'required': GATE_DEFS[gid]['required'],
                        'name': GATE_DEFS[gid]['name'],
                        'open': False,
                    }
                else:
                    self.tiles[(gx, y)] = 'wall'

        for route in ABILITY_ROUTES:
            obstacle = route.get('obstacle') or {}
            if obstacle.get('type') == 'dash_barrier':
                for y in range(obstacle['y0'], obstacle['y1'] + 1):
                    self.route_barriers[(obstacle['tx'], y)] = route['id']

        for secret_id, secret in SECRETS.items():
            wall = secret['wall']
            for y in range(wall['y0'], wall['y1'] + 1):
                self.tiles[(wall['tx'], y)] = 'secret_wall'

        self.zones = [dict(zone) for zone in ZONE_DEFS]
        self.checkpoints = []
        for cp in CHECKPOINT_DEFS:
            self.checkpoints.append({
                'id': cp['id'], 'zone_id': cp['zone_id'], 'name': cp['name'],
                'rect': pygame.Rect(cp['tx'] * TILE_SIZE,
                                    (H - floor_depth) * TILE_SIZE - 32, 16, 32),
            })

    # --- Colisiones con puertas ---
    def is_solid_tile(self, tx, ty, abilities=None):
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return True
        g = self.gates.get((tx, ty))
        if g is not None:
            if g['open']:
                return False
            if abilities is not None and g['required'] in abilities:
                return False  # se abrirá al tocarla; no bloquea el paso final
            return True
        if (tx, ty) in self.route_barriers:
            return not abilities or 'dash_active' not in abilities
        return self.tiles.get((tx, ty), 'empty') in ('wall', 'floor', 'secret_wall')

    def reveal_secret(self, secret_id):
        secret = SECRETS.get(secret_id)
        if secret is None:
            return False
        wall = secret['wall']
        for y in range(wall['y0'], wall['y1'] + 1):
            self.tiles[(wall['tx'], y)] = 'empty'
        return True

    def apply_discovered_secrets(self, discovered_ids):
        for secret_id in discovered_ids or ():
            self.reveal_secret(secret_id)

    def reset_secrets(self):
        for secret in SECRETS.values():
            wall = secret['wall']
            for y in range(wall['y0'], wall['y1'] + 1):
                self.tiles[(wall['tx'], y)] = 'secret_wall'

    def is_solid(self, x, y, abilities=None):
        return self.is_solid_tile(x // TILE_SIZE, y // TILE_SIZE, abilities)

    def check_collision(self, rect, abilities=None):
        x0 = rect.left // TILE_SIZE
        x1 = (rect.right - 1) // TILE_SIZE
        y0 = rect.top // TILE_SIZE
        y1 = (rect.bottom - 1) // TILE_SIZE
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                if self.is_solid_tile(tx, ty, abilities):
                    return True
        return False

    # --- Puertas ---
    def nearby_gate(self, rect, radius_px=56):
        """Puerta cerrada más cercana al rect dentro del radio. Retorna ((tx,ty), gate) o (None,None)."""
        cx, cy = rect.centerx, rect.centery
        best, best_d2 = None, radius_px * radius_px
        for (tx, ty), g in self.gates.items():
            if g['open']:
                continue
            gx, gy = tx * TILE_SIZE + TILE_SIZE // 2, ty * TILE_SIZE + TILE_SIZE // 2
            d2 = (gx - cx) ** 2 + (gy - cy) ** 2
            if d2 <= best_d2:
                best, best_d2 = (tx, ty), d2
        if best is None:
            return None, None
        return best, self.gates[best]

    def open_gate_id(self, gid):
        n = 0
        for g in self.gates.values():
            if g['id'] == gid and not g['open']:
                g['open'] = True
                n += 1
        return n

    def reset_gates(self):
        """Cierra todas las puertas (NG+ / nueva partida)."""
        for g in self.gates.values():
            g['open'] = False

    def try_open_nearby(self, player):
        """Si el jugador toca una puerta y tiene la habilidad, la abre. Retorna (gate|None, opened:bool)."""
        pos, g = self.nearby_gate(player.rect, 52)
        if g is None:
            return None, False
        if g['required'] in player.unlocked_abilities:
            self.open_gate_id(g['id'])
            if hasattr(player, 'opened_gates'):
                player.opened_gates.add(g['id'])
            return g, True
        return g, False

    def try_route_teleport(self, player):
        """Teleport between paired rune anchors when standing near either end."""
        if 'teleport' not in player.unlocked_abilities or player.teleport_cooldown > 0:
            return None
        for route in ABILITY_ROUTES:
            if (route.get('obstacle') or {}).get('type') != 'teleport_anchors':
                continue
            points = (route['start'], route['goal'])
            for index, (tx, ty) in enumerate(points):
                x, y = tx * TILE_SIZE + TILE_SIZE // 2, (ty + 1) * TILE_SIZE
                if ((player.rect.centerx - x) ** 2 + (player.rect.bottom - y) ** 2
                        <= 52 * 52):
                    target = points[1 - index]
                    player.rect.midbottom = (target[0] * TILE_SIZE + TILE_SIZE // 2,
                                             (target[1] + 1) * TILE_SIZE)
                    player.velocity.update(0, 0)
                    player.teleport_cooldown = 0.8
                    return route['id']
        return None

    def apply_opened(self, opened_ids):
        for gid in (opened_ids or []):
            self.open_gate_id(gid)

    # --- Zonas ---
    def get_zone_at(self, x_px):
        tx = int(x_px // TILE_SIZE)
        for z in self.zones:
            if z['x0'] <= tx <= z['x1']:
                return z
        return self.zones[0] if self.zones else {'id': 'wild', 'name': '???'}

    def get_room_at(self, x_px):
        tx = int(x_px // TILE_SIZE)
        return next((room for room in ROOM_DEFS
                     if room['x0'] <= tx <= room['x1']), ROOM_DEFS[0])

    # --- Checkpoints ---
    def checkpoint_near(self, rect, radius_px=40):
        """Checkpoint cuyo rect está dentro del radio del jugador. Retorna cp o None."""
        cx, cy = rect.centerx, rect.centery
        for cp in self.checkpoints:
            gx, gy = cp['rect'].centerx, cp['rect'].centery
            if (gx - cx) ** 2 + (gy - cy) ** 2 <= radius_px * radius_px:
                return cp
        return None

    def spawn_pos_for(self, cp_id):
        """Posición segura (topleft px) junto al checkpoint para respawn/viaje."""
        for cp in self.checkpoints:
            if cp['id'] == cp_id:
                return (cp['rect'].x - 24, cp['rect'].bottom - 16)
        return None

    # --- Dibujo ---
    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = int(camera_offset[0]), int(camera_offset[1])
        start_tx = max(0, (-ox) // TILE_SIZE - 1)
        start_ty = max(0, (-oy) // TILE_SIZE - 1)
        end_tx = min(self.width, (-ox + surface.get_width()) // TILE_SIZE + 2)
        end_ty = min(self.height, (-oy + surface.get_height()) // TILE_SIZE + 2)
        for ty in range(start_ty, end_ty):
            for tx in range(start_tx, end_tx):
                rx = tx * TILE_SIZE + ox
                ry = ty * TILE_SIZE + oy
                rect = pygame.Rect(rx, ry, TILE_SIZE, TILE_SIZE)
                g = self.gates.get((tx, ty))
                if g is not None and not g['open']:
                    col = GATE_DEFS[g['id']]['color']
                    pulse = 0.72 + 0.28 * math.sin(pygame.time.get_ticks() * 0.006 + ty)
                    glow = tuple(min(255, int(channel * pulse)) for channel in col)
                    pygame.draw.rect(surface, glow, rect)
                    pygame.draw.rect(surface, COLORS['BLACK'], rect, 1)
                    pygame.draw.circle(surface, COLORS['WHITE'], rect.center,
                                       2 + int(pulse > 0.9), 1)
                    continue
                route_id = self.route_barriers.get((tx, ty))
                if route_id is not None:
                    pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() * 0.01 + ty)
                    pygame.draw.rect(surface, (int(170 * pulse), 70, 220), rect)
                    pygame.draw.line(surface, (245, 190, 255), rect.topleft,
                                     rect.bottomright, 2)
                    continue
                tile_type = self.tiles.get((tx, ty), 'empty')
                if tile_type == 'empty':
                    continue
                if tile_type in ('wall', 'secret_wall'):
                    zone = self.get_zone_at(tx * TILE_SIZE)
                    tiles = self.biome_tiles.get(zone['id'])
                    if tiles:
                        surface.blit(tiles[1], rect)
                    else:
                        pygame.draw.rect(surface, COLORS['GRAY'], rect)
                elif tile_type == 'floor':
                    zone = self.get_zone_at(tx * TILE_SIZE)
                    tiles = self.biome_tiles.get(zone['id'])
                    if tiles:
                        top_exposed = self.tiles.get((tx, ty - 1), 'empty') == 'empty'
                        surface.blit(tiles[0 if top_exposed else 1], rect)
                        if top_exposed and (tx * 7 + ty * 3) % 17 == 0:
                            accent = pygame.transform.scale(tiles[3], (32, 32))
                            surface.blit(accent, accent.get_rect(midbottom=rect.midtop))
                    else:
                        c = self.tile_colors.get((tx, ty), COLORS['GREEN'])
                        pygame.draw.rect(surface, c, rect)

        for route in ABILITY_ROUTES:
            if (route.get('obstacle') or {}).get('type') != 'teleport_anchors':
                continue
            for tx, ty in (route['start'], route['goal']):
                center = (tx * TILE_SIZE + TILE_SIZE // 2 + ox,
                          (ty + 1) * TILE_SIZE + oy - 5)
                pygame.draw.circle(surface, (185, 95, 240), center, 11, 2)
                pygame.draw.circle(surface, (235, 190, 255), center, 4)

    def get_tile_position(self, world_x, world_y):
        return (int(world_x // TILE_SIZE), int(world_y // TILE_SIZE))


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.trauma = 0.0  # 0..1, decae en Game.update_camera
        self.trauma_scale = 1.0

    def add_trauma(self, amount):
        self.trauma = max(0.0, min(1.0, self.trauma + amount * self.trauma_scale))

    def get_render_offset(self):
        """topleft + desplazamiento aleatorio por trauma (screenshake)."""
        import random as _r
        mag = self.trauma * self.trauma * 14.0
        return (self.camera.x + _r.uniform(-mag, mag),
                self.camera.y + _r.uniform(-mag, mag))

    def apply(self, target):
        return target.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - SCREEN_WIDTH), x)
        y = max(-(self.height - SCREEN_HEIGHT), y)
        self.camera = pygame.Rect(x, y, self.width, self.height)
