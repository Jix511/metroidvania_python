"""Moving traversal mechanisms independent from the static tile collision map."""

import pygame

from constants import TILE_SIZE
from world.world_data import MOVING_PLATFORMS


class MovingPlatform:
    def __init__(self, definition):
        self.id = definition['id']
        self.zone_id = definition['zone_id']
        self.axis = definition['axis']
        self.start = pygame.Vector2(definition['start'][0] * TILE_SIZE,
                                    definition['start'][1] * TILE_SIZE)
        self.end = pygame.Vector2(definition['end'][0] * TILE_SIZE,
                                  definition['end'][1] * TILE_SIZE)
        self.position = self.start.copy()
        self.speed = float(definition['speed'])
        self.direction = 1.0
        self.rect = pygame.Rect(round(self.position.x), round(self.position.y),
                                definition['width'] * TILE_SIZE, 8)
        self.delta = pygame.Vector2()

    def advance(self, dt, rider=None):
        old = self.position.copy()
        target = self.end if self.direction > 0 else self.start
        displacement = target - self.position
        distance = displacement.length()
        step = self.speed * dt
        if distance <= step:
            self.position.update(target)
            self.direction *= -1.0
        elif distance:
            displacement.scale_to_length(step)
            self.position += displacement
        self.delta = self.position - old
        old_rect = self.rect.copy()
        self.rect.topleft = (round(self.position.x), round(self.position.y))
        if (rider is not None and abs(rider.rect.bottom - old_rect.top) <= 3
                and rider.rect.right > old_rect.left and rider.rect.left < old_rect.right
                and rider.velocity.y >= 0):
            rider.rect.x += round(self.delta.x)
            rider.rect.y += round(self.delta.y)

    def catch_falling(self, rider, previous_bottom):
        if (rider.velocity.y >= 0 and previous_bottom <= self.rect.top + 6
                and rider.rect.bottom >= self.rect.top
                and rider.rect.right > self.rect.left
                and rider.rect.left < self.rect.right):
            rider.rect.bottom = self.rect.top
            rider.velocity.y = 0
            rider.on_ground = True
            if hasattr(rider, '_double_jumped'):
                rider._double_jumped = False
            return True
        return False

    def draw(self, surface, offset, active=True):
        rect = self.rect.move(round(offset[0]), round(offset[1]))
        color = (100, 205, 225) if active else (85, 90, 105)
        pygame.draw.rect(surface, (22, 28, 38), rect.inflate(4, 5), border_radius=3)
        pygame.draw.rect(surface, color, rect, border_radius=2)
        pygame.draw.line(surface, (220, 245, 255), rect.topleft, rect.topright, 2)
        for x in range(rect.left + 8, rect.right, 16):
            pygame.draw.circle(surface, (35, 65, 80), (x, rect.centery), 2)


def create_moving_platforms():
    return [MovingPlatform(definition) for definition in MOVING_PLATFORMS]
