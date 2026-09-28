"""Pooled, configurable particles and floating combat text."""

from dataclasses import dataclass
import math
import random

from presentation.effect_data import EFFECT_PRESETS


@dataclass(slots=True)
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    age: float = 0.0
    life: float = 0.5
    size: float = 3.0
    color: tuple = (255, 255, 255)
    gravity: float = 0.0
    drag: float = 0.0
    shape: str = 'square'
    layer: int = 1

    def reset(self, x, y, vx, vy, life, size, color, gravity, drag, shape, layer):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.age, self.life = 0.0, max(0.01, float(life))
        self.size, self.color = float(size), tuple(color)
        self.gravity, self.drag = float(gravity), float(drag)
        self.shape, self.layer = shape, int(layer)

    def update(self, dt):
        self.age += dt
        damping = max(0.0, 1.0 - self.drag * dt)
        self.vx *= damping
        self.vy = self.vy * damping + self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.age < self.life

    @property
    def remaining(self):
        return max(0.0, 1.0 - self.age / self.life)


class Particles:
    """Object pool of particles; legacy burst/trail calls remain supported."""

    def __init__(self, cap=400):
        self.cap = max(1, int(cap))
        self.parts = []
        self._free = []
        self.motion_scale = 1.0

    def set_reduced_motion(self, enabled):
        self.motion_scale = 0.35 if enabled else 1.0

    def _acquire(self):
        if self._free:
            return self._free.pop()
        if len(self.parts) >= self.cap:
            return self.parts.pop(0)
        return Particle()

    def _spawn(self, x, y, angle, speed, life, size, color, gravity, drag,
               shape, layer):
        particle = self._acquire()
        particle.reset(x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                       life, size, color, gravity, drag, shape, layer)
        self.parts.append(particle)

    def emit(self, effect_id, x, y, angle=0.0, spread=math.tau, count=None):
        preset = EFFECT_PRESETS[effect_id]
        total = preset['count'] if count is None else max(0, int(count))
        total = max(1, int(total * self.motion_scale)) if total else 0
        for _ in range(total):
            particle_angle = angle + random.uniform(-spread / 2, spread / 2)
            self._spawn(
                x, y, particle_angle,
                random.uniform(*preset['speed']) * self.motion_scale, random.uniform(*preset['life']),
                random.uniform(*preset['size']), random.choice(preset['colors']),
                preset['gravity'], preset['drag'], preset['shape'], preset['layer'],
            )

    def burst(self, x, y, n=10, color=(255, 255, 255), speed=160.0, life=0.5,
              size=3, grav=500.0, spread=math.tau, angle=0.0):
        total = max(0, int(n))
        total = max(1, int(total * self.motion_scale)) if total else 0
        for _ in range(total):
            particle_angle = angle + random.uniform(-spread / 2, spread / 2)
            self._spawn(x, y, particle_angle, speed * self.motion_scale * random.uniform(0.4, 1.1),
                        life * random.uniform(0.7, 1.2), size, color, grav, 0.0,
                        'square', 1)

    def trail(self, x, y, color=(255, 255, 255), n=1, life=0.3, size=4):
        self.burst(x, y, n=n, color=color, speed=30.0, life=life, size=size, grav=0.0)

    def update(self, dt):
        alive = []
        for particle in self.parts:
            if particle.update(dt):
                alive.append(particle)
            else:
                self._free.append(particle)
        self.parts = alive
        if len(self._free) > self.cap:
            del self._free[:-self.cap]

    def draw(self, surface, offset, min_layer=0, max_layer=2):
        import pygame
        ox, oy = int(offset[0]), int(offset[1])
        visible = (particle for particle in self.parts
                   if min_layer <= particle.layer <= max_layer)
        for particle in sorted(visible, key=lambda item: item.layer):
            remaining = particle.remaining
            size = max(1, int(particle.size * (0.35 + 0.65 * remaining)))
            color = tuple(max(0, min(255, int(channel * (0.45 + 0.55 * remaining))))
                          for channel in particle.color)
            x, y = int(particle.x) + ox, int(particle.y) + oy
            if particle.shape == 'circle':
                pygame.draw.circle(surface, color, (x, y), size)
            elif particle.shape == 'spark':
                length = max(size + 1, int(size * 2.5))
                speed = math.hypot(particle.vx, particle.vy) or 1.0
                end = (x - int(particle.vx / speed * length),
                       y - int(particle.vy / speed * length))
                pygame.draw.line(surface, color, (x, y), end, max(1, size // 2))
            else:
                pygame.draw.rect(surface, color,
                                 pygame.Rect(x - size // 2, y - size // 2, size, size))


class FloatTexts:
    """Damage numbers and short world-space messages."""

    def __init__(self, cap=40):
        self.cap = cap
        self.texts = []

    def add(self, x, y, text, color=(255, 255, 255), life=0.8):
        if len(self.texts) >= self.cap:
            self.texts.pop(0)
        self.texts.append([float(x), float(y - 10), str(text), color, 0.0, life])

    def update(self, dt):
        for text in self.texts:
            text[4] += dt
            text[1] -= 46.0 * dt
        self.texts = [text for text in self.texts if text[4] < text[5]]

    def draw(self, surface, offset, font):
        ox, oy = int(offset[0]), int(offset[1])
        for x, y, text, color, age, life in self.texts:
            if age / life > 0.7:
                continue
            rendered = font.render(text, True, color)
            surface.blit(rendered, (int(x) + ox - rendered.get_width() // 2,
                                    int(y) + oy))
