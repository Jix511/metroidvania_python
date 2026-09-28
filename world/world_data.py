"""Validated world geometry, progression gates, and encounter placement."""

import json
import string

from core.paths import DATA_DIR
from systems.balance_data import BOSS_DEFS, ENEMY_STATS, MINIBOSS_DEFS
from systems.item_data import RARITIES, SLOTS


class WorldDataError(ValueError):
    pass


def _load_document():
    path = DATA_DIR / 'world.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorldDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict):
        raise WorldDataError('world.json must contain an object')
    return document


def _require(document, key, expected_type):
    value = document.get(key)
    if not isinstance(value, expected_type):
        raise WorldDataError(f'world.json.{key} has an invalid type')
    return value


def _rgb(label, value):
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(channel, int) and 0 <= channel <= 255
                       for channel in value)):
        raise WorldDataError(f'{label} must be an RGB color')
    return tuple(value)


WORLD_CONFIG = _load_document()
DIMENSIONS = _require(WORLD_CONFIG, 'dimensions', dict)
BOUNDARIES = _require(WORLD_CONFIG, 'boundaries', dict)
PLATFORMS = _require(WORLD_CONFIG, 'platforms', list)
MOVING_PLATFORMS = _require(WORLD_CONFIG, 'moving_platforms', list)
ABILITY_NAMES = _require(WORLD_CONFIG, 'abilities', dict)
GATE_DEFS = _require(WORLD_CONFIG, 'gates', dict)
DIVIDERS = _require(WORLD_CONFIG, 'dividers', list)
ZONE_DEFS = _require(WORLD_CONFIG, 'zones', list)
ROOM_DEFS = _require(WORLD_CONFIG, 'rooms', list)
ABILITY_ROUTES = _require(WORLD_CONFIG, 'ability_routes', list)
CHECKPOINT_DEFS = _require(WORLD_CONFIG, 'checkpoints', list)
TUTORIAL_SIGN_DEFS = _require(WORLD_CONFIG, 'tutorial_signs', list)
BOSS_ARENAS = _require(WORLD_CONFIG, 'boss_arenas', list)
SHOPKEEPER = _require(WORLD_CONFIG, 'shopkeeper', dict)
LOOT_SPAWNS = _require(WORLD_CONFIG, 'loot_spawns', list)
VICTORY_TEXT = _require(WORLD_CONFIG, 'victory_text', dict)

MAP_WIDTH = DIMENSIONS.get('width')
MAP_HEIGHT = DIMENSIONS.get('height')
if (not isinstance(MAP_WIDTH, int) or MAP_WIDTH <= 4
        or not isinstance(MAP_HEIGHT, int) or MAP_HEIGHT <= 4):
    raise WorldDataError('world dimensions must be positive integers greater than 4')
if (not isinstance(BOUNDARIES.get('floor_depth'), int)
        or not isinstance(BOUNDARIES.get('side_wall_width'), int)):
    raise WorldDataError('world boundaries require integer depths')

for index, platform in enumerate(PLATFORMS):
    if not isinstance(platform, dict) or not {'x0', 'x1', 'y'}.issubset(platform):
        raise WorldDataError(f'platform {index} is incomplete')
    if not (0 <= platform['x0'] <= platform['x1'] < MAP_WIDTH
            and 0 <= platform['y'] < MAP_HEIGHT):
        raise WorldDataError(f'platform {index} is outside the map')
    if 'color' in platform:
        platform['color'] = _rgb(f'platform {index}.color', platform['color'])

for index, platform in enumerate(MOVING_PLATFORMS):
    required = {'id', 'zone_id', 'axis', 'start', 'end', 'width', 'speed'}
    if not isinstance(platform, dict) or not required.issubset(platform):
        raise WorldDataError(f'moving platform {index} is incomplete')
    if (platform['axis'] not in ('x', 'y') or platform['width'] < 1
            or platform['speed'] <= 0
            or len(platform['start']) != 2 or len(platform['end']) != 2):
        raise WorldDataError(f'moving platform {platform["id"]} is invalid')
    for tx, ty in (platform['start'], platform['end']):
        if not (0 <= tx < MAP_WIDTH and 0 <= ty < MAP_HEIGHT):
            raise WorldDataError(f'moving platform {platform["id"]} is outside the map')

