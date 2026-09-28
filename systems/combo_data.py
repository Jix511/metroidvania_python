"""Validated class combo chains."""

import json

from constants import CHARACTER_CLASSES
from core.paths import DATA_DIR


class ComboDataError(ValueError):
    pass


MELEE_PATTERNS = {'sweep_high', 'sweep_low', 'spin', 'thrust', 'downstrike'}
RANGED_PATTERNS = {'focus', 'rising', 'falling', 'fan'}


def _load_combos():
    path = DATA_DIR / 'combos.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ComboDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict) or set(document) != set(CHARACTER_CLASSES):
        raise ComboDataError('combos.json must define every character class')
    for class_id, chains in document.items():
        if not isinstance(chains, dict) or set(chains) != {'ground', 'air'}:
            raise ComboDataError(f'combo {class_id} requires ground and air chains')
        for mode, moves in chains.items():
            if not isinstance(moves, list) or len(moves) < 2:
                raise ComboDataError(f'combo {class_id}.{mode} requires at least two moves')
            for move in moves:
                if (not isinstance(move, dict)
                        or any(key not in move for key in ('damage', 'reach', 'cooldown'))
                        or any(not isinstance(move[key], (int, float)) or move[key] <= 0
                               for key in ('damage', 'reach', 'cooldown'))):
                    raise ComboDataError(f'combo {class_id}.{mode} has an invalid move')
                pattern = move.get('pattern')
                if pattern not in MELEE_PATTERNS | RANGED_PATTERNS:
                    raise ComboDataError(
                        f'combo {class_id}.{mode} has an invalid pattern')
                for key in ('arc', 'aim', 'origin_y', 'speed', 'spread',
                            'angle_offset'):
                    if key in move and not isinstance(move[key], (int, float)):
                        raise ComboDataError(
                            f'combo {class_id}.{mode}.{key} must be numeric')
    return document


COMBOS = _load_combos()
