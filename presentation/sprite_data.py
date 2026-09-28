"""Validated metadata for external sprite sheets."""

import json

from core.paths import DATA_DIR, SPRITES_DIR


class SpriteDataError(ValueError):
    pass


def _load_sprite_sheets():
    path = DATA_DIR / 'sprite_sheets.json'
    try:
        with path.open('r', encoding='utf-8') as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpriteDataError(f'Could not load {path.name}: {exc}') from exc
    if not isinstance(document, dict):
        raise SpriteDataError('sprite_sheets.json must contain an object')
    normalized = {}
    for sprite_id, definition in document.items():
        required = {'source', 'columns', 'rows', 'canvas', 'animations'}
        if not isinstance(definition, dict) or not required.issubset(definition):
            raise SpriteDataError(f'sprite {sprite_id} is incomplete')
        columns, rows = definition['columns'], definition['rows']
        canvas = definition['canvas']
        if (not isinstance(columns, int) or columns < 1
                or not isinstance(rows, int) or rows < 1
                or not isinstance(canvas, list) or len(canvas) != 2
                or not all(isinstance(value, int) and value > 0 for value in canvas)):
            raise SpriteDataError(f'sprite {sprite_id} has invalid dimensions')
        animations = definition['animations']
        if not isinstance(animations, dict) or not animations:
            raise SpriteDataError(f'sprite {sprite_id} requires animations')
        for animation, cells in animations.items():
            if (not isinstance(cells, list) or not cells
                    or not all(isinstance(cell, list) and len(cell) == 2
                               and all(isinstance(value, int) for value in cell)
                               and 0 <= cell[0] < columns and 0 <= cell[1] < rows
                               for cell in cells)):
                raise SpriteDataError(f'sprite {sprite_id}.{animation} has invalid cells')
        source = SPRITES_DIR / definition['source']
        scaling = definition.get('scaling', 'smooth')
        if scaling not in ('nearest', 'smooth'):
            raise SpriteDataError(f'sprite {sprite_id} has an unknown scaling mode')
        normalized[sprite_id] = {
            **definition,
            'source_path': source,
            'canvas': tuple(canvas),
            'padding': max(0, int(definition.get('padding', 0))),
            'scaling': scaling,
            'animations': {name: tuple(tuple(cell) for cell in cells)
                           for name, cells in animations.items()},
        }
    return normalized


SPRITE_SHEETS = _load_sprite_sheets()
