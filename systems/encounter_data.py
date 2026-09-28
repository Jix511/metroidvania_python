"""Validated room-encounter definitions."""

import json

from core.paths import DATA_DIR
from systems.balance_data import ENEMY_STATS
from systems.rewards import validate_reward
from world.world_data import ROOM_DEFS


class EncounterDataError(ValueError):
    pass


def _load_encounters():
    path = DATA_DIR / 'encounters.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EncounterDataError(f'Could not load {path.name}: {exc}') from exc
    rooms = {room['id']: room for room in ROOM_DEFS}
    if not isinstance(document, dict) or not document:
        raise EncounterDataError('encounters.json requires encounter definitions')
    result = {}
    for room_id, definition in document.items():
        if room_id not in rooms or not isinstance(definition, dict):
            raise EncounterDataError(f'unknown encounter room {room_id}')
        waves = definition.get('waves')
        if (not isinstance(definition.get('name'), str) or not definition['name']
                or not isinstance(waves, list) or not waves):
            raise EncounterDataError(f'encounter {room_id} is incomplete')
        if any(not isinstance(wave, list) or not wave
               or any(enemy not in ENEMY_STATS for enemy in wave) for wave in waves):
            raise EncounterDataError(f'encounter {room_id} has invalid waves')
        result[room_id] = {
            'name': definition['name'],
            'waves': tuple(tuple(wave) for wave in waves),
            'reward': validate_reward(f'encounter {room_id}', definition.get('reward', {})),
            'room': rooms[room_id],
        }
    return result


ENCOUNTERS = _load_encounters()
