"""Runtime slicing and normalization for external sprite sheets."""

import pygame

from presentation.sprite_data import SPRITE_SHEETS
from presentation.frame_enrichment import enrich_frames


def _cell(sheet, column, row, columns, rows):
    x0 = round(column * sheet.get_width() / columns)
    x1 = round((column + 1) * sheet.get_width() / columns)
    y0 = round(row * sheet.get_height() / rows)
    y1 = round((row + 1) * sheet.get_height() / rows)
    return sheet.subsurface((x0, y0, x1 - x0, y1 - y0)).copy()


def _trim(surface):
    bounds = surface.get_bounding_rect(min_alpha=1)
    return surface.subsurface(bounds).copy() if bounds.width and bounds.height else surface


def load_sprite_sheet(sprite_id):
    definition = SPRITE_SHEETS[sprite_id]
    sheet = pygame.image.load(str(definition['source_path'])).convert_alpha()
    cells = {
        cell: _trim(_cell(sheet, cell[0], cell[1], definition['columns'], definition['rows']))
        for frames in definition['animations'].values() for cell in frames
    }
    idle_heights = [cells[cell].get_height() for cell in definition['animations']['idle']]
    reference_height = max(1, max(idle_heights))
    canvas_width, canvas_height = definition['canvas']
    padding = definition['padding']
    scale = (canvas_height - padding * 2) / reference_height

    animations = {}
    for name, frame_cells in definition['animations'].items():
        frames = []
        for cell in frame_cells:
            source = cells[cell]
            size = (max(1, round(source.get_width() * scale)),
                    max(1, round(source.get_height() * scale)))
            if definition['scaling'] == 'nearest':
                image = pygame.transform.scale(source, size)
            else:
                image = pygame.transform.smoothscale(source, size)
            frame = pygame.Surface((canvas_width, canvas_height), pygame.SRCALPHA)
            frame.blit(image, ((canvas_width - image.get_width()) // 2,
                               canvas_height - padding - image.get_height()))
            frames.append(frame)
        animations[name] = frames
    return enrich_frames(animations)


def load_player_frames(character_class, fallback_factory):
    sprite_id = f'player:{character_class}'
    if sprite_id not in SPRITE_SHEETS:
        return enrich_frames(fallback_factory(character_class))
    try:
        return load_sprite_sheet(sprite_id)
    except (OSError, ValueError, pygame.error):
        return enrich_frames(fallback_factory(character_class))


def load_entity_frames(kind, entity_id, fallback_factory, fallback_id=None):
    """Load external enemy art while keeping procedural art as a robust fallback."""
    sprite_id = f'{kind}:{entity_id}'
    if sprite_id not in SPRITE_SHEETS:
        return enrich_frames(fallback_factory(fallback_id or entity_id))
    try:
        return load_sprite_sheet(sprite_id)
    except (OSError, ValueError, pygame.error):
        return enrich_frames(fallback_factory(fallback_id or entity_id))
