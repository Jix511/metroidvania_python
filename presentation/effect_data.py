"""Validated particle-emitter presets loaded from JSON."""

import json

from core.paths import DATA_DIR


class EffectDataError(ValueError):
    pass


def _range(label, value, minimum=0.0):
    if (not isinstance(value, list) or len(value) != 2
            or not all(isinstance(number, (int, float)) and not isinstance(number, bool)
                       for number in value)
            or value[0] < minimum or value[1] < value[0]):
        raise EffectDataError(f'{label} must be an ascending numeric pair')
    return tuple(float(number) for number in value)


def _color(label, value):
    if (not isinstance(value, list) or len(value) != 3
            or not all(isinstance(channel, int) and 0 <= channel <= 255
                       for channel in value)):
        raise EffectDataError(f'{label} must be an RGB color')
    return tuple(value)


def validate_effect(effect_id, definition):
    required = {'count', 'colors', 'speed', 'life', 'size', 'gravity', 'drag',
                'shape', 'layer'}
    if not isinstance(definition, dict) or not required.issubset(definition):
        raise EffectDataError(f'effect {effect_id} is incomplete')
    if (not isinstance(definition['count'], int) or isinstance(definition['count'], bool)
            or definition['count'] < 1):
        raise EffectDataError(f'effect {effect_id}.count must be positive')
    colors = definition['colors']
    if not isinstance(colors, list) or not colors:
        raise EffectDataError(f'effect {effect_id}.colors must not be empty')
    if definition['shape'] not in {'square', 'circle', 'spark'}:
        raise EffectDataError(f'effect {effect_id} has an unknown shape')
    if not isinstance(definition['layer'], int) or definition['layer'] not in (0, 1, 2):
        raise EffectDataError(f'effect {effect_id}.layer must be 0, 1, or 2')
    gravity, drag = definition['gravity'], definition['drag']
    if (not isinstance(gravity, (int, float)) or isinstance(gravity, bool)
            or not isinstance(drag, (int, float)) or isinstance(drag, bool)
            or drag < 0):
        raise EffectDataError(f'effect {effect_id} has invalid physics')
    return {
        'count': definition['count'],
        'colors': tuple(_color(f'effect {effect_id}.colors', color) for color in colors),
        'speed': _range(f'effect {effect_id}.speed', definition['speed']),
        'life': _range(f'effect {effect_id}.life', definition['life'], 0.01),
        'size': _range(f'effect {effect_id}.size', definition['size'], 1.0),
        'gravity': float(gravity),
        'drag': float(drag),
        'shape': definition['shape'],
        'layer': definition['layer'],
    }


def _load_effects():
    path = DATA_DIR / 'effects.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EffectDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict) or not document:
        raise EffectDataError('effects.json must contain emitter presets')
    return {effect_id: validate_effect(effect_id, definition)
            for effect_id, definition in document.items()}


EFFECT_PRESETS = _load_effects()
