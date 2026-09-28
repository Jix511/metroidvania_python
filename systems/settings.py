"""Validated persistent graphics and audio preferences."""

from copy import deepcopy

from core.paths import SETTINGS_SAVE_PATH
from systems.json_storage import (JsonStorageError, load_json_with_recovery,
                                  save_json_atomic)


RESOLUTIONS = ((960, 640), (1280, 720), (1600, 900), (1920, 1080))
DEFAULTS = {
    'resolution': [960, 640],
    'fullscreen': False,
    'effects_quality': 'high',
    'minimap_mode': 'full',
    'master_volume': 1.0,
    'music_volume': 0.7,
    'sfx_volume': 1.0,
    'text_size': 'normal',
    'high_contrast': False,
    'reduced_motion': False,
    'screen_shake': 1.0,
    'reduced_flashes': False,
}


def valid(data):
    legacy_required = {'resolution', 'fullscreen', 'master_volume',
                       'music_volume', 'sfx_volume'}
    if (not isinstance(data, dict) or not legacy_required.issubset(data)
            or not set(data).issubset(DEFAULTS)):
        return False
    resolution = data.get('resolution')
    volumes = (data.get('master_volume'), data.get('music_volume'),
               data.get('sfx_volume'))
    return (
        isinstance(resolution, list)
        and len(resolution) == 2
        and tuple(resolution) in RESOLUTIONS
        and isinstance(data.get('fullscreen'), bool)
        and data.get('effects_quality', 'high') in ('low', 'high')
        and data.get('minimap_mode', 'full') in ('full', 'compact', 'hidden')
        and data.get('text_size', 'normal') in ('normal', 'large')
        and isinstance(data.get('high_contrast', False), bool)
        and isinstance(data.get('reduced_motion', False), bool)
        and data.get('screen_shake', 1.0) in (0.0, 0.5, 1.0)
        and isinstance(data.get('reduced_flashes', False), bool)
        and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                and 0.0 <= value <= 1.0 for value in volumes)
    )


def load():
    try:
        data, _recovered = load_json_with_recovery(SETTINGS_SAVE_PATH, valid)
    except (FileNotFoundError, OSError, JsonStorageError):
        data = deepcopy(DEFAULTS)
    return normalize(data)


def save(data):
    normalized = normalize(data)
    try:
        save_json_atomic(SETTINGS_SAVE_PATH, normalized, valid)
        return True
    except (OSError, TypeError, ValueError, JsonStorageError):
        return False


def normalize(data):
    result = deepcopy(DEFAULTS)
    if isinstance(data, dict):
        result.update(data)
    result['resolution'] = list(result['resolution'])
    for key in ('master_volume', 'music_volume', 'sfx_volume'):
        result[key] = round(max(0.0, min(1.0, float(result[key]))), 2)
    return result


def reset():
    result = deepcopy(DEFAULTS)
    save(result)
    return result


def cycle_resolution(data, direction=1):
    current = tuple(data['resolution'])
    index = RESOLUTIONS.index(current) if current in RESOLUTIONS else 0
    data['resolution'] = list(RESOLUTIONS[(index + direction) % len(RESOLUTIONS)])
    return data


def adjust_volume(data, key, amount):
    if key not in ('master_volume', 'music_volume', 'sfx_volume'):
        raise KeyError(key)
    data[key] = round(max(0.0, min(1.0, data[key] + amount)), 2)
    return data


def cycle_effects_quality(data):
    data['effects_quality'] = 'low' if data['effects_quality'] == 'high' else 'high'
    return data


def cycle_minimap_mode(data):
    values = ('full', 'compact', 'hidden')
    current = data.get('minimap_mode', 'full')
    data['minimap_mode'] = values[(values.index(current) + 1) % len(values)]
    return data


def cycle_text_size(data):
    data['text_size'] = 'large' if data.get('text_size', 'normal') == 'normal' else 'normal'
    return data


def cycle_screen_shake(data):
    values = (1.0, 0.5, 0.0)
    current = data.get('screen_shake', 1.0)
    data['screen_shake'] = values[(values.index(current) + 1) % len(values)]
    return data
