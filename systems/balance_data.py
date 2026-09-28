"""Validated loader for enemy, elite, miniboss, and boss balance data."""

import json

from core.paths import DATA_DIR


class BalanceDataError(ValueError):
    pass


def _read_json(filename):
    path = DATA_DIR / filename
    try:
        with path.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BalanceDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(data, dict):
        raise BalanceDataError(f'{path.name} must contain a JSON object')
    return data


def _require_fields(label, data, fields):
    if not isinstance(data, dict):
        raise BalanceDataError(f'{label} must be an object')
    missing = [field for field in fields if field not in data]
    if missing:
        raise BalanceDataError(f'{label} is missing: {", ".join(missing)}')


def _color(label, value):
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(channel, int) and 0 <= channel <= 255
                       for channel in value)):
        raise BalanceDataError(f'{label} must be an RGB color')
    return tuple(value)


def _load_enemies():
    document = _read_json('enemies.json')
    enemies = document.get('enemies')
    affixes = document.get('elite_affixes')
    if not isinstance(enemies, dict) or not enemies:
        raise BalanceDataError('enemies.json requires a non-empty enemies object')
    if not isinstance(affixes, list):
        raise BalanceDataError('enemies.json requires an elite_affixes list')

    required = ('health', 'damage', 'speed', 'xp', 'color', 'name', 'zones', 'tip', 'ai')
    normalized_enemies = {}
    for enemy_id, stats in enemies.items():
        _require_fields(f'enemy {enemy_id}', stats, required)
        stats = dict(stats)
        stats['color'] = _color(f'enemy {enemy_id}.color', stats['color'])
        stats.setdefault('behavior', enemy_id)
        stats.setdefault('flying', enemy_id == 'bat')
        stats.setdefault('trait', 'Vuela' if stats['flying'] else '—')
        stats.setdefault('weight', 1.0)
        if not isinstance(stats['behavior'], str) or not isinstance(stats['flying'], bool):
            raise BalanceDataError(f'enemy {enemy_id} has invalid behavior metadata')
        if (not isinstance(stats['weight'], (int, float))
                or stats['weight'] <= 0):
            raise BalanceDataError(f'enemy {enemy_id}.weight must be a positive number')
        ai = stats['ai']
        _require_fields(f'enemy {enemy_id}.ai', ai,
                        ('detection', 'leash', 'memory', 'attack_cooldown'))
        if any(not isinstance(ai[key], (int, float)) or ai[key] <= 0
               for key in ('detection', 'leash', 'memory', 'attack_cooldown')):
            raise BalanceDataError(f'enemy {enemy_id}.ai values must be positive numbers')
        normalized_enemies[enemy_id] = stats

    normalized_affixes = []
    seen_ids = set()
    for index, affix in enumerate(affixes):
        label = f'elite_affixes[{index}]'
        _require_fields(label, affix, ('id', 'name', 'hp', 'dmg', 'speed', 'xp',
                                       'status', 'outline'))
        if affix['id'] in seen_ids:
            raise BalanceDataError(f'duplicate elite affix: {affix["id"]}')
        seen_ids.add(affix['id'])
        affix = dict(affix)
        status = affix['status']
        if (status is not None and
                (not isinstance(status, list) or len(status) != 2
                 or not isinstance(status[0], str)
                 or not isinstance(status[1], (int, float)))):
            raise BalanceDataError(f'{label}.status must be null or [name, duration]')
        affix['status'] = tuple(status) if status is not None else None
        affix['outline'] = _color(f'{label}.outline', affix['outline'])
        normalized_affixes.append(affix)
    return normalized_enemies, normalized_affixes


def _load_minibosses(enemy_ids):
    document = _read_json('minibosses.json')
    required = ('base', 'name', 'health', 'damage', 'speed', 'xp', 'w', 'h', 'color')
    normalized = {}
    for miniboss_id, stats in document.items():
        _require_fields(f'miniboss {miniboss_id}', stats, required)
        if stats['base'] not in enemy_ids:
            raise BalanceDataError(f'miniboss {miniboss_id} has unknown base enemy')
        stats = dict(stats)
        stats['color'] = _color(f'miniboss {miniboss_id}.color', stats['color'])
        normalized[miniboss_id] = stats
    return normalized


def _load_bosses():
    document = _read_json('bosses.json')
    thresholds = document.get('phase_thresholds')
    bosses = document.get('bosses')
    if (not isinstance(thresholds, list) or not thresholds
            or not all(isinstance(item, list) and len(item) == 2 for item in thresholds)):
        raise BalanceDataError('bosses.json requires phase_thresholds pairs')
    if not isinstance(bosses, dict) or not bosses:
        raise BalanceDataError('bosses.json requires a non-empty bosses object')

    required = ('name', 'epithet', 'intro', 'restoration', 'health', 'damage', 'speed', 'xp', 'gold', 'width',
                'height', 'color', 'skill_points', 'heal_on_kill', 'loot',
                'tuning', 'attacks', 'phases')
    normalized = {}
    for boss_id, definition in bosses.items():
        _require_fields(f'boss {boss_id}', definition, required)
        if any(not isinstance(definition[field], str) or not definition[field]
               for field in ('name', 'epithet', 'intro', 'restoration')):
            raise BalanceDataError(f'boss {boss_id} has invalid narrative text')
        definition = dict(definition)
        definition['color'] = _color(f'boss {boss_id}.color', definition['color'])
        tuning = definition['tuning']
        if not isinstance(tuning, dict) or set(tuning) != {'1', '2', '3'}:
            raise BalanceDataError(f'boss {boss_id}.tuning requires phases 1, 2, and 3')
        definition['tuning'] = {int(phase): values for phase, values in tuning.items()}
        phases = definition['phases']
        if not isinstance(phases, dict) or set(phases) != {'1', '2', '3'}:
            raise BalanceDataError(f'boss {boss_id}.phases requires phases 1, 2, and 3')
        normalized_phases = {}
        for phase, phase_data in phases.items():
            _require_fields(f'boss {boss_id}.phases.{phase}', phase_data,
                            ('message', 'color', 'entry'))
            if phase_data['entry'] not in ('none', 'summon', 'ring', 'hazard', 'meteor'):
                raise BalanceDataError(f'boss {boss_id}.phases.{phase} has invalid entry')
            phase_data = dict(phase_data)
            phase_data['color'] = _color(
                f'boss {boss_id}.phases.{phase}.color', phase_data['color'])
            normalized_phases[int(phase)] = phase_data
        definition['phases'] = normalized_phases
        if not all(isinstance(item, list) and len(item) == 2 for item in definition['loot']):
            raise BalanceDataError(f'boss {boss_id}.loot must contain [slot, rarity] pairs')
        definition['loot'] = [tuple(item) for item in definition['loot']]
        normalized[boss_id] = definition
    return normalized, [tuple(item) for item in thresholds]


ENEMY_STATS, ELITE_AFFIXES = _load_enemies()
MINIBOSS_DEFS = _load_minibosses(ENEMY_STATS)
BOSS_DEFS, PHASE_THRESHOLDS = _load_bosses()
