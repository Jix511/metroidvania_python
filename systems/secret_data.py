"""Validated hidden-room, chest and challenge definitions."""

import json

from core.paths import DATA_DIR
from systems.balance_data import ENEMY_STATS
from systems.rewards import validate_reward
from world.world_data import MAP_HEIGHT, ZONE_DEFS


class SecretDataError(ValueError):
    pass


def _load_secrets():
    path = DATA_DIR / 'secrets.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SecretDataError(f'Could not load {path.name}: {exc}') from exc
    zones = {zone['id']: zone for zone in ZONE_DEFS}
    if not isinstance(document, dict) or not document:
        raise SecretDataError('secrets.json must contain secret definitions')
    result = {}
    for secret_id, secret in document.items():
        required = {'name', 'zone_id', 'kind', 'wall', 'chest', 'reward'}
        if not isinstance(secret, dict) or not required.issubset(secret):
            raise SecretDataError(f'secret {secret_id} is incomplete')
        zone = zones.get(secret['zone_id'])
        wall, chest = secret['wall'], secret['chest']
        if secret['kind'] not in ('chest', 'combat') or zone is None:
            raise SecretDataError(f'secret {secret_id} has invalid type or zone')
        if (not {'tx', 'y0', 'y1'}.issubset(wall)
                or not zone['x0'] <= wall['tx'] <= zone['x1']
                or not 0 <= wall['y0'] <= wall['y1'] < MAP_HEIGHT):
            raise SecretDataError(f'secret {secret_id} has an invalid wall')
        if (not {'tx', 'ty'}.issubset(chest)
                or not zone['x0'] <= chest['tx'] <= zone['x1']
                or not 0 <= chest['ty'] < MAP_HEIGHT):
            raise SecretDataError(f'secret {secret_id} has an invalid chest')
        if secret['kind'] == 'combat':
            if (not isinstance(secret.get('enemies'), list) or not secret['enemies']
                    or any(enemy not in ENEMY_STATS for enemy in secret['enemies'])
                    or not isinstance(secret.get('time_limit'), (int, float))
                    or secret['time_limit'] <= 0):
                raise SecretDataError(f'secret {secret_id} has an invalid challenge')
        result[secret_id] = {
            **secret,
            'reward': validate_reward(f'secret {secret_id}.reward', secret['reward']),
        }
    return result


SECRETS = _load_secrets()
