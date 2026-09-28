"""Validated and reusable XP, gold, skill-point, and item rewards."""

import json

from core.paths import DATA_DIR
from systems.item_data import RARITIES, SLOTS
from systems.items import generate_item


class RewardDataError(ValueError):
    pass


RARITY_ORDER = tuple(RARITIES)
HEAL_MODES = {'none', 'half', 'full'}


def validate_reward(label, reward):
    if not isinstance(reward, dict):
        raise RewardDataError(f'{label} must be an object')
    normalized = {
        'xp': reward.get('xp', 0),
        'gold': reward.get('gold', 0),
        'skill_points': reward.get('skill_points', 0),
        'heal': reward.get('heal', 'none'),
        'drop_gold': reward.get('drop_gold', 0),
        'items': reward.get('items', []),
    }
    for key in ('xp', 'gold', 'skill_points', 'drop_gold'):
        if (not isinstance(normalized[key], int) or isinstance(normalized[key], bool)
                or normalized[key] < 0):
            raise RewardDataError(f'{label}.{key} must be a non-negative integer')
    if normalized['heal'] not in HEAL_MODES:
        raise RewardDataError(f'{label}.heal must be one of {sorted(HEAL_MODES)}')
    if not isinstance(normalized['items'], list):
        raise RewardDataError(f'{label}.items must be a list')
    items = []
    for index, item in enumerate(normalized['items']):
        item_label = f'{label}.items[{index}]'
        if not isinstance(item, dict):
            raise RewardDataError(f'{item_label} must be an object')
        item = dict(item)
        if item.get('slot') is not None and item['slot'] not in SLOTS:
            raise RewardDataError(f'{item_label} has an unknown slot')
        if item.get('rarity') is not None and item['rarity'] not in RARITIES:
            raise RewardDataError(f'{item_label} has an unknown rarity')
        if (item.get('minimum_rarity') is not None
                and item['minimum_rarity'] not in RARITIES):
            raise RewardDataError(f'{item_label} has an unknown minimum rarity')
        level_offset = item.get('level_offset', 0)
        luck = item.get('luck', 0.0)
        if (not isinstance(level_offset, int) or isinstance(level_offset, bool)
                or not isinstance(luck, (int, float)) or isinstance(luck, bool)):
            raise RewardDataError(f'{item_label} has invalid generation values')
        items.append(item)
    normalized['items'] = items
    return normalized


def _load_presets():
    path = DATA_DIR / 'rewards.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RewardDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict) or not document:
        raise RewardDataError('rewards.json must contain reward presets')
    return {reward_id: validate_reward(f'reward {reward_id}', reward)
            for reward_id, reward in document.items()}


REWARD_PRESETS = _load_presets()


def boss_reward(definition, xp, gold):
    return validate_reward('boss reward', {
        'xp': int(xp),
        'gold': int(gold),
        'skill_points': definition['skill_points'],
        'heal': definition['heal_on_kill'],
        'drop_gold': 25,
        'items': [
            {'slot': slot, 'rarity': rarity, 'level_offset': 1}
            for slot, rarity in definition['loot']
        ],
    })


def grant_reward(player, reward, item_level=None, item_factory=generate_item):
    """Apply currencies/stats and return generated items for the caller to place."""
    spec = validate_reward('runtime reward', reward)
    before_level = player.level
    player.gain_experience(spec['xp'])
    gold = player.add_gold(spec['gold'])
    player.skill_points += spec['skill_points']
    if spec['heal'] == 'full':
        player.health = player.max_health
    elif spec['heal'] == 'half':
        player.health = min(player.max_health, player.health + player.max_health // 2)

    base_level = max(1, player.level if item_level is None else int(item_level))
    items = []
    for item_spec in spec['items']:
        level = max(1, base_level + item_spec.get('level_offset', 0))
        item = item_factory(level, item_spec.get('slot'), item_spec.get('rarity'),
                            item_spec.get('luck', 0.0))
        minimum = item_spec.get('minimum_rarity')
        if minimum and RARITY_ORDER.index(item['rarity']) < RARITY_ORDER.index(minimum):
            item = item_factory(level, item_spec.get('slot'), minimum,
                                item_spec.get('luck', 0.0))
        items.append(item)
    return {
        'xp': spec['xp'],
        'gold': gold,
        'skill_points': spec['skill_points'],
        'items': items,
        'drop_gold': spec['drop_gold'],
        'levels_gained': player.level - before_level,
    }


def reward_summary(result):
    parts = []
    if result['xp']:
        parts.append(f"+{result['xp']} XP")
    if result['gold']:
        parts.append(f"+{result['gold']} oro")
    if result['skill_points']:
        parts.append(f"+{result['skill_points']} pt habilidad")
    if result['items']:
        parts.append(f"{len(result['items'])} objeto(s)")
    return ' · '.join(parts)
