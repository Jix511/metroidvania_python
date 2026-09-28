"""Player-save validation and version migrations."""

from copy import deepcopy

from constants import CHARACTER_CLASSES, TILE_SIZE
from world.world_data import ROOM_DEFS, ZONE_DEFS
from systems.encounter_data import ENCOUNTERS
from systems.route_data import ROUTES


CURRENT_SAVE_VERSION = 20

_OLD_ZONE_RANGES = ((0, 25), (26, 45), (46, 62), (63, 80), (81, 100))


def _migrate_world_x(x):
    tx = float(x) / TILE_SIZE
    for index, (old_x0, old_x1) in enumerate(_OLD_ZONE_RANGES):
        if old_x0 <= tx <= old_x1 and index < len(ZONE_DEFS):
            zone = ZONE_DEFS[index]
            ratio = (tx - old_x0) / max(1, old_x1 - old_x0)
            new_tx = zone['x0'] + ratio * (zone['x1'] - zone['x0'])
            return new_tx * TILE_SIZE
    return x


def is_player_save_candidate(data):
    if not isinstance(data, dict):
        return False
    if data.get('character_class') not in CHARACTER_CLASSES:
        return False
    position = data.get('position')
    if (not isinstance(position, (list, tuple)) or len(position) != 2
            or not all(isinstance(value, (int, float)) for value in position)):
        return False
    if not isinstance(data.get('level'), int) or data['level'] < 1:
        return False
    expected_containers = {
        'skill_ranks': dict,
        'equipment': dict,
        'inventory': list,
        'opened_gates': list,
        'unlocked_checkpoints': list,
        'explored_zones': list,
        'explored_rooms': list,
        'completed_encounters': list,
        'completed_routes': list,
        'miniboss_defeated_ids': list,
        'bestiary': dict,
        'quest_states': dict,
        'collected_items': list,
        'discovered_secrets': list,
        'opened_secret_chests': list,
        'statistics': dict,
        'unlocked_achievements': list,
        'souls': int,
    }
    return all(key not in data or isinstance(data[key], kind)
               for key, kind in expected_containers.items())


def migrate_player_save(data):
    if not is_player_save_candidate(data):
        raise ValueError('Invalid player save schema')

    migrated = deepcopy(data)

    source_version = int(migrated.get('save_version', 0) or 0)
    if source_version < 13:
        migrated['position'] = list(migrated['position'])
        migrated['position'][0] = _migrate_world_x(migrated['position'][0])
        respawn = migrated.get('respawn_point')
        if isinstance(respawn, (list, tuple)) and len(respawn) == 2:
            migrated['respawn_point'] = [_migrate_world_x(respawn[0]), respawn[1]]

    boss_ids = migrated.get('boss_defeated_ids', migrated.get('boss_defeated', []))
    if isinstance(boss_ids, bool):
        boss_ids = ['sanctum_guardian'] if boss_ids else []
    migrated['boss_defeated_ids'] = list(boss_ids or [])
    migrated.pop('boss_defeated', None)

    for key in ('base_speed', 'speed'):
        value = migrated.get(key)
        if isinstance(value, (int, float)) and value < 20:
            migrated[key] = value * 60.0

    migrated.setdefault('skill_ranks', {})
    migrated.setdefault('equipment', {})
    migrated.setdefault('inventory', [])
    migrated.setdefault('opened_gates', [])
    migrated.setdefault('unlocked_checkpoints', [])
    known_zones = {zone['id'] for zone in ZONE_DEFS}
    explored = {zone_id for zone_id in migrated.get('explored_zones', [])
                if isinstance(zone_id, str) and zone_id in known_zones}
    tx = migrated['position'][0] // TILE_SIZE
    current_zone = next((zone['id'] for zone in ZONE_DEFS
                         if zone['x0'] <= tx <= zone['x1']), 'meadow')
    explored.update(('meadow', current_zone))
    migrated['explored_zones'] = sorted(explored)
    known_rooms = {room['id'] for room in ROOM_DEFS}
    explored_rooms = {room_id for room_id in migrated.get('explored_rooms', [])
                      if isinstance(room_id, str) and room_id in known_rooms}
    current_room = next((room['id'] for room in ROOM_DEFS
                         if room['x0'] <= tx <= room['x1']), ROOM_DEFS[0]['id'])
    explored_rooms.add(current_room)
    migrated['explored_rooms'] = sorted(explored_rooms)
    migrated['completed_encounters'] = sorted(
        encounter_id for encounter_id in migrated.get('completed_encounters', [])
        if isinstance(encounter_id, str) and encounter_id in ENCOUNTERS)
    migrated['completed_routes'] = sorted(
        route_id for route_id in migrated.get('completed_routes', [])
        if isinstance(route_id, str) and route_id in ROUTES)
    migrated.setdefault('miniboss_defeated_ids', [])
    migrated.setdefault('bestiary', {})
    migrated.setdefault('quest_states', {})
    migrated.setdefault('collected_items', [])
    migrated.setdefault('discovered_secrets', [])
    migrated.setdefault('opened_secret_chests', [])
    from systems.run_stats import normalize_stats
    migrated['statistics'] = normalize_stats(migrated.get('statistics'))
    migrated.setdefault('unlocked_achievements', [])
    migrated['souls'] = max(0, int(migrated.get('souls', 0) or 0))
    migrated['save_version'] = CURRENT_SAVE_VERSION
    return migrated