for gate_id, gate in GATE_DEFS.items():
    if not isinstance(gate, dict) or not {'required', 'name', 'color'}.issubset(gate):
        raise WorldDataError(f'gate {gate_id} is incomplete')
    if gate['required'] not in ABILITY_NAMES:
        raise WorldDataError(f'gate {gate_id} requires an unknown ability')
    gate['color'] = _rgb(f'gate {gate_id}.color', gate['color'])

for divider in DIVIDERS:
    required = {'tx', 'gate_id', 'wall_y0', 'wall_y1', 'gate_y0', 'gate_y1'}
    if not isinstance(divider, dict) or not required.issubset(divider):
        raise WorldDataError('a divider is incomplete')
    if divider['gate_id'] not in GATE_DEFS:
        raise WorldDataError(f'divider references unknown gate {divider["gate_id"]}')
    if not (0 <= divider['tx'] < MAP_WIDTH
            and 0 <= divider['wall_y0'] <= divider['gate_y0']
            <= divider['gate_y1'] <= divider['wall_y1'] < MAP_HEIGHT):
        raise WorldDataError(f'divider {divider["gate_id"]} is outside the map')

zone_ids = set()
previous_x1 = -1
for zone in ZONE_DEFS:
    if not isinstance(zone, dict) or not {'id', 'name', 'x0', 'x1'}.issubset(zone):
        raise WorldDataError('a zone is incomplete')
    if zone['id'] in zone_ids or zone['x0'] != previous_x1 + 1 or zone['x1'] < zone['x0']:
        raise WorldDataError('zones must be unique, ordered, and contiguous')
    zone_ids.add(zone['id'])
    previous_x1 = zone['x1']
if not ZONE_DEFS or ZONE_DEFS[0]['x0'] != 0 or previous_x1 < MAP_WIDTH - 1:
    raise WorldDataError('zones must cover the complete map width')

room_ids = set()
room_cursor = 0
for room in ROOM_DEFS:
    required = {'id', 'zone_id', 'name', 'kind', 'x0', 'x1'}
    if not isinstance(room, dict) or not required.issubset(room):
        raise WorldDataError('a room is incomplete')
    if (room['id'] in room_ids or room['zone_id'] not in zone_ids
            or room['x0'] != room_cursor or room['x1'] < room['x0']):
        raise WorldDataError(f'invalid or non-contiguous room {room.get("id")}')
    zone = next(zone for zone in ZONE_DEFS if zone['id'] == room['zone_id'])
    if not (zone['x0'] <= room['x0'] <= room['x1'] <= zone['x1']):
        raise WorldDataError(f'room {room["id"]} escapes its zone')
    room_ids.add(room['id'])
    room_cursor = room['x1'] + 1
if room_cursor < MAP_WIDTH:
    raise WorldDataError('rooms must cover the complete map width')

route_ids = set()
for route in ABILITY_ROUTES:
    required = {'id', 'zone_id', 'name', 'required', 'start', 'goal', 'reward'}
    if not isinstance(route, dict) or not required.issubset(route):
        raise WorldDataError('an ability route is incomplete')
    if (route['id'] in route_ids or route['zone_id'] not in zone_ids
            or route['required'] not in ABILITY_NAMES):
        raise WorldDataError(f'invalid ability route {route.get("id")}')
    zone = next(zone for zone in ZONE_DEFS if zone['id'] == route['zone_id'])
    for point in ('start', 'goal'):
        value = route[point]
        if (not isinstance(value, list) or len(value) != 2
                or not all(isinstance(number, int) for number in value)
                or not zone['x0'] <= value[0] <= zone['x1']
                or not 0 <= value[1] < MAP_HEIGHT):
            raise WorldDataError(f'ability route {route["id"]}.{point} is invalid')
    obstacle = route.get('obstacle')
    if obstacle is not None and obstacle.get('type') not in ('dash_barrier', 'teleport_anchors'):
        raise WorldDataError(f'ability route {route["id"]} has an invalid obstacle')
    route_ids.add(route['id'])

