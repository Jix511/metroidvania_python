# spells.py - Hechizos del mago: proyectiles aliados y datos de lanzamiento.

import math
import pygame

# Hechizo: tecla, cooldown, descripción corta para la barra de hechizos.
SPELL_DEFS = {
    'fireball':    {'key': 'RMB', 'cooldown': 1.0,  'label': 'Bola de Fuego'},
    'frost_nova':  {'action': 'nova', 'cooldown': 6.0,  'label': 'Nova Escarcha'},
    'meteor':      {'action': 'meteor', 'cooldown': 20.0, 'label': 'Meteoritos'},
    'blizzard':    {'action': 'blizzard', 'cooldown': 15.0, 'label': 'Ventisca'},
    'arcane_orbit': {'passive': True, 'cooldown': 0.0,  'label': 'Órbita Arcana'},
    'whirlwind':   {'action': 'whirlwind', 'cooldown': 5.0,  'label': 'Torbellino'},
    'triple_shot': {'key': 'RMB', 'cooldown': 4.0,  'label': 'Triple'},
    'backflip':    {'action': 'dash', 'cooldown': 3.0, 'label': 'Voltereta'},
    'nine_tail_burst': {'key': 'RMB', 'cooldown': 6.0, 'label': 'Nueve Colas'},
    'soul_reap': {'key': 'RMB', 'cooldown': 1.5, 'label': 'Cosecha Espectral'},
}

# Habilidad desbloqueada -> hechizo lanzable.
ABILITY_SPELL = {
    'fireball': 'fireball',
    'frost_nova': 'frost_nova',
    'meteor': 'meteor',
    'blizzard': 'blizzard',
    'arcane_orbit': 'arcane_orbit',
    'whirlwind': 'whirlwind',
    'triple_shot': 'triple_shot',
    'backflip': 'backflip',
    'nine_tail_burst': 'nine_tail_burst',
    'soul_reap': 'soul_reap',
}


class AllyShot(pygame.sprite.Sprite):
    """Proyectil del jugador: daña enemigos, muere en muros y al impactar."""
    def __init__(self, x, y, vx, vy, damage, radius=6, life=2.0,
                 color=(255, 140, 40), burn=False, pierce=0, visual='orb',
                 element='physical'):
        super().__init__()
        self.damage = int(damage)
        self.velocity = pygame.math.Vector2(vx, vy)
        self.life = float(life)
        self.burn = burn
        self.pierce = int(pierce)
        self.hit_ids = set()  # ids de enemigos ya golpeados (perforación)
        self.visual = visual
        self.color = color
        self.element = element
        size = radius * 2 + 4
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), radius)
        pygame.draw.circle(self.image, (255, 240, 200), (size // 2, size // 2), max(1, radius // 2))
        self.rect = self.image.get_rect(center=(int(x), int(y)))

    def update(self, tilemap, dt):
        dt = min(dt, 1.0 / 20.0)
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return
        self.rect.x += int(round(self.velocity.x * dt))
        self.rect.y += int(round(self.velocity.y * dt))
        if tilemap is not None and tilemap.check_collision(self.rect):
            self.kill()


def direction_to(x0, y0, x1, y1):
    d = max(1.0, math.hypot(x1 - x0, y1 - y0))
    return (x1 - x0) / d, (y1 - y0) / d
