"""External achievement catalog and progress evaluation."""

import json

from core.paths import DATA_DIR


def _load():
    with (DATA_DIR / 'achievements.json').open(encoding='utf-8') as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or not document:
        raise ValueError('achievements.json must contain achievements')
    for achievement_id, item in document.items():
        required = ('name', 'description', 'category', 'metric', 'target', 'reward')
        if any(key not in item for key in required) or item['target'] <= 0:
            raise ValueError(f'Invalid achievement: {achievement_id}')
    return document


ACHIEVEMENTS = _load()


def progress(player, definition):
    metric = definition['metric']
    if metric == 'explored_rooms':
        return len(player.explored_rooms)
    if metric == 'discovered_secrets':
        return len(player.discovered_secrets)
    return int(player.statistics.get(metric, 0))


def completed(player, definition):
    required_class = definition.get('class')
    return ((required_class is None or player.character_class == required_class)
            and progress(player, definition) >= definition['target'])


def pending(player):
    return [(achievement_id, definition) for achievement_id, definition in ACHIEVEMENTS.items()
            if achievement_id not in player.unlocked_achievements
            and completed(player, definition)]
