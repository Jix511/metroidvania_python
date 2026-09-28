"""Load auxiliary art atlases used by the world and interface."""

import pygame

from core.paths import SPRITES_DIR


def _cell(sheet, column, row, columns, rows):
    x0 = round(column * sheet.get_width() / columns)
    x1 = round((column + 1) * sheet.get_width() / columns)
    y0 = round(row * sheet.get_height() / rows)
    y1 = round((row + 1) * sheet.get_height() / rows)
    image = sheet.subsurface((x0, y0, x1 - x0, y1 - y0)).copy()
    bounds = image.get_bounding_rect(min_alpha=1)
    return image.subsurface(bounds).copy() if bounds.width and bounds.height else image


def _fit(image, width, height):
    scale = min(width / max(1, image.get_width()), height / max(1, image.get_height()))
    size = (max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)))
    return pygame.transform.scale(image, size)


def load_art_assets():
    """Return optional NPC and inventory art; missing files simply disable it."""
    try:
        sheet = pygame.image.load(str(SPRITES_DIR / 'support-atlas.png')).convert_alpha()
        assets = {'shopkeeper': _fit(_cell(sheet, 0, 0, 5, 3), 56, 64)}
        names = ('weapon', 'dagger', 'staff', 'bow', 'reaper',
                 'helmet', 'armor', 'boots', 'accessory', 'hunter_eye')
        for index, name in enumerate(names):
            assets[name] = _fit(_cell(sheet, index % 5, 1 + index // 5, 5, 3), 36, 36)
        return assets
    except (OSError, ValueError, pygame.error):
        return {}


def load_biome_tiles():
    """Return four 16px tiles for each world zone from the environment atlas."""
    zone_ids = ('meadow', 'caves', 'ruins', 'sanctum', 'peak')
    try:
        sheet = pygame.image.load(
            str(SPRITES_DIR / 'world' / 'biome-atlas.png')).convert_alpha()
        return {
            zone: tuple(_fit(_cell(sheet, column, row, 4, 5), 16, 16)
                        for column in range(4))
            for row, zone in enumerate(zone_ids)
        }
    except (OSError, ValueError, pygame.error):
        return {}