checkpoint_ids = set()
for checkpoint in CHECKPOINT_DEFS:
    required = {'id', 'zone_id', 'name', 'tx'}
    if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
        raise WorldDataError('a checkpoint is incomplete')
    if checkpoint['id'] in checkpoint_ids or checkpoint['zone_id'] not in zone_ids:
        raise WorldDataError(f'invalid checkpoint {checkpoint.get("id")}')
    if not isinstance(checkpoint['tx'], int) or not 0 <= checkpoint['tx'] < MAP_WIDTH:
        raise WorldDataError(f'checkpoint {checkpoint["id"]} is outside the map')
    checkpoint_ids.add(checkpoint['id'])

allowed_actions = {'jump', 'travel', 'attack', 'skills', 'potion', 'inventory'}
for sign in TUTORIAL_SIGN_DEFS:
    if not isinstance(sign, dict) or not {'tx', 'title', 'text'}.issubset(sign):
        raise WorldDataError('a tutorial sign is incomplete')
    fields = {field for _literal, field, _spec, _conversion
              in string.Formatter().parse(sign['text']) if field}
    if not fields.issubset(allowed_actions):
        raise WorldDataError(f'tutorial sign uses unknown actions: {sorted(fields)}')
    if not isinstance(sign['tx'], int) or not 0 <= sign['tx'] < MAP_WIDTH:
        raise WorldDataError(f'tutorial sign {sign["title"]} is outside the map')


def _spawn_pairs(key, id_key, definitions):
    entries = _require(WORLD_CONFIG, key, list)
    result = []
    for entry in entries:
        if (not isinstance(entry, dict) or entry.get(id_key) not in definitions
                or not isinstance(entry.get('tx'), int)
                or not 0 <= entry['tx'] < MAP_WIDTH):
            raise WorldDataError(f'{key} contains an invalid spawn')
        result.append((entry[id_key], entry['tx']))
    return result


ENEMY_SPAWNS = _spawn_pairs('enemy_spawns', 'enemy', ENEMY_STATS)
LOAD_SPAWNS = _spawn_pairs('load_enemy_spawns', 'enemy', ENEMY_STATS)
MINIBOSS_SPAWNS = _spawn_pairs('miniboss_spawns', 'miniboss', MINIBOSS_DEFS)

arena_ids = set()
for arena in BOSS_ARENAS:
    required = {'id', 'trigger_tx', 'spawn_tx', 'x0', 'x1'}
    if not isinstance(arena, dict) or not required.issubset(arena):
        raise WorldDataError('a boss arena is incomplete')
    if arena['id'] not in BOSS_DEFS or arena['id'] in arena_ids:
        raise WorldDataError(f'invalid boss arena {arena.get("id")}')
    if not (0 <= arena['x0'] <= arena['trigger_tx'] <= arena['x1'] < MAP_WIDTH
            and 0 <= arena['spawn_tx'] < MAP_WIDTH):
        raise WorldDataError(f'boss arena {arena["id"]} is outside the map')
    arena_ids.add(arena['id'])

if set(VICTORY_TEXT) != set(BOSS_DEFS):
    raise WorldDataError('victory_text must contain every boss')
if not {'tx', 'ty', 'x_offset', 'y_offset'}.issubset(SHOPKEEPER):
    raise WorldDataError('shopkeeper position is incomplete')
if not (0 <= SHOPKEEPER['tx'] < MAP_WIDTH and 0 <= SHOPKEEPER['ty'] < MAP_HEIGHT):
    raise WorldDataError('shopkeeper position is outside the map')
for loot in LOOT_SPAWNS:
    required = {'tx', 'ty', 'slot', 'rarity', 'level', 'name'}
    if not isinstance(loot, dict) or not required.issubset(loot):
        raise WorldDataError('a loot spawn is incomplete')
    if loot['slot'] not in SLOTS or loot['rarity'] not in RARITIES:
        raise WorldDataError(f'loot spawn {loot.get("name")} has invalid item data')
    if not (isinstance(loot['level'], int) and loot['level'] > 0
            and 0 <= loot['tx'] < MAP_WIDTH and 0 <= loot['ty'] < MAP_HEIGHT):
        raise WorldDataError(f'loot spawn {loot["name"]} is outside the map')
