"""Short-lived class-specific combat accents drawn in world space."""

from dataclasses import dataclass
import math

import pygame


@dataclass(slots=True)
class CombatAccent:
    kind: str
    x: float
    y: float
    facing: int
    age: float
    life: float
    color: tuple
    scale: float = 1.0


CLASS_COLORS = {
    'warrior': (255, 205, 95),
    'rogue': (205, 90, 225),
    'mage': (100, 195, 255),
    'ranger': (145, 225, 125),
    'kitsune': (255, 105, 185),
    'reaper': (85, 235, 220),
}


class CombatVisuals:
    def __init__(self, cap=48):
        self.cap = cap
        self.accents = []

    def add(self, kind, x, y, facing=1, color=(255, 255, 255), life=0.22,
            scale=1.0):
        if len(self.accents) >= self.cap:
            self.accents.pop(0)
        self.accents.append(CombatAccent(kind, x, y, facing, 0.0, life,
                                         tuple(color), scale))

    def class_attack(self, character_class, x, y, facing=1, power=1.0,
                     variant=None):
        color = CLASS_COLORS.get(character_class, (255, 255, 255))
        kind = {'warrior': 'heavy_slash', 'rogue': 'twin_slash',
                'mage': 'sigil', 'ranger': 'bow_flash',
                'reaper': 'soul_scythe'}.get(character_class, 'slash')
        if variant in ('sweep_high', 'sweep_low', 'spin', 'thrust', 'downstrike'):
            kind = variant
        self.add(kind, x, y, facing, color, scale=max(0.8, power))

    def update(self, dt):
        for accent in self.accents:
            accent.age += dt
        self.accents = [accent for accent in self.accents if accent.age < accent.life]

    def draw(self, surface, offset):
        ox, oy = int(offset[0]), int(offset[1])
        for accent in self.accents:
            progress = accent.age / accent.life
            alpha = max(0, int(235 * (1.0 - progress)))
            color = (*accent.color, alpha)
            size = max(20, int(54 * accent.scale))
            layer = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            center = pygame.Vector2(size, size)
            direction = 1 if accent.facing >= 0 else -1
            if accent.kind == 'heavy_slash':
                box = pygame.Rect(size // 3, size // 3, size, size)
                start = 205 if direction > 0 else -25
                pygame.draw.arc(layer, color, box, math.radians(start),
                                math.radians(start + 115), max(3, size // 12))
                pygame.draw.line(layer, (*accent.color, alpha // 2), center,
                                 center + (direction * size * 0.8, size * 0.28), 2)
            elif accent.kind == 'twin_slash':
                for shift in (-7, 7):
                    pygame.draw.line(layer, color,
                                     center + (-direction * 10, -20 + shift),
                                     center + (direction * 28, 16 + shift), 3)
            elif accent.kind == 'sigil':
                radius = max(4, int(size * (0.25 + progress * 0.35)))
                pygame.draw.circle(layer, color, center, radius, 2)
                for angle in range(0, 360, 90):
                    rad = math.radians(angle + progress * 90)
                    point = center + pygame.Vector2(math.cos(rad), math.sin(rad)) * radius
                    pygame.draw.circle(layer, color, point, 3)
            elif accent.kind == 'bow_flash':
                tip = center + (direction * int(size * 0.65), 0)
                pygame.draw.line(layer, color, center + (0, -18), tip, 2)
                pygame.draw.line(layer, color, center + (0, 18), tip, 2)
                pygame.draw.line(layer, (*accent.color, alpha // 2),
                                 center + (-direction * 14, 0), tip, 1)
            elif accent.kind == 'soul_scythe':
                box = pygame.Rect(size // 5, size // 4, int(size * 1.35), size)
                start = 190 if direction > 0 else -10
                pygame.draw.arc(layer, color, box, math.radians(start),
                                math.radians(start + 155), max(4, size // 10))
                pygame.draw.arc(layer, (*accent.color, alpha // 3), box.inflate(8, 8),
                                math.radians(start), math.radians(start + 155), 2)
            elif accent.kind in ('sweep_high', 'sweep_low', 'spin', 'downstrike'):
                box = pygame.Rect(size // 4, size // 4, int(size * 1.25), size)
                if accent.kind == 'spin':
                    pygame.draw.circle(layer, color, center, int(size * 0.62),
                                       max(3, size // 12))
                elif accent.kind == 'downstrike':
                    pygame.draw.arc(layer, color, box, math.radians(250),
                                    math.radians(350), max(4, size // 11))
                else:
                    start = 205 if accent.kind == 'sweep_high' else 145
                    if direction < 0:
                        start = 180 - start
                    pygame.draw.arc(layer, color, box, math.radians(start),
                                    math.radians(start + 125), max(4, size // 11))
            elif accent.kind == 'thrust':
                end = center + (direction * int(size * 0.85), 0)
                pygame.draw.line(layer, color, center, end, max(3, size // 12))
                pygame.draw.circle(layer, color, end, 4)
            else:
                pygame.draw.circle(layer, color, center, size // 2, 2)
            surface.blit(layer, layer.get_rect(center=(int(accent.x) + ox,
                                                       int(accent.y) + oy)))
