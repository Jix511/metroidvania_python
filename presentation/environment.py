"""Layered biome backgrounds, weather and animated environmental accents."""

import math
import random

import pygame


PALETTES = {
    'meadow': ((31, 55, 62), (48, 82, 70), (31, 58, 47)),
    'caves': ((10, 19, 32), (20, 39, 58), (27, 54, 66)),
    'ruins': ((13, 34, 39), (24, 55, 57), (36, 65, 60)),
    'sanctum': ((27, 20, 43), (48, 35, 70), (63, 48, 83)),
    'peak': ((27, 40, 57), (47, 66, 82), (68, 84, 96)),
}

AMBIENT_DARKNESS = {
    'meadow': 52,
    'caves': 126,
    'ruins': 82,
    'sanctum': 104,
    'peak': 66,
}


def ambient_alpha(zone_id, high_contrast=False):
    value = AMBIENT_DARKNESS.get(zone_id, AMBIENT_DARKNESS['meadow'])
    return min(value, 72) if high_contrast else value


class EnvironmentRenderer:
    def __init__(self, width, height, seed=7219):
        self.width, self.height = width, height
        self.time = 0.0
        rng = random.Random(seed)
        self.weather = [(rng.random(), rng.random(), rng.uniform(0.65, 1.35))
                        for _ in range(80)]

    def update(self, dt):
        self.time += dt

    def _palette(self, zone_id):
        return PALETTES.get(zone_id, PALETTES['meadow'])

    def draw_background(self, surface, camera_x, zone_id, quality='high',
                        transition=None, boss_id=None):
        self._draw_biome(surface, camera_x, zone_id, quality)
        if transition is not None:
            next_zone, amount = transition
            if amount > 0:
                blended = pygame.Surface((self.width, self.height))
                self._draw_biome(blended, camera_x, next_zone, quality)
                blended.set_alpha(round(255 * max(0.0, min(1.0, amount))))
                surface.blit(blended, (0, 0))
        if boss_id:
            self._boss_arena_layer(surface, camera_x, boss_id)

    def _draw_biome(self, surface, camera_x, zone_id, quality):
        sky, far, near = self._palette(zone_id)
        surface.fill(sky)
        self._far_layer(surface, camera_x, zone_id, far)
        self._mid_layer(surface, camera_x, zone_id, near)
        if quality == 'high':
            self._near_layer(surface, camera_x, zone_id, near)

    def _mid_layer(self, surface, camera_x, zone_id, color):
        shift = int(camera_x * 0.2) % 260
        if zone_id == 'meadow':
            for x in range(-260 - shift, self.width + 300, 210):
                pygame.draw.rect(surface, (38, 70, 55), (x + 100, self.height - 290, 18, 210))
                pygame.draw.circle(surface, (42, 82, 61), (x + 109, self.height - 300), 62)
                pygame.draw.circle(surface, (53, 92, 62), (x + 70, self.height - 280), 40)
        elif zone_id == 'caves':
            for x in range(-260 - shift, self.width + 300, 130):
                h = 42 + (x // 130 % 4) * 13
                crystal = (35, 88, 112)
                pygame.draw.polygon(surface, crystal,
                                    ((x + 50, self.height - 75),
                                     (x + 62, self.height - 75 - h),
                                     (x + 75, self.height - 75)))
                pygame.draw.line(surface, (75, 150, 175),
                                 (x + 62, self.height - 75 - h),
                                 (x + 62, self.height - 82), 2)
        elif zone_id == 'ruins':
            for x in range(-260 - shift, self.width + 300, 190):
                pygame.draw.rect(surface, (40, 72, 69), (x + 45, self.height - 260, 32, 190))
                pygame.draw.rect(surface, (55, 91, 84), (x + 28, self.height - 270, 66, 14))
                pygame.draw.arc(surface, (75, 115, 105),
                                (x + 74, self.height - 225, 100, 145), math.pi, math.tau, 7)
        elif zone_id == 'sanctum':
            for x in range(-260 - shift, self.width + 300, 170):
                pygame.draw.rect(surface, (58, 43, 78), (x + 50, self.height - 330, 26, 260))
                pygame.draw.polygon(surface, (105, 68, 135),
                                    ((x + 63, self.height - 285),
                                     (x + 73, self.height - 270),
                                     (x + 63, self.height - 255),
                                     (x + 53, self.height - 270)))
        else:
            for x in range(-260 - shift, self.width + 300, 155):
                peak = self.height - 220 - (x // 155 % 3) * 45
                pygame.draw.polygon(surface, (61, 75, 91),
                                    ((x, self.height - 55), (x + 78, peak),
                                     (x + 160, self.height - 55)))
                pygame.draw.polygon(surface, (142, 160, 174),
                                    ((x + 58, peak + 30), (x + 78, peak),
                                     (x + 99, peak + 36)))

    def _boss_arena_layer(self, surface, camera_x, boss_id):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pulse = (math.sin(self.time * 2.5) + 1.0) * 0.5
        if boss_id == 'cavern_mother':
            for x in range(20, self.width, 145):
                pygame.draw.arc(overlay, (55, 125, 78, 125),
                                (x, self.height - 245, 110, 210), math.pi, math.tau, 9)
                pygame.draw.circle(overlay, (105, 220, 115, 85),
                                   (x + 55, self.height - 75), 8 + round(pulse * 3))
        elif boss_id == 'sanctum_guardian':
            center = (self.width // 2, self.height - 145)
            for radius in (55, 95, 140):
                pygame.draw.circle(overlay, (180, 115, 255, 45 + round(pulse * 30)),
                                   center, radius, 2)
            for x in (75, self.width - 105):
                pygame.draw.rect(overlay, (125, 90, 165, 135),
                                 (x, self.height - 330, 30, 275))
        elif boss_id == 'void_heart':
            for index, x in enumerate(range(55, self.width, 120)):
                y = 90 + (index % 3) * 75 + round(math.sin(self.time * 1.8 + index) * 12)
                pygame.draw.polygon(overlay, (175, 70, 235, 115),
                                    ((x, y - 24), (x + 15, y), (x, y + 30), (x - 12, y)))
            pygame.draw.circle(overlay, (205, 80, 255, 35 + round(pulse * 28)),
                               (self.width // 2, self.height // 2), 190)
        surface.blit(overlay, (0, 0))

    def _far_layer(self, surface, camera_x, zone_id, color):
        shift = int(camera_x * 0.12) % 240
        baseline = self.height - 175
        if zone_id == 'meadow':
            points = [(-80, self.height), (-80, baseline + 25)]
            for x in range(-240 - shift, self.width + 300, 120):
                points.extend(((x, baseline), (x + 55, baseline - 70),
                               (x + 120, baseline)))
            points.extend(((self.width + 80, self.height),))
            pygame.draw.polygon(surface, color, points)
        elif zone_id in ('caves', 'peak'):
            for x in range(-240 - shift, self.width + 240, 120):
                peak = 110 + ((x // 120) % 3) * 35
                pygame.draw.polygon(surface, color,
                                    ((x, self.height), (x + 64, peak),
                                     (x + 130, self.height)))
        else:
            for x in range(-180 - shift, self.width + 200, 145):
                pygame.draw.rect(surface, color, (x, baseline - 105, 34, 280))
                pygame.draw.rect(surface, color, (x - 18, baseline - 112, 70, 12))
                if zone_id == 'sanctum':
                    pygame.draw.arc(surface, color, (x + 18, baseline - 90, 110, 150),
                                    math.pi, math.tau, 16)

    def _near_layer(self, surface, camera_x, zone_id, color):
        shift = int(camera_x * 0.28) % 190
        if zone_id == 'meadow':
            for x in range(-190 - shift, self.width + 190, 150):
                pygame.draw.rect(surface, color, (x + 70, self.height - 245, 15, 150))
                pygame.draw.circle(surface, color, (x + 78, self.height - 255), 54)
        elif zone_id == 'caves':
            for x in range(-190 - shift, self.width + 190, 95):
                length = 65 + (x // 95 % 3) * 28
                pygame.draw.polygon(surface, color,
                                    ((x, 0), (x + 48, 0), (x + 22, length)))
        elif zone_id == 'ruins':
            water_y = self.height - 115
            pygame.draw.rect(surface, color, (0, water_y, self.width, 115))
            for x in range(-190 - shift, self.width + 190, 170):
                pygame.draw.line(surface, (65, 105, 101),
                                 (x, water_y + 15), (x + 80, water_y + 15), 2)
        elif zone_id == 'sanctum':
            for x in range(-190 - shift, self.width + 190, 130):
                pulse = 4 + int(2 * math.sin(self.time * 2 + x))
                pygame.draw.polygon(surface, color,
                                    ((x + 40, self.height - 80),
                                     (x + 52, self.height - 140 - pulse),
                                     (x + 64, self.height - 80)))
        else:
            for x in range(-190 - shift, self.width + 190, 105):
                pygame.draw.line(surface, color, (x, self.height - 80),
                                 (x + 48, self.height - 220), 10)

    def draw_weather(self, surface, zone_id, quality='high', restored=False):
        count = 80 if quality == 'high' else 28
        if restored:
            count = max(12, count // 3)
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for px, py, speed in self.weather[:count]:
            if zone_id == 'peak':
                x = int((px * self.width - self.time * 95 * speed) % self.width)
                y = int((py * self.height + self.time * 72 * speed) % self.height)
                pygame.draw.line(overlay, (215, 235, 255, 155), (x, y), (x + 8, y - 5), 1)
            elif zone_id == 'caves':
                x = int(px * self.width)
                y = int((py * self.height + self.time * 22 * speed) % self.height)
                pygame.draw.circle(overlay, (90, 180, 215, 90), (x, y), 1)
            elif zone_id == 'ruins':
                x = int(px * self.width + math.sin(self.time + py * 10) * 8)
                y = int((py * self.height - self.time * 18 * speed) % self.height)
                pygame.draw.circle(overlay, (125, 205, 195, 80), (x, y), 2, 1)
            elif zone_id == 'sanctum':
                x = int(px * self.width)
                y = int((py * self.height - self.time * 12 * speed) % self.height)
                pygame.draw.circle(overlay, (185, 135, 255, 95), (x, y), 1)
            else:
                x = int((px * self.width + self.time * 12 * speed) % self.width)
                y = int(py * self.height + math.sin(self.time * speed + px * 8) * 7)
                pygame.draw.circle(overlay, (225, 235, 150, 75), (x, y), 1)
        surface.blit(overlay, (0, 0))

    def draw_contact_shadow(self, surface, center, width, airborne=False):
        if airborne:
            width = max(8, int(width * 0.65))
        shadow = pygame.Surface((width + 8, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (5, 8, 12, 95 if not airborne else 48), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=center))

    def draw_lighting(self, surface, zone_id, lights, quality='high',
                      high_contrast=False):
        """Apply ambient darkness, radial light masks and restrained colored glow."""
        darkness = ambient_alpha(zone_id, high_contrast)
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((4, 7, 14, darkness))
        glow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        rings = 8 if quality == 'high' else 4
        limit = 28 if quality == 'high' else 12
        for x, y, radius, color, strength in lights[:limit]:
            if x + radius < 0 or x - radius > self.width or y + radius < 0 or y - radius > self.height:
                continue
            for step in range(rings, 0, -1):
                fraction = step / rings
                current_radius = max(2, round(radius * fraction))
                alpha = round(darkness * (fraction ** 1.7))
                pygame.draw.circle(overlay, (0, 0, 0, alpha),
                                   (round(x), round(y)), current_radius)
            pygame.draw.circle(glow, (*color, max(8, int(strength * 0.16))),
                               (round(x), round(y)), max(3, round(radius * 0.42)))
            pygame.draw.circle(glow, (*color, max(12, int(strength * 0.32))),
                               (round(x), round(y)), max(2, round(radius * 0.14)))
        surface.blit(overlay, (0, 0))
        # Composición alfa normal: BLEND_RGBA_ADD suma el RGB completo aunque
        # el píxel tenga poca opacidad y producía círculos sólidos alrededor
        # de cada clase/proyectil.
        surface.blit(glow, (0, 0))
